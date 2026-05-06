import unittest
from unittest.mock import patch

from astroclocks.settings import AppSettings, normalize_settings
from astroclocks.star_search_catalog import (
    fetch_simbad_stars,
    local_star_search_objects,
    merge_star_search_objects,
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
        self.assertEqual(star_spectral_class("DA4"), "")
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
            return {
                "data": [["HD 146233", 219.902058, -37.793467, "*", "G2V", 5.49]]
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
        self.assertIn("flux.filter = 'V'", queries[0])
        self.assertIn("UPPER(basic.sp_type) LIKE 'G%'", queries[0])

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

    def test_star_search_merge_preserves_bands_by_coordinate(self):
        local_star = {
            "name": "Example",
            "ra_hours": 1.0,
            "declination": 2.0,
            "spectral_type": "G2V",
            "spectral_class": "G",
            "magnitude": 5.0,
            "magnitude_band": "V",
            "source": "BSC local",
            "source_id": "BSC 1",
        }
        cached_star = dict(local_star, magnitude=5.4, magnitude_band="B", source="SIMBAD/CDS")

        merged = merge_star_search_objects([local_star], [cached_star])

        self.assertEqual({star["magnitude_band"] for star in merged}, {"V", "B"})


if __name__ == "__main__":
    unittest.main()
