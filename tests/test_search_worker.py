import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from astroclocks.app import AstroClocksApp
from astroclocks.orbit_worker import OrbitCalculationJob
from astroclocks.search_worker import calculate_search, start_search
from tests.test_orbit_worker import request as orbit_request


def request(kind):
    app = AstroClocksApp.__new__(AstroClocksApp)
    filters = (app._default_star_search_filters() if kind == "stars"
               else app._default_deep_sky_filters())
    filters.update(min_magnitude=40, max_magnitude=41, use_magnitude=True)
    return dict(kind=kind, filters=filters, search_context=orbit_request()["search_context"],
                allow_online=False, offline_note="offline",
                snapshot=dict(language="fr", network_online=False,
                              star_search_cached_stars=[], deep_sky_simbad_cached_objects=[]))


class SearchWorkerTests(unittest.TestCase):
    def test_visibility_results_keep_coordinates_and_metadata_without_mutating_catalog(self):
        for kind in ("stars", "deep_sky"):
            data = request(kind)
            data["filters"].update(min_magnitude=-50, max_magnitude=50, min_altitude=-90,
                                   visible_night=False, transit_night=False,
                                   exclude_polar_circle=False)
            item = dict(name="sample", ra_hours=4.2, declination=30, magnitude=3,
                        magnitude_band=data["filters"]["magnitude_band"])
            if kind == "stars":
                item["spectral_class"] = data["filters"]["spectral_type"]
            else:
                item["category"] = data["filters"]["category"]
            catalog_method = "_star_search_catalog" if kind == "stars" else "_deep_sky_catalog"
            with self.subTest(kind=kind), patch.object(AstroClocksApp, catalog_method, return_value=[item]):
                messages = queue.Queue()
                calculate_search(3, data, messages)
                status, _, payload = messages.get_nowait()
                self.assertEqual(status, "result")
                result = payload["stars" if kind == "stars" else "objects"]
                self.assertEqual(len(result), 1)
                self.assertEqual(result[0]["name"], "sample")
                self.assertEqual(result[0]["coordinate_frame"], "jnow")
                self.assertIn("max_altitude", result[0])
                self.assertNotIn("coordinate_frame", item)

    def test_poll_delivers_worker_failure_on_ui_thread(self):
        callbacks = []
        root = Mock()
        root.after.side_effect = lambda delay, callback: callbacks.append(callback)
        app = SimpleNamespace(root=root, language="fr", network_online=False,
                              star_search_cached_stars=[], deep_sky_simbad_cached_objects=[],
                              _apply_star_search_results=Mock(), _tr=lambda key, **kw: kw["error"])
        with patch("astroclocks.search_worker.threading.Thread") as thread:
            start_search(app, "stars", 5, {}, {}, False, None)
            messages = thread.call_args.kwargs["args"][0]
            messages.put(("error", 5, "cannot start worker"))
            callbacks[0]()
        app._apply_star_search_results.assert_called_once_with(
            5, {"stars": [], "total": 0, "note": "cannot start worker"})
        self.assertEqual(app.search_calculation_jobs, {})

    def test_both_pipelines_run_without_tk_or_app_initialization(self):
        for kind in ("stars", "deep_sky"):
            with self.subTest(kind=kind), patch("tkinter.Tk", side_effect=AssertionError("Tk")), patch.object(
                AstroClocksApp, "__init__", side_effect=AssertionError("UI initialization"),
            ):
                messages = queue.Queue()
                calculate_search(7, request(kind), messages)
                status, generation, payload = messages.get_nowait()
                self.assertEqual((status, generation), ("result", 7))
                self.assertGreater(payload["total"], 0)
                self.assertEqual(payload["stars" if kind == "stars" else "objects"], [])
                self.assertIn("offline", payload["note"])

    def test_both_spawned_pipelines_return_results(self):
        for kind in ("stars", "deep_sky"):
            with self.subTest(kind=kind):
                messages = queue.Queue()
                job = OrbitCalculationJob(9, request(kind), target=calculate_search)
                background = threading.Thread(target=job.run, args=(messages,))
                background.start()
                try:
                    status, generation, payload = messages.get(timeout=30)
                    self.assertEqual((status, generation), ("result", 9), payload)
                    self.assertGreater(payload["total"], 0)
                finally:
                    job.cancel()
                    background.join(timeout=5)
                self.assertFalse(background.is_alive())

    def test_replacement_and_destroy_cancel_jobs_and_ignore_old_results(self):
        callbacks = []
        root = Mock()
        root.after.side_effect = lambda delay, callback: callbacks.append(callback)
        app = SimpleNamespace(root=root, language="fr", network_online=False,
                              star_search_cached_stars=[], deep_sky_simbad_cached_objects=[],
                              _apply_star_search_results=Mock(), _apply_deep_sky_search_results=Mock())
        with patch("astroclocks.search_worker.threading.Thread"):
            start_search(app, "stars", 1, {}, {}, False, None)
            first = app.search_calculation_jobs["stars"]
            start_search(app, "stars", 2, {}, {}, False, None)
            second = app.search_calculation_jobs["stars"]
            self.assertTrue(first.cancelled.is_set())
            callbacks[0]()
            self.assertEqual(len(callbacks), 2)
            close = root.bind.call_args.args[1]
            close(SimpleNamespace(widget=object()))
            self.assertFalse(second.cancelled.is_set())
            close(SimpleNamespace(widget=root))
            self.assertTrue(second.cancelled.is_set())
            callbacks[1]()
            app._apply_star_search_results.assert_not_called()


if __name__ == "__main__":
    unittest.main()
