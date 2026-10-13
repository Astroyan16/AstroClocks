import unittest
from unittest.mock import Mock, patch

from astroclocks.app import AstroClocksApp
from astroclocks.app_object_search import _target_catalog_links


class DeepSkyOnlineEnrichmentTests(unittest.TestCase):
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
        with patch("astroclocks.app_deep_sky.fetch_simbad_deep_sky_objects", return_value=[]), patch(
            "astroclocks.app_deep_sky.fetch_simbad_deep_sky_details", return_value=[remote]
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
