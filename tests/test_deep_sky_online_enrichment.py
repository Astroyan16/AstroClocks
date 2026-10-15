import datetime
import threading
import unittest
from unittest.mock import Mock, patch

from astroclocks.app import AstroClocksApp
from astroclocks.app_object_search import _target_catalog_links
from astroclocks.astronomy import convert_star_catalog_j2000_to_jnow, j2000_to_jnow_coordinates


class DeepSkyOnlineEnrichmentTests(unittest.TestCase):
    def test_batch_precession_preserves_order_existing_jnow_and_input_records(self):
        epoch = datetime.datetime(2026, 10, 15, tzinfo=datetime.timezone.utc)
        objects = [
            dict(name="south", ra_hours=23.9, declination=-70, magnitude=8),
            dict(name="already converted", ra_hours=0.1, declination=30, coordinate_frame="jnow"),
            dict(name="north", ra_hours=2.3, declination=85),
        ]
        original = [dict(item) for item in objects]
        app = AstroClocksApp.__new__(AstroClocksApp)
        with patch("astroclocks.app_deep_sky.convert_star_catalog_j2000_to_jnow",
                   side_effect=lambda stars: convert_star_catalog_j2000_to_jnow(stars, now_utc=epoch)):
            result = app._deep_sky_objects_to_jnow(objects)
        self.assertEqual(objects, original)
        self.assertEqual([item["name"] for item in result], [item["name"] for item in objects])
        self.assertEqual(result[1], objects[1])
        for index in (0, 2):
            expected = j2000_to_jnow_coordinates(objects[index]["ra_hours"], objects[index]["declination"], now_utc=epoch)
            self.assertAlmostEqual(result[index]["ra_hours"], expected[0], places=10)
            self.assertAlmostEqual(result[index]["declination"], expected[1], places=10)
            self.assertEqual(result[index]["coordinate_frame"], "jnow")

    def test_query_timeout_keeps_local_results_and_reports_timeout(self):
        local = dict(name="NGC 71", category="galaxy", source="OpenNGC", aliases=(),
                     ra_hours=0.3, declination=30, magnitude=12.1, magnitude_band="V")
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.language = "fr"
        app._deep_sky_visibility_context = lambda context: []
        app._deep_sky_catalog = lambda band: [local]
        app._deep_sky_offline_cache_note = lambda: None
        app._filter_deep_sky_list = lambda catalog, filters, context: list(catalog)
        app._queue_deep_sky_search_results = Mock()
        filters = dict(category="galaxy", magnitude_band="V", min_magnitude=-2,
                       max_magnitude=13, use_magnitude=True)
        with patch("astroclocks.app_deep_sky.fetch_simbad_deep_sky_objects",
                   side_effect=TimeoutError("The read operation timed out")), patch(
            "astroclocks.app_deep_sky.log_exception"
        ), patch("astroclocks.app_deep_sky.fetch_simbad_deep_sky_details", return_value=[]):
            app._run_deep_sky_search(1, filters, {}, allow_online=True)
        payload = app._queue_deep_sky_search_results.call_args.args[1]
        self.assertEqual(payload["objects"], [local])
        self.assertIn("Délai de réponse", payload["note"])
        self.assertNotIn("indisponible", payload["note"])

    def test_online_results_enrich_local_objects_missing_from_discovery_query(self):
        local = dict(name="NGC 71", category="galaxy", source="OpenNGC", aliases=(),
                     ra_hours=0.3, declination=30, magnitude=14.1, magnitude_band="V")
        remote = dict(name="NGC    71", source_id="NGC    71", category="galaxy",
                      source="SIMBAD/CDS", aliases=("NGC 71",), ra_hours=0.31,
                      declination=30.1, magnitude=14.2, magnitude_band="V", object_type="G")
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.language = "fr"
        app._deep_sky_visibility_context = lambda context: []
        app._deep_sky_catalog = lambda band: [local]
        app._deep_sky_offline_cache_note = lambda: None
        app._filter_deep_sky_list = lambda catalog, filters, context: list(catalog)
        app._queue_deep_sky_search_results = Mock()
        filters = dict(category="galaxy", magnitude_band="V", min_magnitude=14,
                       max_magnitude=18, use_magnitude=True)
        enrichment_started = threading.Event()
        def discover(*args, **kwargs):
            if not enrichment_started.wait(5):
                raise AssertionError("Discovery must overlap local enrichment")
            return []
        def details(*args):
            enrichment_started.set()
            return [remote]
        with patch("astroclocks.app_deep_sky.fetch_simbad_deep_sky_objects", side_effect=discover), patch(
            "astroclocks.app_deep_sky.fetch_simbad_deep_sky_details", side_effect=details
        ) as enrich, patch("astroclocks.app_deep_sky.merge_cached_simbad_deep_sky_objects",
                           side_effect=lambda objects, category: objects), patch(
            "astroclocks.app_deep_sky.deep_sky_search_objects", return_value=[local]
        ):
            app._run_deep_sky_search(1, filters, {}, allow_online=True)
        enrich.assert_called_once_with([local], "V")
        result = app._queue_deep_sky_search_results.call_args.args[1]["objects"][0]
        self.assertEqual(result["declination"], 30.1)
        self.assertEqual(result["magnitude"], 14.2)
        self.assertIn("SIMBAD", result["source"])
        self.assertIn("SIMBAD", app._format_deep_sky_source(result))
        self.assertEqual(_target_catalog_links(result)[0][0], "SIMBAD/CDS")
