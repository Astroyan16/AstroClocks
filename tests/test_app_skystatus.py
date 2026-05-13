import unittest

from astroclocks.app_skymap import _set_sky_status


class _FakeText:
    def __init__(self):
        self.content = ""
        self.state = None
        self.delete_calls = 0
        self.insert_calls = 0
        self.tags = {"danger"}

    def config(self, **kwargs):
        self.state = kwargs.get("state", self.state)

    def delete(self, _start, _end):
        self.delete_calls += 1
        self.content = ""

    def insert(self, _index, text):
        self.insert_calls += 1
        self.content = text

    def tag_remove(self, _tag, _start, _end):
        pass

    def tag_names(self):
        return tuple(self.tags)

    def tag_configure(self, tag_name, **_kwargs):
        self.tags.add(tag_name)

    def _offset_from_index(self, index):
        if index in ("1.0", "end"):
            return 0 if index == "1.0" else len(self.content)
        if "+" in index and index.endswith("c"):
            parts = index.split("+")[1:]
            return sum(int(part[:-1]) for part in parts if part.endswith("c"))
        return 0

    def search(self, needle, start, _end):
        offset = self._offset_from_index(start)
        position = self.content.find(needle, offset)
        if position < 0:
            return ""
        return f"1.0+{position}c"

    def tag_add(self, _tag, _start, _end):
        pass

    def tag_raise(self, _tag):
        pass


class SkyStatusCachingTests(unittest.TestCase):
    def _app_stub(self):
        app = type("Stub", (), {})()
        app.sky_status = _FakeText()
        app.sky_status_payload = None
        return app

    def test_redundant_payload_skips_text_widget_rewrite(self):
        app = self._app_stub()

        _set_sky_status(app, "line 1\nline 2", ("line 2",), (("line 1", "#ffffff"),))
        self.assertEqual(app.sky_status.delete_calls, 1)
        self.assertEqual(app.sky_status.insert_calls, 1)

        _set_sky_status(app, "line 1\nline 2", ("line 2",), (("line 1", "#ffffff"),))
        self.assertEqual(app.sky_status.delete_calls, 1)
        self.assertEqual(app.sky_status.insert_calls, 1)

    def test_changed_payload_updates_text_widget(self):
        app = self._app_stub()

        _set_sky_status(app, "line 1", (), ())
        _set_sky_status(app, "line 1\nline 2", (), ())

        self.assertEqual(app.sky_status.delete_calls, 2)
        self.assertEqual(app.sky_status.insert_calls, 2)


if __name__ == "__main__":
    unittest.main()
