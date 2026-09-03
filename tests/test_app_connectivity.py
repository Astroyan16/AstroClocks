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
    def _app_stub(self):
        app = object.__new__(AstroClocksApp)
        app.language = "fr"
        app.success = "#7bd88f"
        app.danger = "#ff5c5c"
        app.muted = "#93a6b7"
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

    def test_first_failure_keeps_checking_when_state_is_unknown(self):
        app = self._app_stub()

        AstroClocksApp._apply_connectivity_result(app, False)

        self.assertIsNone(app.network_online)
        self.assertEqual(app.connectivity_consecutive_failures, 1)
        self.assertEqual(app.connectivity_label.text, "● Vérification connexion")
        self.assertEqual(app.connectivity_label.foreground, app.muted)

    def test_first_failure_keeps_connected_state(self):
        app = self._app_stub()
        app.network_online = True

        AstroClocksApp._apply_connectivity_result(app, False)

        self.assertTrue(app.network_online)
        self.assertEqual(app.connectivity_consecutive_failures, 1)
        self.assertEqual(app.connectivity_label.text, "● Connecté")
        self.assertEqual(app.connectivity_label.foreground, app.success)

    def test_worker_queues_result_without_calling_tk(self):
        app = self._app_stub()

        with mock.patch("astroclocks.app.socket.create_connection") as connection:
            connection.return_value.__enter__.return_value = object()
            AstroClocksApp._run_connectivity_check(app)

        self.assertTrue(app.connectivity_result_queue.get_nowait())

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
        self.assertEqual(app.connectivity_label.text, "● Hors-ligne")
        self.assertEqual(app.connectivity_label.foreground, app.danger)

    def test_success_resets_failure_counter(self):
        app = self._app_stub()
        app.network_online = False
        app.connectivity_consecutive_failures = 2

        AstroClocksApp._apply_connectivity_result(app, True)

        self.assertTrue(app.network_online)
        self.assertEqual(app.connectivity_consecutive_failures, 0)
        self.assertEqual(app.connectivity_label.text, "● Connecté")
        self.assertEqual(app.connectivity_label.foreground, app.success)


if __name__ == "__main__":
    unittest.main()
