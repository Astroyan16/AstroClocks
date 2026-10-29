import queue
import unittest
from unittest import mock

from astroclocks.app import AstroClocksApp
from astroclocks.i18n import translate


class _FakeLabel:
    def __init__(self):
        self.text = None
        self.foreground = None

    def config(self, **kwargs):
        if "text" in kwargs:
            self.text = kwargs["text"]
        if "foreground" in kwargs:
            self.foreground = kwargs["foreground"]


class _FakeRoot:
    def __init__(self):
        self.after_calls = []

    def after(self, delay_ms, callback):
        self.after_calls.append((delay_ms, callback))


class ConnectivityStateTests(unittest.TestCase):
    def test_unconfigured_api_does_not_warn_even_with_stale_failure(self):
        app = self._app_stub()
        app.network_online = True
        app.service_status = {"metar": True, "meteofrance": False}
        app.connectivity_dialog = mock.Mock()
        row = _FakeLabel()
        app.connectivity_rows = {"meteofrance": row}
        with mock.patch("astroclocks.app.service_configured", side_effect=lambda name: name != "meteofrance"):
            app._refresh_connectivity_display()
        self.assertEqual(app.connectivity_label.foreground, app.success)
        self.assertEqual(row.text, "Non configuré")
        self.assertEqual(row.foreground, app.muted)

    def test_configured_api_failure_warns(self):
        app = self._app_stub()
        app.network_online = True
        app.service_status = {"metar": True, "meteofrance": False}
        with mock.patch("astroclocks.app.service_configured", return_value=True):
            app._refresh_connectivity_display()
        self.assertEqual(app.connectivity_label.foreground, app.warning)

    def test_skipped_service_clears_previous_failures(self):
        app = self._app_stub()
        app.service_status = {"meteofrance": False}
        app.service_failures = {"meteofrance": 2}
        app.service_details = {"meteofrance": "timeout"}
        app._apply_connectivity_result((True, {"meteofrance": (None, "", False)}))
        self.assertIsNone(app.service_status["meteofrance"])
        self.assertEqual(app.service_failures["meteofrance"], 0)
        self.assertEqual(app.connectivity_label.foreground, app.success)

    def _app_stub(self):
        app = object.__new__(AstroClocksApp)
        app.language = "fr"
        app.success = "#7bd88f"
        app.danger = "#ff5c5c"
        app.muted = "#93a6b7"
        app.warning = "orange"
        app.gbg = "#18212b"
        app.connectivity_icon = mock.Mock()
        app.connectivity_icon.find_withtag.return_value = (1, 2)
        app.connectivity_icon.type.side_effect = lambda item: "line" if item == 1 else "rectangle"
        app.network_online = None
        app.connectivity_check_pending = True
        app.connectivity_consecutive_failures = 0
        app.connectivity_result_queue = queue.Queue()
        app.connectivity_label = _FakeLabel()
        app._tr = lambda key, **values: translate("fr", key, **values)
        app._update_aladin_button_state = lambda: None
        app._update_online_controls_state = lambda: None
        app._schedule_connectivity_check = lambda delay_ms=1000: None
        return app

    def test_network_indicator_colors_follow_connection_and_service_states(self):
        cases = (
            (None, {"simbad": None}, "muted", "network.checking"),
            (True, {"simbad": True, "imcce": True}, "success", "network.connected"),
            (True, {"simbad": False, "imcce": True}, "warning", "network.partial_one"),
            (True, {"simbad": False, "imcce": False}, "warning", "network.partial"),
            (False, {"simbad": False, "imcce": False}, "danger", "network.offline"),
        )
        for online, services, color_name, text_key in cases:
            with self.subTest(online=online, services=services):
                app = self._app_stub()
                app.network_online = online
                app.service_status = services
                app._refresh_connectivity_display()
                color = getattr(app, color_name)
                count = sum(state is False for state in services.values())
                self.assertEqual(app.connectivity_label.text, app._tr(text_key, count=count))
                self.assertEqual(app.connectivity_label.foreground, color)
                app.connectivity_icon.itemconfigure.assert_any_call("network", fill=color)
                app.connectivity_icon.itemconfigure.assert_any_call(2, fill=app.gbg, outline=color)

    def test_network_icon_updates_without_label(self):
        app = self._app_stub()
        app.network_online = True
        app.service_status = {"simbad": False}
        app.connectivity_label = None

        app._refresh_connectivity_display()

        app.connectivity_icon.itemconfigure.assert_any_call("network", fill=app.warning)

    def test_service_failure_does_not_turn_internet_off_and_recovers_independently(self):
        app = self._app_stub()
        app.warning = "orange"
        app.service_status = {"simbad": None, "imcce": None}
        app.service_failures = {"simbad": 0, "imcce": 0}
        app.service_details = {}
        result = (True, {"simbad": (False, "timeout", False), "imcce": (True, "HTTP 200", True)})
        app._apply_connectivity_result(result)
        self.assertFalse(app.service_status["simbad"])
        self.assertEqual(app.connectivity_label.foreground, app.warning)
        app._apply_connectivity_result(result)
        self.assertTrue(app.network_online)
        self.assertFalse(app.service_status["simbad"])
        self.assertTrue(app.service_status["imcce"])
        self.assertIn("1 indisponible", app.connectivity_label.text)
        self.assertEqual(app.connectivity_label.foreground, app.warning)
        app._apply_connectivity_result((True, {"simbad": (True, "HTTP 200", True)}))
        self.assertTrue(app.service_status["simbad"])
        self.assertEqual(app.service_failures["simbad"], 0)
        self.assertEqual(app.connectivity_label.text, "Connecté")

    def test_startup_failure_marks_offline_immediately(self):
        app = self._app_stub()

        AstroClocksApp._apply_connectivity_result(app, False)

        self.assertFalse(app.network_online)
        self.assertEqual(app.connectivity_consecutive_failures, 1)
        self.assertEqual(app.connectivity_label.text, "Hors-ligne")
        self.assertEqual(app.connectivity_label.foreground, app.danger)

    def test_previously_available_service_requires_two_failures(self):
        app = self._app_stub()
        app.network_online = True
        app.service_status = {"simbad": True}
        app.service_failures = {"simbad": 0}
        app.service_details = {}
        result = (True, {"simbad": (False, "timeout", False)})

        app._apply_connectivity_result(result)
        self.assertTrue(app.service_status["simbad"])
        self.assertEqual(app.connectivity_label.foreground, app.success)

        app._apply_connectivity_result(result)
        self.assertFalse(app.service_status["simbad"])
        self.assertEqual(app.connectivity_label.foreground, app.warning)

    def test_first_failure_keeps_connected_state(self):
        app = self._app_stub()
        app.network_online = True

        AstroClocksApp._apply_connectivity_result(app, False)

        self.assertTrue(app.network_online)
        self.assertEqual(app.connectivity_consecutive_failures, 1)
        self.assertEqual(app.connectivity_label.text, "Connecté")
        self.assertEqual(app.connectivity_label.foreground, app.success)

    def test_worker_queues_result_without_calling_tk(self):
        app = self._app_stub()

        with mock.patch("astroclocks.app.check_services", return_value=(True, {})):
            AstroClocksApp._run_connectivity_check(app)

        self.assertEqual(app.connectivity_result_queue.get_nowait(), (True, {}))

    def test_poll_waits_on_ui_thread_until_worker_result_is_available(self):
        app = self._app_stub()
        app.root = _FakeRoot()
        applied_results = []
        app._apply_connectivity_result = applied_results.append

        AstroClocksApp._poll_connectivity_result(app)

        self.assertEqual(len(app.root.after_calls), 1)
        self.assertEqual(applied_results, [])

        app.connectivity_result_queue.put(True)
        app.root.after_calls[0][1]()

        self.assertEqual(applied_results, [True])

    def test_second_consecutive_failure_marks_offline(self):
        app = self._app_stub()
        app.network_online = True
        app.connectivity_consecutive_failures = 1

        AstroClocksApp._apply_connectivity_result(app, False)

        self.assertFalse(app.network_online)
        self.assertEqual(app.connectivity_consecutive_failures, 2)
        self.assertEqual(app.connectivity_label.text, "Hors-ligne")
        self.assertEqual(app.connectivity_label.foreground, app.danger)

    def test_success_resets_failure_counter(self):
        app = self._app_stub()
        app.network_online = False
        app.connectivity_consecutive_failures = 2

        AstroClocksApp._apply_connectivity_result(app, True)

        self.assertTrue(app.network_online)
        self.assertEqual(app.connectivity_consecutive_failures, 0)
        self.assertEqual(app.connectivity_label.text, "Connecté")
        self.assertEqual(app.connectivity_label.foreground, app.success)


if __name__ == "__main__":
    unittest.main()
