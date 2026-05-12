import unittest

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
