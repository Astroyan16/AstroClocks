import unittest

from astroclocks.deep_sky_catalog import (
    _append_simbad_band_rows,
    deep_sky_category_for_type,
    deep_sky_search_objects,
    merge_deep_sky_objects,
)
from astroclocks.app import AstroClocksApp


class DeepSkyCatalogTests(unittest.TestCase):
    def test_openngc_objects_include_category_and_photometry(self):
        objects = {}
        for sky_object in deep_sky_search_objects():
            keys = {sky_object["name"], *sky_object["aliases"]}
            if "NGC 224" in keys:
                objects["NGC 224"] = sky_object
            if "NGC 6205" in keys:
                objects["NGC 6205"] = sky_object

        self.assertEqual(objects["NGC 224"]["category"], "galaxy")
        self.assertIsNotNone(objects["NGC 224"]["magnitude"])
        self.assertIn(objects["NGC 224"]["magnitude_band"], {"V", "B"})
        self.assertEqual(objects["NGC 6205"]["category"], "globular_cluster")

    def test_requested_type_groups_are_mapped(self):
        self.assertEqual(deep_sky_category_for_type("PN"), "planetary_nebula")
        self.assertEqual(deep_sky_category_for_type("HII"), "emission_nebula")
        self.assertEqual(deep_sky_category_for_type("RfN"), "reflection_nebula")
        self.assertEqual(deep_sky_category_for_type("DrkN"), "dark_nebula")
        self.assertEqual(deep_sky_category_for_type("SNR"), "supernova_remnant")
        self.assertEqual(deep_sky_category_for_type("GGroup"), "galaxy_cluster")

    def test_supplemental_quasar_catalog_is_available(self):
        quasars = [
            sky_object
            for sky_object in deep_sky_search_objects()
            if sky_object["category"] == "quasar"
        ]

        self.assertTrue(any(sky_object["name"] == "3C 273" for sky_object in quasars))

    def test_dark_nebula_search_ignores_magnitude_filter(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app._deep_sky_objects_to_jnow = lambda sky_objects: list(sky_objects)
        app._deep_sky_visibility_metrics = lambda _sky_object, _context: {
            "max_altitude": 35,
            "max_night_altitude": 25,
            "visible_at_night": True,
        }
        catalog = [
            {
                "name": "B033",
                "category": "dark_nebula",
                "magnitude": None,
                "ra_hours": 5.68,
                "declination": -2.45,
            }
        ]

        dark_filters = {
            "category": "dark_nebula",
            "use_magnitude": False,
            "min_magnitude": None,
            "max_magnitude": None,
            "min_altitude": 10,
            "visible_night": True,
        }
        magnitude_filters = {
            **dark_filters,
            "use_magnitude": True,
            "min_magnitude": -2,
            "max_magnitude": 15,
        }

        self.assertEqual(len(app._filter_deep_sky_list(catalog, dark_filters, [])), 1)
        self.assertEqual(len(app._filter_deep_sky_list(catalog, magnitude_filters, [])), 0)

    def test_merge_deep_sky_objects_deduplicates_local_and_simbad_entries(self):
        local = {
            "name": "IC 10",
            "aliases": ("IC10",),
            "ra_hours": 0.33815,
            "declination": 59.30377778,
            "object_type": "G",
            "category": "galaxy",
            "magnitude": 10.35,
            "magnitude_band": "V",
            "source": "OpenNGC",
        }
        remote = {
            "name": "IC   10",
            "aliases": (),
            "ra_hours": 0.3381486666666667,
            "declination": 59.3037911111111,
            "object_type": "rG",
            "category": "galaxy",
            "morphology": "IBm",
            "magnitude": 9.5,
            "magnitude_band": "V",
            "source": "SIMBAD/CDS",
            "source_id": "IC   10",
        }

        merged = merge_deep_sky_objects([local], [remote])

        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["name"], "IC 10")
        self.assertEqual(merged[0]["magnitude"], 9.5)
        self.assertEqual(merged[0]["morphology"], "IBm")
        self.assertIn("IC10", merged[0]["aliases"])
        self.assertIn("IC   10", merged[0]["aliases"])
        self.assertEqual(merged[0]["source"], "OpenNGC + SIMBAD/CDS")

    def test_galaxy_type_label_includes_morphology(self):
        app = AstroClocksApp.__new__(AstroClocksApp)
        app._tr = lambda key, **_values: {
            "deep_sky.category.galaxy": "Galaxie",
            "deep_sky.category.open_cluster": "Amas ouvert",
        }[key]

        galaxy = {"category": "galaxy", "morphology": "SA(s)b"}
        cluster = {"category": "open_cluster", "morphology": "III 2 m"}

        self.assertEqual(app._deep_sky_category_label(galaxy), "Galaxie (SA(s)b)")
        self.assertEqual(app._deep_sky_category_label(cluster), "Amas ouvert")

    def test_simbad_band_rows_prefer_v_over_b(self):
        objects_by_id = {}

        _append_simbad_band_rows(
            objects_by_id,
            [["M  31", 10.684708333333333, 41.26875, "AGN", "SA(s)b", 4.36]],
            "B",
        )
        _append_simbad_band_rows(
            objects_by_id,
            [["M  31", 10.684708333333333, 41.26875, "AGN", "SA(s)b", 3.44]],
            "V",
        )

        self.assertEqual(len(objects_by_id), 1)
        self.assertEqual(objects_by_id["M  31"]["magnitude"], 3.44)
        self.assertEqual(objects_by_id["M  31"]["magnitude_band"], "V")
        self.assertEqual(objects_by_id["M  31"]["morphology"], "SA(s)b")


if __name__ == "__main__":
    unittest.main()
