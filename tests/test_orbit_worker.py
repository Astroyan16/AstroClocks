import multiprocessing
import queue
import threading
import unittest
from unittest.mock import Mock, patch

from astroclocks.app import AstroClocksApp
from astroclocks.double_star_catalog import DOUBLE_STARS
from astroclocks.orbit_worker import OrbitCalculationJob, calculate_orbit_catalog


def request():
    app = AstroClocksApp.__new__(AstroClocksApp)
    filters = app._default_double_filters()
    filters.update(max_primary=100, max_secondary=100, min_sep=0, max_sep=10000,
                   min_altitude=-90, visible_night=False, include_physical=True,
                   include_noted=True, include_apparent=True, include_uncertain=True)
    return {
        "search_context": dict(latitude=48.8, longitude=2.2, alpha_hh=0,
                               alpha_mm=0, alpha_ss=0, hour_angle_offset_hours=0,
                               timezone_name="Europe/Paris", daylight_saving_enabled=False),
        "language": "fr", "catalog": list(DOUBLE_STARS[:10]), "filters": filters,
        "ephemeris_index": None, "orbit_index": None, "notes": [],
        "result_metadata": {"total": 10, "source_key": "double.source.local"},
    }


class OrbitWorkerTests(unittest.TestCase):
    def test_cancel_during_process_start_never_blocks_the_calling_thread(self):
        started, release = threading.Event(), threading.Event()
        process = Mock()
        process.pid = 123
        context = Mock()
        context.Process.return_value = process
        process.start.side_effect = lambda: (started.set(), release.wait(5))
        job = OrbitCalculationJob(1, {})
        messages = queue.Queue()
        with patch("astroclocks.orbit_worker.multiprocessing.get_context", return_value=context):
            background = threading.Thread(target=job.run, args=(messages,))
            background.start()
            try:
                self.assertTrue(started.wait(5))
                job.cancel()
                self.assertTrue(job.cancelled.is_set())
                self.assertTrue(background.is_alive())
            finally:
                release.set()
                background.join(timeout=5)
        self.assertFalse(background.is_alive())
        self.assertTrue(messages.empty())
        process.terminate.assert_called_once_with()
        process.join.assert_called_once_with(timeout=1)
        process.close.assert_called_once_with()
        context.Queue.return_value.close.assert_called_once_with()

    def test_process_start_failure_is_reported_and_resources_closed(self):
        context = Mock()
        context.Process.return_value.pid = None
        context.Process.return_value.start.side_effect = OSError("cannot start worker")
        messages = queue.Queue()
        with patch("astroclocks.orbit_worker.multiprocessing.get_context", return_value=context):
            OrbitCalculationJob(2, {}).run(messages)
        self.assertEqual(messages.get_nowait(), ("error", 2, "cannot start worker"))
        context.Process.return_value.close.assert_called_once_with()
        context.Queue.return_value.close.assert_called_once_with()

    def test_calculation_never_creates_tk_and_reports_progress(self):
        messages = queue.Queue()
        with patch("tkinter.Tk", side_effect=AssertionError("Tk in calculation")), patch.object(
            AstroClocksApp, "__init__", side_effect=AssertionError("UI initialization in calculation"),
        ):
            calculate_orbit_catalog(7, request(), messages)
        updates = []
        while not messages.empty():
            updates.append(messages.get_nowait())
        self.assertTrue(any(kind == "progress" for kind, _, _ in updates))
        self.assertEqual(updates[-1][0:2], ("result", 7))
        self.assertEqual(len(updates[-1][2]["stars"]), 10)
        self.assertTrue(all(star["coordinate_frame"] == "jnow" for star in updates[-1][2]["stars"]))

    def test_spawned_process_returns_results_without_live_app_objects(self):
        context = multiprocessing.get_context("spawn")
        messages = context.Queue()
        worker = context.Process(target=calculate_orbit_catalog, args=(8, request(), messages))
        worker.start()
        try:
            while True:
                kind, generation, payload = messages.get(timeout=30)
                self.assertEqual(generation, 8)
                self.assertNotEqual(kind, "error", payload)
                if kind == "result":
                    self.assertEqual(len(payload["stars"]), 10)
                    break
            worker.join(timeout=5)
            self.assertEqual(worker.exitcode, 0)
        finally:
            if worker.is_alive():
                worker.terminate()
                worker.join(timeout=5)
            worker.close()
            messages.close()


if __name__ == "__main__":
    unittest.main()
