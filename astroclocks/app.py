import ctypes
import math
import tempfile
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.font import Font

from astroplan import download_IERS_A
from astropy.coordinates import name_resolve

from astroclocks.astronomy import (
    compute_clock_state,
    compute_declination_display,
    convert_star_catalog_j2000_to_jnow,
    format_timezone_label,
    jnow_to_icrs_degrees,
    resolve_deep_sky_coordinates,
    resolve_solar_system_coordinates,
)
from astroclocks.settings import (
    AppSettings,
    DEFAULT_ALADIN_FOV_DEG,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_SITE_NAME,
    format_latitude_display,
    format_longitude_display,
    load_app_settings,
    save_app_settings,
)
from astroclocks.sites import LOCATION_PRESETS, preset_label
from astroclocks.utils import is_float, resource_path


APP_VERSION = "3.0"

BRIGHT_STARS_J2000 = [
    ("Sirius", 6.7525, -16.7161, -1.46),
    ("Canopus", 6.3992, -52.6957, -0.74),
    ("Arcturus", 14.2610, 19.1825, -0.05),
    ("Vega", 18.6156, 38.7837, 0.03),
    ("Capella", 5.2782, 45.9980, 0.08),
    ("Rigel", 5.2423, -8.2016, 0.12),
    ("Procyon", 7.6550, 5.2250, 0.34),
    ("Achernar", 1.6286, -57.2368, 0.46),
    ("Betelgeuse", 5.9195, 7.4071, 0.50),
    ("Hadar", 14.0637, -60.3730, 0.61),
    ("Altair", 19.8464, 8.8683, 0.77),
    ("Acrux", 12.4433, -63.0991, 0.76),
    ("Aldebaran", 4.5987, 16.5093, 0.85),
    ("Spica", 13.4199, -11.1613, 0.97),
    ("Antares", 16.4901, -26.4320, 1.06),
    ("Pollux", 7.7553, 28.0262, 1.14),
    ("Fomalhaut", 22.9608, -29.6222, 1.16),
    ("Deneb", 20.6905, 45.2803, 1.25),
    ("Regulus", 10.1395, 11.9672, 1.35),
    ("Adhara", 6.9771, -28.9721, 1.50),
    ("Castor", 7.5767, 31.8883, 1.58),
    ("Shaula", 17.5601, -37.1038, 1.62),
    ("Bellatrix", 5.4189, 6.3497, 1.64),
    ("Elnath", 5.4382, 28.6075, 1.65),
    ("Miaplacidus", 9.2201, -69.7172, 1.67),
]


class AstroClocksApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(f"AstroClocks v{APP_VERSION}")
        self.root.iconbitmap(resource_path("AppIcon.ico"))
        self.root.minsize(1440, 900)

        self.gbg = "#101419"
        self.card_bg = "#171f26"
        self.card_edge = "#2b3a45"
        self.ebg = "#0b1015"
        self.fg = "#f6c451"
        self.text = "#edf3f8"
        self.muted = "#93a6b7"
        self.accent = "#4cc9f0"
        self.success = "#7bd88f"
        self.button_bg = "#22303a"
        self.settings = load_app_settings()
        self.site_name = self.settings.site_name
        self.latitude = self.settings.latitude
        self.longitude = self.settings.longitude
        self.aladin_fov_deg = self.settings.aladin_fov_deg
        self.coord_font_size = 24
        self.aladin_button = None
        self.sky_canvas = None
        self.sky_status = None
        self.bright_stars_jnow = convert_star_catalog_j2000_to_jnow(BRIGHT_STARS_J2000)
        self.sky_geometry = None
        self.sky_star_points = []
        self.sky_hover_position = None
        self.sky_base_status = ""
        self.is_fullscreen = False
        self.windowed_geometry = None
        self.windowed_state = "normal"

        self._configure_styles()
        self._configure_root()
        self._create_frames()
        self._create_site_widgets()
        self._create_search_widgets()
        self._create_time_widgets()
        self._create_coordinate_widgets()
        self._create_hour_angle_widgets()
        self._create_sky_widgets()
        self.update_site_labels()
        self.update_value()

        self.root.bind("<Return>", lambda event: self.search_coordinates())
        self.root.bind("<Configure>", self._update_coordinate_font_size)

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("default")

        self.root.option_add("*TCombobox*Listbox*Background", self.ebg)
        self.root.option_add("*TCombobox*Listbox*Foreground", self.text)
        self.root.option_add("*TCombobox*Listbox*selectBackground", self.accent)
        self.root.option_add("*TCombobox*Listbox*selectForeground", self.ebg)

        style.map("TCombobox", fieldbackground=[("readonly", self.ebg)])
        style.map("TCombobox", selectbackground=[("readonly", self.ebg)])
        style.map("TCombobox", selectforeground=[("readonly", self.text)])
        style.map("TCombobox", background=[("readonly", self.card_edge)])
        style.map("TCombobox", foreground=[("readonly", self.text)])
        style.configure(
            "TCombobox",
            arrowsize=18,
            fieldbackground=self.ebg,
            background=self.card_edge,
            foreground=self.text,
            borderwidth=0,
            padding=6,
        )

    def _configure_root(self):
        self.root.attributes("-fullscreen", False)
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)
        self.root.config(background=self.gbg)
        self.root.grid_columnconfigure(0, weight=1, uniform="main")
        self.root.grid_columnconfigure(1, weight=1, uniform="main")
        self.root.grid_columnconfigure(2, weight=1, uniform="main")
        self.root.grid_rowconfigure(0, weight=0)
        for row in range(1, 6):
            self.root.grid_rowconfigure(row, weight=1)

    def _current_monitor_geometry(self):
        try:
            self.root.update_idletasks()

            class Rect(ctypes.Structure):
                _fields_ = [
                    ("left", ctypes.c_long),
                    ("top", ctypes.c_long),
                    ("right", ctypes.c_long),
                    ("bottom", ctypes.c_long),
                ]

            class MonitorInfo(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_ulong),
                    ("rcMonitor", Rect),
                    ("rcWork", Rect),
                    ("dwFlags", ctypes.c_ulong),
                ]

            monitor = ctypes.windll.user32.MonitorFromWindow(self.root.winfo_id(), 2)
            monitor_info = MonitorInfo()
            monitor_info.cbSize = ctypes.sizeof(MonitorInfo)
            if not ctypes.windll.user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info)):
                raise RuntimeError("Unable to read monitor geometry")

            rect = monitor_info.rcMonitor
            return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top
        except Exception:
            return 0, 0, self.root.winfo_screenwidth(), self.root.winfo_screenheight()

    def _enter_fullscreen(self):
        if self.is_fullscreen:
            return

        self.windowed_geometry = self.root.geometry()
        try:
            self.windowed_state = self.root.state()
        except tk.TclError:
            self.windowed_state = "normal"

        left, top, width, height = self._current_monitor_geometry()
        if self.windowed_state == "zoomed":
            self.root.state("normal")
            self.root.update_idletasks()

        self.root.attributes("-fullscreen", False)
        self.root.overrideredirect(True)
        self.root.geometry(f"{width}x{height}+{left}+{top}")
        self.root.update_idletasks()
        self.root.update()
        self.root.attributes("-topmost", True)
        self.root.lift()
        self.root.focus_force()
        self.root.geometry(f"{width}x{height}+{left}+{top}")
        self.is_fullscreen = True

    def _toggle_fullscreen(self, _event=None):
        if self.is_fullscreen:
            self._exit_fullscreen()
            return

        self._enter_fullscreen()

    def _exit_fullscreen(self, _event=None):
        self.root.attributes("-topmost", False)
        self.root.attributes("-fullscreen", False)
        if not self.is_fullscreen:
            return

        self.root.overrideredirect(False)
        if self.windowed_geometry:
            self.root.geometry(self.windowed_geometry)
        if self.windowed_state == "zoomed":
            self.root.after(50, lambda: self.root.state("zoomed"))
        self.is_fullscreen = False

    def _create_header(self):
        header = tk.Frame(self.root, bg=self.gbg)
        header.grid(column=0, row=0, columnspan=3, sticky="ew", padx=20, pady=(18, 4))
        header.grid_columnconfigure(0, weight=1)

        title = tk.Label(
            header,
            text=f"AstroClocks v{APP_VERSION}",
            foreground=self.fg,
            background=self.gbg,
            font=Font(family="Segoe UI", size=28, weight="bold"),
            anchor="w",
        )
        title.grid(column=0, row=0, sticky="w")

        subtitle = tk.Label(
            header,
            text="Temps civil, temps sideral, coordonnees JNow et horizon local temps reel",
            foreground=self.muted,
            background=self.gbg,
            font=Font(family="Segoe UI", size=11),
            anchor="w",
        )
        subtitle.grid(column=0, row=1, sticky="w", pady=(0, 4))

        header_actions = tk.Frame(header, bg=self.gbg)
        header_actions.grid(column=1, row=0, rowspan=2, sticky="e")

        settings_button = tk.Button(
            header_actions,
            text="Parametres",
            foreground=self.text,
            background=self.button_bg,
            activeforeground=self.ebg,
            activebackground=self.fg,
            font=Font(family="Segoe UI", size=10, weight="bold"),
            padx=14,
            pady=5,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self.open_settings_dialog,
        )
        settings_button.grid(column=0, row=0, padx=(0, 8), sticky="e")

        fullscreen_button = tk.Button(
            header_actions,
            text="Plein Ecran (F11)",
            foreground=self.ebg,
            background=self.accent,
            activeforeground=self.ebg,
            activebackground=self.fg,
            font=Font(family="Segoe UI", size=10, weight="bold"),
            padx=14,
            pady=5,
            relief="flat",
            bd=0,
            cursor="hand2",
            command=self._toggle_fullscreen,
        )
        fullscreen_button.grid(column=1, row=0, sticky="e")

    def _build_labelframe(self, title, column, row, padx=10, pady=10, relief="raised", bd=None, rowspan=1):
        shell = tk.Frame(
            self.root,
            background=self.card_bg,
            highlightbackground=self.card_edge,
            highlightcolor=self.accent,
            highlightthickness=2 if bd else 1,
            bd=0,
        )
        shell.grid(column=column, row=row, rowspan=rowspan, padx=padx, pady=pady, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        tk.Label(
            shell,
            text=title.upper(),
            foreground=self.muted,
            background=self.card_bg,
            font=Font(family="Segoe UI", size=10, weight="bold"),
            anchor="w",
        ).grid(column=0, row=0, padx=14, pady=(12, 4), sticky="ew")

        body = tk.Frame(shell, background=self.card_bg)
        body.grid(column=0, row=1, padx=10, pady=(0, 10), sticky="nsew")
        return body

    def _build_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            bg=self.button_bg,
            fg=self.text,
            activebackground=self.accent,
            activeforeground=self.ebg,
            font=Font(family="Segoe UI", size=11, weight="bold"),
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            cursor="hand2",
            command=command,
        )

    def _create_frames(self):
        self._create_header()
        timezone = format_timezone_label()
        self.lf_long = self._build_labelframe("Site d'observation", 0, 1)
        self.lf_search = self._build_labelframe("Find coordinates of an object", 1, 1)
        self.lf_sky = self._build_labelframe("Horizon local", 2, 1, rowspan=5, bd=6)
        self.lf_local = self._build_labelframe(f"Local Time ({timezone})", 0, 2)
        self.lf_utc = self._build_labelframe("UTC", 1, 2)
        self.lf_alpha = self._build_labelframe("Alpha JNow (h m s)", 0, 3)
        self.lf_delta = self._build_labelframe("Delta JNow (d m s)", 1, 3)
        self.lf_gmst = self._build_labelframe("Greenwich Sidereal Time", 0, 4)
        self.lf_lst = self._build_labelframe("Local Sidereal Time", 1, 4)
        self.lf_ha = self._build_labelframe(
            "Hour Angle (EAST circle +6h)", 0, 5, relief="ridge", bd=6
        )
        self.lf_dec = self._build_labelframe("Declination (+90deg)", 1, 5, relief="ridge", bd=6)
        for frame in (
            self.lf_long,
            self.lf_local,
            self.lf_utc,
            self.lf_gmst,
            self.lf_lst,
            self.lf_search,
            self.lf_alpha,
            self.lf_delta,
            self.lf_ha,
            self.lf_dec,
            self.lf_sky,
        ):
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)

    def _create_site_widgets(self):
        self.site_name_label = tk.Label(
            self.lf_long,
            font=Font(family="Segoe UI", size=13, weight="bold"),
            background=self.ebg,
            foreground=self.text,
            anchor="w",
            padx=10,
            pady=6,
        )
        self.site_name_label.grid(column=0, row=0, columnspan=2, padx=8, pady=(8, 4), sticky="ew")

        self.latlabel = tk.Label(
            self.lf_long,
            font=Font(family="Segoe UI", size=12),
            background=self.ebg,
            foreground=self.fg,
            anchor="w",
            padx=10,
            pady=5,
        )
        self.latlabel.grid(column=0, row=1, columnspan=2, padx=8, pady=4, sticky="ew")

        self.longlabel = tk.Label(
            self.lf_long,
            font=Font(family="Segoe UI", size=12),
            background=self.ebg,
            foreground=self.fg,
            anchor="w",
            padx=10,
            pady=5,
        )
        self.longlabel.grid(column=0, row=2, columnspan=2, padx=8, pady=4, sticky="ew")

        self.fov_label = tk.Label(
            self.lf_long,
            font=Font(family="Segoe UI", size=12),
            background=self.ebg,
            foreground=self.muted,
            anchor="w",
            padx=10,
            pady=5,
        )
        self.fov_label.grid(column=0, row=3, columnspan=2, padx=8, pady=4, sticky="ew")

        self._build_button(self.lf_long, "Parametres", self.open_settings_dialog).grid(
            column=0, row=4, padx=8, pady=8, sticky="ew"
        )

        self._build_button(self.lf_long, "Meudon T1m", self.set_default_site).grid(
            column=1, row=4, padx=8, pady=8, sticky="ew"
        )
        self.lf_long.grid_columnconfigure(0, weight=1)
        self.lf_long.grid_columnconfigure(1, weight=1)

    def _create_search_widgets(self):
        self.search_entry = tk.Entry(
            self.lf_search,
            width=30,
            bg=self.ebg,
            fg=self.text,
            font=Font(family="Segoe UI", size=13),
            insertbackground=self.fg,
            relief="flat",
            highlightbackground=self.card_edge,
            highlightcolor=self.accent,
            highlightthickness=1,
        )
        self.search_entry.grid(column=0, row=0, ipady=7, padx=8, pady=8, sticky="ew")

        self._build_button(self.lf_search, "Search", self.search_coordinates).grid(
            column=1, row=1, padx=8, pady=8, sticky="ew"
        )

        self.aladin_button = self._build_button(
            self.lf_search,
            f"Aladin {self.aladin_fov_deg:.2f}\N{DEGREE SIGN}",
            self.show_sky_view,
        )
        self.aladin_button.grid(
            column=1, row=0, padx=8, pady=8, sticky="ew"
        )

        self.combo_box = ttk.Combobox(
            self.lf_search,
            values=[
                "Asteroid",
                "Comet",
                "Dwarf Planet",
                "Planet",
                "Natural Satellite",
                "Star, Deep Sky Object",
            ],
            font=Font(family="Segoe UI", size=13),
        )
        self.combo_box.grid(column=0, row=1, padx=8, pady=8, sticky="ew")
        self.combo_box["state"] = "readonly"
        self.combo_box.current(5)

        self.result_text = tk.Text(
            self.lf_search,
            state=tk.DISABLED,
            height=3,
            width=30,
            foreground=self.text,
            background=self.ebg,
            font=Font(family="Segoe UI", size=12),
            relief="flat",
            highlightbackground=self.card_edge,
            highlightcolor=self.accent,
            highlightthickness=1,
            padx=8,
            pady=8,
        )
        self.result_text.grid(
            column=0,
            row=2,
            columnspan=2,
            ipadx=1,
            ipady=1,
            padx=8,
            pady=8,
            sticky="nsew",
        )
        self.lf_search.grid_columnconfigure(0, weight=1)
        self.lf_search.grid_columnconfigure(1, weight=0)
        self.lf_search.grid_rowconfigure(2, weight=1)

    def _create_time_widgets(self):
        self.label_local = self._build_clock_label(self.lf_local)
        self.label_utc = self._build_clock_label(self.lf_utc)
        self.label_gmst = self._build_clock_label(self.lf_gmst)
        self.label_lst = self._build_clock_label(self.lf_lst)

    def _build_clock_label(self, parent):
        label = tk.Label(
            parent,
            font=Font(family="Consolas", size=30, weight="bold"),
            background=self.ebg,
            foreground=self.fg,
            anchor="center",
            padx=10,
            pady=10,
        )
        label.pack(fill="both", expand=True, padx=8, pady=8)
        return label

    def _create_coordinate_widgets(self):
        self.alpha_hh = tk.StringVar(value=0)
        self.alpha_mm = tk.StringVar(value=0)
        self.alpha_ss = tk.StringVar(value=0)
        self.delta_dd = tk.StringVar(value=0)
        self.delta_mm = tk.StringVar(value=0)
        self.delta_ss = tk.StringVar(value=0)

        self.lbl_alpha = tk.Label(
            self.lf_alpha,
            text=self._alpha_text(),
            bg=self.ebg,
            fg=self.fg,
            font=Font(family="Consolas", size=self.coord_font_size, weight="bold"),
            padx=10,
            pady=8,
        )
        self.lbl_alpha.grid(column=0, row=0, ipadx=1, ipady=1, padx=8, pady=8, sticky="ew")

        self.lbl_delta = tk.Label(
            self.lf_delta,
            text=self._delta_text(),
            bg=self.ebg,
            fg=self.fg,
            font=Font(family="Consolas", size=self.coord_font_size, weight="bold"),
            padx=10,
            pady=8,
        )
        self.lbl_delta.grid(column=0, row=0, ipadx=1, ipady=1, padx=8, pady=8, sticky="ew")

        self._build_spinbox(self.lf_alpha, self.alpha_hh, 0, 23, 1)
        self._build_spinbox(self.lf_alpha, self.alpha_mm, 0, 59, 2)
        self._build_spinbox(self.lf_alpha, self.alpha_ss, 0, 59, 3)
        self._build_spinbox(self.lf_delta, self.delta_dd, -90, 90, 1)
        self._build_spinbox(self.lf_delta, self.delta_mm, 0, 59, 2)
        self._build_spinbox(self.lf_delta, self.delta_ss, 0, 59, 3)

        self._build_button(self.lf_alpha, "Set", self.update_value).grid(
            column=4, row=0, padx=8, pady=8, sticky="ew"
        )

        self._build_button(self.lf_delta, "Set", self.update_value).grid(
            column=4, row=0, padx=8, pady=8, sticky="ew"
        )

        for frame in (self.lf_alpha, self.lf_delta):
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_columnconfigure(1, weight=0)
            frame.grid_columnconfigure(2, weight=0)
            frame.grid_columnconfigure(3, weight=0)
            frame.grid_columnconfigure(4, weight=0)

    def _build_spinbox(self, parent, variable, minimum, maximum, column, row=0):
        tk.Spinbox(
            parent,
            from_=minimum,
            to=maximum,
            textvariable=variable,
            wrap=True,
            font=Font(family="Consolas", size=22, weight="bold"),
            width=3,
            justify="center",
            fg=self.fg,
            bg=self.ebg,
            buttonbackground=self.button_bg,
            format="%2.0f",
            insertbackground=self.fg,
            relief="flat",
            highlightbackground=self.card_edge,
            highlightcolor=self.accent,
            highlightthickness=1,
            command=self.update_value,
        ).grid(column=column, row=row, ipadx=1, ipady=1, padx=8, pady=8, sticky="ew")

    def _update_coordinate_font_size(self, _event=None):
        available_width = min(self.lf_alpha.winfo_width(), self.lf_delta.winfo_width())
        if available_width <= 1:
            return

        if available_width < 380:
            size = 12
        elif available_width < 430:
            size = 14
        elif available_width < 500:
            size = 16
        elif available_width < 560:
            size = 18
        elif available_width < 640:
            size = 20
        elif available_width < 720:
            size = 22
        else:
            size = 24

        if size != self.coord_font_size:
            self.coord_font_size = size
            self.lbl_alpha.config(font=Font(family="Consolas", size=size, weight="bold"))
            self.lbl_delta.config(font=Font(family="Consolas", size=size, weight="bold"))

    def _create_hour_angle_widgets(self):
        self.lbl_hour_angle = tk.Label(
            self.lf_ha,
            text="06h 00m 00s",
            bg=self.ebg,
            fg=self.fg,
            font=Font(family="Consolas", size=44, weight="bold"),
            padx=10,
            pady=8,
        )
        self.lbl_hour_angle.grid(column=0, row=0, ipadx=1, ipady=1, padx=8, pady=8, sticky="nsew")

        self.lbl_dec_angle = tk.Label(
            self.lf_dec,
            text=compute_declination_display(0, 0, 0),
            bg=self.ebg,
            fg=self.fg,
            font=Font(family="Consolas", size=44, weight="bold"),
            padx=10,
            pady=8,
        )
        self.lbl_dec_angle.grid(column=0, row=0, ipadx=1, ipady=1, padx=8, pady=8, sticky="nsew")

    def _create_sky_widgets(self):
        self.lf_sky.grid_columnconfigure(0, weight=1)
        self.lf_sky.grid_rowconfigure(0, weight=1)
        self.lf_sky.grid_rowconfigure(1, weight=0)

        self.sky_canvas = tk.Canvas(
            self.lf_sky,
            bg=self.ebg,
            highlightthickness=0,
            bd=0,
            cursor="crosshair",
        )
        self.sky_canvas.grid(column=0, row=0, padx=8, pady=8, sticky="nsew")
        self.sky_canvas.bind("<Configure>", lambda _event: self._update_sky_map())
        self.sky_canvas.bind("<Motion>", self._on_sky_motion)
        self.sky_canvas.bind("<Leave>", self._on_sky_leave)
        self.sky_canvas.bind("<Button-1>", self._on_sky_click)

        self.sky_status = tk.Label(
            self.lf_sky,
            text="",
            bg=self.card_bg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10),
            justify="left",
            anchor="w",
            height=3,
        )
        self.sky_status.grid(column=0, row=1, padx=8, pady=(2, 8), sticky="ew")

    def _parse_clock_hours(self, value):
        hours, minutes, seconds = value.split(":")
        return float(hours) + (float(minutes) / 60) + (float(seconds) / 3600)

    def _current_target_coordinates(self):
        ra_hours = (
            float(self.alpha_hh.get())
            + (float(self.alpha_mm.get()) / 60)
            + (float(self.alpha_ss.get()) / 3600)
        )
        delta_degrees_text = str(self.delta_dd.get()).strip()
        dec_sign = -1 if delta_degrees_text.startswith("-") else 1
        dec_degrees = dec_sign * (
            abs(float(self.delta_dd.get()))
            + (float(self.delta_mm.get()) / 60)
            + (float(self.delta_ss.get()) / 3600)
        )
        return ra_hours, dec_degrees

    def _normalize_hour_angle(self, hours):
        return ((hours + 12) % 24) - 12

    def _equatorial_to_horizontal(self, ra_hours, declination, lst_hours):
        hour_angle = self._normalize_hour_angle(lst_hours - ra_hours)
        hour_angle_rad = math.radians(hour_angle * 15)
        dec_rad = math.radians(declination)
        lat_rad = math.radians(self.latitude)

        sin_altitude = (
            math.sin(dec_rad) * math.sin(lat_rad)
            + math.cos(dec_rad) * math.cos(lat_rad) * math.cos(hour_angle_rad)
        )
        altitude_rad = math.asin(max(-1.0, min(1.0, sin_altitude)))
        cos_altitude = max(1e-12, math.cos(altitude_rad))

        sin_azimuth = -math.sin(hour_angle_rad) * math.cos(dec_rad) / cos_altitude
        cos_azimuth = (
            math.sin(dec_rad) - math.sin(altitude_rad) * math.sin(lat_rad)
        ) / (cos_altitude * max(1e-12, math.cos(lat_rad)))
        azimuth = math.degrees(math.atan2(sin_azimuth, cos_azimuth)) % 360

        return math.degrees(altitude_rad), azimuth, hour_angle

    def _horizontal_to_equatorial(self, altitude, azimuth, lst_hours):
        altitude_rad = math.radians(altitude)
        azimuth_rad = math.radians(azimuth)
        lat_rad = math.radians(self.latitude)

        sin_declination = (
            math.sin(altitude_rad) * math.sin(lat_rad)
            + math.cos(altitude_rad) * math.cos(lat_rad) * math.cos(azimuth_rad)
        )
        declination_rad = math.asin(max(-1.0, min(1.0, sin_declination)))
        cos_declination = max(1e-12, math.cos(declination_rad))

        sin_hour_angle = -math.sin(azimuth_rad) * math.cos(altitude_rad) / cos_declination
        cos_hour_angle = (
            math.sin(altitude_rad) - math.sin(lat_rad) * math.sin(declination_rad)
        ) / (max(1e-12, math.cos(lat_rad)) * cos_declination)
        hour_angle_hours = math.degrees(math.atan2(sin_hour_angle, cos_hour_angle)) / 15
        hour_angle_hours = self._normalize_hour_angle(hour_angle_hours)
        ra_hours = (lst_hours - hour_angle_hours) % 24

        return ra_hours, math.degrees(declination_rad), hour_angle_hours

    def _project_horizontal_point(self, center_x, center_y, radius, altitude, azimuth):
        if altitude < 0:
            return None

        sky_radius = ((90 - altitude) / 90) * radius
        azimuth_rad = math.radians(azimuth)
        x = center_x + sky_radius * math.sin(azimuth_rad)
        y = center_y - sky_radius * math.cos(azimuth_rad)
        return x, y

    def _project_target(self, center_x, center_y, radius, altitude, azimuth):
        plotted_altitude = max(0, min(90, altitude))
        sky_radius = ((90 - plotted_altitude) / 90) * radius
        azimuth_rad = math.radians(azimuth)
        x = center_x + sky_radius * math.sin(azimuth_rad)
        y = center_y - sky_radius * math.cos(azimuth_rad)
        return x, y, altitude >= 0

    def _draw_sky_grid(self, canvas, center_x, center_y, radius):
        canvas.create_oval(
            center_x - radius,
            center_y - radius,
            center_x + radius,
            center_y + radius,
            fill="#071018",
            outline=self.card_edge,
            width=2,
        )

        grid_color = "#1d3341"
        for altitude in (30, 60):
            ring_radius = ((90 - altitude) / 90) * radius
            canvas.create_oval(
                center_x - ring_radius,
                center_y - ring_radius,
                center_x + ring_radius,
                center_y + ring_radius,
                outline=grid_color,
                dash=(4, 5),
            )
            canvas.create_text(
                center_x + ring_radius - 6,
                center_y - 8,
                text=f"{altitude}\N{DEGREE SIGN}",
                fill=self.muted,
                font=Font(family="Segoe UI", size=8),
                anchor="e",
            )

        for azimuth, label in ((0, "N"), (90, "E"), (180, "S"), (270, "W")):
            azimuth_rad = math.radians(azimuth)
            x = center_x + radius * math.sin(azimuth_rad)
            y = center_y - radius * math.cos(azimuth_rad)
            line_options = {"fill": self.accent if azimuth == 0 else grid_color}
            if azimuth != 0:
                line_options["dash"] = (4, 5)
            canvas.create_line(center_x, center_y, x, y, **line_options)
            label_x = center_x + (radius + 16) * math.sin(azimuth_rad)
            label_y = center_y - (radius + 16) * math.cos(azimuth_rad)
            canvas.create_text(
                label_x,
                label_y,
                text=label,
                fill=self.muted,
                font=Font(family="Segoe UI", size=10, weight="bold"),
                anchor="center",
            )

        canvas.create_text(
            center_x,
            center_y,
            text="Zenith",
            fill=self.muted,
            font=Font(family="Segoe UI", size=9),
        )
        canvas.create_text(
            center_x,
            center_y + radius + 34,
            text=f"Horizon local | Latitude {self.latitude:+.3f}\N{DEGREE SIGN}",
            fill=self.muted,
            font=Font(family="Segoe UI", size=9),
        )

    def _draw_star_catalog(self, canvas, center_x, center_y, radius, lst_hours):
        self.sky_star_points = []
        for name, ra_hours, declination, magnitude in self.bright_stars_jnow:
            altitude, azimuth, hour_angle = self._equatorial_to_horizontal(
                ra_hours,
                declination,
                lst_hours,
            )
            point = self._project_horizontal_point(center_x, center_y, radius, altitude, azimuth)
            if point is None:
                continue

            x, y = point
            size = max(1.5, 4.4 - magnitude)
            fill = "#fff4c7" if magnitude < 0.5 else "#d7eaff"
            canvas.create_oval(x - size, y - size, x + size, y + size, fill=fill, outline="")
            self.sky_star_points.append(
                {
                    "name": name,
                    "x": x,
                    "y": y,
                    "ra_hours": ra_hours,
                    "declination": declination,
                    "altitude": altitude,
                    "azimuth": azimuth,
                    "hour_angle": hour_angle,
                    "magnitude": magnitude,
                    "size": size,
                }
            )

            if magnitude <= 0.9:
                canvas.create_text(
                    x + 7,
                    y - 7,
                    text=name,
                    fill="#b8c8d6",
                    font=Font(family="Segoe UI", size=8),
                    anchor="w",
                )

    def _draw_target_marker(self, canvas, center_x, center_y, radius, altitude, azimuth):
        x, y, visible = self._project_target(center_x, center_y, radius, altitude, azimuth)
        marker_color = self.success if visible else self.fg
        canvas.create_oval(x - 11, y - 11, x + 11, y + 11, outline=marker_color, width=2)
        canvas.create_line(x - 17, y, x + 17, y, fill=marker_color, width=2)
        canvas.create_line(x, y - 17, x, y + 17, fill=marker_color, width=2)
        canvas.create_text(
            x,
            y + 26,
            text="Cible",
            fill=marker_color,
            font=Font(family="Segoe UI", size=9, weight="bold"),
        )
        return visible

    def _format_ra(self, ra_hours):
        total_seconds = int(round((ra_hours % 24) * 3600)) % (24 * 3600)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}h {minutes:02d}m {seconds:02d}s"

    def _format_dec(self, dec_degrees):
        sign = "-" if dec_degrees < 0 else "+"
        total_seconds = int(round(abs(dec_degrees) * 3600))
        degrees = min(90, total_seconds // 3600)
        minutes = 0 if degrees == 90 else (total_seconds % 3600) // 60
        seconds = 0 if degrees == 90 else total_seconds % 60
        return f"{sign}{degrees:02d}\N{DEGREE SIGN} {minutes:02d}' {seconds:02d}\""

    def _coordinates_to_fields(self, ra_hours, dec_degrees):
        total_ra_seconds = int(round((ra_hours % 24) * 3600)) % (24 * 3600)
        alpha_hh = total_ra_seconds // 3600
        alpha_mm = (total_ra_seconds % 3600) // 60
        alpha_ss = total_ra_seconds % 60

        dec_degrees = max(-90, min(90, dec_degrees))
        total_dec_seconds = int(round(abs(dec_degrees) * 3600))
        delta_dd = min(90, total_dec_seconds // 3600)
        delta_mm = 0 if delta_dd == 90 else (total_dec_seconds % 3600) // 60
        delta_ss = 0 if delta_dd == 90 else total_dec_seconds % 60
        if dec_degrees < 0:
            delta_dd = "-0" if delta_dd == 0 else -delta_dd

        return alpha_hh, alpha_mm, alpha_ss, delta_dd, delta_mm, delta_ss

    def _sky_coordinates_from_canvas(self, x, y):
        if not self.sky_geometry:
            return None

        center_x = self.sky_geometry["center_x"]
        center_y = self.sky_geometry["center_y"]
        radius = self.sky_geometry["radius"]
        dx = x - center_x
        dy = y - center_y
        if (dx**2 + dy**2) ** 0.5 > radius:
            return None

        sky_radius = (dx**2 + dy**2) ** 0.5
        altitude = 90 - (sky_radius / radius) * 90
        azimuth = math.degrees(math.atan2(dx, -dy)) % 360
        ra_hours, declination, hour_angle = self._horizontal_to_equatorial(
            altitude,
            azimuth,
            self.sky_geometry["lst_hours"],
        )
        return ra_hours, declination, hour_angle, altitude, azimuth

    def _nearest_sky_star(self, x, y):
        nearest = None
        nearest_distance = 999
        for star in self.sky_star_points:
            distance = ((star["x"] - x) ** 2 + (star["y"] - y) ** 2) ** 0.5
            if distance < nearest_distance:
                nearest = star
                nearest_distance = distance

        if nearest is not None and nearest_distance <= max(12, nearest["size"] + 8):
            return nearest
        return None

    def _draw_hover_overlay(self, x, y, star=None):
        if self.sky_canvas is None:
            return

        self.sky_canvas.delete("sky-hover")
        color = self.fg if star else self.accent
        if star:
            x = star["x"]
            y = star["y"]

        self.sky_canvas.create_oval(
            x - 14,
            y - 14,
            x + 14,
            y + 14,
            outline=color,
            width=2,
            tags="sky-hover",
        )
        self.sky_canvas.create_line(x - 22, y, x + 22, y, fill=color, tags="sky-hover")
        self.sky_canvas.create_line(x, y - 22, x, y + 22, fill=color, tags="sky-hover")

    def _update_sky_hover(self):
        if self.sky_hover_position is None:
            if self.sky_canvas is not None:
                self.sky_canvas.delete("sky-hover")
            self.sky_status.config(text=self.sky_base_status)
            return

        x, y = self.sky_hover_position
        coordinates = self._sky_coordinates_from_canvas(x, y)
        if coordinates is None:
            self.sky_canvas.delete("sky-hover")
            self.sky_status.config(text=self.sky_base_status)
            return

        star = self._nearest_sky_star(x, y)
        self._draw_hover_overlay(x, y, star)

        if star:
            label = (
                f"{star['name']} | RA JNow {self._format_ra(star['ra_hours'])} | "
                f"Dec {self._format_dec(star['declination'])} | "
                f"Alt {star['altitude']:+.1f}\N{DEGREE SIGN} Az {star['azimuth']:.0f}\N{DEGREE SIGN} | "
                f"mag {star['magnitude']:.2f}"
            )
        else:
            ra_hours, declination, hour_angle, altitude, azimuth = coordinates
            label = (
                f"Pointeur | RA JNow {self._format_ra(ra_hours)} | "
                f"Dec {self._format_dec(declination)} | "
                f"Alt {altitude:+.1f}\N{DEGREE SIGN} Az {azimuth:.0f}\N{DEGREE SIGN} | "
                f"HA {hour_angle:+.2f}h"
            )

        self.sky_status.config(text=f"{label}\n{self.sky_base_status}")

    def _set_target_from_coordinates(self, ra_hours, dec_degrees, label):
        alpha_hh, alpha_mm, alpha_ss, delta_dd, delta_mm, delta_ss = self._coordinates_to_fields(
            ra_hours,
            dec_degrees,
        )
        self.alpha_hh.set(alpha_hh)
        self.alpha_mm.set(alpha_mm)
        self.alpha_ss.set(alpha_ss)
        self.delta_dd.set(delta_dd)
        self.delta_mm.set(delta_mm)
        self.delta_ss.set(delta_ss)
        self.update_value()
        self._set_result_text(
            f"{label}\nRA JNow: {self._format_ra(ra_hours)}\n"
            f"Dec JNow: {self._format_dec(dec_degrees)}"
        )

    def _on_sky_motion(self, event):
        self.sky_hover_position = (event.x, event.y)
        self._update_sky_hover()

    def _on_sky_leave(self, _event):
        self.sky_hover_position = None
        if self.sky_canvas is not None:
            self.sky_canvas.delete("sky-hover")
        if self.sky_status is not None:
            self.sky_status.config(text=self.sky_base_status)

    def _on_sky_click(self, event):
        self.sky_hover_position = (event.x, event.y)
        coordinates = self._sky_coordinates_from_canvas(event.x, event.y)
        if coordinates is None:
            return

        star = self._nearest_sky_star(event.x, event.y)
        if star:
            self._set_target_from_coordinates(
                star["ra_hours"],
                star["declination"],
                f"Cible definie depuis la carte: {star['name']}",
            )
            return

        ra_hours, declination, _hour_angle, _altitude, _azimuth = coordinates
        self._set_target_from_coordinates(
            ra_hours,
            declination,
            "Cible definie depuis la carte",
        )

    def _update_sky_map(self, state=None):
        if self.sky_canvas is None or self.sky_status is None:
            return

        width = self.sky_canvas.winfo_width()
        height = self.sky_canvas.winfo_height()
        if width < 80 or height < 80:
            return

        if state is None:
            state = compute_clock_state(
                self.longitude,
                self.alpha_hh.get(),
                self.alpha_mm.get(),
                self.alpha_ss.get(),
            )

        self.sky_canvas.delete("all")

        center_x = width / 2
        center_y = height / 2 - 10
        radius = max(40, min(width * 0.43, height * 0.38))
        lst_hours = self._parse_clock_hours(state["lst"])
        self.sky_geometry = {
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius,
            "lst_hours": lst_hours,
        }
        target_ra_hours, target_declination = self._current_target_coordinates()
        target_altitude, target_azimuth, target_hour_angle = self._equatorial_to_horizontal(
            target_ra_hours,
            target_declination,
            lst_hours,
        )

        self._draw_sky_grid(self.sky_canvas, center_x, center_y, radius)
        self._draw_star_catalog(self.sky_canvas, center_x, center_y, radius, lst_hours)
        target_visible = self._draw_target_marker(
            self.sky_canvas,
            center_x,
            center_y,
            radius,
            target_altitude,
            target_azimuth,
        )

        chart_note = "au-dessus de l'horizon" if target_visible else "sous l'horizon"
        self.sky_base_status = (
            f"LST {state['lst']} | HA cible {target_hour_angle:+.2f}h | "
            f"Alt {target_altitude:+.1f}\N{DEGREE SIGN} Az {target_azimuth:.0f}\N{DEGREE SIGN}\n"
            f"Horizon local JNow: {chart_note}"
        )
        self.sky_status.config(text=self.sky_base_status)
        self._update_sky_hover()

    def _set_result_text(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, text)
        self.result_text.config(state=tk.DISABLED)

    def _alpha_text(self):
        return (
            f"{int(self.alpha_hh.get()):02d}h "
            f"{int(self.alpha_mm.get()):02d}m "
            f"{int(self.alpha_ss.get()):02d}s"
        )

    def _delta_text(self):
        delta_degrees_text = str(self.delta_dd.get()).strip()
        delta_sign = "-" if delta_degrees_text.startswith("-") else ""
        delta_degrees = abs(int(delta_degrees_text))
        return (
            f"{delta_sign}{delta_degrees:02d}\N{DEGREE SIGN} "
            f"{int(self.delta_mm.get()):02d}' "
            f"{int(self.delta_ss.get()):02d}\""
        )

    def _sanitize_coordinate_values(self):
        self.alpha_hh.set(self._sanitize_int(self.alpha_hh.get(), 0, 23))
        self.alpha_mm.set(self._sanitize_int(self.alpha_mm.get(), 0, 59))
        self.alpha_ss.set(self._sanitize_int(self.alpha_ss.get(), 0, 59))
        self.delta_dd.set(self._sanitize_int(self.delta_dd.get(), -90, 90))
        self.delta_mm.set(self._sanitize_int(self.delta_mm.get(), 0, 59))
        self.delta_ss.set(self._sanitize_int(self.delta_ss.get(), 0, 59))

    def _sanitize_int(self, value, minimum, maximum):
        value_text = str(value).strip()
        try:
            sanitized = int(value_text)
        except ValueError:
            sanitized = minimum

        sanitized = max(minimum, min(maximum, sanitized))
        if minimum < 0 and sanitized == 0 and value_text.startswith("-"):
            return "-0"
        return str(sanitized)

    def _build_aladin_html(self, ra_deg, dec_deg):
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>AstroClocks v{APP_VERSION} Sky View</title>
  <script type="text/javascript" src="https://aladin.cds.unistra.fr/AladinLite/api/v3/latest/aladin.js" charset="utf-8"></script>
  <style>
    html, body {{
      margin: 0;
      height: 100%;
      font-family: "Segoe UI", Calibri, sans-serif;
      background: {self.ebg};
      color: {self.fg};
    }}
    #header {{
      box-sizing: border-box;
      width: 100%;
      padding: 10px 14px;
      background: {self.card_bg};
      font-size: 14px;
      border-bottom: 1px solid {self.card_edge};
    }}
    #aladin-lite-div {{
      width: 100%;
      height: calc(100% - 42px);
    }}
  </style>
