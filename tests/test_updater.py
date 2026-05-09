import unittest
from unittest.mock import patch

from astroclocks.updater import (
    ReleaseInfo,
    _release_candidate,
    check_for_updates,
    compare_versions,
    parse_version,
)


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


if __name__ == "__main__":
    unittest.main()
