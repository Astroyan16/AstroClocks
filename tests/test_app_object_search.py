import unittest

from astroclocks.app_object_search import (
    _apply_coordinate_result,
    _coordinate_result_message,
    _with_search_fallback,
)


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
        }[key]
        result = {
            "source": "local",
            "source_catalog": "Messier",
            "source_note": "",
            "source_ra": "12:34:56",
            "source_dec": "+12:34:56",
            "_search_fallback_reason": "error",
        }

        message = _coordinate_result_message(app, result)

        self.assertEqual(message, "Local coordinates\nLocal fallback used")


if __name__ == "__main__":
    unittest.main()