</head>
<body>
  <div id="header">AstroClocks v{APP_VERSION} | Aladin Lite | FOV: {self.aladin_fov_deg:.2f}° | ICRS RA: {ra_deg:.6f}° Dec: {dec_deg:+.6f}°</div>
  <div id="aladin-lite-div"></div>
  <script>
    A.init.then(() => {{
      A.aladin('#aladin-lite-div', {{
        survey: 'P/DSS2/color',
        target: '{ra_deg:.8f} {dec_deg:+.8f}',
        cooFrame: 'J2000',
        fov: {self.aladin_fov_deg:.6f},
        showLayersControl: true,
        showGotoControl: true,
        showFullscreenControl: true,
        showFrame: true,
        showStatusBar: true
      }});
    }});
  </script>
</body>
</html>
"""

    def show_sky_view(self):
        self._sanitize_coordinate_values()
        self.update_value()

        try:
            ra_deg, dec_deg = jnow_to_icrs_degrees(
                self.alpha_hh.get(),
                self.alpha_mm.get(),
                self.alpha_ss.get(),
                self.delta_dd.get(),
                self.delta_mm.get(),
                self.delta_ss.get(),
            )
            html_content = self._build_aladin_html(ra_deg, dec_deg)
            output_file = Path(tempfile.gettempdir()) / "astroclocks_aladin_sky_view.html"
            output_file.write_text(html_content, encoding="utf-8")
            webbrowser.open_new_tab(output_file.as_uri())
        except Exception:
            self._set_result_text("Interactive sky view unavailable. Check internet connection.")
            return

        self._set_result_text(
            f"Opened interactive sky view (ICRS): RA {ra_deg:.6f}° "
            f"Dec {dec_deg:+.6f}° | FOV {self.aladin_fov_deg:.2f}°"
        )

    def update_value(self):
        self._sanitize_coordinate_values()
        self.lbl_alpha.config(text=self._alpha_text())
        self.lbl_delta.config(text=self._delta_text())
        self.lbl_dec_angle.config(
            text=compute_declination_display(
                self.delta_dd.get(),
                self.delta_mm.get(),
                self.delta_ss.get(),
            )
        )
        self._update_sky_map()

    def update_site_labels(self):
        self.site_name_label.config(text=self.site_name)
        self.latlabel.config(text=f"Latitude  : {format_latitude_display(self.latitude)}")
        self.longlabel.config(text=f"Longitude : {format_longitude_display(self.longitude)}")
        self.fov_label.config(text=f"Champ Aladin : {self.aladin_fov_deg:.2f}\N{DEGREE SIGN}")
        if self.aladin_button is not None:
            self.aladin_button.config(text=f"Aladin {self.aladin_fov_deg:.2f}\N{DEGREE SIGN}")

    def _save_current_settings(self):
        self.settings = AppSettings(
            site_name=self.site_name,
            latitude=self.latitude,
            longitude=self.longitude,
            aladin_fov_deg=self.aladin_fov_deg,
        )
        save_app_settings(self.settings)

    def set_default_site(self):
        self.site_name = DEFAULT_SITE_NAME
        self.latitude = DEFAULT_LATITUDE
        self.longitude = DEFAULT_LONGITUDE
        self.aladin_fov_deg = DEFAULT_ALADIN_FOV_DEG
        self._save_current_settings()
        self.update_site_labels()
        self._update_sky_map()

    def _parse_float_setting(self, value, label, minimum, maximum):
        if not is_float(value):
            raise ValueError(f"{label} doit etre un nombre.")

        numeric_value = float(value)
        if numeric_value < minimum or numeric_value > maximum:
            raise ValueError(f"{label} doit etre entre {minimum} et {maximum}.")

        return numeric_value

    def open_settings_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Parametres AstroClocks")
        dialog.configure(bg=self.gbg)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        preset_lookup = {preset_label(preset): preset for preset in LOCATION_PRESETS}
        preset_values = list(preset_lookup)

        preset_var = tk.StringVar(value="")
        site_var = tk.StringVar(value=self.site_name)
        latitude_var = tk.StringVar(value=f"{self.latitude:.5f}")
        longitude_var = tk.StringVar(value=f"{self.longitude:.5f}")
        fov_var = tk.StringVar(value=f"{self.aladin_fov_deg:.2f}")

        body = tk.Frame(dialog, bg=self.gbg, padx=18, pady=16)
        body.grid(column=0, row=0, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)

        def add_label(row, text):
            tk.Label(
                body,
                text=text,
                bg=self.gbg,
                fg=self.muted,
                font=Font(family="Segoe UI", size=10, weight="bold"),
                anchor="w",
            ).grid(column=0, row=row, padx=(0, 10), pady=7, sticky="w")

        def build_entry(row, variable):
            entry = tk.Entry(
                body,
                textvariable=variable,
                bg=self.ebg,
                fg=self.text,
                insertbackground=self.fg,
                font=Font(family="Segoe UI", size=11),
                relief="flat",
                highlightbackground=self.card_edge,
                highlightcolor=self.accent,
                highlightthickness=1,
                width=34,
            )
            entry.grid(column=1, row=row, pady=7, sticky="ew")
            return entry

        add_label(0, "Lieu connu")
        preset_combo = ttk.Combobox(
            body,
            textvariable=preset_var,
            values=preset_values,
            font=Font(family="Segoe UI", size=10),
            width=42,
        )
        preset_combo.grid(column=1, row=0, pady=7, sticky="ew")
        preset_combo["state"] = "readonly"

        def apply_preset(_event=None):
            preset = preset_lookup.get(preset_var.get())
            if preset is None:
                return
            site_var.set(preset["name"])
            latitude_var.set(f"{preset['latitude']:.5f}")
            longitude_var.set(f"{preset['longitude']:.5f}")

        preset_combo.bind("<<ComboboxSelected>>", apply_preset)

        add_label(1, "Nom du site")
        build_entry(1, site_var)
        add_label(2, "Latitude")
        build_entry(2, latitude_var)
        add_label(3, "Longitude")
        build_entry(3, longitude_var)
        add_label(4, "Champ Aladin")
        build_entry(4, fov_var)

        hint = tk.Label(
            body,
            text="Latitude [-90, 90], longitude [-180, 180], champ Aladin en degres.",
            bg=self.gbg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=9),
            anchor="w",
        )
        hint.grid(column=0, row=5, columnspan=2, pady=(2, 12), sticky="ew")

        actions = tk.Frame(body, bg=self.gbg)
        actions.grid(column=0, row=6, columnspan=2, sticky="e")

        def apply_settings():
            try:
                latitude = self._parse_float_setting(latitude_var.get(), "Latitude", -90, 90)
                longitude = self._parse_float_setting(longitude_var.get(), "Longitude", -180, 180)
                fov = self._parse_float_setting(fov_var.get(), "Champ Aladin", 0.01, 180)
            except ValueError as exc:
                messagebox.showerror("Parametres invalides", str(exc), parent=dialog)
                return

            self.site_name = site_var.get().strip() or "Site personnalise"
            self.latitude = latitude
            self.longitude = longitude
            self.aladin_fov_deg = fov
            self._save_current_settings()
            self.update_site_labels()
            self._update_sky_map()
            dialog.destroy()

        self._build_button(actions, "Annuler", dialog.destroy).grid(column=0, row=0, padx=(0, 8))
        self._build_button(actions, "Appliquer", apply_settings).grid(column=1, row=0)

        dialog.bind("<Return>", lambda _event: apply_settings())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.update_idletasks()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog.winfo_width()) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{max(0, x)}+{max(0, y)}")

    def _apply_coordinate_result(self, result):
        self._set_result_text(result["message"])
        self.alpha_hh.set(result["alpha_hh"])
        self.alpha_mm.set(result["alpha_mm"])
        self.alpha_ss.set(result["alpha_ss"])
        self.delta_dd.set(result["delta_dd"])
        self.delta_mm.set(result["delta_mm"])
        self.delta_ss.set(result["delta_ss"])
        self.update_value()

    def search_coordinates(self):
        solar_system = [
            "sun",
            "soleil",
            "mercure",
            "mercury",
            "venus",
            "lune",
            "moon",
            "mars",
            "jupiter",
            "saturne",
            "saturn",
            "uranus",
            "neptune",
            "pluto",
            "pluton",
        ]
        solar_system_types = [
            "Asteroid",
            "Comet",
            "Dwarf Planet",
            "Planet",
            "Natural Satellite",
        ]

        selected_type = self.combo_box.get()
        object_name = self.search_entry.get()

        if selected_type in solar_system_types:
            try:
                result = resolve_solar_system_coordinates(selected_type, object_name)
            except Exception:
                self._set_result_text("An error occurred while retrieving the ephemerides.")
                return

            self._apply_coordinate_result(result)
            return

        if object_name.lower() in solar_system:
            self._set_result_text("Please select the right object type !")
            return

        if not selected_type:
            self._set_result_text("Please select an object type.")
            return

        if not object_name:
            self._set_result_text("")
            return

        try:
            result = resolve_deep_sky_coordinates(object_name)
        except name_resolve.NameResolveError:
            self._set_result_text(
                "Object not found !\nPlease enter a valid name\n(ex : M13, HIP114971, Sirius,..)"
            )
            return

        self._apply_coordinate_result(result)

    def clocks(self):
        self._sanitize_coordinate_values()
        state = compute_clock_state(
            self.longitude,
            self.alpha_hh.get(),
            self.alpha_mm.get(),
            self.alpha_ss.get(),
        )

        self.label_local.config(text=state["local"])
        self.label_utc.config(text=state["utc"])
        self.label_gmst.config(text=state["gmst"])
        self.label_lst.config(text=state["lst"])
        self.lbl_hour_angle.config(text=state["hour_angle"])
        try:
            self._update_sky_map(state)
        except Exception as exc:
            if self.sky_status is not None:
                self.sky_status.config(text=f"Carte du ciel indisponible: {exc}")
        finally:
            self.root.after(250, self.clocks)

    def run(self):
        download_IERS_A()
        self.clocks()
        self.root.mainloop()


def main():
    app = AstroClocksApp()
    app.run()
