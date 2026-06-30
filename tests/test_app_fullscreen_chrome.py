import unittest

from astroclocks.app import AstroClocksApp


class _FakeRoot:
    def __init__(self):
        self.idle_callbacks = []
        self.timed_callbacks = []

    def after_idle(self, callback):
        self.idle_callbacks.append(callback)

    def after(self, delay, callback):
        self.timed_callbacks.append((delay, callback))


class FullscreenChromeTests(unittest.TestCase):
    def test_chrome_is_reapplied_after_native_frame_is_restored(self):
        app = object.__new__(AstroClocksApp)
        app.root = _FakeRoot()
        chrome_calls = []
        app._apply_native_window_chrome = lambda window: chrome_calls.append(window)

        AstroClocksApp._restore_root_chrome_after_fullscreen(app)

        self.assertEqual(chrome_calls, [app.root])
        self.assertEqual(len(app.root.idle_callbacks), 1)
        self.assertEqual([delay for delay, _callback in app.root.timed_callbacks], [75])

        app.root.idle_callbacks[0]()
        app.root.timed_callbacks[0][1]()
        self.assertEqual(chrome_calls, [app.root, app.root, app.root])


if __name__ == "__main__":
    unittest.main()
