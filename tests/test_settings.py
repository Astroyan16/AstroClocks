import unittest

from astroclocks.settings import (
    AppSettings,
    COORDINATE_SOURCE_APP,
    COORDINATE_SOURCE_MOUNT,
    normalize_settings,
)


class SettingsTests(unittest.TestCase):
    def test_normalize_settings_keeps_valid_coordinate_source(self):
        settings = normalize_settings(
            AppSettings(coordinate_source=COORDINATE_SOURCE_MOUNT)
        )
        self.assertEqual(settings.coordinate_source, COORDINATE_SOURCE_MOUNT)

    def test_normalize_settings_falls_back_for_invalid_coordinate_source(self):
        settings = normalize_settings(AppSettings(coordinate_source="invalid"))
        self.assertEqual(settings.coordinate_source, COORDINATE_SOURCE_APP)


if __name__ == "__main__":
    unittest.main()
