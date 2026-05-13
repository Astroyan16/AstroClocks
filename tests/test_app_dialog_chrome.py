import unittest

from astroclocks.app import AstroClocksApp


class _FakeDialog:
    def __init__(self):
        self.bound = []
        self.alpha = None
        self.focused = False
        self.deiconified = False
        self.lift_anchor = None

    def attributes(self, name, value=None):
        if name == "-alpha" and value is not None:
            self.alpha = value

    def deiconify(self):
        self.deiconified = True

    def lift(self, anchor=None):
        self.lift_anchor = anchor

    def update_idletasks(self):
        pass

    def update(self):
        pass

    def focus_set(self):
        self.focused = True

    def bind(self, event, callback, add=None):
        self.bound.append((event, callback, add))


class RevealDialogChromeTests(unittest.TestCase):
    def test_reveal_dialog_reapplies_root_chrome_and_restores_on_destroy(self):
        app = object.__new__(AstroClocksApp)
        app.root = object()
        chrome_calls = []
        app._apply_native_window_chrome = lambda window: chrome_calls.append(window)

        dialog = _FakeDialog()

        AstroClocksApp._reveal_dialog(app, dialog, anchor=app.root, focus=True)

        self.assertTrue(dialog.deiconified)
        self.assertEqual(chrome_calls, [dialog, app.root])
        self.assertEqual(dialog.lift_anchor, app.root)
        self.assertTrue(dialog.focused)
        self.assertTrue(any(event == "<Destroy>" for event, _callback, _add in dialog.bound))

        destroy_callback = next(
            callback for event, callback, _add in dialog.bound if event == "<Destroy>"
        )

        class _Event:
            def __init__(self, widget):
                self.widget = widget

        child_widget = object()
        destroy_callback(_Event(child_widget))
        self.assertEqual(chrome_calls, [dialog, app.root])

        destroy_callback(_Event(dialog))
        self.assertEqual(chrome_calls, [dialog, app.root, app.root])


if __name__ == "__main__":
    unittest.main()
