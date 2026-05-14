import tkinter as tk
import unittest

from astroclocks.app import AstroClocksApp


class _ButtonProbe:
    def __init__(self):
        self.state = None
        self.cursor = None

    def config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class OnlineControlsStateTests(unittest.TestCase):
    def _make_app(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.combo_box = None
        app.network_online = True
        app.double_remote_search_pending = False
        app.deep_sky_search_pending = False
        app.star_search_pending = False
        app.double_apply_button = _ButtonProbe()
        app.double_search_button = _ButtonProbe()
        app.double_orbit_recompute_button = _ButtonProbe()
        app.double_reset_button = _ButtonProbe()
        app.double_clear_cache_button = _ButtonProbe()
        app.deep_sky_apply_button = _ButtonProbe()
        app.deep_sky_online_button = _ButtonProbe()
        app.deep_sky_reset_button = _ButtonProbe()
        app.deep_sky_clear_cache_button = _ButtonProbe()
        app.star_search_apply_button = _ButtonProbe()
        app.star_search_online_button = _ButtonProbe()
        app.star_search_reset_button = _ButtonProbe()
        app.star_search_clear_cache_button = _ButtonProbe()
        return app

    def test_double_online_buttons_are_disabled_offline(self):
        app = self._make_app()
        app.network_online = False

        AstroClocksApp._update_double_search_buttons_state(app)

        self.assertEqual(app.double_apply_button.state, tk.NORMAL)
        self.assertEqual(app.double_search_button.state, tk.DISABLED)
        self.assertEqual(app.double_orbit_recompute_button.state, tk.DISABLED)
        self.assertEqual(app.double_search_button.cursor, "arrow")

    def test_deep_sky_online_button_stays_disabled_offline_after_search(self):
        app = self._make_app()
        app.network_online = False
        app.deep_sky_search_pending = False

        AstroClocksApp._update_deep_sky_search_buttons_state(app)

        self.assertEqual(app.deep_sky_apply_button.state, tk.NORMAL)
        self.assertEqual(app.deep_sky_online_button.state, tk.DISABLED)
        self.assertEqual(app.deep_sky_reset_button.state, tk.NORMAL)

    def test_star_online_button_stays_disabled_offline_after_search(self):
        app = self._make_app()
        app.network_online = False
        app.star_search_pending = False

        AstroClocksApp._update_star_search_buttons_state(app)

        self.assertEqual(app.star_search_apply_button.state, tk.NORMAL)
        self.assertEqual(app.star_search_online_button.state, tk.DISABLED)
        self.assertEqual(app.star_search_clear_cache_button.state, tk.NORMAL)

    def test_online_buttons_stay_disabled_while_search_is_pending(self):
        app = self._make_app()
        app.network_online = True
        app.deep_sky_search_pending = True
        app.star_search_pending = True
        app.double_remote_search_pending = True

        AstroClocksApp._update_double_search_buttons_state(app)
        AstroClocksApp._update_deep_sky_search_buttons_state(app)
        AstroClocksApp._update_star_search_buttons_state(app)

        self.assertEqual(app.double_apply_button.state, tk.DISABLED)
        self.assertEqual(app.double_search_button.state, tk.DISABLED)
        self.assertEqual(app.deep_sky_apply_button.state, tk.DISABLED)
        self.assertEqual(app.deep_sky_online_button.state, tk.DISABLED)
        self.assertEqual(app.star_search_apply_button.state, tk.DISABLED)
        self.assertEqual(app.star_search_online_button.state, tk.DISABLED)


if __name__ == "__main__":
    unittest.main()
