import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from astroclocks.app_skymap import _on_sky_click


class SkyMapTargetTests(unittest.TestCase):
    def test_click_transfers_star_or_solar_metadata(self):
        for kind, name in (("star", "Sirius"), ("solar", "Moon"), ("solar", "Sun")):
            with self.subTest(name=name):
                target = dict(name=name, ra_hours=4, declination=20, magnitude=0)
                if kind == "solar":
                    target["kind"] = kind
                app = SimpleNamespace(
                    _sky_coordinates_from_canvas=lambda x, y: (4, 20, 0, 30, 40),
                    _nearest_sky_object=lambda x, y: target,
                    _tr=lambda key, **kw: key,
                    _set_target_from_coordinates=Mock(),
                )
                _on_sky_click(app, SimpleNamespace(x=100, y=100))
                information = app._set_target_from_coordinates.call_args.kwargs["target_information"]
                if kind == "star":
                    self.assertEqual(information["magnitude"], 0)
                    self.assertEqual(information["magnitude_band"], "V")
                    self.assertEqual(information["target_kind"], "star")
                else:
                    self.assertEqual(information["source"], "local_solar")
                    self.assertEqual(information["target_kind"], "star" if name == "Sun" else None)

    def test_click_empty_sky_keeps_coordinate_target(self):
        app = SimpleNamespace(
            _sky_coordinates_from_canvas=lambda x, y: (4, 20, 0, 30, 40),
            _nearest_sky_object=lambda x, y: None,
            _tr=lambda key, **kw: key, _set_target_from_coordinates=Mock(),
        )
        _on_sky_click(app, SimpleNamespace(x=100, y=100))
        self.assertEqual(app._set_target_from_coordinates.call_args.args[:2], (4, 20))
        self.assertNotIn("target_information", app._set_target_from_coordinates.call_args.kwargs)
