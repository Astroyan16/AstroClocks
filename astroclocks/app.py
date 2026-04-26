import tempfile
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import ttk
from tkinter.font import Font

from astroplan import download_IERS_A
from astropy.coordinates import name_resolve

from astroclocks.astronomy import (
    compute_clock_state,
    compute_declination_display,
    format_timezone_label,
    jnow_to_icrs_degrees,
    resolve_deep_sky_coordinates,
    resolve_solar_system_coordinates,
)
from astroclocks.settings import (
    DEFAULT_LONGITUDE,
    format_longitude_display,
    load_longitude,
    save_longitude,
)
from astroclocks.utils import is_float, resource_path


APP_VERSION = "3.0"

BRIGHT_STARS = [
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
        self.longitude = load_longitude()
        self.coord_font_size = 24
        self.sky_canvas = None
        self.sky_status = None

        self._configure_styles()
        self._configure_root()
        self._create_frames()
        self._create_longitude_widgets()
        self._create_search_widgets()
        self._create_time_widgets()
        self._create_coordinate_widgets()
        self._create_hour_angle_widgets()
        self._create_sky_widgets()
        self.update_longitude_label()
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
        self.root.bind(
            "<F11>",
            lambda event: self.root.attributes(
                "-fullscreen", not self.root.attributes("-fullscreen")
            ),
        )
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        self.root.config(background=self.gbg)
        self.root.grid_columnconfigure(0, weight=1, uniform="main")
        self.root.grid_columnconfigure(1, weight=1, uniform="main")
        self.root.grid_columnconfigure(2, weight=1, uniform="main")
        self.root.grid_rowconfigure(0, weight=0)
        for row in range(1, 6):
            self.root.grid_rowconfigure(row, weight=1)

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
            text="Temps civil, temps sideral, coordonnees JNow et carte equatoriale temps reel",
            foreground=self.muted,
            background=self.gbg,
            font=Font(family="Segoe UI", size=11),
            anchor="w",
        )
        subtitle.grid(column=0, row=1, sticky="w", pady=(0, 4))

        pill = tk.Label(
            header,
            text="F11 plein ecran",
            foreground=self.ebg,
            background=self.accent,
            font=Font(family="Segoe UI", size=10, weight="bold"),
            padx=14,
            pady=5,
        )
        pill.grid(column=1, row=0, rowspan=2, sticky="e")

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
        self.lf_long = self._build_labelframe("Longitude", 0, 1)
        self.lf_search = self._build_labelframe("Find coordinates of an object", 1, 1)
        self.lf_sky = self._build_labelframe("Live sky map", 2, 1, rowspan=5, bd=6)
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

    def _create_longitude_widgets(self):
        self.long_entry = tk.Entry(
            self.lf_long,
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
        self.long_entry.grid(column=0, row=0, ipady=7, padx=8, pady=8, sticky="ew")

        self._build_button(self.lf_long, "Set", self.set_longitude).grid(
            column=1, row=0, padx=8, pady=8, sticky="ew"
        )

        self.longlabel = tk.Label(
            self.lf_long,
            font=Font(family="Segoe UI", size=18, weight="bold"),
            background=self.ebg,
            foreground=self.fg,
            padx=10,
            pady=8,
        )
        self.longlabel.grid(column=0, row=1, padx=8, pady=8, sticky="ew")

        self._build_button(self.lf_long, "Reset", self.set_longitude_default).grid(
            column=1, row=1, padx=8, pady=8, sticky="ew"
        )
        self.lf_long.grid_columnconfigure(0, weight=1)

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

        self._build_button(self.lf_search, "Aladin 0.5°", self.show_sky_view).grid(
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
        )
        self.sky_canvas.grid(column=0, row=0, padx=8, pady=8, sticky="nsew")
        self.sky_canvas.bind("<Configure>", lambda _event: self._update_sky_map())

        self.sky_status = tk.Label(
            self.lf_sky,
            text="",
            bg=self.card_bg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10),
            justify="left",
            anchor="w",
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
        dec_sign = -1 if float(self.delta_dd.get()) < 0 else 1
        dec_degrees = dec_sign * (
            abs(float(self.delta_dd.get()))
            + (float(self.delta_mm.get()) / 60)
            + (float(self.delta_ss.get()) / 3600)
        )
        return ra_hours, dec_degrees

    def _normalize_hour_angle(self, hours):
        return ((hours + 12) % 24) - 12

    def _project_sky_point(self, center_x, center_y, radius, hour_angle, declination):
        x = center_x + (hour_angle / 6) * radius
        y = center_y - (declination / 90) * radius
        distance = ((x - center_x) ** 2 + (y - center_y) ** 2) ** 0.5
        if distance > radius:
            return None
        return x, y

    def _project_target(self, center_x, center_y, radius, hour_angle, declination):
        plotted_hour_angle = max(-6, min(6, hour_angle))
        plotted_declination = max(-90, min(90, declination))
        x = center_x + (plotted_hour_angle / 6) * radius
        y = center_y - (plotted_declination / 90) * radius

        dx = x - center_x
        dy = y - center_y
        distance = (dx**2 + dy**2) ** 0.5
        visible = abs(hour_angle) <= 6 and distance <= radius
        if distance > radius:
            scale = radius / distance
            x = center_x + dx * scale
            y = center_y + dy * scale
        return x, y, visible

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
        for declination in (-60, -30, 0, 30, 60):
            y = center_y - (declination / 90) * radius
            span = max(0, (radius**2 - (y - center_y) ** 2) ** 0.5)
            canvas.create_line(
                center_x - span,
                y,
                center_x + span,
                y,
                fill=grid_color,
                dash=(4, 5),
            )
            canvas.create_text(
                center_x + span - 6,
                y - 8,
                text=f"{declination:+d}\N{DEGREE SIGN}",
                fill=self.muted,
                font=Font(family="Segoe UI", size=8),
                anchor="e",
            )

        for hour_angle in (-6, -3, 0, 3, 6):
            x = center_x + (hour_angle / 6) * radius
            span = max(0, (radius**2 - (x - center_x) ** 2) ** 0.5)
            color = self.accent if hour_angle == 0 else grid_color
            width = 2 if hour_angle == 0 else 1
            line_options = {"fill": color, "width": width}
            if hour_angle != 0:
                line_options["dash"] = (4, 5)
            canvas.create_line(x, center_y - span, x, center_y + span, **line_options)
            canvas.create_text(
                x,
                center_y + span + 14,
                text=f"{hour_angle:+d}h",
                fill=self.muted,
                font=Font(family="Segoe UI", size=8),
                anchor="center",
            )

        canvas.create_text(
            center_x,
            center_y - radius - 16,
            text="Dec +90",
            fill=self.muted,
            font=Font(family="Segoe UI", size=9),
        )
        canvas.create_text(
            center_x,
            center_y + radius + 34,
            text="Meridien local au centre",
            fill=self.muted,
            font=Font(family="Segoe UI", size=9),
        )

    def _draw_star_catalog(self, canvas, center_x, center_y, radius, lst_hours):
        for name, ra_hours, declination, magnitude in BRIGHT_STARS:
            hour_angle = self._normalize_hour_angle(lst_hours - ra_hours)
            if abs(hour_angle) > 6:
                continue

            point = self._project_sky_point(
                center_x,
                center_y,
                radius,
                hour_angle,
                declination,
            )
            if point is None:
                continue

            x, y = point
            size = max(1.5, 4.4 - magnitude)
            fill = "#fff4c7" if magnitude < 0.5 else "#d7eaff"
            canvas.create_oval(x - size, y - size, x + size, y + size, fill=fill, outline="")

            if magnitude <= 0.9:
                canvas.create_text(
                    x + 7,
                    y - 7,
                    text=name,
                    fill="#b8c8d6",
                    font=Font(family="Segoe UI", size=8),
                    anchor="w",
                )

    def _draw_target_marker(self, canvas, center_x, center_y, radius, hour_angle, declination):
        x, y, visible = self._project_target(center_x, center_y, radius, hour_angle, declination)
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
        target_ra_hours, target_declination = self._current_target_coordinates()
        target_hour_angle = self._normalize_hour_angle(lst_hours - target_ra_hours)

        self._draw_sky_grid(self.sky_canvas, center_x, center_y, radius)
        self._draw_star_catalog(self.sky_canvas, center_x, center_y, radius, lst_hours)
        target_visible = self._draw_target_marker(
            self.sky_canvas,
            center_x,
            center_y,
            radius,
            target_hour_angle,
            target_declination,
        )

        chart_note = "dans la fenetre +/-6h" if target_visible else "hors fenetre, marqueur au bord"
        self.sky_status.config(
            text=(
                f"LST {state['lst']} | HA cible {target_hour_angle:+.2f}h | "
                f"Dec {target_declination:+.1f}\N{DEGREE SIGN}\n"
                f"Projection equatoriale temps reel: {chart_note}"
            )
        )

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
        return (
            f"{int(self.delta_dd.get()):02d}\N{DEGREE SIGN} "
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
        try:
            sanitized = int(value)
        except ValueError:
            sanitized = minimum

        sanitized = max(minimum, min(maximum, sanitized))
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
  <div id="header">AstroClocks v{APP_VERSION} | Aladin Lite | FOV: 0.5° | ICRS RA: {ra_deg:.6f}° Dec: {dec_deg:+.6f}°</div>
  <div id="aladin-lite-div"></div>
  <script>
    A.init.then(() => {{
      A.aladin('#aladin-lite-div', {{
        survey: 'P/DSS2/color',
        target: '{ra_deg:.8f} {dec_deg:+.8f}',
        cooFrame: 'J2000',
        fov: 0.5,
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
            f"Opened interactive sky view (ICRS): RA {ra_deg:.6f}° Dec {dec_deg:+.6f}° | FOV 0.5°"
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

    def update_longitude_label(self):
        self.longlabel.config(text=format_longitude_display(self.longitude))

    def set_longitude_default(self):
        self.longitude = DEFAULT_LONGITUDE
        save_longitude(self.longitude)
        self.update_longitude_label()
        self._update_sky_map()

    def set_longitude(self):
        entry_value = self.long_entry.get()
        if not is_float(entry_value):
            self.set_longitude_default()
            return

        longitude = float(entry_value)
        if longitude < -180 or longitude > 180:
            self.set_longitude_default()
            return

        self.longitude = longitude
        save_longitude(self.longitude)
        self.update_longitude_label()
        self._update_sky_map()

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
        self._update_sky_map(state)
        self.root.after(250, self.clocks)

    def run(self):
        download_IERS_A()
        self.clocks()
        self.root.mainloop()


def main():
    app = AstroClocksApp()
    app.run()
