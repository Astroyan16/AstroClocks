import tkinter as tk
import queue
import unittest
from unittest.mock import Mock, patch

from astroclocks.app import AstroClocksApp


class _ButtonProbe:
    def __init__(self):
        self.state = None
        self.cursor = None

    def config(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class OnlineControlsStateTests(unittest.TestCase):
    def setUp(self):
        for module in ("app_deep_sky", "app_star_search"):
            patcher = patch(f"astroclocks.{module}.load_page_state", return_value=None)
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_orbit_progress_runs_once_and_stops_when_results_arrive(self):
        app = self._make_app()
        app.double_orbit_progress = Mock()
        app.double_orbit_recompute_pending = True
        app.double_remote_search_pending = True
        app.double_search_generation = 1
        app._render_double_star_results = Mock()
        app._poll_double_orbit_progress = Mock()
        app.double_orbit_progress_job = None

        app._update_double_search_buttons_state()
        app._update_double_search_buttons_state()
        app.double_orbit_progress.grid.assert_called_once_with()
        app.double_orbit_progress.configure.assert_called_once_with(value=0)
        app._poll_double_orbit_progress.assert_called_once_with()
        app.double_orbit_progress.start.assert_not_called()

        # A stale result must not interrupt the current calculation.
        app._apply_double_star_search_results(0, {})
        app.double_orbit_progress.grid_remove.assert_not_called()
        app._apply_double_star_search_results(1, {
            "stars": [], "total": 0, "source_key": "double.source.local",
            "note": "calculation failed",
        })
        app.double_orbit_progress.grid_remove.assert_called_once_with()
        self.assertFalse(app.double_orbit_recompute_pending)
        self.assertFalse(app.double_orbit_progress_running)

    def test_online_search_does_not_show_orbit_progress(self):
        app = self._make_app()
        app.double_orbit_progress = Mock()
        app.double_remote_search_pending = True
        app.double_orbit_recompute_pending = False
        app._update_double_search_buttons_state()
        app.double_orbit_progress.start.assert_not_called()
        app.double_orbit_progress.grid.assert_not_called()

    def test_orbit_progress_uses_completed_objects_and_ignores_stale_updates(self):
        app = self._make_app()
        app._poll_double_orbit_calculation = Mock()
        app.double_orbit_progress_queue = queue.Queue()
        app.double_orbit_progress = Mock()
        app.double_status_label = Mock()
        app.root = Mock()
        app._tr = lambda key, **values: (key, values)
        app.double_search_generation = 2
        app.double_orbit_recompute_pending = True
        app.double_remote_search_pending = True
        report = app._double_orbit_progress_callback(2, "orbits")
        report(1, 4)
        report(2, 4)
        app.root.after.assert_not_called()
        app.double_orbit_progress_queue.put((1, "visibility", 4, 4))
        app._poll_double_orbit_progress()
        app.double_orbit_progress.configure.assert_called_with(value=25)
        app.double_status_label.config.assert_called_with(text=(
            "double.progress.orbits", {"completed": 2, "total": 4},
        ))
        app._double_orbit_progress_callback(2, "visibility")(3, 4)
        app._poll_double_orbit_progress()
        app.double_orbit_progress.configure.assert_called_with(value=87.5)
        app._double_orbit_progress_callback(2, "visibility")(4, 4)
        app._poll_double_orbit_progress()
        app.double_orbit_progress.configure.assert_called_with(value=100)

    def test_visibility_progress_counts_objects_rejected_by_filters(self):
        app = self._make_app()
        app._double_stars_to_jnow = lambda stars: stars
        app._double_star_visibility_metrics = lambda star, context: {}
        app._double_group_allowed = lambda star, filters: False
        updates = []
        results = app._filter_double_star_list(
            [{"name": "first"}, {"name": "second"}], {}, {},
            progress_callback=lambda done, total: updates.append((done, total)),
        )
        self.assertEqual(results, [])
        self.assertEqual(updates, [(0, 2), (1, 2), (2, 2)])

    def test_process_messages_are_applied_on_the_ui_thread_for_current_generation_only(self):
        app = self._make_app()
        app.double_search_generation = 2
        app.double_orbit_messages = queue.Queue()
        app.double_orbit_progress_queue = queue.Queue()
        app.double_orbit_job = Mock()
        app._apply_double_star_search_results = Mock()
        app.double_orbit_messages.put(("result", 1, {"stars": ["old"]}))
        app.double_orbit_messages.put(("progress", 2, (2, "visibility", 1, 2)))
        app.double_orbit_messages.put(("result", 2, {"stars": ["new"]}))
        app._poll_double_orbit_calculation()
        self.assertEqual(app.double_orbit_progress_queue.get_nowait(), (2, "visibility", 1, 2))
        app._apply_double_star_search_results.assert_called_once_with(2, {"stars": ["new"]})
        self.assertIsNone(app.double_orbit_job)

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

    def test_simbad_failure_leaves_wds_orbits_and_aladin_available(self):
        app = self._make_app()
        app.service_status = {"simbad": False, "vizier": True, "orb6": True, "aladin": True}
        app.aladin_button = _ButtonProbe()
        app._update_online_controls_state()
        app._update_aladin_button_state()
        self.assertEqual(app.deep_sky_online_button.state, tk.DISABLED)
        self.assertEqual(app.star_search_online_button.state, tk.DISABLED)
        self.assertEqual(app.double_search_button.state, tk.NORMAL)
        self.assertEqual(app.double_orbit_recompute_button.state, tk.NORMAL)
        self.assertEqual(app.aladin_button.state, tk.NORMAL)

    def test_wds_failure_does_not_disable_orbit_refresh(self):
        app = self._make_app()
        app.service_status = {"vizier": False, "orb6": True}
        app._update_double_search_buttons_state()
        self.assertEqual(app.double_search_button.state, tk.DISABLED)
        self.assertEqual(app.double_orbit_recompute_button.state, tk.NORMAL)

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
