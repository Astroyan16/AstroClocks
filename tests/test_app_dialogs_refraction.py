import datetime
import unittest

from astroclocks.app_dialogs import (
    _refraction_parameter_config,
    _refraction_station_cache_key,
    _refraction_station_cache_is_valid,
)
from astroclocks.settings import (
    ATMOSPHERIC_REFRACTION_BENNETT,
    ATMOSPHERIC_REFRACTION_HOHENKERK_SINCLAIR,
    ATMOSPHERIC_REFRACTION_NONE,
    ATMOSPHERIC_REFRACTION_SAEMUNDSSON,
    ATMOSPHERIC_REFRACTION_SOFA,
)


class RefractionParameterStateTests(unittest.TestCase):
    def test_disabled_model_disables_all_refraction_parameters(self):
        config = _refraction_parameter_config(ATMOSPHERIC_REFRACTION_NONE)

        self.assertFalse(config["common_enabled"])
        self.assertFalse(config["sofa_enabled"])
        self.assertFalse(config["weather_enabled"])

    def test_simple_models_enable_only_common_parameters(self):
        for model in (
            ATMOSPHERIC_REFRACTION_BENNETT,
            ATMOSPHERIC_REFRACTION_SAEMUNDSSON,
        ):
            with self.subTest(model=model):
                config = _refraction_parameter_config(model)
                self.assertTrue(config["common_enabled"])
                self.assertFalse(config["sofa_enabled"])
                self.assertTrue(config["weather_enabled"])

    def test_sofa_model_enables_all_parameters(self):
        config = _refraction_parameter_config(ATMOSPHERIC_REFRACTION_SOFA)

        self.assertTrue(config["common_enabled"])
        self.assertTrue(config["sofa_enabled"])
        self.assertTrue(config["weather_enabled"])

    def test_hohenkerk_sinclair_model_enables_all_parameters(self):
        config = _refraction_parameter_config(ATMOSPHERIC_REFRACTION_HOHENKERK_SINCLAIR)

        self.assertTrue(config["common_enabled"])
        self.assertTrue(config["sofa_enabled"])
        self.assertTrue(config["weather_enabled"])

    def test_station_cache_key_is_stable_for_display_precision(self):
        self.assertEqual(
            _refraction_station_cache_key(48.8050000001, 2.2300600001, 20),
            _refraction_station_cache_key(48.805, 2.23006, 20),
        )

    def test_station_cache_key_changes_for_site_or_radius(self):
        key = _refraction_station_cache_key(48.805, 2.23006, 20)
        self.assertNotEqual(key, _refraction_station_cache_key(48.806, 2.23006, 20))
        self.assertNotEqual(key, _refraction_station_cache_key(48.805, 2.23006, 10))

    def test_station_cache_expires_after_ten_minutes(self):
        now = datetime.datetime(2026, 7, 10, 12, tzinfo=datetime.timezone.utc)
        key = _refraction_station_cache_key(48.805, 2.23006, 20)
        cache = {"key": key, "stations": [{"station_id": "LFPV"}], "created_at": now}

        self.assertTrue(
            _refraction_station_cache_is_valid(
                cache, key, now=now + datetime.timedelta(minutes=9, seconds=59)
            )
        )
        self.assertFalse(
            _refraction_station_cache_is_valid(
                cache, key, now=now + datetime.timedelta(minutes=10, seconds=1)
            )
        )


if __name__ == "__main__":
    unittest.main()
