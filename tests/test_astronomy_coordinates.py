import datetime
import unittest

from astroclocks.astronomy import (
    j2000_to_jnow_coordinates,
    jnow_to_j2000_coordinates,
    normalize_miriade_object_name,
    normalize_sesame_object_name,
    resolve_local_solar_system_coordinates,
)


class CoordinateConversionTests(unittest.TestCase):
    def test_j2000_jnow_roundtrip_keeps_coordinates_close(self):
        observation_time = datetime.datetime(2026, 4, 29, 12, tzinfo=datetime.timezone.utc)
        ra_hours = 18.615649
        dec_degrees = 38.783689

        jnow_ra, jnow_dec = j2000_to_jnow_coordinates(
            ra_hours,
            dec_degrees,
            now_utc=observation_time,
        )
        roundtrip_ra, roundtrip_dec = jnow_to_j2000_coordinates(
            jnow_ra,
            jnow_dec,
            now_utc=observation_time,
        )

        self.assertAlmostEqual(roundtrip_ra, ra_hours, places=7)
        self.assertAlmostEqual(roundtrip_dec, dec_degrees, places=6)

    def test_miriade_name_normalization_accepts_accents(self):
        self.assertEqual(normalize_miriade_object_name("Vénus"), "Venus")
        self.assertEqual(normalize_miriade_object_name("Saturne"), "Saturn")

    def test_sesame_name_normalization_accepts_accents(self):
        self.assertEqual(normalize_sesame_object_name("Bételgeuse"), "Betelgeuse")

    def test_local_solar_system_coordinates_accept_accents(self):
        result = resolve_local_solar_system_coordinates(
            "Vénus",
            now_utc=datetime.datetime(2026, 4, 29, 12, tzinfo=datetime.timezone.utc),
        )
        self.assertIsNotNone(result)
        self.assertEqual(result["source"], "local_solar")
        self.assertEqual(result["solar_system_name"], "Venus")


if __name__ == "__main__":
    unittest.main()
