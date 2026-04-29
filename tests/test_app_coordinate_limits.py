import unittest

from astroclocks.app import AstroClocksApp


class AppCoordinateLimitTests(unittest.TestCase):
    def setUp(self):
        self.app = AstroClocksApp.__new__(AstroClocksApp)

    def test_declination_sanitization_excludes_exact_poles(self):
        self.assertEqual(
            self.app._sanitize_declination_fields(90, 12, 34),
            ("89", "59", "59"),
        )
        self.assertEqual(
            self.app._sanitize_declination_fields(-90, 12, 34),
            ("-89", "59", "59"),
        )

    def test_coordinate_formatting_excludes_exact_poles(self):
        self.assertEqual(self.app._coordinates_to_fields(0, 90)[3:], (89, 59, 59))
        self.assertEqual(self.app._coordinates_to_fields(0, -90)[3:], (-89, 59, 59))


if __name__ == "__main__":
    unittest.main()
