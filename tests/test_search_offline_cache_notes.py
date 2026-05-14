import unittest
from types import SimpleNamespace

from astroclocks.app_deep_sky import _run_deep_sky_search
from astroclocks.app_double_stars import _run_double_star_search
from astroclocks.app_star_search import _run_star_search


class SearchOfflineCacheNotesTests(unittest.TestCase):
    def test_deep_sky_offline_search_mentions_cached_simbad_entries(self):
        captured = {}

        app = SimpleNamespace(
            network_online=False,
            deep_sky_simbad_cached_objects=[{"name": "A"}, {"name": "B"}],
            _tr=lambda key, **values: f"{key}:{values.get('count', values.get('error', ''))}",
            _deep_sky_visibility_context=lambda search_context=None: {},
            _deep_sky_catalog=lambda preferred_band=None: [],
            _deep_sky_offline_cache_note=lambda: "deep_sky.offline_cached:2",
            _filter_deep_sky_list=lambda catalog, filters, visibility_context=None: [],
            _queue_deep_sky_search_results=lambda generation, payload: captured.update(payload),
        )

        _run_deep_sky_search(
            app,
            generation=1,
            filters={"category": "galaxy", "magnitude_band": "V", "use_magnitude": True},
            search_context={},
            allow_online=False,
            offline_note=None,
        )

        self.assertIn("deep_sky.offline_cached:2", captured["note"])

    def test_star_offline_search_mentions_cached_simbad_stars(self):
        captured = {}

        app = SimpleNamespace(
            network_online=False,
            star_search_cached_stars=[{"name": "A"}, {"name": "B"}, {"name": "C"}],
            _tr=lambda key, **values: f"{key}:{values.get('count', values.get('error', ''))}",
            _deep_sky_visibility_context=lambda search_context=None: {},
            _star_search_catalog=lambda cached_stars=None, spectral_type=None, magnitude_band=None: [],
            _star_search_offline_cache_note=lambda: "star_search.offline_cached:3",
            _filter_star_search_list=lambda catalog, filters, visibility_context=None: [],
            _queue_star_search_results=lambda generation, payload: captured.update(payload),
        )

        _run_star_search(
            app,
            generation=1,
            filters={"spectral_type": "G", "magnitude_band": "V"},
            search_context={},
            allow_online=False,
            offline_note=None,
        )

        self.assertIn("star_search.offline_cached:3", captured["note"])

    def test_double_offline_search_mentions_cached_wds_entries(self):
        captured = {}

        app = SimpleNamespace(
            network_online=False,
            double_wds_cached_stars=[{"name": "A"}],
            double_orb6_index=None,
            double_orb6_orbit_index=None,
            _tr=lambda key, **values: f"{key}:{values.get('count', values.get('error', ''))}",
            _double_visibility_context=lambda search_context=None: {},
            _double_offline_cache_note=lambda: "double.offline_cached:1",
            _double_local_catalog=lambda: [],
            _enrich_double_star_orbits=lambda catalog, orb6_index, orb6_orbit_index=None: (catalog, 0),
            _filter_double_star_list=lambda catalog, filters, visibility_context=None: [],
            _double_orb6_status_note=lambda count, orb6_index: None,
            _queue_double_star_search_results=lambda generation, payload: captured.update(payload),
        )

        _run_double_star_search(
            app,
            generation=1,
            filters={
                "max_primary": 8,
                "max_secondary": 10,
                "min_sep": 0.5,
                "max_sep": 20,
                "include_physical": True,
                "include_noted": True,
                "include_apparent": True,
                "include_uncertain": True,
            },
            allow_online=False,
            search_context={},
            refresh_orbits=False,
        )

        self.assertIn("double.offline_cached:1", captured["note"])


if __name__ == "__main__":
    unittest.main()
