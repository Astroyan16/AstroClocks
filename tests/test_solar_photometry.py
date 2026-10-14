import datetime
import math
import erfa
import numpy as np
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from astroclocks import astronomy
from astroclocks.app_object_search import _target_information_text
from astroclocks.i18n import translate
from astroclocks.solar_photometry import AU_KM, estimate_visual_magnitude


class SolarPhotometryTests(unittest.TestCase):
    def test_year_fraction_handles_leap_year_without_future_utc_conversion(self):
        utc = datetime.timezone.utc
        self.assertEqual(astronomy._photometry_decimal_year(datetime.datetime(2024, 1, 1, tzinfo=utc)), 2024)
        self.assertEqual(astronomy._photometry_decimal_year(datetime.datetime(2024, 7, 2, tzinfo=utc)), 2024.5)
        self.assertEqual(astronomy._photometry_decimal_year(datetime.datetime(2023, 7, 2, 12, tzinfo=utc)), 2023.5)

    def test_local_ephemerides_do_not_construct_future_year_for_photometry(self):
        original = erfa.dtf2d
        def reject_future_utc(scale, year, *args, **kwargs):
            if scale in (b"UTC", "UTC") and np.any(np.asarray(year) > 2026):
                raise AssertionError("Synthetic future UTC conversion")
            return original(scale, year, *args, **kwargs)
        now = datetime.datetime(2026, 10, 14, 12, tzinfo=datetime.timezone.utc)
        with patch.object(erfa, "dtf2d", side_effect=reject_future_utc):
            result = astronomy.resolve_local_solar_system_coordinates("Mars", now, 48.8, 2.2)
            positions = astronomy.compute_solar_system_positions(48.8, 2.2, now)
        self.assertIsNotNone(result["magnitude"])
        self.assertEqual(len(positions), 9)

    def test_sun_distance_scaling_and_planet_distance_scaling(self):
        self.assertAlmostEqual(estimate_visual_magnitude("Sun", (1, 0, 0), (1, 0, 0)), -26.74)
        self.assertAlmostEqual(estimate_visual_magnitude("Sun", (2, 0, 0), (2, 0, 0)), -25.23485, places=4)
        # Jupiter at zero phase: Mallama & Hilton eq. 8, absolute V=-9.395.
        near = estimate_visual_magnitude("Jupiter", (1, 0, 0), (-1, 0, 0))
        far = estimate_visual_magnitude("Jupiter", (2, 0, 0), (-2, 0, 0))
        self.assertAlmostEqual(near, -7.88985, places=4)
        self.assertAlmostEqual(far-near, 3.01030, places=4)

    def test_moon_phase_and_validity_limits(self):
        distance = 384400/AU_KM
        full = estimate_visual_magnitude("Moon", (distance, 0, 0), (-1, 0, 0))
        quarter = estimate_visual_magnitude("Moon", (0, distance, 0), (-1, 0, 0))
        self.assertAlmostEqual(full, -12.73, delta=.01)
        self.assertAlmostEqual(quarter, -10.13, delta=.03)
        self.assertIsNone(estimate_visual_magnitude("Moon", (-distance, 0, 0), (-1, 0, 0)))
        self.assertIsNone(estimate_visual_magnitude("Pluto", (1, 0, 0), (-1, 0, 0)))
        self.assertIsNone(estimate_visual_magnitude("Mars", (0, 0, 0), (-1, 0, 0)))

    def test_saturn_rings_brighten_the_system_when_open(self):
        ra, dec = map(math.radians, (40.589, 83.537))
        pole = math.cos(dec)*math.cos(ra), math.cos(dec)*math.sin(ra), math.sin(dec)
        edge = (-math.sin(ra), math.cos(ra), 0)
        direction = tuple(math.sin(math.radians(25))*p + math.cos(math.radians(25))*e
                          for p, e in zip(pole, edge))
        magnitude_open = estimate_visual_magnitude("Saturn", tuple(9*x for x in direction), tuple(-x for x in direction), 2000)
        magnitude_edge = estimate_visual_magnitude("Saturn", tuple(9*x for x in edge), tuple(-x for x in edge), 2000)
        self.assertLess(magnitude_open, magnitude_edge-.8)

    def test_local_resolver_uses_one_body_position_and_exposes_distance(self):
        original = astronomy.get_body
        with patch.object(astronomy, "get_body", wraps=original) as get_body:
            result = astronomy.resolve_local_solar_system_coordinates(
                "Mars", now_utc=datetime.datetime(2026, 10, 14, 12, tzinfo=datetime.timezone.utc),
                latitude=48.8, longitude=2.2,
            )
        get_body.assert_called_once()
        self.assertAlmostEqual(result["magnitude"], 1.02, delta=.1)
        self.assertAlmostEqual(result["distance_au"], 1.569, delta=.005)
        self.assertTrue(result["magnitude_estimated"])
        app = SimpleNamespace(_tr=lambda key, **kw: translate("fr", key, **kw),
                              _object_type_display=lambda kind: "Planète")
        text = _target_information_text(app, result)
        self.assertIn("estimée", text)
        self.assertIn("UA", text)
        self.assertTrue(text.splitlines()[-1].startswith("Source des données"))

    def test_all_local_bodies_have_distance_and_moon_displays_kilometres(self):
        positions = astronomy.compute_solar_system_positions(
            48.8, 2.2, datetime.datetime(2026, 10, 14, 12, tzinfo=datetime.timezone.utc))
        self.assertEqual(len(positions), 9)
        for position in positions:
            self.assertGreater(position["distance_au"], 0)
            self.assertTrue(math.isfinite(position["magnitude"]))
        moon = next(p for p in positions if p["name"] == "Moon")
        self.assertGreater(moon["distance_km"], 350000)
        app = SimpleNamespace(_tr=lambda key, **kw: translate("en", key, **kw))
        self.assertIn("km", _target_information_text(app, dict(moon, source="local_solar")))
