import queue
import threading
import unittest
from unittest.mock import patch

from astroclocks.app import AstroClocksApp
from astroclocks import app_skymap


class SkyWorkerTests(unittest.TestCase):
    def request(self):
        return dict(
            key=(400, 400, 1), size=(400, 400), site=(48.8, 2.2), language="fr",
            stars=(("Test", 5.0, 48.8, 1.0),), lst=5.0,
            horizontal_transform=AstroClocksApp._equatorial_to_horizontal,
            need_solar=True, solar_bucket=1,
            options=dict(sky_magnitude_limit=4, sky_show_altaz_grid=True,
                         sky_show_equatorial_grid=True, sky_show_solar_system=True,
                         card_edge="#223344", muted="#8899aa", accent="#aabbcc", ebg="#001122"),
        )

    def test_worker_projects_and_composes_without_tk_calls(self):
        requests, results = queue.Queue(maxsize=1), queue.Queue(maxsize=1)
        requests.put(self.request())
        positions = [dict(name="Mars", ra_hours=5.0, declination=48.8)]
        with patch.object(app_skymap, "Font", side_effect=AssertionError("Tk font in worker")), patch.object(
            app_skymap, "compute_solar_system_positions", return_value=positions
        ) as solar:
            photo_patch = patch.object(app_skymap.ImageTk, "PhotoImage", side_effect=AssertionError("Tk image in worker")) if app_skymap.ImageTk else patch.object(app_skymap, "ImageTk", None)
            with photo_patch:
                worker = threading.Thread(target=app_skymap._sky_scene_worker,
                                          args=(requests, results, 1.27), daemon=True)
                worker.start()
                try:
                    key, scene, error = results.get(timeout=10)
                    self.assertIsNone(error)
                    self.assertEqual(key, self.request()["key"])
                    self.assertEqual(len(scene["stars"]), 1)
                    self.assertEqual(scene["solar"][0]["label"], "Mars")
                    self.assertAlmostEqual(scene["stars"][0]["altitude"], 90)
                    self.assertTrue(scene["grid"])
                    if app_skymap.Image:
                        self.assertEqual(scene["image"].size, (400, 400))
                        self.assertEqual(scene["image"].mode, "RGB")
                        self.assertEqual(scene["image"].getpixel((0, 0)), (0, 17, 34))
                    self.assertNotEqual(solar.call_args, None)
                finally:
                    app_skymap._put_latest(requests, None)
                    worker.join(timeout=5)
                self.assertFalse(worker.is_alive())

    def fake_app(self):
        app = object.__new__(AstroClocksApp)
        class Canvas:
            def winfo_width(self): return 400
            def winfo_height(self): return 400
        app.sky_canvas = Canvas()
        app.sky_status = object()
        app.sky_scene_requests = queue.Queue(maxsize=1)
        app.sky_scene_results = queue.Queue(maxsize=1)
        app.sky_scene_requested_key = None
        app.sky_scene_worker_closed = False
        app.sky_last_scene = None
        app.sky_map_cache_key = None
        app.target_active = False
        app.target_solar_system_name = None
        app.named_stars_jnow = []
        app.mount_show_reticle = True
        app.language = "en"
        app.sky_magnitude_limit = 4
        app.sky_show_altaz_grid = True
        app.sky_show_equatorial_grid = True
        app.sky_show_solar_system = False
        app.card_edge = app.muted = app.accent = app.ebg = "#001122"
        app._active_site_coordinates = lambda: (48.8, 2.2)
        app.applied = []
        app._apply_sky_map_scene = app.applied.append
        return app

    def test_latest_request_replaces_queued_work_and_stale_results_are_ignored(self):
        app = self.fake_app()
        state = {"lst": "05:00:00"}
        with patch.object(app_skymap.time, "monotonic", return_value=16):
            app._update_sky_map(state)
            original = app.sky_scene_requests.get_nowait()
            app.language = "fr"
            app._update_sky_map(state)
            app.sky_show_equatorial_grid = False
            app.sky_scene_results.put((original["key"], {"key": original["key"]}, None))
            app._update_sky_map(state)
            self.assertEqual(app.applied, [])
            self.assertEqual(app.sky_scene_requests.qsize(), 1)
            newest = app.sky_scene_requests.get_nowait()
            self.assertEqual(newest["language"], "fr")
            self.assertFalse(newest["options"]["sky_show_equatorial_grid"])
            app.sky_scene_results.put((newest["key"], {"key": newest["key"]}, None))
            app._update_sky_map(state)
            self.assertEqual(app.applied, [{"key": newest["key"]}])
            self.assertTrue(app.sky_scene_requests.empty())

    def test_slow_valid_scene_is_shown_even_after_refresh_tick(self):
        app = self.fake_app()
        state = {"lst": "05:00:00"}
        with patch.object(app_skymap.time, "monotonic", return_value=16):
            app._update_sky_map(state)
        request = app.sky_scene_requests.get_nowait()
        app.sky_scene_results.put((request["key"], {"key": request["key"]}, None))
        with patch.object(app_skymap.time, "monotonic", return_value=24):
            app._update_sky_map(state)
        self.assertEqual(len(app.applied), 1)
        self.assertEqual(app.sky_scene_requests.qsize(), 1)


if __name__ == "__main__":
    unittest.main()
