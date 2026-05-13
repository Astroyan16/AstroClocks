import unittest

from astroclocks.app_dialogs import _coordinate_source_combo_config
from astroclocks.settings import COORDINATE_SOURCE_APP, COORDINATE_SOURCE_MOUNT


class CoordinateSourceComboConfigTests(unittest.TestCase):
    def setUp(self):
        self.labels = {
            COORDINATE_SOURCE_APP: "AstroClocks settings",
            COORDINATE_SOURCE_MOUNT: "ASCOM mount",
        }
        self.unavailable = "AstroClocks settings (ASCOM mount unavailable)"
        self.disconnected = "AstroClocks settings (ASCOM mount not connected)"

    def test_mount_connected_keeps_requested_selection_and_readonly_state(self):
        config = _coordinate_source_combo_config(
            COORDINATE_SOURCE_MOUNT,
            True,
            True,
            self.labels,
            self.unavailable,
            self.disconnected,
        )

        self.assertEqual(
            config,
            {
                "values": ["AstroClocks settings", "ASCOM mount"],
                "selected_label": "ASCOM mount",
                "state": "readonly",
            },
        )

    def test_mount_unavailable_shows_fallback_label_and_disabled_state(self):
        config = _coordinate_source_combo_config(
            COORDINATE_SOURCE_MOUNT,
            False,
            False,
            self.labels,
            self.unavailable,
            self.disconnected,
        )

        self.assertEqual(
            config,
            {
                "values": ["AstroClocks settings", "ASCOM mount"],
                "selected_label": self.unavailable,
                "state": "disabled",
            },
        )

    def test_mount_disconnected_shows_disconnected_fallback_and_disabled_state(self):
        config = _coordinate_source_combo_config(
            COORDINATE_SOURCE_MOUNT,
            True,
            False,
            self.labels,
            self.unavailable,
            self.disconnected,
        )

        self.assertEqual(config["selected_label"], self.disconnected)
        self.assertEqual(config["state"], "disabled")

    def test_mount_unavailable_keeps_app_selection_without_fallback_text(self):
        config = _coordinate_source_combo_config(
            COORDINATE_SOURCE_APP,
            False,
            False,
            self.labels,
            self.unavailable,
            self.disconnected,
        )

        self.assertEqual(config["selected_label"], "AstroClocks settings")
        self.assertEqual(config["state"], "disabled")


if __name__ == "__main__":
    unittest.main()
