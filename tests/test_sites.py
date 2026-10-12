import math
import unittest

from astroclocks.sites import LOCATION_PRESETS, preset_label


class SitePresetTests(unittest.TestCase):
    def test_all_presets_have_valid_elevations_and_unique_labels(self):
        self.assertEqual(len(LOCATION_PRESETS), 152)
        self.assertEqual(len({preset_label(site) for site in LOCATION_PRESETS}), 152)
        for site in LOCATION_PRESETS:
            with self.subTest(site=site["name"]):
                self.assertTrue(math.isfinite(site["altitude_m"]))
                self.assertGreaterEqual(site["altitude_m"], -500)
                self.assertLessEqual(site["altitude_m"], 9000)

    def test_published_observatory_elevations(self):
        sites = {site["name"]: site for site in LOCATION_PRESETS}
        for name, altitude in (
            ("Observatoire de Meudon - T1m", 162),
            ("Observatoire de Meudon - T60", 162),
            ("Observatoire de Nice", 375),
            ("Observatoire du Pic du Midi", 2877),
            ("Observatoire de Haute-Provence", 650),
        ):
            self.assertEqual(sites[name]["altitude_m"], altitude)

    def test_paris_presets_share_the_same_point_elevation(self):
        sites = [site for site in LOCATION_PRESETS if site["name"] == "Paris"]
        self.assertEqual(len(sites), 2)
        self.assertEqual(sites[0]["altitude_m"], sites[1]["altitude_m"])
