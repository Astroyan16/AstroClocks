import datetime
import io
import re
import sqlite3
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs

from astroclocks.app import AstroClocksApp
from astroclocks.settings import AppSettings, normalize_settings
from astroclocks.star_search_catalog import (
    _normalize_cached_star,
    _fetch_simbad_json,
    _simbad_star_query,
    fetch_simbad_stars,
    local_star_search_objects,
    merge_star_search_objects,
    resolve_star_photometry,
    normalize_star_magnitude_band,
    normalize_star_spectral_type,
    star_spectral_class,
)


class StarSearchCatalogTests(unittest.TestCase):
    def test_normalizers_fall_back_to_defaults(self):
        self.assertEqual(normalize_star_spectral_type("x"), "G")
        self.assertEqual(normalize_star_magnitude_band("x"), "V")
        self.assertEqual(star_spectral_class("gG9"), "G")
        self.assertEqual(star_spectral_class("sdF8"), "F")
        self.assertEqual(star_spectral_class("DA4"), "D")
        settings = normalize_settings(
            AppSettings(
                star_search_spectral_type="x",
                star_search_magnitude_band="x",
            )
        )
        self.assertEqual(settings.star_search_spectral_type, "G")
        self.assertEqual(settings.star_search_magnitude_band, "V")

    def test_simbad_query_uses_selected_spectral_type_and_band(self):
        queries = []

        def fake_fetch(query, _timeout):
            queries.append(query)
            if "WHERE flux.filter = 'V'" in query:
                return {
                    "data": [["HD 146233", 219.902058, -37.793467, "*", "G2V", 5.49, "E"]]
                }
            return {
                "data": [[
                    "HD 146233", 219.902058, -37.793467, "*", "G2V",
                    5.49, "E", None, None, 5.70, None, None, None, None, None,
                    None, None, None, None, None, None
                ]]
            }

        with patch("astroclocks.star_search_catalog._fetch_simbad_json", side_effect=fake_fetch):
            stars = fetch_simbad_stars(
                "G",
                min_magnitude=-2,
                max_magnitude=8.5,
                magnitude_band="V",
            )

        self.assertEqual(len(stars), 1)
        self.assertEqual(stars[0]["spectral_class"], "G")
        self.assertEqual(stars[0]["magnitude_band"], "V")
        self.assertEqual(stars[0]["photometry"]["B"], 5.70)
        self.assertEqual(stars[0]["photometry"]["V"], 5.49)
        self.assertEqual(stars[0]["magnitude_flag"], "E")
        self.assertIn("flux.filter = 'V'", queries[0])
        self.assertIn("basic.sp_type LIKE 'G%'", queries[0])
        self.assertIn("basic.sp_type LIKE 'sdG%'", queries[0])
        self.assertIn("ORDER BY mag ASC, main_id ASC", queries[0])
        self.assertIn("LEFT JOIN flux AS flux_0", queries[1])

    def test_extended_spectral_families_and_subdwarfs(self):
        examples = {
            "WN6(h)-s": "WR", "WC8+O7.5III": "WR", "WO2": "WR",
            "[WC10]": "WR", "DA2.9": "D", "DBAZ3": "D", "DQ6": "D",
            "D3": "D", "C-N5": "C", "C-R3": "C", "N5": "C", "R2": "C",
            "S6-9/1-2e": "S", "MS5": "S", "SC7": "S",
            "L5": "L/T/Y", "T8": "L/T/Y", "Y2": "L/T/Y", "sdO6": "O",
            "sdB": "B", "esdM5": "M", "usdL3": "L/T/Y",
            "M3III+S": "M", "G2V+DA": "G",
        }
        for value, expected in examples.items():
            with self.subTest(value=value):
                self.assertEqual(star_spectral_class(value), expected)
                self.assertEqual(normalize_star_spectral_type(value), expected)
        for category in ("WR", "D", "C", "S", "L/T/Y"):
            with self.subTest(category=category):
                settings = normalize_settings(AppSettings(star_search_spectral_type=category))
                self.assertEqual(settings.star_search_spectral_type, category)
        for value in ("unknown", "SNIa-norm", "LBV", "Transient"):
            self.assertEqual(star_spectral_class(value), "")

    def test_simbad_extended_families_use_matching_prefixes(self):
        expected_patterns = {
            "WR": ("WN%", "WC%", "WO%", "[WC%"), "D": ("DA%", "DB%", "DQ%", "D3%"),
            "C": ("C%", "R%", "N%"), "S": ("S%", "MS%", "SC%"),
            "L/T/Y": ("L%", "T%", "Y%", "sdL%", "sdT%", "sdY%"),
            "B": ("B%", "sdB%"),
            "O": ("O%", "SDO%"),
        }
        for category, patterns in expected_patterns.items():
            query = _simbad_star_query(category, -2, 12, "V", 100)
            with self.subTest(category=category):
                for pattern in patterns:
                    self.assertIn(f"basic.sp_type LIKE '{pattern}'", query)
                self.assertIn("flux.flux BETWEEN -2 AND 12", query)
        self.assertIn("AND basic.sp_type NOT LIKE 'MS%'",
                      _simbad_star_query("M", -2, 12, "V", 100))

    def test_query_selects_families_without_supernovae_or_lbv(self):
        examples = (
            ("WN6+O5", "WR"), ("[WC10]", "WR"), ("DA2.9", "D"),
            ("C-N5", "C"), ("S6e", "S"), ("MS5", "S"), ("SC7", "S"),
            ("M3III", "M"), ("sdM5", "M"), ("sdB2", "B"),
            ("L5", "L/T/Y"), ("T8", "L/T/Y"), ("sdY2", "L/T/Y"),
            ("L?", "L/T/Y"), ("Swk", "S"),
            ("SNIa-norm", ""), ("LBV", ""),
        )
        with sqlite3.connect(":memory:") as database:
            database.create_function(
                "regexp", 2, lambda value, pattern: int(re.search(pattern, value or "") is not None)
            )
            database.execute("CREATE TABLE basic (oid, main_id, ra, dec, otype, sp_type)")
            database.execute("CREATE TABLE flux (oidref, filter, flux, qual)")
            for index, (spectral, _category) in enumerate(examples):
                database.execute("INSERT INTO basic VALUES (?, ?, 15, 30, '*', ?)",
                                 (index, spectral, spectral))
                database.execute("INSERT INTO flux VALUES (?, 'V', 8, 'C')", (index,))
            for category in ("WR", "D", "C", "S", "M", "B", "L/T/Y"):
                query = _simbad_star_query(category, -2, 12, "V", 100)
                query = query.replace("SELECT TOP 100", "SELECT", 1)
                names = {row[0] for row in database.execute(query)}
                with self.subTest(category=category):
                    self.assertEqual(names, {s for s, c in examples if c == category})

    def test_combined_family_queries_keep_compact_indexable_prefix_filters(self):
        for category in ("S", "L/T/Y"):
            with self.subTest(category=category):
                query = _simbad_star_query(category, -2, 18, "V", 5000)
                self.assertLessEqual(query.count(" LIKE "), 21)
                self.assertIn("1 = regexp(basic.sp_type,", query)
                self.assertLess(len(query), 2000)
                self.assertNotIn("\\", query)

    def test_cache_reclassifies_previously_misidentified_spectra(self):
        star = _normalize_cached_star({
            "name": "WR example", "ra_hours": 1, "declination": 2,
            "spectral_type": "WC8+O7", "spectral_class": "O",
            "magnitude": 8, "magnitude_band": "V",
        })
        self.assertEqual(star["spectral_class"], "WR")

    def test_long_spectral_queries_use_post(self):
        query = _simbad_star_query("L/T/Y", -2, 12, "V", 100)
        with patch("astroclocks.star_search_catalog.urlopen",
                   return_value=io.BytesIO(b'{"data": []}')) as open_url:
            self.assertEqual(_fetch_simbad_json(query, 20), {"data": []})
        self.assertNotIn("?", open_url.call_args.args[0])
        form = parse_qs(open_url.call_args.kwargs["data"].decode("utf-8"))
        self.assertEqual(form["query"], [query])
        self.assertEqual(open_url.call_args.kwargs["timeout"], 20)

    def test_local_star_search_uses_enriched_sky_catalog(self):
        stars = local_star_search_objects()
        self.assertGreater(len(stars), 5500)

        by_name = {star["name"]: star for star in stars}
        self.assertEqual(by_name["Sirius"]["spectral_class"], "A")
        self.assertEqual(by_name["Sirius"]["magnitude_band"], "V")
        self.assertEqual(by_name["Sirius"]["source"], "BSC local")
        self.assertEqual(by_name["Betelgeuse"]["spectral_class"], "M")

        default_g_stars = [
            star
            for star in stars
            if star["spectral_class"] == "G" and star["magnitude_band"] == "V"
        ]
        self.assertGreater(len(default_g_stars), 100)

    def test_star_search_merge_combines_photometry_by_coordinate(self):
        local_star = {
            "name": "Example",
            "ra_hours": 1.0,
            "declination": 2.0,
            "aliases": (),
            "spectral_type": "G2V",
            "spectral_class": "G",
            "magnitude": 5.0,
            "magnitude_band": "V",
            "photometry": {"V": 5.0},
            "source": "BSC local",
            "source_id": "BSC 1",
        }
        cached_star = dict(
            local_star,
            magnitude=5.4,
            magnitude_band="B",
            photometry={"B": 5.4},
            source="SIMBAD/CDS",
        )

        merged = merge_star_search_objects([local_star], [cached_star], preferred_band="B")

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["magnitude_band"], "B")
        self.assertEqual(merged[0]["magnitude"], 5.4)
        self.assertEqual(merged[0]["photometry"]["V"], 5.0)
        self.assertEqual(merged[0]["photometry"]["B"], 5.4)

    def test_star_search_merge_deduplicates_local_and_simbad_alias_names(self):
        local_star = {
            "name": "HR 6175",
            "ra_hours": 16.61930556,
            "declination": -10.567222,
            "aliases": (),
            "spectral_type": "O9.5Vn",
            "spectral_class": "O",
            "magnitude": 2.56,
            "magnitude_band": "V",
            "source": "BSC local",
            "source_id": "BSC 6175",
        }
        cached_star = {
            "name": "* zet Oph",
            "ra_hours": 16.61931668,
            "declination": -10.56708604,
            "aliases": (),
            "object_type": "Be*",
            "spectral_type": "O9.2IVnn",
            "spectral_class": "O",
            "magnitude": 2.56,
            "magnitude_band": "V",
            "source": "SIMBAD/CDS",
            "source_id": "* zet Oph",
        }

        merged = merge_star_search_objects([local_star], [cached_star])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["name"], "* zet Oph")
        self.assertIn("HR 6175", merged[0]["aliases"])
        self.assertEqual(merged[0]["source"], "BSC local + SIMBAD/CDS")

    def test_star_search_merge_does_not_repeat_simbad_source(self):
        local_star = {
            "name": "HR 1865",
            "ra_hours": 5.58563889,
            "declination": 9.93416667,
            "aliases": (),
            "spectral_type": "O8III",
            "spectral_class": "O",
            "magnitude": 3.39,
            "magnitude_band": "V",
            "source": "BSC local + SIMBAD/CDS",
            "source_id": "BSC 1865",
        }
        cached_star = {
            "name": "* lam Ori",
            "ra_hours": 5.58564000,
            "declination": 9.93415000,
            "aliases": ("Meissa",),
            "object_type": "*",
            "spectral_type": "O8III",
            "spectral_class": "O",
            "magnitude": 3.39,
            "magnitude_band": "V",
            "source": "SIMBAD/CDS",
            "source_id": "* lam Ori",
        }

        merged = merge_star_search_objects([local_star], [cached_star])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["source"], "BSC local + SIMBAD/CDS")
        self.assertIn("HR 1865", merged[0]["aliases"])
        self.assertIn("Meissa", merged[0]["aliases"])

    def test_resolve_star_photometry_switches_to_cached_band(self):
        star = {
            "name": "M101 test star",
            "ra_hours": 1.0,
            "declination": 2.0,
            "aliases": (),
            "spectral_type": "G2V",
            "spectral_class": "G",
            "magnitude": 5.49,
            "magnitude_band": "V",
            "photometry": {"V": 5.49, "B": 5.70},
            "source": "SIMBAD/CDS",
            "source_id": "HD 146233",
        }

        resolved = resolve_star_photometry(star, preferred_band="B")

        self.assertEqual(resolved["magnitude_band"], "B")
        self.assertEqual(resolved["magnitude"], 5.70)

    def test_star_search_filter_can_exclude_suspect_magnitude_flags(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app._deep_sky_visibility_context = lambda: []
        app._deep_sky_visibility_metrics = lambda _star, _context: {
            "max_altitude": 55,
            "max_night_altitude": 48,
            "visible_at_night": True,
        }
        app._stars_to_jnow = lambda stars: list(stars)

        stars = [
            {
                "name": "Suspect star",
                "spectral_class": "G",
                "magnitude_band": "V",
                "magnitude": 7.0,
                "magnitude_flag": "E",
                "ra_hours": 5.0,
                "declination": 20.0,
            },
            {
                "name": "Clean star",
                "spectral_class": "G",
                "magnitude_band": "V",
                "magnitude": 7.1,
                "magnitude_flag": "",
                "ra_hours": 6.0,
                "declination": 22.0,
            },
        ]
        filters = {
            "spectral_type": "G",
            "magnitude_band": "V",
            "min_magnitude": -2,
            "max_magnitude": 8.5,
            "min_altitude": 10,
            "visible_night": True,
            "exclude_suspect_magnitudes": True,
        }

        filtered = app._filter_star_search_list(stars, filters, [])

        self.assertEqual([star["name"] for star in filtered], ["Clean star"])

    def test_transit_time_sort_uses_actual_datetime_order(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app.star_search_sort_column = "transit_time"

        late_evening = datetime.datetime(
            2026, 5, 7, 23, 30, tzinfo=datetime.timezone.utc
        )
        after_midnight = datetime.datetime(
            2026, 5, 8, 0, 30, tzinfo=datetime.timezone.utc
        )

        first_value = app._star_search_sort_value(
            {
                "name": "Late evening transit",
                "meridian_transit_local_datetime": late_evening,
                "meridian_transit_sort_timestamp": late_evening.timestamp(),
            }
        )
        second_value = app._star_search_sort_value(
            {
                "name": "After midnight transit",
                "meridian_transit_local_datetime": after_midnight,
                "meridian_transit_sort_timestamp": after_midnight.timestamp(),
            }
        )

        self.assertLess(first_value, second_value)


if __name__ == "__main__":
    unittest.main()
