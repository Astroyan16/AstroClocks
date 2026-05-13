import unittest

from astroclocks.app_skymap import _sky_label_position


class _FakeCanvas:
    def __init__(self, width, height):
        self._width = width
        self._height = height

    def winfo_width(self):
        return self._width

    def winfo_height(self):
        return self._height


class _FakeFont:
    def __init__(self, text_width, line_height=12):
        self._text_width = text_width
        self._line_height = line_height

    def measure(self, _text):
        return self._text_width

    def metrics(self, name):
        if name == "linespace":
            return self._line_height
        raise KeyError(name)


class SkyLabelPositionTests(unittest.TestCase):
    def test_label_switches_to_left_anchor_near_right_edge(self):
        canvas = _FakeCanvas(200, 200)
        font = _FakeFont(text_width=40)

        x, y, anchor = _sky_label_position(None, canvas, 185, 100, "Arcturus", font)

        self.assertEqual(anchor, "e")
        self.assertLessEqual(x, 178)

    def test_label_clamps_inside_left_margin_when_text_is_wide(self):
        canvas = _FakeCanvas(200, 200)
        font = _FakeFont(text_width=80)

        x, _y, anchor = _sky_label_position(None, canvas, 12, 100, "Wide label", font)

        self.assertEqual(anchor, "w")
        self.assertGreaterEqual(x, 10)

    def test_label_stays_inside_bottom_margin(self):
        canvas = _FakeCanvas(200, 200)
        font = _FakeFont(text_width=30, line_height=14)

        _x, y, _anchor = _sky_label_position(None, canvas, 100, 194, "Capella", font)

        self.assertLessEqual(y, 183)


if __name__ == "__main__":
    unittest.main()
