import unittest

from astroclocks.settings import (
    ATMOSPHERIC_REFRACTION_BENNETT,
    ATMOSPHERIC_REFRACTION_HOHENKERK_SINCLAIR,
    ATMOSPHERIC_REFRACTION_NONE,
    ATMOSPHERIC_REFRACTION_SOFA,
    AppSettings,
    COORDINATE_SOURCE_APP,
    COORDINATE_SOURCE_MOUNT,
    DEFAULT_REFRACTION_STATION_RADIUS_KM,
    REFRACTION_STATION_RADIUS_OPTIONS_KM,
    MOUNT_REFRACTION_SOURCE_APP,
    MOUNT_REFRACTION_SOURCE_AUTO,
    MOUNT_REFRACTION_SOURCE_DRIVER,
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

    def test_normalize_settings_keeps_valid_mount_refraction_model(self):
        settings = normalize_settings(
            AppSettings(mount_refraction_model=ATMOSPHERIC_REFRACTION_BENNETT)
        )
        self.assertEqual(settings.mount_refraction_model, ATMOSPHERIC_REFRACTION_BENNETT)

    def test_normalize_settings_keeps_sofa_refraction_model(self):
        settings = normalize_settings(
            AppSettings(mount_refraction_model=ATMOSPHERIC_REFRACTION_SOFA)
        )
        self.assertEqual(settings.mount_refraction_model, ATMOSPHERIC_REFRACTION_SOFA)

    def test_normalize_settings_keeps_hohenkerk_sinclair_refraction_model(self):
        settings = normalize_settings(
            AppSettings(mount_refraction_model=ATMOSPHERIC_REFRACTION_HOHENKERK_SINCLAIR)
        )
        self.assertEqual(
            settings.mount_refraction_model, ATMOSPHERIC_REFRACTION_HOHENKERK_SINCLAIR
        )

    def test_normalize_settings_falls_back_for_invalid_mount_refraction_model(self):
        settings = normalize_settings(AppSettings(mount_refraction_model="invalid"))
        self.assertEqual(settings.mount_refraction_model, ATMOSPHERIC_REFRACTION_NONE)

    def test_normalize_settings_keeps_refraction_source(self):
        for source in (
            MOUNT_REFRACTION_SOURCE_AUTO,
            MOUNT_REFRACTION_SOURCE_APP,
            MOUNT_REFRACTION_SOURCE_DRIVER,
        ):
            with self.subTest(source=source):
                settings = normalize_settings(AppSettings(mount_refraction_source=source))
                self.assertEqual(settings.mount_refraction_source, source)

    def test_normalize_settings_falls_back_for_invalid_refraction_source(self):
        settings = normalize_settings(AppSettings(mount_refraction_source="invalid"))
        self.assertEqual(settings.mount_refraction_source, MOUNT_REFRACTION_SOURCE_AUTO)

    def test_normalize_settings_clamps_refraction_atmosphere_parameters(self):
        settings = normalize_settings(
            AppSettings(
                refraction_pressure_hpa=1200,
                refraction_temperature_c=-120,
                refraction_altitude_m=10000,
                refraction_humidity_percent=120,
                refraction_wavelength_nm=100,
            )
        )
        self.assertEqual(settings.refraction_pressure_hpa, 1100)
        self.assertEqual(settings.refraction_temperature_c, -80)
        self.assertEqual(settings.refraction_altitude_m, 9000)
        self.assertEqual(settings.refraction_humidity_percent, 100)
        self.assertEqual(settings.refraction_wavelength_nm, 200)

    def test_normalize_settings_keeps_valid_refraction_station_radius(self):
        settings = normalize_settings(AppSettings(refraction_station_radius_km=10))
        self.assertEqual(settings.refraction_station_radius_km, 10)

    def test_refraction_station_radius_includes_rural_search_ranges(self):
        self.assertEqual(DEFAULT_REFRACTION_STATION_RADIUS_KM, 50)
        self.assertTrue({50, 100, 150}.issubset(REFRACTION_STATION_RADIUS_OPTIONS_KM))

    def test_normalize_settings_falls_back_for_invalid_refraction_station_radius(self):
        settings = normalize_settings(AppSettings(refraction_station_radius_km=12))
        self.assertEqual(
            settings.refraction_station_radius_km,
            DEFAULT_REFRACTION_STATION_RADIUS_KM,
        )


if __name__ == "__main__":
    unittest.main()
