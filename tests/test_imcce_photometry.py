import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from astroclocks.astronomy import get_planet_coord, resolve_solar_system_coordinates
from astroclocks.app_object_search import _target_information_text
from astroclocks.i18n import translate


class ImccePhotometryTests(unittest.TestCase):
    def test_coordinates_and_magnitude_use_one_response(self):
        client = Mock()
        client.service.ephemcc.return_value = SimpleNamespace(flag=1, result=json.dumps(
            {"data": [{"RA": "+08:46:41.71655", "DEC": "+19:13:40.1941", "VMag": 1.02976}]}
        ))
        with patch("astroclocks.astronomy.zeep.Client", return_value=client):
            result = resolve_solar_system_coordinates("Planet", "Mars")
        self.assertAlmostEqual(result["magnitude"], 1.02976)
        self.assertEqual(result["magnitude_band"], "V")
        self.assertEqual(result["miriade_name"], "p:Mars")
        client.service.ephemcc.assert_called_once()
        app = SimpleNamespace(_tr=lambda key, **kw: translate("fr", key, **kw),
                              _object_type_display=lambda kind: "Planète")
        self.assertIn("Magnitude : 1.03 (V)", _target_information_text(app, result))

    def test_unavailable_photometry_does_not_break_coordinate_search(self):
        for magnitude in (None, "", "NaN", "--", 0, -4.5):
            with self.subTest(magnitude=magnitude), patch(
                "astroclocks.astronomy._get_planet_ephemeris",
                return_value=dict(RA="+08:46:41.7", DEC="+19:13:40.1", VMag=magnitude),
            ):
                result = resolve_solar_system_coordinates("Planet", "Mars")
                self.assertEqual(result["magnitude"], magnitude if isinstance(magnitude, (int, float)) else None)
                self.assertEqual(result["alpha_hh"], 8)

    def test_coordinate_only_helper_keeps_its_return_format(self):
        with patch("astroclocks.astronomy._get_planet_ephemeris", return_value=dict(RA="ra", DEC="dec", VMag=1)):
            self.assertEqual(get_planet_coord("p", "Mars"), ("ra", "dec"))
