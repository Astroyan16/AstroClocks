import unittest
from unittest.mock import Mock, patch

from astroclocks.app_object_search import (
    search_coordinates,
    _apply_coordinate_result,
    _coordinate_result_message,
    _with_search_fallback,
    _target_information_text,
)
from astroclocks.i18n import translate
from astroclocks.local_object_catalog import resolve_local_object_coordinates
from types import SimpleNamespace


class _FakeEntry:
    def __init__(self, value=""):
        self._value = value

    def get(self):
        return self._value


class ObjectSearchTargetModeTests(unittest.TestCase):
    def _app_stub(self):
        app = type("Stub", (), {})()
        app.search_entry = _FakeEntry("Lune")
        app.target_display_name = ""
        app.target_solar_system_name = None
        app.visibility_start_date = "existing"
        app._update_visibility_date_label = lambda: None
        app._set_coordinate_fields_calls = []
        app._set_coordinate_fields = (
            lambda ra_hours, dec_degrees, frame="j2000": app._set_coordinate_fields_calls.append(
                (ra_hours, dec_degrees, frame)
            )
        )
        app.update_value_calls = []
        app.update_value = lambda preserve_solar_target=False: app.update_value_calls.append(
            preserve_solar_target
        )
        app._set_result_text_calls = []
        app._set_result_text = lambda text, foreground=None: app._set_result_text_calls.append(
            (text, foreground)
        )
        app._current_target_status_color = lambda: "#7bd88f"
        app._tr = lambda key, **values: f"{key}|{values}"
        app._coordinate_result_message = (
            lambda result: f"{result.get('source')}|{result.get('source_ra')}|{result.get('source_dec')}"
        )
        return app

    def test_imcce_search_still_runs_when_cds_is_down(self):
        app = self._app_stub()
        app.service_status = {"imcce": True, "sesame": False, "simbad": False}
        app.network_online = True
        app.search_entry = _FakeEntry("Ceres")
        app.coordinate_search_pending = False
        app._selected_object_type_code = lambda: "Asteroid"
        app._active_site_coordinates = lambda: (48.8, 2.2)
        app._start_coordinate_search = Mock()
        with patch("astroclocks.app_object_search.resolve_local_solar_system_coordinates", return_value=None):
            search_coordinates(app)
        app._start_coordinate_search.assert_called_once_with("Asteroid", "Ceres", fallback_result=None)

    def test_sesame_search_still_runs_when_imcce_is_down(self):
        app = self._app_stub()
        app.service_status = {"imcce": False, "sesame": True}
        app.network_online = True
        app.search_entry = _FakeEntry("unknown distant star")
        app.coordinate_search_pending = False
        app._selected_object_type_code = lambda: "Star, Deep Sky Object"
        app._active_site_coordinates = lambda: (48.8, 2.2)
        app._start_coordinate_search = Mock()
        with patch("astroclocks.app_object_search.resolve_local_solar_system_coordinates", return_value=None), patch(
            "astroclocks.app_object_search.resolve_local_object_coordinates", return_value=None
        ):
            search_coordinates(app)
        app._start_coordinate_search.assert_called_once_with("Star, Deep Sky Object", "unknown distant star", fallback_result=None)

    def test_with_search_fallback_marks_copy_without_mutating_original(self):
        original = {"source": "local", "source_ra": "12:34:56"}

        fallback = _with_search_fallback(original, "error")

        self.assertIsNot(fallback, original)
        self.assertEqual(fallback["_search_fallback_reason"], "error")
        self.assertNotIn("_search_fallback_reason", original)

    def test_imcce_result_keeps_online_coordinates_and_disables_local_solar_tracking(self):
        app = self._app_stub()
        result = {
            "source": "imcce",
            "display_name": "Moon",
            "solar_system_name": "Moon",
            "source_ra": "12:34:56",
            "source_dec": "+12:34:56",
            "alpha_hh": 12,
            "alpha_mm": 34,
            "alpha_ss": "56",
            "delta_dd": 12,
            "delta_mm": 34,
            "delta_ss": "56",
        }

        _apply_coordinate_result(app, result)

        self.assertEqual(app.target_display_name, "Moon")
        self.assertIsNone(app.target_solar_system_name)
        self.assertEqual(app.update_value_calls, [False])
        self.assertEqual(app._set_coordinate_fields_calls[0][2], "jnow")

    def test_local_solar_result_preserves_dynamic_solar_tracking(self):
        app = self._app_stub()
        result = {
            "source": "local_solar",
            "display_name": "Moon",
            "solar_system_name": "Moon",
            "source_ra": "12:34:56",
            "source_dec": "+12:34:56",
            "alpha_hh": 12,
            "alpha_mm": 34,
            "alpha_ss": "56",
            "delta_dd": 12,
            "delta_mm": 34,
            "delta_ss": "56",
        }

        _apply_coordinate_result(app, result)

        self.assertEqual(app.target_solar_system_name, "Moon")
        self.assertEqual(app.update_value_calls, [True])
        self.assertEqual(app._set_coordinate_fields_calls[0][2], "jnow")

    def test_coordinate_result_message_mentions_local_fallback_after_online_error(self):
        app = type("Stub", (), {})()
        app._tr = lambda key, **values: {
            "result.local_coordinates": "Local coordinates",
            "result.local_fallback_error": "Local fallback used",
            "result.info_unknown": "Not available",
            "result.source.local_solar": "Astropy",
            "result.target_information": "Magnitude: {magnitude}\nType: {object_type}\nData source: {source}",
        }[key].format(**values)
        result = {
            "source": "local",
            "source_catalog": "Messier",
            "source_note": "",
            "source_ra": "12:34:56",
            "source_dec": "+12:34:56",
            "_search_fallback_reason": "error",
        }

        message = _coordinate_result_message(app, result)

        self.assertTrue(message.startswith("Local coordinates\nLocal fallback used\n"))
        self.assertIn("Data source: Messier", message)

    def test_local_star_and_galaxy_include_structured_photometry_and_type(self):
        app = SimpleNamespace(_tr=lambda key, **kw: translate("fr", key, **kw))
        star = resolve_local_object_coordinates("Sirius")
        text = _target_information_text(app, star)
        self.assertIn("Magnitude : -1.46 (V)", text)
        self.assertIn("Type : Étoile", text)
        self.assertIn("catalogue local étoiles", text)
        galaxy = resolve_local_object_coordinates("M31")
        text = _target_information_text(app, galaxy)
        self.assertIsNotNone(galaxy["magnitude"])
        self.assertIn("Galaxie", text)
        self.assertIn("OpenNGC", text)

    def test_binary_components_and_missing_data_are_explicit(self):
        app = SimpleNamespace(_tr=lambda key, **kw: translate("en", key, **kw))
        text = _target_information_text(app, dict(target_kind="double_star", mag_primary=0,
                                                  mag_secondary=4.2, source="WDS"))
        self.assertIn("0.00 / 4.20 (primary / secondary)", text)
        self.assertIn("Type: Double star", text)
        self.assertIn("Data source: WDS", text)
        text = _target_information_text(app, dict(source="sesame"))
        self.assertIn("Magnitude: Not available", text)
        self.assertIn("CDS Sesame", text)

    def test_coordinate_source_and_photometry_source_remain_distinct(self):
        app = SimpleNamespace(_tr=lambda key, **kw: translate("fr", key, **kw))
        text = _target_information_text(app, dict(source="sesame", magnitude=3.4,
                                                 magnitude_band="V", magnitude_source="OpenNGC local"))
        self.assertIn("3.40 (V) — OpenNGC local", text)
        self.assertIn("Source des données : CDS Sesame", text)


if __name__ == "__main__":
    unittest.main()
