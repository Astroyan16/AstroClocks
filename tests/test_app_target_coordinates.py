import datetime
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from astroclocks.app import AstroClocksApp
from astroclocks.i18n import translate
from astroclocks.settings import COORDINATE_SOURCE_APP, COORDINATE_SOURCE_MOUNT


class _FakeVar:
    def __init__(self, value):
        self._value = str(value)

    def get(self):
        return self._value

    def set(self, value):
        self._value = str(value)


class AppTargetCoordinateTests(unittest.TestCase):
    def setUp(self):
        self.app = AstroClocksApp.__new__(AstroClocksApp)
        self.app.language = "fr"
        self.app._tr = lambda key, **values: translate("fr", key, **values)
        self.app.latitude = 48.8566
        self.app.longitude = 2.3522
        self.app.coordinate_source = COORDINATE_SOURCE_APP
        self.app.mount_last_snapshot = None
        self.app.site_info_lines = ("cached",)
        self.app.solar_system_cache_key = ("solar",)
        self.app.sky_map_cache_key = ("sky",)
        self.app.visibility_cache_key = ("visibility",)
        self.app.target_jnow_cache_key = None
        self.app.target_jnow_cache = None
        self.app.alpha_hh = _FakeVar("12")
        self.app.alpha_mm = _FakeVar("34")
        self.app.alpha_ss = _FakeVar("56")
        self.app.delta_dd = _FakeVar("21")
        self.app.delta_mm = _FakeVar("43")
        self.app.delta_ss = _FakeVar("12")
        self.app.target_active = True
        self.app.target_solar_system_name = None

    def test_active_site_context_uses_mount_coordinates_when_requested_and_available(self):
        self.app.coordinate_source = COORDINATE_SOURCE_MOUNT
        self.app.mount_last_snapshot = SimpleNamespace(site_latitude=43.61, site_longitude=1.44)

        state = AstroClocksApp._active_site_context(self.app)

        self.assertEqual(state["requested_source"], COORDINATE_SOURCE_MOUNT)
        self.assertEqual(state["effective_source"], COORDINATE_SOURCE_MOUNT)
        self.assertEqual(state["coordinates"], (43.61, 1.44))
        self.assertFalse(state["fallback"])
        self.assertEqual(state["label"], "Monture ASCOM")

    def test_active_site_context_falls_back_to_app_coordinates_when_mount_location_is_missing(self):
        self.app.coordinate_source = COORDINATE_SOURCE_MOUNT
        self.app.mount_last_snapshot = SimpleNamespace(site_latitude=None, site_longitude=1.44)

        state = AstroClocksApp._active_site_context(self.app)

        self.assertEqual(state["requested_source"], COORDINATE_SOURCE_MOUNT)
        self.assertEqual(state["effective_source"], COORDINATE_SOURCE_APP)
        self.assertEqual(state["coordinates"], (48.8566, 2.3522))
        self.assertTrue(state["fallback"])
        self.assertIn("indisponible", state["label"])

    def test_invalidate_site_dependent_state_clears_cached_keys(self):
        AstroClocksApp._invalidate_site_dependent_state(self.app)

        self.assertIsNone(self.app.site_info_lines)
        self.assertIsNone(self.app.solar_system_cache_key)
        self.assertIsNone(self.app.sky_map_cache_key)
        self.assertIsNone(self.app.visibility_cache_key)

    def test_current_target_coordinates_reuses_jnow_cache_within_same_utc_hour(self):
        first_time = datetime.datetime(2026, 5, 26, 21, 5, tzinfo=datetime.timezone.utc)
        second_time = datetime.datetime(2026, 5, 26, 21, 59, tzinfo=datetime.timezone.utc)

        with patch(
            "astroclocks.app.j2000_to_jnow_coordinates",
            return_value=(12.75, 21.5),
        ) as mocked_convert:
            first = AstroClocksApp._current_target_coordinates(self.app, now_utc=first_time)
            second = AstroClocksApp._current_target_coordinates(self.app, now_utc=second_time)

        mocked_convert.assert_called_once()
        self.assertEqual(first, (12.75, 21.5))
        self.assertEqual(second, (12.75, 21.5))

    def test_current_target_coordinates_refreshes_jnow_cache_when_utc_hour_changes(self):
        first_time = datetime.datetime(2026, 5, 26, 21, 59, tzinfo=datetime.timezone.utc)
        second_time = datetime.datetime(2026, 5, 26, 22, 0, tzinfo=datetime.timezone.utc)

        with patch(
            "astroclocks.app.j2000_to_jnow_coordinates",
            side_effect=[(12.75, 21.5), (12.76, 21.49)],
        ) as mocked_convert:
            first = AstroClocksApp._current_target_coordinates(self.app, now_utc=first_time)
            second = AstroClocksApp._current_target_coordinates(self.app, now_utc=second_time)

        self.assertEqual(mocked_convert.call_count, 2)
        self.assertEqual(first, (12.75, 21.5))
        self.assertEqual(second, (12.76, 21.49))

    def test_current_target_jnow_coordinates_uses_dynamic_solar_target(self):
        self.app.target_solar_system_name = "Moon"
        self.app._visibility_state_at_time = lambda now_utc: ({}, 10.0)
        self.app._current_solar_system_target = (
            lambda lst_hours: {"ra_hours": 5.5, "declination": -18.25}
        )

        coordinates = AstroClocksApp._current_target_jnow_coordinates(self.app)

        self.assertEqual(coordinates, (5.5, -18.25))

    def test_current_target_jnow_coordinates_rejects_missing_dynamic_solar_target(self):
        self.app.target_solar_system_name = "Moon"
        self.app._visibility_state_at_time = lambda now_utc: ({}, 10.0)
        self.app._current_solar_system_target = lambda lst_hours: None

        with self.assertRaisesRegex(RuntimeError, "Aucune cible active"):
            AstroClocksApp._current_target_jnow_coordinates(self.app)


if __name__ == "__main__":
    unittest.main()
