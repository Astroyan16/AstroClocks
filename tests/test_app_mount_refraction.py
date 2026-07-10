import unittest
from types import SimpleNamespace
from unittest.mock import patch

from astroclocks.app import AstroClocksApp
from astroclocks import ascom_mount
from astroclocks.settings import (
    ATMOSPHERIC_REFRACTION_BENNETT,
    ATMOSPHERIC_REFRACTION_NONE,
    ATMOSPHERIC_REFRACTION_SAEMUNDSSON,
    ATMOSPHERIC_REFRACTION_SOFA,
    MOUNT_REFRACTION_SOURCE_APP,
    MOUNT_REFRACTION_SOURCE_AUTO,
    MOUNT_REFRACTION_SOURCE_DRIVER,
)


class MountRefractionTests(unittest.TestCase):
    def test_disabled_model_keeps_equatorial_coordinates_unchanged(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.mount_refraction_model = ATMOSPHERIC_REFRACTION_NONE

        coordinates = AstroClocksApp._apply_mount_refraction_to_equatorial(
            app,
            12.5,
            42.0,
            lst_hours=13.0,
        )

        self.assertEqual(coordinates, (12.5, 42.0))

    def test_current_pointing_coordinates_apply_refraction_to_target(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.mount_refraction_model = ATMOSPHERIC_REFRACTION_BENNETT
        app.target_active = True
        app.target_solar_system_name = None
        app._current_target_coordinates = lambda now_utc=None: (12.5, 42.0)
        app._visibility_state_at_time = lambda now_utc: ({}, 13.0)

        def apply_refraction(
            ra_hours,
            declination,
            lst_hours=None,
            mount_snapshot=None,
        ):
            self.assertEqual((ra_hours, declination, lst_hours), (12.5, 42.0, 13.0))
            self.assertIsNone(mount_snapshot)
            return 12.49, 42.12

        app._apply_mount_refraction_to_equatorial = apply_refraction

        coordinates = AstroClocksApp._current_pointing_jnow_coordinates(app)

        self.assertEqual(coordinates, (12.49, 42.12))

    def test_mount_refraction_is_not_applied_when_ascom_already_applies_it(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.mount_refraction_model = ATMOSPHERIC_REFRACTION_BENNETT
        app.mount_last_snapshot = SimpleNamespace(does_refraction=True)
        app._equatorial_to_horizontal = lambda *args: self.fail(
            "Unexpected local refraction calculation"
        )

        coordinates = AstroClocksApp._apply_mount_refraction_to_equatorial(
            app,
            12.5,
            42.0,
            lst_hours=13.0,
        )

        self.assertEqual(coordinates, (12.5, 42.0))

    def test_mount_refraction_is_not_applied_when_ascom_state_is_unknown(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.mount_refraction_model = ATMOSPHERIC_REFRACTION_BENNETT
        app.mount_last_snapshot = SimpleNamespace(does_refraction=None)
        app._equatorial_to_horizontal = lambda *args: self.fail(
            "Unexpected local refraction calculation"
        )

        coordinates = AstroClocksApp._apply_mount_refraction_to_equatorial(
            app,
            12.5,
            42.0,
            lst_hours=13.0,
        )

        self.assertEqual(coordinates, (12.5, 42.0))

    def test_refraction_source_policy_can_override_ascom_state(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        snapshot = SimpleNamespace(does_refraction=True)

        app.mount_refraction_source = MOUNT_REFRACTION_SOURCE_AUTO
        self.assertFalse(AstroClocksApp._should_apply_local_mount_refraction(app, snapshot))

        app.mount_refraction_source = MOUNT_REFRACTION_SOURCE_APP
        self.assertTrue(AstroClocksApp._should_apply_local_mount_refraction(app, snapshot))

        app.mount_refraction_source = MOUNT_REFRACTION_SOURCE_DRIVER
        self.assertFalse(AstroClocksApp._should_apply_local_mount_refraction(app, snapshot))

    def test_clock_state_uses_refraction_corrected_pointing_coordinates(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app._current_pointing_coordinate_fields = (
            lambda now_utc=None: (11, 59, 30, 42, 7, 12)
        )
        captured = {}

        def clock_state(now_utc=None, alpha_fields=(0, 0, 0)):
            captured["alpha_fields"] = alpha_fields
            return {"hour_angle": "corrected"}

        app._clock_state_at_time = clock_state

        state = AstroClocksApp._compute_target_clock_state(app)

        self.assertEqual(state["hour_angle"], "corrected")
        self.assertEqual(captured["alpha_fields"], (11, 59, 30))

    def test_goto_coordinates_use_refraction_corrected_pointing_coordinates(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.target_active = True
        app.mount_last_snapshot = SimpleNamespace(
            equatorial_system=ascom_mount.EQUATORIAL_SYSTEM_TOPOCENTRIC
        )
        app._mount_frame_supports_goto = lambda snapshot: True
        app._current_pointing_jnow_coordinates = lambda now_utc=None: (12.49, 42.12)

        coordinates = AstroClocksApp._current_target_mount_coordinates(app)

        self.assertEqual(coordinates, (12.49, 42.12))

    def test_j2000_goto_conversion_uses_refraction_corrected_jnow_coordinates(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.target_active = True
        app.mount_last_snapshot = SimpleNamespace(
            equatorial_system=ascom_mount.EQUATORIAL_SYSTEM_J2000
        )
        app._mount_frame_supports_goto = lambda snapshot: True
        app._current_pointing_jnow_coordinates = lambda now_utc=None: (12.49, 42.12)

        with patch(
            "astroclocks.app.jnow_to_j2000_coordinates",
            return_value=(12.45, 42.08),
        ) as mocked_convert:
            coordinates = AstroClocksApp._current_target_mount_coordinates(app)

        mocked_convert.assert_called_once()
        self.assertEqual(mocked_convert.call_args.args[:2], (12.49, 42.12))
        self.assertEqual(coordinates, (12.45, 42.08))

    def test_bennett_model_raises_altitude_before_reconverting(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.mount_refraction_model = ATMOSPHERIC_REFRACTION_BENNETT
        app.refraction_pressure_hpa = 1010.0
        app.refraction_temperature_c = 10.0
        captured = {}
        app._equatorial_to_horizontal = lambda ra, dec, lst: (15.0, 180.0, 1.0)

        def horizontal_to_equatorial(altitude, azimuth, lst_hours):
            captured["altitude"] = altitude
            captured["azimuth"] = azimuth
            captured["lst_hours"] = lst_hours
            return 12.49, 42.12, 1.1

        app._horizontal_to_equatorial = horizontal_to_equatorial

        coordinates = AstroClocksApp._apply_mount_refraction_to_equatorial(
            app,
            12.5,
            42.0,
            lst_hours=13.0,
        )

        self.assertEqual(coordinates, (12.49, 42.12))
        self.assertGreater(captured["altitude"], 15.0)
        self.assertEqual(captured["azimuth"], 180.0)
        self.assertEqual(captured["lst_hours"], 13.0)

    def test_atmosphere_parameters_scale_refraction(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.refraction_pressure_hpa = 505.0
        app.refraction_temperature_c = 10.0

        scaled = AstroClocksApp._atmospheric_refraction_degrees(
            app,
            15.0,
            ATMOSPHERIC_REFRACTION_BENNETT,
        )

        app.refraction_pressure_hpa = 1010.0
        standard = AstroClocksApp._atmospheric_refraction_degrees(
            app,
            15.0,
            ATMOSPHERIC_REFRACTION_BENNETT,
        )
        self.assertAlmostEqual(scaled, standard / 2, places=8)

    def test_sofa_model_uses_humidity_and_wavelength(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.refraction_pressure_hpa = 1013.25
        app.refraction_temperature_c = 15.0
        app.refraction_altitude_m = 0.0
        app.refraction_humidity_percent = 0.0
        app.refraction_wavelength_nm = 400.0

        dry_blue = AstroClocksApp._atmospheric_refraction_degrees(
            app,
            30.0,
            ATMOSPHERIC_REFRACTION_SOFA,
        )
        app.refraction_humidity_percent = 100.0
        humid_blue = AstroClocksApp._atmospheric_refraction_degrees(
            app,
            30.0,
            ATMOSPHERIC_REFRACTION_SOFA,
        )
        app.refraction_wavelength_nm = 900.0
        humid_infrared = AstroClocksApp._atmospheric_refraction_degrees(
            app,
            30.0,
            ATMOSPHERIC_REFRACTION_SOFA,
        )

        self.assertGreater(dry_blue, humid_blue)
        self.assertNotAlmostEqual(humid_blue, humid_infrared, places=9)

    def test_zero_pressure_uses_standard_sea_level_pressure_and_site_altitude(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.refraction_pressure_hpa = 0.0
        app.refraction_altitude_m = 0.0

        sea_level_pressure = AstroClocksApp._effective_refraction_pressure_hpa(app)

        app.refraction_altitude_m = 2000.0
        mountain_pressure = AstroClocksApp._effective_refraction_pressure_hpa(app)
        self.assertAlmostEqual(sea_level_pressure, 1013.25, places=2)
        self.assertLess(mountain_pressure, sea_level_pressure)

    def test_weather_station_pressure_is_reduced_from_sea_level_to_site_altitude(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.refraction_pressure_hpa = 1013.25
        app.refraction_altitude_m = 0.0

        sea_level_site_pressure = AstroClocksApp._effective_refraction_pressure_hpa(app)

        app.refraction_altitude_m = 2000.0
        mountain_site_pressure = AstroClocksApp._effective_refraction_pressure_hpa(app)
        self.assertLess(mountain_site_pressure, sea_level_site_pressure)

    def test_models_do_not_correct_below_supported_horizon_band(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.mount_refraction_model = ATMOSPHERIC_REFRACTION_SAEMUNDSSON
        app._equatorial_to_horizontal = lambda ra, dec, lst: (-2.0, 180.0, 1.0)
        app._horizontal_to_equatorial = (
            lambda altitude, azimuth, lst_hours: self.fail("Unexpected reconversion")
        )

        coordinates = AstroClocksApp._apply_mount_refraction_to_equatorial(
            app,
            12.5,
            42.0,
            lst_hours=13.0,
        )

        self.assertEqual(coordinates, (12.5, 42.0))


if __name__ == "__main__":
    unittest.main()
