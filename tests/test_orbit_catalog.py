import datetime
import unittest

from astroclocks.orbit_catalog import (
    _build_orbit_index,
    _build_orb6_index,
    _parse_orbit_line,
    enrich_double_stars_with_orb6,
    orbit_position_at_year,
)


class OrbitCatalogTests(unittest.TestCase):
    def test_orb6_period_keeps_leading_digit(self):
        line = (
            "092827.41+090324.4 09285+0903 STF1356         7390  81858  46454"
            "   5.69   7.28  43089.      d  26.         0.8599 a  0.0022"
            "   65.347    0.093  325.982     0.074  36649.      m  11."
            "       0.5619   0.0014   302.54     0.14   2000 2008 2 n"
            " Mut2010b wds09285+0903b.png"
        )

        orbit = _parse_orbit_line(line)

        self.assertIsNotNone(orbit)
        self.assertEqual(orbit["period_value"], 43089.0)
        self.assertAlmostEqual(orbit["period_years"], 43089.0 / 365.25)

    def test_wds_09285_orbit_matches_orb6_ephemeris_near_2026(self):
        line = (
            "092827.41+090324.4 09285+0903 STF1356         7390  81858  46454"
            "   5.69   7.28  43089.      d  26.         0.8599 a  0.0022"
            "   65.347    0.093  325.982     0.074  36649.      m  11."
            "       0.5619   0.0014   302.54     0.14   2000 2008 2 n"
            " Mut2010b wds09285+0903b.png"
        )

        orbit = _parse_orbit_line(line)
        position = orbit_position_at_year(orbit, 2026.3260273972603)

        self.assertAlmostEqual(position["rho"], 0.964, places=3)
        self.assertAlmostEqual(position["theta"], 120.4, places=1)

    def test_high_eccentricity_orbit_stays_stable_near_periastron(self):
        line = (
            "130346.09-203500.3 13038-2035 BU  341         8757 113415  63738"
            "   6.25   6.51     58.53    y   0.19       0.815  a  0.091"
            "    91.8      0.3    135.5       0.5     2023.731   y   0.018"
            "    0.9882   0.0021   239.3      3.8    2000 2024 3 n Tok2024b"
            " wds13038-2035b.png"
        )

        orbit = _parse_orbit_line(line)
        position = orbit_position_at_year(orbit, 2025.0)

        self.assertAlmostEqual(position["rho"], 0.247, places=3)
        self.assertAlmostEqual(position["theta"], 133.9, places=1)

    def test_arcminute_orbit_ephemeris_is_scaled_to_arcseconds(self):
        orbit_line = (
            "143940.90-605006.5 14396-6050 LDS 494AC      .     128620  71683"
            "   0.14  12.7    5470.      c 530.       188.62   M 11.92"
            "    107.6      1.9    126.        5.      2850.      c  50."
            "       0.50     0.09      72.3      7.7    2000      5 n Krv2017"
            "  wds14396-6050f.png"
        )
        orbit = _parse_orbit_line(orbit_line)
        orb6_index = _build_orb6_index(
            [
                {
                    "wds": "14396-6050",
                    "designation": "LDS 494AC",
                    "designation_key": "LDS494AC",
                    "grade": 5,
                    "reference": "Krv2017",
                    "predictions": [
                        {
                            "year": 2025.0,
                            "theta": 266.3,
                            "rho": 126.023,
                            "rho_precision": 3,
                        }
                    ],
                    "notes": "",
                }
            ]
        )
        orbit_index = _build_orbit_index([orbit])

        enriched, matched = enrich_double_stars_with_orb6(
            [{"wds": "14396-6050", "designation": "LDS 494AC"}],
            orb6_index,
            when=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
            orbit_index=orbit_index,
        )

        self.assertEqual(matched, 1)
        self.assertAlmostEqual(enriched[0]["orb6_current_separation"], 7561.38, places=2)
        self.assertEqual(enriched[0]["orb6_separation_precision"], 2)


if __name__ == "__main__":
    unittest.main()
