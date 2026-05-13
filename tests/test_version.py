import unittest

from astroclocks.version import (
    APP_EXECUTABLE_NAME,
    APP_EXECUTABLE_STEM,
    APP_VERSION,
    installer_name,
)


class VersionMetadataTests(unittest.TestCase):
    def test_executable_name_matches_stem(self):
        self.assertEqual(APP_EXECUTABLE_NAME, f"{APP_EXECUTABLE_STEM}.exe")

    def test_installer_name_remains_versioned(self):
        self.assertEqual(installer_name(), f"Install_AstroClocks{APP_VERSION}.exe")


if __name__ == "__main__":
    unittest.main()
