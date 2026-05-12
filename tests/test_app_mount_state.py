import unittest
from types import SimpleNamespace
from unittest.mock import patch

from astroclocks import ascom_mount
from astroclocks.app import AstroClocksApp
from astroclocks.i18n import translate


class MountSettingsStateTests(unittest.TestCase):
    def _app_stub(self):
        app = object.__new__(AstroClocksApp)
        app.language = "fr"
        app.danger = "#ff5c5c"
        app.success = "#7bd88f"
        app.accent = "#4cc9f0"
        app.muted = "#93a6b7"
        app.mount_ascom_available = True
        app.mount_connected = False
        app.mount_ascom_driver_id = ""
        app.mount_ascom_driver_name = ""
        app.mount_last_snapshot = None
        app.mount_last_error = ""
        app.mount_availability_error = ""
        app.mount_telescope = None
        app.mount_ascom_driver_id = ""
        app.mount_ascom_driver_name = ""
        app.sky_map_cache_key = "cached"
        app._tr = lambda key, **values: translate("fr", key, **values)
        app._mount_equatorial_frame_label = lambda equatorial_system: "Topocentrique"
        app._mount_tracking_label = lambda snapshot: "sidéral"
        app._active_site_context = lambda: ("app", 0.0, 0.0)
        app._invalidate_site_dependent_state = lambda: None
        app.update_site_labels = lambda: None
        app._update_sky_map = lambda *args, **kwargs: None
        app._update_visibility_chart = lambda *args, **kwargs: None
        app._schedule_mount_poll = lambda: None
        app._poll_ascom_mount = lambda: None
        return app

    def test_mount_settings_state_reports_pending_coordinates(self):
        app = self._app_stub()
        app.mount_connected = True
        app.mount_ascom_driver_name = "SynScan App Driver"

        state = AstroClocksApp.mount_settings_state(app)

        self.assertTrue(state["connected"])
        self.assertTrue(state["has_driver"])
        self.assertFalse(state["snapshot_ready"])
        self.assertEqual(state["status_color"], app.accent)
        self.assertIn("En attente des coordonnées", state["status_text"])

    def test_mount_settings_state_reports_connected_coordinates(self):
        app = self._app_stub()
        app.mount_connected = True
        app.mount_last_snapshot = SimpleNamespace(
            driver_name="SynScan App Driver",
            driver_id="ASCOM.SynScan.Driver",
            equatorial_system=1,
        )

        state = AstroClocksApp.mount_settings_state(app)

        self.assertTrue(state["snapshot_ready"])
        self.assertEqual(state["status_color"], app.success)
        self.assertIn("Repère", state["status_text"])
        self.assertIn("Suivi", state["status_text"])

    def test_connect_ascom_mount_reports_connect_failure_when_initial_snapshot_fails(self):
        app = self._app_stub()
        app.mount_ascom_driver_id = "ASCOM.SynScan.Driver"
        app.mount_ascom_driver_name = "SynScan App Driver"
        telescope = object()

        with (
            patch("astroclocks.app.ascom_mount.connect", return_value=(telescope, "SynScan App Driver")),
            patch(
                "astroclocks.app.ascom_mount.read_snapshot",
                side_effect=ascom_mount.AscomMountError(
                    "Unable to read the ASCOM mount coordinates: mount not ready"
                ),
            ),
            patch("astroclocks.app.ascom_mount.disconnect") as mocked_disconnect,
        ):
            with self.assertRaisesRegex(RuntimeError, "Impossible de connecter la monture ASCOM"):
                AstroClocksApp.connect_ascom_mount(app)

        mocked_disconnect.assert_called_once_with(telescope)
        self.assertFalse(app.mount_connected)
        self.assertIsNone(app.mount_telescope)
        self.assertIsNone(app.mount_last_snapshot)
        self.assertIn("Impossible de connecter la monture ASCOM", app.mount_last_error)

    def test_mount_connect_error_message_detects_synscan_unavailable(self):
        app = self._app_stub()

        message = AstroClocksApp._mount_connect_error_message(
            app,
            "Unable to read the ASCOM mount coordinates: SynScan app not connected",
        )

        self.assertEqual(
            message,
            "Impossible de joindre SynScan ou la monture via SynScan. Vérifiez que "
            "SynScan est lancé et que la monture y est connectée.",
        )


if __name__ == "__main__":
    unittest.main()
