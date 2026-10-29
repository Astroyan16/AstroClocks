import gc
import tkinter as tk
import unittest
from unittest.mock import patch
from tkinter.font import Font
from tkinter import ttk

from astroclocks.app import AstroClocksApp
from astroclocks.settings import AppSettings
from astroclocks.i18n import LANGUAGE_OPTIONS, LANGUAGE_NAMES
from astroclocks.sites import LOCATION_PRESETS, preset_label


class SettingsDialogSmokeTests(unittest.TestCase):
    def test_pointing_display_stays_empty_until_target_is_selected(self):
        root = tk.Tk()
        root.withdraw()
        try:
            with patch("astroclocks.app.load_app_settings", return_value=AppSettings()):
                app = AstroClocksApp(root)
                for language in ("fr", "en"):
                    app.language = language
                    app.update_value(activate_target=False)
                    app.clocks()
                    self.assertEqual(app.lbl_hour_angle.cget("text"), "--h --m --s")
                    self.assertEqual(app.lbl_dec_angle.cget("text"), "--° --' --\"")
                    for label, key, _kwargs in app.labelframe_title_labels:
                        if key in ("frame.hour_angle", "frame.declination"):
                            self.assertEqual(label.cget("foreground"), app.muted)
                            self.assertEqual(label.cget("text"), app._tr(key, suffix="").upper())
                            note = app.pointing_no_target_labels[key]
                            self.assertEqual(note.cget("foreground"), app.warning)
                            self.assertEqual(
                                note.cget("text"), app._tr("frame.no_target_suffix").upper(),
                            )
                app._activate_target_from_controls()
                app.clocks()
                self.assertNotEqual(app.lbl_hour_angle.cget("text"), "--h --m --s")
                self.assertNotEqual(app.lbl_dec_angle.cget("text"), "--° --' --\"")
                for label, key, _kwargs in app.labelframe_title_labels:
                    if key in ("frame.hour_angle", "frame.declination"):
                        self.assertEqual(label.cget("foreground"), app.muted)
                        self.assertEqual(app.pointing_no_target_labels[key].cget("text"), "")
                        self.assertNotIn(
                            app._tr("frame.no_target_suffix").upper(),
                            label.cget("text"),
                        )
        finally:
            for callback in root.tk.call("after", "info"):
                root.after_cancel(callback)
            root.destroy()
            gc.collect()

    def test_settings_groups_and_altitude_without_refraction(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        root.withdraw()
        try:
            with patch("astroclocks.app.load_app_settings", return_value=AppSettings()), patch(
                "astroclocks.app.save_app_settings"
            ) as save:
                app = AstroClocksApp(root)
                app.open_settings_dialog()
                root.update_idletasks()
                dialog = next(child for child in root.winfo_children()
                              if isinstance(child, tk.Toplevel))

                def walk(widget):
                    for child in widget.winfo_children():
                        yield child
                        yield from walk(child)

                notebook = next(widget for widget in walk(dialog)
                                if isinstance(widget, ttk.Notebook))
                tabs = [notebook.nametowidget(tab) for tab in notebook.tabs()]
                self.assertEqual([notebook.tab(tab, "text") for tab in tabs], [
                    app._tr(f"settings.tab.{key}")
                    for key in ("general", "sky", "weather", "mount")
                ])
                greenwich = next(widget for widget in walk(tabs[1])
                                 if isinstance(widget, tk.Checkbutton)
                                 and widget.cget("text") == app._tr("settings.show_greenwich_sidereal_clock"))
                self.assertFalse(root.getboolean(root.getvar(greenwich.cget("variable"))))
                greenwich.invoke()
                self.assertTrue(root.getboolean(root.getvar(greenwich.cget("variable"))))
                defaults = next(widget for widget in walk(dialog)
                                if isinstance(widget, tk.Button)
                                and widget.cget("text") == app._tr("button.default"))
                defaults.invoke()
                self.assertFalse(root.getboolean(root.getvar(greenwich.cget("variable"))))
                for key, expected in (
                    ("settings.sky_show_altaz_grid", False),
                    ("settings.sky_show_equatorial_grid", True),
                    ("settings.sky_show_solar_system", True),
                ):
                    checkbox = next(widget for widget in walk(tabs[1])
                                    if isinstance(widget, tk.Checkbutton)
                                    and widget.cget("text") == app._tr(key))
                    self.assertEqual(root.getboolean(root.getvar(checkbox.cget("variable"))), expected)
                site_widgets = list(walk(tabs[0]))
                altitude_label = next(widget for widget in site_widgets
                                      if isinstance(widget, tk.Label)
                                      and widget.cget("text") == app._tr("settings.refraction_altitude"))
                altitude = next(widget for widget in altitude_label.master.winfo_children()
                                if isinstance(widget, tk.Entry)
                                and widget.grid_info()["row"] == altitude_label.grid_info()["row"])
                self.assertEqual(altitude.cget("state"), "normal")
                preset_combo = next(widget for widget in site_widgets
                                    if isinstance(widget, ttk.Combobox)
                                    and preset_label(LOCATION_PRESETS[0]) in widget.cget("values"))
                for name in ("Observatoire du Pic du Midi", "Observatoire de Meudon - T1m"):
                    site = next(site for site in LOCATION_PRESETS if site["name"] == name)
                    preset_combo.set(preset_label(site))
                    preset_combo.event_generate("<<ComboboxSelected>>")
                    root.update_idletasks()
                    self.assertEqual(float(altitude.get()), site["altitude_m"])
                altitude.delete(0, tk.END)
                altitude.insert(0, "250")
                language_values = tuple(label for _, label in LANGUAGE_OPTIONS)
                self.assertTrue(any(isinstance(widget, ttk.Combobox)
                                    and tuple(widget.cget("values")) == language_values
                                    for widget in walk(tabs[1])))
                self.assertFalse(any(isinstance(widget, ttk.Combobox)
                                     and tuple(widget.cget("values")) == language_values
                                     for widget in site_widgets))
                model = next(widget for widget in walk(tabs[2])
                             if isinstance(widget, ttk.Combobox)
                             and app._tr("settings.refraction_none") in widget.cget("values"))
                self.assertEqual(model.get(), app._tr("settings.refraction_none"))
                for tab in tabs[1:]:
                    notebook.select(tab)
                    root.update_idletasks()
                    section_titles = (
                        app._tr("settings.group.advanced"),
                        app._tr("settings.instrument"),
                    )
                    self.assertFalse(any(isinstance(widget, tk.Checkbutton)
                                         and widget.cget("text") in section_titles
                                         for widget in walk(tab)))
                    disclosures = [widget for widget in walk(tab)
                                   if isinstance(widget, tk.Button)
                                   and widget.cget("text") in section_titles]
                    self.assertEqual(len(disclosures), 1)
                    for disclosure in disclosures:
                        title = disclosure.cget("text")
                        closed_image = disclosure.cget("image")
                        self.assertEqual(root.tk.call("image", "width", closed_image), 20)
                        self.assertEqual(Font(root=root, font=disclosure.cget("font")).actual("size"), 10)
                        content = next(child for child in disclosure.master.winfo_children()
                                       if isinstance(child, tk.Frame))
                        self.assertFalse(content.winfo_ismapped())
                        if tab == tabs[2]:
                            api_button = next(widget for widget in walk(content)
                                              if isinstance(widget, tk.Button)
                                              and widget.cget("text") == app._tr("settings.meteofrance_api_configure"))
                            self.assertFalse(api_button.winfo_ismapped())
                        disclosure.invoke()
                        root.update_idletasks()
                        self.assertEqual(disclosure.cget("text"), title)
                        self.assertNotEqual(disclosure.cget("image"), closed_image)
                        self.assertTrue(content.winfo_ismapped())
                        if tab == tabs[2]:
                            self.assertTrue(api_button.winfo_ismapped())
                        self.assertLessEqual(dialog.winfo_reqheight(), root.winfo_screenheight())
                        disclosure.invoke()
                        root.update_idletasks()
                        self.assertEqual(disclosure.cget("text"), title)
                        self.assertEqual(disclosure.cget("image"), closed_image)
                        self.assertFalse(content.winfo_ismapped())
                apply = next(widget for widget in walk(dialog)
                             if isinstance(widget, tk.Button)
                             and widget.cget("text") == app._tr("button.apply"))
                apply.invoke()
                self.assertEqual(app.refraction_altitude_m, 250)
                self.assertEqual(save.call_args.args[0].refraction_altitude_m, 250)
                self.assertTrue(save.call_args.args[0].hide_greenwich_sidereal_clock)
                self.assertFalse(save.call_args.args[0].sky_show_altaz_grid)
                self.assertTrue(save.call_args.args[0].sky_show_equatorial_grid)
                self.assertTrue(save.call_args.args[0].sky_show_solar_system)
        finally:
            for callback in root.tk.call("after", "info"):
                root.after_cancel(callback)
            root.destroy()
            gc.collect()

    def test_greenwich_setting_reflows_search_and_preserves_pointing_emphasis(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk display unavailable: {exc}")
        try:
            with patch("astroclocks.app.load_app_settings", return_value=AppSettings()), patch(
                "astroclocks.app.save_app_settings"
            ) as save:
                app = AstroClocksApp(root)
                root.geometry("1200x800")
                root.update()
                self.assertTrue(app.hide_greenwich_sidereal_clock)
                self.assertFalse(app.lf_gmst.winfo_ismapped())
                self.assertEqual(app.lf_search.master.grid_info()["rowspan"], 2)
                positions = (
                    (app.lf_utc, 0, 2), (app.lf_gmst, 1, 2),
                    (app.lf_alpha, 0, 3), (app.lf_delta, 1, 3),
                    (app.lf_local, 0, 4), (app.lf_lst, 1, 4),
                    (app.lf_ha, 0, 5), (app.lf_dec, 1, 5),
                )
                def walk(widget):
                    for child in widget.winfo_children():
                        yield child
                        yield from walk(child)

                for hide in (False, True):
                    app.open_settings_dialog()
                    dialog = next(child for child in root.winfo_children()
                                  if isinstance(child, tk.Toplevel))
                    widgets = list(walk(dialog))
                    checkbox = next(widget for widget in widgets
                                    if isinstance(widget, tk.Checkbutton)
                                    and widget.cget("text") == app._tr("settings.show_greenwich_sidereal_clock"))
                    checkbox.invoke()
                    language = next(widget for widget in widgets
                                    if isinstance(widget, ttk.Combobox)
                                    and tuple(widget.cget("values")) == tuple(label for _, label in LANGUAGE_OPTIONS))
                    selected_language = "en" if hide else "fr"
                    language.set(LANGUAGE_NAMES[selected_language])
                    apply = next(widget for widget in widgets
                                 if isinstance(widget, tk.Button)
                                 and widget.cget("text") == app._tr("button.apply"))
                    apply.invoke()
                    root.update()
                    app._update_dynamic_fonts()
                    self.assertEqual(app.hide_greenwich_sidereal_clock, hide)
                    self.assertEqual(app.language, selected_language)
                    self.assertEqual(save.call_args.args[0].hide_greenwich_sidereal_clock, hide)
                    self.assertEqual(bool(app.lf_gmst.winfo_ismapped()), not hide)
                    self.assertEqual(app.lf_search.master.grid_info()["rowspan"], 2 if hide else 1)
                    self.assertGreater(app.angle_font_size, app.clock_font_size)
                    self.assertGreater(app.angle_font_size, app.coord_font_size)
                    for label in app.angle_labels:
                        self.assertEqual(Font(root=root, font=label.cget("font")).actual("size"), app.angle_font_size)
                    if not hide:
                        for frame, column, row in positions:
                            grid = frame.master.grid_info()
                            self.assertEqual((grid["column"], grid["row"]), (column, row))
        finally:
            for callback in root.tk.call("after", "info"):
                root.after_cancel(callback)
            root.destroy()
            gc.collect()

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
            for callback in root.tk.call("after", "info"):
                root.after_cancel(callback)
            root.destroy()
            gc.collect()


if __name__ == "__main__":
    unittest.main()
