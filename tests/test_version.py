import unittest
from pathlib import Path

from astroclocks.version import (
    APP_EXECUTABLE_NAME,
    APP_EXECUTABLE_STEM,
    APP_VERSION,
    installer_name,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class VersionMetadataTests(unittest.TestCase):
    def test_executable_name_matches_stem(self):
        self.assertEqual(APP_EXECUTABLE_NAME, f"{APP_EXECUTABLE_STEM}.exe")

    def test_installer_name_remains_versioned(self):
        self.assertEqual(installer_name(), f"Install_AstroClocks{APP_VERSION}.exe")

    def test_pyproject_version_matches_runtime_metadata(self):
        pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn(f'version = "{APP_VERSION}"', pyproject)

    def test_inno_setup_metadata_matches_runtime_metadata(self):
        installer_script = (PROJECT_ROOT / "AstroClocks-v3.3.iss").read_text(
            encoding="utf-8"
        )
        self.assertIn(f'#define MyAppVersion "{APP_VERSION}"', installer_script)
        self.assertIn(
            f'#define MyAppExeName "{APP_EXECUTABLE_NAME}"',
            installer_script,
        )
        self.assertIn(
            f'#define MyAppSourceDir "output\\{APP_EXECUTABLE_STEM}"',
            installer_script,
        )
        self.assertIn(
            f"OutputBaseFilename={installer_name()[:-4]}",
            installer_script,
        )


if __name__ == "__main__":
    unittest.main()
