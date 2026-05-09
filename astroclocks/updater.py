"""Online update helpers for AstroClocks Windows releases."""

from __future__ import annotations

import json
import os
import re
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


def _release_candidate(release):
    if release.get("draft") or release.get("prerelease"):
        return None

    for asset in release.get("assets", []):
        asset_name = str(asset.get("name") or "")
        match = INSTALLER_NAME_PATTERN.match(asset_name)
        installer_url = str(asset.get("browser_download_url") or "")
        if not match or not installer_url:
            continue
        version = match.group("version")
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
                "GitHub rate limit reached while checking for updates. Please try again later."
            ) from exc
        raise UpdateError(f"Update server returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise UpdateError(f"Network error while checking for updates: {exc.reason}") from exc


def fetch_latest_release(timeout=10):
    with _github_request(RELEASES_API_URL, timeout=timeout) as response:
        payload = json.load(response)

    if not isinstance(payload, list):
        raise UpdateError("Unexpected update feed format.")

    candidates = []
    for release in payload:
        candidate = _release_candidate(release)
        if candidate is not None:
            candidates.append(candidate)

    if not candidates:
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
    target_dir = Path(destination_dir or Path(tempfile.gettempdir()) / "AstroClocks-Updates")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / release.installer_name

    with _github_request(release.installer_url, timeout=timeout) as response:
        with open(target_path, "wb") as file:
            while True:
                chunk = response.read(chunk_size)
                if not chunk:
                    break
                file.write(chunk)

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
