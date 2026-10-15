import re
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from astroclocks import settings
from astroclocks.app import AstroClocksApp
from astroclocks.deep_sky_catalog import fetch_simbad_deep_sky_objects, merge_cached_simbad_deep_sky_objects
from astroclocks.star_search_catalog import fetch_simbad_stars, merge_cached_simbad_stars
from astroclocks.simbad_paging import (
    SimbadPage, after_condition, continuation, load_page_state, save_page_state,
)


class SimbadPagingTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings_patch = patch.object(settings, "SETTINGS_FILE", Path(self.directory.name) / "settings.ini")
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)

    def test_both_catalogues_page_through_equal_magnitudes_without_gaps_or_duplicates(self):
        with sqlite3.connect(":memory:") as database:
            database.execute("CREATE TABLE basic (oid, main_id, ra, dec, otype, morph_type, sp_type)")
            database.execute("CREATE TABLE allfluxes (oidref, V)")
            database.execute("CREATE TABLE flux (oidref, filter, flux, qual)")
            names = ["A", "B'quoted", "C", "D", "E"]
            for index, (name, magnitude) in enumerate(zip(names, [0.40000000596] * 3 + [1.10000002384] * 2)):
                database.execute("INSERT INTO basic VALUES (?, ?, ?, 20, 'G', '', 'G2V')",
                                 (index, name, 15 + index))
                database.execute("INSERT INTO allfluxes VALUES (?, ?)", (index, magnitude))
                database.execute("INSERT INTO flux VALUES (?, 'V', ?, 'E')", (index, magnitude))

            def fetch(query, timeout):
                match = re.search(r"SELECT TOP (\d+)", query)
                if match:
                    query = query.replace(match.group(0), "SELECT", 1) + f" LIMIT {match.group(1)}"
                rows = [list(row) for row in database.execute(query)]
                if match:
                    # SIMBAD serializes REAL magnitudes with fewer digits than
                    # their internal binary representation. Never page using
                    # this rounded number as the SQL comparison boundary.
                    for row in rows:
                        row[5] = float(f"{row[5]:.5g}")
                return {"data": rows}

            for kind in ("stars", "deep_sky"):
                with self.subTest(kind=kind), patch(f"astroclocks.{'star_search_catalog' if kind == 'stars' else 'deep_sky_catalog'}._fetch_simbad_json", side_effect=fetch):
                    received, cursor, more_flags = [], None, []
                    for _ in range(3):
                        if kind == "stars":
                            page = fetch_simbad_stars("G", -2, 13, row_limit=2, after=cursor, paged=True)
                        else:
                            page = fetch_simbad_deep_sky_objects("galaxy", -2, 13, row_limit=2, after=cursor, paged=True)
                        self.assertTrue(all(item["magnitude_flag"] == "E" for item in page))
                        received.extend(item["name"] for item in page)
                        more_flags.append(page.has_more)
                        cursor = page.cursor
                    self.assertEqual(received, names)
                    self.assertEqual(more_flags, [True, True, False])

    def test_exact_multiple_of_page_size_is_complete_without_an_empty_extra_page(self):
        page = SimbadPage([], [["A", 1], ["B", 1]], 2, magnitude_index=1)
        self.assertFalse(page.has_more)
        self.assertEqual(page.cursor, [1, "B"])
        self.assertEqual(after_condition(None, [None, "B'quoted"]), "\n  AND basic.main_id > 'B''quoted'")

    def test_resume_state_survives_restart_and_changed_query_starts_over(self):
        filters = dict(spectral_type="G", magnitude_band="V", min_magnitude=-2, max_magnitude=13)
        first = SimbadPage([], [["A", 1], ["B", 2], ["C", 3]], 2, magnitude_index=1)
        save_page_state("stars", filters, first)
        state = continuation("stars", filters, True)
        self.assertEqual(state["cursor"], [2, "B"])
        self.assertEqual(state["count"], 2)
        self.assertIsNone(continuation("stars", dict(filters, magnitude_band="B"), True))
        self.assertIsNone(continuation("stars", filters, False))
        last = SimbadPage([], [["C", 3]], 2, magnitude_index=1)
        save_page_state("stars", filters, last, state)
        self.assertEqual(load_page_state("stars")["count"], 3)
        self.assertIsNone(continuation("stars", filters, True))

    def test_next_page_appends_to_cache_and_new_search_replaces_the_category(self):
        for kind in ("stars", "deep_sky"):
            def item(name, ra):
                return dict(name=name, ra_hours=ra, declination=20, magnitude=3, magnitude_band="V",
                            spectral_type="G2V", spectral_class="G", category="galaxy")
            def merge(items, append=False):
                if kind == "stars":
                    return merge_cached_simbad_stars(items, "G", "V", append=append)
                return merge_cached_simbad_deep_sky_objects(items, "galaxy", append=append)
            with self.subTest(kind=kind):
                merge([item("A", 1)])
                self.assertEqual({x["name"] for x in merge([item("B", 2)], append=True)}, {"A", "B"})
                self.assertEqual({x["name"] for x in merge([item("C", 3)])}, {"C"})

    def test_both_pipelines_resume_after_failure_without_losing_previous_page(self):
        from astroclocks.deep_sky_catalog import load_cached_simbad_deep_sky_objects
        from astroclocks.star_search_catalog import load_cached_simbad_stars
        for kind in ("stars", "deep_sky"):
            with self.subTest(kind=kind):
                app = AstroClocksApp.__new__(AstroClocksApp)
                app.language = "fr"
                app.online_load_more = False
                app._deep_sky_visibility_context = lambda context: []
                app._star_search_offline_cache_note = lambda: None
                app._deep_sky_offline_cache_note = lambda: None
                app._star_search_catalog = lambda cached_stars=None, **kwargs: (
                    cached_stars if cached_stars is not None else load_cached_simbad_stars())
                app._deep_sky_catalog = lambda band: load_cached_simbad_deep_sky_objects()
                app._filter_star_search_list = lambda catalog, *args: list(catalog)
                app._filter_deep_sky_list = lambda catalog, *args: list(catalog)
                deliver = Mock()
                app._queue_star_search_results = deliver
                app._queue_deep_sky_search_results = deliver
                filters = dict(spectral_type="G", category="galaxy", use_magnitude=True,
                               magnitude_band="V", min_magnitude=-2, max_magnitude=13)
                def item(name, ra):
                    return dict(name=name, ra_hours=ra, declination=20, magnitude=ra,
                                magnitude_band="V", spectral_type="G2V", spectral_class="G", category="galaxy")
                first = SimbadPage([item("A", 1), item("B", 2)],
                                   [["A", 1], ["B", 2], ["C", 3]], 2, 1)
                last = SimbadPage([item("C", 3)], [["C", 3]], 2, 1)
                module = "astroclocks.app_star_search" if kind == "stars" else "astroclocks.app_deep_sky"
                function = "fetch_simbad_stars" if kind == "stars" else "fetch_simbad_deep_sky_objects"
                run = app._run_star_search if kind == "stars" else app._run_deep_sky_search
                with patch(f"{module}.{function}", side_effect=[first, TimeoutError("slow"), last]) as fetch, patch(
                    "astroclocks.app_deep_sky.fetch_simbad_deep_sky_details", return_value=[]
                ), patch("astroclocks.app_deep_sky.deep_sky_search_objects", return_value=[]), patch(
                    f"{module}.log_exception"
                ):
                    run(1, filters, {}, True)
                    state = load_page_state(kind)
                    self.assertTrue(state["has_more"])
                    app.online_load_more = True
                    run(2, filters, {}, True)
                    self.assertEqual(load_page_state(kind), state)
                    payload = deliver.call_args.args[1]
                    self.assertEqual({obj["name"] for obj in payload["stars" if kind == "stars" else "objects"]}, {"A", "B"})
                    run(3, filters, {}, True)
                    self.assertEqual(fetch.call_args.kwargs["after"], [2, "B"])
                    payload = deliver.call_args.args[1]
                    self.assertEqual({obj["name"] for obj in payload["stars" if kind == "stars" else "objects"]}, {"A", "B", "C"})
                    self.assertFalse(load_page_state(kind)["has_more"])
                    self.assertEqual(load_page_state(kind)["count"], 3)


if __name__ == "__main__":
    unittest.main()
