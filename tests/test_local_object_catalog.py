import unittest

from astroclocks.local_object_catalog import (
    normalize_local_object_name,
    resolve_local_object_coordinates,
)


class LocalObjectCatalogTests(unittest.TestCase):
    def test_local_catalog_accepts_accents_and_star_aliases(self):
        self.assertEqual(normalize_local_object_name("Bételgeuse"), "betelgeuse")
        result = resolve_local_object_coordinates("Alpha Orionis")
        self.assertIsNotNone(result)
        self.assertEqual(result["display_name"], "Betelgeuse")

    def test_local_catalog_resolves_messier_and_ngc_aliases(self):
        messier = resolve_local_object_coordinates("M31")
        ngc = resolve_local_object_coordinates("NGC 224")
        pleiades = resolve_local_object_coordinates("M45")
        self.assertIsNotNone(messier)
        self.assertIsNotNone(ngc)
        self.assertIsNotNone(pleiades)
        self.assertEqual(messier["source"], "local")
        self.assertEqual(messier["source_ra"], ngc["source_ra"])
        self.assertEqual(messier["source_dec"], ngc["source_dec"])


if __name__ == "__main__":
    unittest.main()
