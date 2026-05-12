import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from astroclocks.updater import (
    ReleaseInfo,
    UpdateError,
    _release_candidate,
    download_installer,
    fetch_latest_release,
    check_for_updates,
    compare_versions,
    parse_version,
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload
        self._offset = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, size=-1):
        if size is None or size < 0:
            size = len(self._payload) - self._offset
        chunk = self._payload[self._offset : self._offset + size]
        self._offset += len(chunk)
        return chunk


class UpdaterTests(unittest.TestCase):
    def test_parse_version_ignores_stable_suffix(self):
        self.assertEqual(parse_version("v3.3.1-stable"), (3, 3, 1))

    def test_compare_versions_handles_patch_release(self):
        self.assertGreater(compare_versions("3.3.1", "3.3"), 0)
        self.assertEqual(compare_versions("3.3.1", "3.3.1"), 0)
        self.assertLess(compare_versions("3.2.9", "3.3"), 0)

    def test_release_candidate_uses_windows_installer_asset(self):
        release = {
            "tag_name": "v3.3.1-stable",
            "name": "AstroClocks v3.3.1 stable",
            "html_url": "https://example.invalid/releases/v3.3.1-stable",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "name": "Install_AstroClocks3.3.1.exe",
                    "browser_download_url": "https://example.invalid/Install_AstroClocks3.3.1.exe",
                }
            ],
        }

        candidate = _release_candidate(release)

        self.assertIsNotNone(candidate)
        self.assertEqual(candidate.version, "3.3.1")
        self.assertEqual(candidate.installer_name, "Install_AstroClocks3.3.1.exe")

    def test_release_candidate_rejects_incoherent_release_metadata(self):
        release = {
            "tag_name": "v3.3.4-stable",
            "name": "AstroClocks v3.3.4 stable",
            "html_url": "https://example.invalid/releases/v3.3.4-stable",
            "draft": False,
            "prerelease": False,
            "assets": [
                {
                    "name": "Install_AstroClocks3.3.3.exe",
                    "browser_download_url": "https://example.invalid/Install_AstroClocks3.3.3.exe",
                }
            ],
        }

        self.assertIsNone(_release_candidate(release))

    @patch("astroclocks.updater.fetch_latest_release")
    def test_check_for_updates_reports_available_release(self, mocked_fetch_latest_release):
        mocked_fetch_latest_release.return_value = ReleaseInfo(
            version="3.3.1",
            tag_name="v3.3.1-stable",
            name="AstroClocks v3.3.1 stable",
            html_url="https://example.invalid/releases/v3.3.1-stable",
            installer_name="Install_AstroClocks3.3.1.exe",
            installer_url="https://example.invalid/Install_AstroClocks3.3.1.exe",
        )

        result = check_for_updates("3.3")

        self.assertTrue(result.update_available)
        self.assertEqual(result.current_version, "3.3")
        self.assertEqual(result.latest_release.version, "3.3.1")

    @patch("astroclocks.updater._github_request")
    def test_fetch_latest_release_rejects_invalid_json(self, mocked_request):
        mocked_request.return_value = _FakeResponse(b"{invalid")

        with self.assertRaisesRegex(UpdateError, "invalid JSON"):
            fetch_latest_release()

    @patch("astroclocks.updater._github_request")
    def test_fetch_latest_release_reports_incoherent_windows_release(self, mocked_request):
        payload = b"""
        [
          {
            "tag_name": "v3.3.4-stable",
            "name": "AstroClocks v3.3.4 stable",
            "html_url": "https://example.invalid/releases/v3.3.4-stable",
            "draft": false,
            "prerelease": false,
            "assets": [
              {
                "name": "Install_AstroClocks3.3.3.exe",
                "browser_download_url": "https://example.invalid/Install_AstroClocks3.3.3.exe"
              }
            ]
          }
        ]
        """
        mocked_request.return_value = _FakeResponse(payload)

        with self.assertRaisesRegex(UpdateError, "incoherent Windows release metadata"):
            fetch_latest_release()

    @patch("astroclocks.updater._github_request")
    def test_fetch_latest_release_prefers_valid_candidate_when_feed_contains_invalid_one(
        self, mocked_request
    ):
        payload = b"""
        [
          {
            "tag_name": "v3.3.4-stable",
            "name": "AstroClocks v3.3.4 stable",
            "html_url": "https://example.invalid/releases/v3.3.4-stable",
            "draft": false,
            "prerelease": false,
            "assets": [
              {
                "name": "Install_AstroClocks3.3.3.exe",
                "browser_download_url": "https://example.invalid/Install_AstroClocks3.3.3.exe"
              }
            ]
          },
          {
            "tag_name": "v3.3.5-stable",
            "name": "AstroClocks v3.3.5 stable",
            "html_url": "https://example.invalid/releases/v3.3.5-stable",
            "draft": false,
            "prerelease": false,
            "assets": [
              {
                "name": "Install_AstroClocks3.3.5.exe",
                "browser_download_url": "https://example.invalid/Install_AstroClocks3.3.5.exe"
              }
            ]
          }
        ]
        """
        mocked_request.return_value = _FakeResponse(payload)

        candidate = fetch_latest_release()

        self.assertEqual(candidate.version, "3.3.5")
        self.assertEqual(candidate.installer_name, "Install_AstroClocks3.3.5.exe")

    @patch("astroclocks.updater._github_request")
    def test_download_installer_rejects_empty_download(self, mocked_request):
        mocked_request.return_value = _FakeResponse(b"")
        release = ReleaseInfo(
            version="3.3.5",
            tag_name="v3.3.5-stable",
            name="AstroClocks v3.3.5 stable",
            html_url="https://example.invalid/releases/v3.3.5-stable",
            installer_name="Install_AstroClocks3.3.5.exe",
            installer_url="https://example.invalid/Install_AstroClocks3.3.5.exe",
        )

        with TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(UpdateError, "Downloaded installer is empty"):
                download_installer(release, destination_dir=temp_dir)
            self.assertFalse(
                Path(temp_dir, "Install_AstroClocks3.3.5.exe.part").exists()
            )

    def test_download_installer_rejects_invalid_metadata(self):
        release = ReleaseInfo(
            version="3.3.5",
            tag_name="v3.3.5-stable",
            name="AstroClocks v3.3.5 stable",
            html_url="https://example.invalid/releases/v3.3.5-stable",
            installer_name="AstroClocks.zip",
            installer_url="https://example.invalid/AstroClocks.zip",
        )

        with TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(UpdateError, "Installer metadata is invalid"):
                download_installer(release, destination_dir=temp_dir)


if __name__ == "__main__":
    unittest.main()
