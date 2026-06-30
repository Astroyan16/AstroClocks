import tkinter as tk
import unittest
from types import SimpleNamespace

from astroclocks.app_deep_sky import (
    _apply_deep_sky_search_results,
    _queue_deep_sky_search_results,
)
from astroclocks.app_double_stars import (
    _apply_double_star_search_results,
    _queue_double_star_search_results,
)
from astroclocks.app_star_search import (
    _apply_star_search_results,
    _queue_star_search_results,
)


class _AfterRaisesRoot:
    def after(self, _delay, _callback):
        raise RuntimeError("window closed")


class SearchAsyncResultsTests(unittest.TestCase):
    def test_star_apply_results_updates_cache_and_renders_for_current_generation(self):
        captured = {"render": None, "buttons": 0}
        app = SimpleNamespace(
            star_search_generation=3,
            star_search_pending=True,
            star_search_cached_stars=[],
            _update_star_search_buttons_state=lambda: captured.__setitem__("buttons", captured["buttons"] + 1),
            _render_star_search_results=lambda stars, total, note: captured.__setitem__(
                "render",
                (stars, total, note),
            ),
        )

        _apply_star_search_results(
            app,
            3,
            {"stars": [{"name": "Sirius"}], "total": 1, "note": "ok", "cached_stars": [{"name": "Sirius"}]},
        )

        self.assertFalse(app.star_search_pending)
        self.assertEqual(app.star_search_cached_stars, [{"name": "Sirius"}])
        self.assertEqual(captured["buttons"], 1)
        self.assertEqual(captured["render"], ([{"name": "Sirius"}], 1, "ok"))

    def test_star_apply_results_ignores_stale_generation(self):
        captured = {"render": 0, "buttons": 0}
        app = SimpleNamespace(
            star_search_generation=4,
            star_search_pending=True,
            star_search_cached_stars=[{"name": "Altair"}],
            _update_star_search_buttons_state=lambda: captured.__setitem__("buttons", captured["buttons"] + 1),
            _render_star_search_results=lambda stars, total, note: captured.__setitem__("render", captured["render"] + 1),
        )

        _apply_star_search_results(
            app,
            3,
            {"stars": [{"name": "Sirius"}], "total": 1, "note": "stale", "cached_stars": [{"name": "Sirius"}]},
        )

        self.assertTrue(app.star_search_pending)
        self.assertEqual(app.star_search_cached_stars, [{"name": "Altair"}])
        self.assertEqual(captured["buttons"], 0)
        self.assertEqual(captured["render"], 0)

    def test_star_queue_results_clears_pending_when_ui_thread_is_unavailable(self):
        app = SimpleNamespace(
            root=_AfterRaisesRoot(),
            star_search_pending=True,
        )

        _queue_star_search_results(app, 1, {"stars": [], "total": 0})

        self.assertFalse(app.star_search_pending)

    def test_deep_sky_apply_results_updates_cache_and_renders_for_current_generation(self):
        captured = {"render": None, "buttons": 0}
        app = SimpleNamespace(
            deep_sky_search_generation=2,
            deep_sky_search_pending=True,
            deep_sky_simbad_cached_objects=[],
            _update_deep_sky_search_buttons_state=lambda: captured.__setitem__("buttons", captured["buttons"] + 1),
            _render_deep_sky_results=lambda objects, total, note: captured.__setitem__(
                "render",
                (objects, total, note),
            ),
        )

        _apply_deep_sky_search_results(
            app,
            2,
            {
                "objects": [{"name": "M 51"}],
                "total": 1,
                "note": "ok",
                "simbad_cached_objects": [{"name": "M 51"}],
            },
        )

        self.assertFalse(app.deep_sky_search_pending)
        self.assertEqual(app.deep_sky_simbad_cached_objects, [{"name": "M 51"}])
        self.assertEqual(captured["buttons"], 1)
        self.assertEqual(captured["render"], ([{"name": "M 51"}], 1, "ok"))

    def test_deep_sky_apply_results_ignores_stale_generation(self):
        captured = {"render": 0, "buttons": 0}
        app = SimpleNamespace(
            deep_sky_search_generation=6,
            deep_sky_search_pending=True,
            deep_sky_simbad_cached_objects=[{"name": "NGC 7000"}],
            _update_deep_sky_search_buttons_state=lambda: captured.__setitem__("buttons", captured["buttons"] + 1),
            _render_deep_sky_results=lambda objects, total, note: captured.__setitem__("render", captured["render"] + 1),
        )

        _apply_deep_sky_search_results(
            app,
            5,
            {
                "objects": [{"name": "M 51"}],
                "total": 1,
                "note": "stale",
                "simbad_cached_objects": [{"name": "M 51"}],
            },
        )

        self.assertTrue(app.deep_sky_search_pending)
        self.assertEqual(app.deep_sky_simbad_cached_objects, [{"name": "NGC 7000"}])
        self.assertEqual(captured["buttons"], 0)
        self.assertEqual(captured["render"], 0)

    def test_deep_sky_queue_results_clears_pending_when_ui_thread_is_unavailable(self):
        app = SimpleNamespace(
            root=_AfterRaisesRoot(),
            deep_sky_search_pending=True,
        )

        _queue_deep_sky_search_results(app, 1, {"objects": [], "total": 0})

        self.assertFalse(app.deep_sky_search_pending)

    def test_double_apply_results_updates_caches_and_renders_for_current_generation(self):
        captured = {"render": None, "buttons": 0}
        app = SimpleNamespace(
            double_search_generation=8,
            double_remote_search_pending=True,
            double_wds_cached_stars=[],
            double_orb6_index=None,
            double_orb6_orbit_index=None,
            _update_double_search_buttons_state=lambda: captured.__setitem__("buttons", captured["buttons"] + 1),
            _render_double_star_results=lambda stars, total, source_key, note: captured.__setitem__(
                "render",
                (stars, total, source_key, note),
            ),
        )

        _apply_double_star_search_results(
            app,
            8,
            {
                "stars": [{"wds": "12345+6789"}],
                "total": 1,
                "source_key": "double.source.wds",
                "note": "ok",
                "wds_cached_stars": [{"wds": "12345+6789"}],
                "orb6_index": {"from_cache": False},
                "orb6_orbit_index": {"from_cache": False},
            },
        )

        self.assertFalse(app.double_remote_search_pending)
        self.assertEqual(app.double_wds_cached_stars, [{"wds": "12345+6789"}])
        self.assertEqual(app.double_orb6_index, {"from_cache": False})
        self.assertEqual(app.double_orb6_orbit_index, {"from_cache": False})
        self.assertEqual(captured["buttons"], 1)
        self.assertEqual(
            captured["render"],
            ([{"wds": "12345+6789"}], 1, "double.source.wds", "ok"),
        )

    def test_double_apply_results_ignores_stale_generation(self):
        captured = {"render": 0, "buttons": 0}
        app = SimpleNamespace(
            double_search_generation=9,
            double_remote_search_pending=True,
            double_wds_cached_stars=[{"wds": "old"}],
            double_orb6_index={"from_cache": True},
            double_orb6_orbit_index={"from_cache": True},
            _update_double_search_buttons_state=lambda: captured.__setitem__("buttons", captured["buttons"] + 1),
            _render_double_star_results=lambda stars, total, source_key, note: captured.__setitem__(
                "render",
                captured["render"] + 1,
            ),
        )

        _apply_double_star_search_results(
            app,
            8,
            {
                "stars": [{"wds": "new"}],
                "total": 1,
                "source_key": "double.source.wds",
                "note": "stale",
                "wds_cached_stars": [{"wds": "new"}],
                "orb6_index": {"from_cache": False},
                "orb6_orbit_index": {"from_cache": False},
            },
        )

        self.assertTrue(app.double_remote_search_pending)
        self.assertEqual(app.double_wds_cached_stars, [{"wds": "old"}])
        self.assertEqual(app.double_orb6_index, {"from_cache": True})
        self.assertEqual(app.double_orb6_orbit_index, {"from_cache": True})
        self.assertEqual(captured["buttons"], 0)
        self.assertEqual(captured["render"], 0)

    def test_double_queue_results_clears_pending_when_ui_thread_is_unavailable(self):
        app = SimpleNamespace(
            root=_AfterRaisesRoot(),
            double_remote_search_pending=True,
        )

        _queue_double_star_search_results(app, 1, {"stars": [], "total": 0, "source_key": "double.source.local"})

        self.assertFalse(app.double_remote_search_pending)


if __name__ == "__main__":
    unittest.main()
