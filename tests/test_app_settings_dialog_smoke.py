import tkinter as tk
import unittest

from astroclocks.app import AstroClocksApp


class SettingsDialogSmokeTests(unittest.TestCase):
    def test_settings_dialog_opens_and_is_visible(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        root.withdraw()
        try:
            app = AstroClocksApp(root)
            app.open_settings_dialog()
            root.update_idletasks()
            dialogs = [child for child in root.winfo_children() if isinstance(child, tk.Toplevel)]
            self.assertTrue(dialogs)
            self.assertTrue(dialogs[-1].winfo_viewable())
        finally:
            for child in list(root.winfo_children()):
                if isinstance(child, tk.Toplevel):
                    child.destroy()
            root.destroy()


if __name__ == "__main__":
    unittest.main()
