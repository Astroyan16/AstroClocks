"""Online update helpers for AstroClocks Windows releases."""

from __future__ import annotations

import json
import os
import re
import socket
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from astroclocks.version import INSTALLER_NAME_PREFIX, UPDATE_REPOSITORY


RELEASES_API_URL = f"https://api.github.com/repos/{UPDATE_REPOSITORY}/releases"
INSTALLER_NAME_PATTERN = re.compile(
    rf"^{re.escape(INSTALLER_NAME_PREFIX)}(?P<version>\d+(?:\.\d+){{1,3}})\.exe$",
    re.IGNORECASE,
)
VERSION_PATTERN = re.compile(r"(?P<version>\d+(?:\.\d+){1,3})")
USER_AGENT = "AstroClocks-Updater"


class UpdateError(RuntimeError):
    """Raised when update metadata or installer download fails."""


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag_name: str
    name: str
    html_url: str
    installer_name: str
    installer_url: str


@dataclass(frozen=True)
class UpdateCheckResult:
    current_version: str
    latest_release: ReleaseInfo
    update_available: bool


def _extract_version(text):
    match = VERSION_PATTERN.search(str(text or ""))
    return match.group("version") if match else None


def parse_version(version):
    normalized = _extract_version(version)
    if normalized is None:
        raise UpdateError(f"Invalid version string: {version}")
    return tuple(int(part) for part in normalized.split("."))


def compare_versions(left, right):
    left_parts = parse_version(left)
    right_parts = parse_version(right)
    max_length = max(len(left_parts), len(right_parts))
    padded_left = left_parts + (0,) * (max_length - len(left_parts))
    padded_right = right_parts + (0,) * (max_length - len(right_parts))
    if padded_left < padded_right:
        return -1
    if padded_left > padded_right:
        return 1
    return 0


def _public_release(release):
    return not release.get("draft") and not release.get("prerelease")


def _release_declared_versions(release):
    versions = []
    for value in (release.get("tag_name"), release.get("name")):
        version = _extract_version(value)
        if version and version not in versions:
            versions.append(version)
    return versions


def _release_metadata_is_coherent(release, asset_version):
    declared_versions = _release_declared_versions(release)
    if not declared_versions:
        return True
    return all(compare_versions(version, asset_version) == 0 for version in declared_versions)


def _release_has_windows_installer_asset(release):
    if not _public_release(release):
        return False
    for asset in release.get("assets", []):
        asset_name = str(asset.get("name") or "")
        if INSTALLER_NAME_PATTERN.match(asset_name):
            return True
    return False


def _release_candidate(release):
    if not _public_release(release):
        return None

    for asset in release.get("assets", []):
        asset_name = str(asset.get("name") or "")
        match = INSTALLER_NAME_PATTERN.match(asset_name)
        installer_url = str(asset.get("browser_download_url") or "")
        if not match or not installer_url:
            continue
        version = match.group("version")
        if not _release_metadata_is_coherent(release, version):
            continue
        return ReleaseInfo(
            version=version,
            tag_name=str(release.get("tag_name") or ""),
            name=str(release.get("name") or ""),
            html_url=str(release.get("html_url") or ""),
            installer_name=asset_name,
            installer_url=installer_url,
        )

    fallback_version = _extract_version(release.get("tag_name")) or _extract_version(
        release.get("name")
    )
    if fallback_version is None:
        return None

    return None


def _github_request(url, timeout):
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        return urlopen(request, timeout=timeout)
    except HTTPError as exc:
        if exc.code == 404:
            raise UpdateError(
                "Update feed unavailable. GitHub releases may be private or missing."
            ) from exc
        if exc.code == 403:
            raise UpdateError(
                "GitHub rate limit reached while accessing the update server. Please try again later."
            ) from exc
        raise UpdateError(f"Update server returned HTTP {exc.code}.") from exc
    except TimeoutError as exc:
        raise UpdateError("Update request timed out.") from exc
    except socket.timeout as exc:
        raise UpdateError("Update request timed out.") from exc
    except URLError as exc:
        if isinstance(exc.reason, (TimeoutError, socket.timeout)):
            raise UpdateError("Update request timed out.") from exc
        raise UpdateError(f"Network error while accessing the update server: {exc.reason}") from exc


def _read_json_response(response):
    try:
        payload_bytes = response.read()
    except OSError as exc:
        raise UpdateError(f"Unable to read the update feed: {exc}") from exc

    try:
        payload_text = payload_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise UpdateError("Update feed returned unreadable data.") from exc

    try:
        return json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise UpdateError("Update feed returned invalid JSON.") from exc


def _validate_release_info(release):
    if not isinstance(release, ReleaseInfo):
        raise UpdateError("Installer metadata is invalid.")
    if not INSTALLER_NAME_PATTERN.match(str(release.installer_name or "")):
        raise UpdateError("Installer metadata is invalid.")
    if not str(release.installer_url or "").strip():
        raise UpdateError("Installer metadata is invalid.")
    installer_version = _extract_version(release.installer_name)
    if installer_version is None or compare_versions(release.version, installer_version) != 0:
        raise UpdateError("Installer metadata is invalid.")


def fetch_latest_release(timeout=10):
    with _github_request(RELEASES_API_URL, timeout=timeout) as response:
        payload = _read_json_response(response)

    if not isinstance(payload, list):
        raise UpdateError("Unexpected update feed format.")

    candidates = []
    saw_incoherent_windows_release = False
    for release in payload:
        candidate = _release_candidate(release)
        if candidate is not None:
            candidates.append(candidate)
        elif _release_has_windows_installer_asset(release):
            saw_incoherent_windows_release = True

    if not candidates:
        if saw_incoherent_windows_release:
            raise UpdateError("Update feed contains incoherent Windows release metadata.")
        raise UpdateError("No installable public Windows release was found.")

    return max(candidates, key=lambda candidate: parse_version(candidate.version))


def check_for_updates(current_version, timeout=10):
    normalized_current = _extract_version(current_version)
    if normalized_current is None:
        raise UpdateError(f"Invalid current version: {current_version}")

    latest_release = fetch_latest_release(timeout=timeout)
    return UpdateCheckResult(
        current_version=normalized_current,
        latest_release=latest_release,
        update_available=compare_versions(latest_release.version, normalized_current) > 0,
    )


def download_installer(release, destination_dir=None, timeout=30, chunk_size=1024 * 128):
    _validate_release_info(release)
    target_dir = Path(destination_dir or Path(tempfile.gettempdir()) / "AstroClocks-Updates")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / release.installer_name
    temp_path = target_path.with_suffix(f"{target_path.suffix}.part")

    with _github_request(release.installer_url, timeout=timeout) as response:
        with open(temp_path, "wb") as file:
            wrote_bytes = 0
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                file.write(chunk)
                wrote_bytes += len(chunk)

    if wrote_bytes <= 0:
        try:
            temp_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise UpdateError("Downloaded installer is empty.")

    temp_path.replace(target_path)

    return target_path


def launch_installer(installer_path):
    installer_path = Path(installer_path)
    if not installer_path.exists():
        raise UpdateError(f"Installer not found: {installer_path}")

    try:
        os.startfile(str(installer_path))
    except AttributeError:
        subprocess.Popen([str(installer_path)])
    except OSError as exc:
        raise UpdateError(f"Unable to launch installer: {exc}") from exc
