import datetime
import math
import socket
import tempfile
import threading
import tkinter as tk
import time
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk
from tkinter.font import Font
from zoneinfo import available_timezones

from astroplan import download_IERS_A
from astropy.coordinates import name_resolve
try:
    from PIL import Image, ImageDraw, ImageTk
except ImportError:
    Image = None
    ImageDraw = None
    ImageTk = None

from astroclocks.astronomy import (
    compute_clock_state,
    compute_declination_display,
    compute_sun_altitudes,
    compute_solar_system_body_positions,
    compute_solar_system_positions,
    convert_star_catalog_j2000_to_jnow,
    format_timezone_label,
    jnow_to_icrs_degrees,
    resolve_deep_sky_coordinates,
    resolve_solar_system_coordinates,
    resolve_timezone,
)
from astroclocks.double_star_catalog import (
    DOUBLE_STARS,
    build_wds_notes_url,
    fetch_wds_double_stars,
    fetch_wds_notes,
    load_cached_wds_double_stars,
    merge_cached_wds_double_stars,
)
from astroclocks.i18n import LANGUAGE_NAMES, LANGUAGE_OPTIONS, translate
from astroclocks.orbit_catalog import (
    enrich_double_stars_with_orb6,
    fetch_orb6_ephemerides,
    fetch_orb6_orbits,
    load_cached_orb6_ephemerides,
    load_cached_orb6_orbits,
    orbit_position_at_year,
    sample_orbit_points,
)
from astroclocks.settings import (
    AppSettings,
    DEFAULT_ALADIN_FOV_DEG,
    DEFAULT_COUNTRY,
    DEFAULT_DAYLIGHT_SAVING_ENABLED,
    DEFAULT_DECLINATION_OFFSET_ENABLED,
    DEFAULT_DOUBLE_INCLUDE_APPARENT,
    DEFAULT_DOUBLE_INCLUDE_NOTED,
    DEFAULT_DOUBLE_INCLUDE_PHYSICAL,
    DEFAULT_DOUBLE_INCLUDE_UNCERTAIN,
    DEFAULT_DOUBLE_EXCLUDE_POLAR_CIRCLE,
    DEFAULT_DOUBLE_MAX_PRIMARY_MAGNITUDE,
    DEFAULT_DOUBLE_MAX_SECONDARY_MAGNITUDE,
    DEFAULT_DOUBLE_MAX_SEPARATION,
    DEFAULT_DOUBLE_MIN_MAX_ALTITUDE,
    DEFAULT_DOUBLE_MIN_SEPARATION,
    DEFAULT_DOUBLE_USE_ONLINE,
    DEFAULT_DOUBLE_VISIBLE_NIGHT,
    DEFAULT_HOUR_ANGLE_OFFSET_ENABLED,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_SITE_NAME,
    DEFAULT_SKY_MAGNITUDE_LIMIT,
    DEFAULT_SKY_SHOW_ALTAZ_GRID,
    DEFAULT_SKY_SHOW_EQUATORIAL_GRID,
    DEFAULT_SKY_SHOW_SOLAR_SYSTEM,
    DEFAULT_TIMEZONE_NAME,
    MAX_SKY_MAGNITUDE_LIMIT,
    format_latitude_display,
    format_longitude_display,
    load_app_settings,
    save_app_settings,
)
from astroclocks.sites import LOCATION_PRESETS, preset_label
from astroclocks.star_catalog import SKY_STARS_J2000
from astroclocks.utils import is_float, resource_path
from astroclocks.windowing import (
    center_window_on_pointer_monitor,
    current_monitor_geometry as window_current_monitor_geometry,
    fallback_screen_geometry as window_fallback_screen_geometry,
    monitor_geometry as window_monitor_geometry,
    monitor_geometry_from_handle as window_monitor_geometry_from_handle,
    monitor_geometry_from_point as window_monitor_geometry_from_point,
    move_window_to as window_move_window_to,
    pointer_monitor_geometry as window_pointer_monitor_geometry,
)


APP_VERSION = "3.2"
APP_RELEASE_MONTH = 4
APP_YEAR = "2026"
APP_AUTHOR = "Yannis Benazza"
APP_EMAIL = "yannis.benazza@obspm.fr"
APP_PHONE = "01 45 07 71 59"
CLOCK_REFRESH_HZ = 15
CLOCK_REFRESH_MS = round(1000 / CLOCK_REFRESH_HZ)
SKY_MAP_ANTIALIASED_REFRESH_SECONDS = 8
SKY_MAP_CANVAS_REFRESH_SECONDS = 8
SKY_STAR_SUBPIXEL_STEPS = 4
SKY_STAR_BRIGHTNESS_MULTIPLIER = 1.27
SOLAR_SYSTEM_CACHE_SECONDS = 10
DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 900
MIN_WINDOW_WIDTH = 1234
MIN_WINDOW_HEIGHT = 844
INITIAL_WINDOW_SCREEN_WIDTH_RATIO = 0.92
INITIAL_WINDOW_SCREEN_HEIGHT_RATIO = 0.90
WINDOW_SCREEN_MARGIN = 32
SKY_STAR_LABEL_MAX_MAGNITUDE = 1.25
TARGET_LOW_ALTITUDE_COLOR = "#f6c451"
NAMED_STAR_COLORS = {
    "Achernar": "#b9d7ff",
    "Acrux": "#b8d6ff",
    "Adhara": "#bddbff",
    "Aldebaran": "#ffb36a",
    "Alioth": "#d6e7ff",
    "Alkaid": "#c9ddff",
    "Alnair": "#c6ddff",
    "Alnilam": "#b7d7ff",
    "Alnitak": "#b6d7ff",
    "Alpha Centauri": "#fff0c4",
    "Alphard": "#ffc074",
    "Altair": "#f4fbff",
    "Antares": "#ff805c",
    "Arcturus": "#ffad62",
    "Atria": "#ffbf78",
    "Bellatrix": "#bfdcff",
    "Betelgeuse": "#ff8d5c",
    "Canopus": "#fff0c0",
    "Capella": "#fff0a8",
    "Castor": "#e3f0ff",
    "Deneb": "#d6e8ff",
    "Denebola": "#eef6ff",
    "Dubhe": "#ffd08a",
    "Elnath": "#dbeaff",
    "Fomalhaut": "#eef6ff",
    "Gacrux": "#ffb370",
    "Hadar": "#b7d8ff",
    "Hamal": "#ffbf78",
    "Kaus Australis": "#bcd9ff",
    "Kochab": "#ffca86",
    "Markab": "#d8e9ff",
    "Menkalinan": "#f6fbff",
    "Menkent": "#ffc17a",
    "Miaplacidus": "#f6fbff",
    "Mimosa": "#b8d8ff",
    "Mirach": "#ffbd78",
    "Mirfak": "#fff0b8",
    "Mirzam": "#bcdcff",
    "Nunki": "#c5ddff",
    "Peacock": "#bddbff",
    "Pollux": "#ffc078",
    "Procyon": "#fff7d5",
    "Regulus": "#d4e8ff",
    "Rigel": "#b8d8ff",
    "Rigil Kentaurus": "#fff0c4",
    "Saiph": "#bad9ff",
    "Sargas": "#ffe0a6",
    "Shaula": "#b9d8ff",
    "Sirius": "#f2f8ff",
    "Spica": "#b9d9ff",
    "Vega": "#e6f1ff",
    "Wezen": "#fff0b0",
}
TWILIGHT_PHASE_COLORS = {
    "day": "#243744",
    "civil": "#20303c",
    "nautical": "#1a2732",
    "astronomical": "#141f29",
}
DOUBLE_NIGHT_SUN_MAX_ALTITUDE = -6
DOUBLE_NIGHT_TARGET_MIN_ALTITUDE = 10
DOUBLE_PHYSICAL_NOTE_FLAGS = frozenset({"O", "C", "Z", "T", "V"})
DOUBLE_NOTED_NOTE_FLAGS = frozenset({"N"})
DOUBLE_APPARENT_NOTE_FLAGS = frozenset({"Y", "S", "U"})
DOUBLE_UNCERTAIN_NOTE_FLAGS = frozenset({"I", "X"})
SOLAR_SYSTEM_BODY_COLORS = {
    "Sun": "#ffd166",
    "Moon": "#dce6ef",
    "Mercury": "#b8a189",
    "Venus": "#f4d58d",
    "Mars": "#ff8a65",
    "Jupiter": "#f2c078",
    "Saturn": "#e6d3a3",
    "Uranus": "#8ecae6",
    "Neptune": "#7aa2ff",
}
OBJECT_TYPE_CODES = (
    "Asteroid",
    "Comet",
    "Dwarf Planet",
    "Planet",
    "Natural Satellite",
    "Star, Deep Sky Object",
)


def apply_app_icon(window, default=False):
    """Apply the AstroClocks icon to a Tk/Toplevel window when the platform supports it."""
    icon_path = resource_path("AppIcon.ico")
    try:
        if default:
            window.iconbitmap(default=icon_path)
        window.iconbitmap(icon_path)
    except (tk.TclError, TypeError):
        pass


class AstroClocksApp:
    def __init__(self, root=None, loading_window=None, loading_status_var=None):
        self.root = root or tk.Tk()
        self.loading_window = loading_window
        self.loading_status_var = loading_status_var
        self.startup_monitor_geometry = getattr(
            self.root,
            "_astroclocks_startup_monitor_geometry",
            None,
        )
        self.root.withdraw()
        self.root.title(f"AstroClocks v{APP_VERSION}")
        apply_app_icon(self.root, default=True)
        if self.loading_window is not None:
            apply_app_icon(self.loading_window)
        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)

        self.gbg = "#101419"
        self.card_bg = "#171f26"
        self.card_edge = "#2b3a45"
        self.ebg = "#0b1015"
        self.fg = "#f6c451"
        self.text = "#edf3f8"
        self.muted = "#93a6b7"
        self.accent = "#4cc9f0"
        self.success = "#7bd88f"
        self.danger = "#ff5c5c"
        self.button_bg = "#22303a"
        self._set_loading_status("Chargement des paramètres...")
        self.settings = load_app_settings()
        self.site_name = self.settings.site_name
        self.country = self.settings.country
        self.latitude = self.settings.latitude
        self.longitude = self.settings.longitude
        self.aladin_fov_deg = self.settings.aladin_fov_deg
        self.sky_magnitude_limit = self.settings.sky_magnitude_limit
        self.sky_show_altaz_grid = self.settings.sky_show_altaz_grid
        self.sky_show_equatorial_grid = self.settings.sky_show_equatorial_grid
        self.sky_show_solar_system = self.settings.sky_show_solar_system
        self.timezone_name = self._normalize_timezone_name(self.settings.timezone_name)
        self.daylight_saving_enabled = self.settings.daylight_saving_enabled
        self.language = self.settings.language
        self.hour_angle_offset_enabled = self.settings.hour_angle_offset_enabled
        self.declination_offset_enabled = self.settings.declination_offset_enabled
        self.clock_font_size = 30
        self.coord_font_size = 24
        self.angle_font_size = 44
        self.header_title_font_size = 21
        self.search_button = None
        self.aladin_button = None
        self.connectivity_label = None
        self.network_online = None
        self.connectivity_check_pending = False
        self.sky_canvas = None
        self.sky_status = None
        self._set_loading_status("Conversion du catalogue d'étoiles...")
        self.named_stars_jnow = convert_star_catalog_j2000_to_jnow(SKY_STARS_J2000)
        self.sky_geometry = None
        self.sky_map_cache_key = None
        self.sky_star_image = None
        self.sky_star_stamp_cache = {}
        self.sky_star_points = []
        self.sky_solar_system_points = []
        self.sky_hover_position = None
        self.sky_hover_update_pending = False
        self.sky_last_status_update_time = 0
        self.sky_base_status = ""
        self.sky_base_status_highlights = ()
        self.solar_system_cache_key = None
        self.solar_system_cache = []
        self.target_active = False
        self.target_solar_system_name = None
        self.is_fullscreen = False
        self.windowed_geometry = None
        self.windowed_state = "normal"
        self.labelframe_title_labels = []
        self.object_type_label_to_code = {}
        self.angle_labels = []
        self.clock_labels = []
        self.site_info_lines = None
        self.site_info_font = None
        self.site_info_name_font = None
        self.notebook = None
        self.main_tab = None
        self.visibility_tab = None
        self.double_star_tab = None
        self.visibility_canvas = None
        self.visibility_status = None
        self.visibility_cache_key = None
        self.visibility_curve_points = []
        self.visibility_chart_geometry = None
        self.visibility_hover_position = None
        self.double_star_results = []
        self.double_star_tree = None
        self.double_reset_button = None
        self.double_tree_separators = []
        self.double_sort_column = "name"
        self.double_sort_reverse = False
        self.double_search_generation = 0
        self.double_remote_search_pending = False
        self.double_orb6_index = None
        self.double_orb6_orbit_index = None
        self.double_wds_note_cache = {}
        self.double_wds_cached_stars = []
        self.coordinate_search_generation = 0
        self.coordinate_search_pending = False
        self.translated_widgets = []

        self._set_loading_status("Chargement du cache ORB6...")
        self.double_orb6_index = load_cached_orb6_ephemerides()
        self.double_orb6_orbit_index = load_cached_orb6_orbits()
        self.double_wds_cached_stars = load_cached_wds_double_stars()

        self._set_loading_status("Préparation de l'interface...")
        self._configure_styles()
        self._configure_root()
        self._create_frames()
        self._create_site_widgets()
        self._create_search_widgets()
        self._create_time_widgets()
        self._create_coordinate_widgets()
        self._create_hour_angle_widgets()
        self._create_sky_widgets()
        self._create_visibility_widgets()
        self._create_double_star_widgets()
        self.update_site_labels()
        self.update_value(activate_target=False)
        self._schedule_connectivity_check(0)
        self._set_loading_status("Affichage de la fenêtre...")
        self._place_initial_window()
        self._close_loading_window()

        self.root.bind("<Return>", lambda event: self.search_coordinates())
        self.root.bind("<Configure>", self._update_dynamic_fonts)
        self._update_dynamic_fonts()

    def _tr(self, key, **values):
        return translate(self.language, key, **values)

    def _set_loading_status(self, text):
        if self.loading_status_var is None:
            return
        try:
            self.loading_status_var.set(text)
            if self.loading_window is not None:
                self.loading_window.update_idletasks()
                self.loading_window.update()
        except (tk.TclError, RuntimeError):
            pass

    def _close_loading_window(self):
        if self.loading_window is None:
            return
        try:
            self.loading_window.destroy()
        except (tk.TclError, RuntimeError):
            pass
        self.loading_window = None
        self.loading_status_var = None

    def _release_date_text(self):
        return f"{self._tr(f'about.month.{APP_RELEASE_MONTH}')} {APP_YEAR}"

    def _normalize_timezone_name(self, timezone_name):
        timezone_name = str(timezone_name or "").strip()
        if timezone_name:
            try:
                format_timezone_label(timezone_name)
            except ValueError:
                return DEFAULT_TIMEZONE_NAME
        return timezone_name

    def _validate_timezone_name(self, timezone_name):
        timezone_name = str(timezone_name or "").strip()
        if timezone_name:
            format_timezone_label(timezone_name)
        return timezone_name

    def _timezone_options(self):
        offsets = ["UTC"]
        for total_minutes in range(-12 * 60, 14 * 60 + 1, 15):
            if total_minutes == 0:
                continue
            sign = "+" if total_minutes > 0 else "-"
            absolute_minutes = abs(total_minutes)
            offsets.append(
                f"UTC{sign}{absolute_minutes // 60:02d}:{absolute_minutes % 60:02d}"
            )

        zone_names = sorted(available_timezones())
        preferred = [name for name in ("Europe/Paris", "UTC") if name in zone_names or name == "UTC"]
        options = preferred + zone_names + offsets
        if self.timezone_name:
            options.insert(0, self.timezone_name)
        return list(dict.fromkeys(options))

    def _timezone_label(self):
        try:
            label = format_timezone_label(
                self.timezone_name,
                daylight_saving_enabled=self.daylight_saving_enabled
                and bool(self.timezone_name),
            )
        except ValueError:
            label = format_timezone_label()

        if self._timezone_has_daylight_saving_active():
            label = f"{label} ({self._tr('timezone.daylight_saving_active')})"
        return label

    def _timezone_has_daylight_saving_active(self):
        if self.timezone_name:
            return self.daylight_saving_enabled
        return time.localtime().tm_isdst > 0

    def _local_time_title_kwargs(self):
        return {"timezone": self._timezone_label()}

    def _configure_styles(self):
        style = ttk.Style()
        style.theme_use("default")

        self.root.option_add("*TCombobox*Listbox*Background", self.ebg)
        self.root.option_add("*TCombobox*Listbox*Foreground", self.text)
        self.root.option_add("*TCombobox*Listbox*selectBackground", self.accent)
        self.root.option_add("*TCombobox*Listbox*selectForeground", self.ebg)

        style.map(
            "TCombobox",
            fieldbackground=[("disabled", self.card_bg), ("readonly", self.ebg)],
        )
        style.map(
            "TCombobox",
            selectbackground=[("disabled", self.card_bg), ("readonly", self.ebg)],
        )
        style.map(
            "TCombobox",
            selectforeground=[("disabled", self.muted), ("readonly", self.text)],
        )
        style.map(
            "TCombobox",
            background=[("disabled", self.card_edge), ("readonly", self.card_edge)],
        )
        style.map(
            "TCombobox",
            foreground=[("disabled", self.muted), ("readonly", self.text)],
        )
        style.configure(
            "TCombobox",
            arrowsize=18,
            fieldbackground=self.ebg,
            background=self.card_edge,
            foreground=self.text,
            borderwidth=0,
            padding=6,
        )
        style.configure(
            "TNotebook",
            background=self.gbg,
            borderwidth=0,
            tabmargins=(0, 0, 0, 0),
        )
        style.configure(
            "TNotebook.Tab",
            background=self.button_bg,
            foreground=self.text,
            borderwidth=0,
            padding=(16, 8),
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", self.accent), ("active", self.card_edge)],
            foreground=[("selected", self.ebg), ("active", self.text)],
        )
        style.configure(
            "Treeview",
            background=self.ebg,
            fieldbackground=self.ebg,
            foreground=self.text,
            rowheight=27,
            borderwidth=1,
            relief="solid",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Treeview.Heading",
            background=self.button_bg,
            foreground=self.text,
            borderwidth=1,
            relief="solid",
            font=("Segoe UI", 10, "bold"),
        )
        style.map(
            "Treeview.Heading",
            background=[("pressed", self.text), ("active", self.accent)],
            foreground=[("pressed", self.ebg), ("active", self.ebg)],
        )
        style.map(
            "Treeview",
            background=[("selected", self.accent)],
            foreground=[("selected", self.ebg)],
        )
        for scrollbar_style in ("Dark.Vertical.TScrollbar", "Dark.Horizontal.TScrollbar"):
            style.configure(
                scrollbar_style,
                background=self.button_bg,
                darkcolor=self.button_bg,
                lightcolor=self.button_bg,
                troughcolor=self.ebg,
                bordercolor=self.card_edge,
                arrowcolor=self.text,
                relief="flat",
                borderwidth=0,
                arrowsize=13,
            )
            style.map(
                scrollbar_style,
                background=[("pressed", self.card_edge), ("active", self.accent)],
                arrowcolor=[("pressed", self.text), ("active", self.ebg)],
            )

    def _configure_root(self):
        self.root.attributes("-fullscreen", False)
        self.root.bind("<F11>", self._toggle_fullscreen)
        self.root.bind("<Escape>", self._exit_fullscreen)
        self.root.config(background=self.gbg)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=0)
        self.root.grid_rowconfigure(1, weight=1)

    def _monitor_geometry_from_handle(self, hwnd, use_work_area=False):
        return window_monitor_geometry_from_handle(hwnd, use_work_area=use_work_area)

    def _monitor_geometry_from_point(self, x, y, use_work_area=False):
        return window_monitor_geometry_from_point(x, y, use_work_area=use_work_area)

    def _monitor_geometry(self, monitor, use_work_area=False):
        return window_monitor_geometry(monitor, use_work_area=use_work_area)

    def _fallback_screen_geometry(self):
        return window_fallback_screen_geometry(self.root)

    def _current_monitor_geometry(self, use_work_area=False):
        return window_current_monitor_geometry(self.root, use_work_area=use_work_area)

    def _pointer_monitor_geometry(self, use_work_area=False):
        return window_pointer_monitor_geometry(self.root, use_work_area=use_work_area)

    def _move_window_to(self, window, x, y):
        window_move_window_to(window, x, y)

    def _place_initial_window(self):
        monitor_x, monitor_y, monitor_width, monitor_height = (
            self.startup_monitor_geometry
            or self._pointer_monitor_geometry(use_work_area=True)
        )
        screen_width = monitor_width
        screen_height = monitor_height

        available_width = max(1, screen_width - WINDOW_SCREEN_MARGIN)
        available_height = max(1, screen_height - WINDOW_SCREEN_MARGIN)
        target_width = min(
            round(screen_width * INITIAL_WINDOW_SCREEN_WIDTH_RATIO),
            available_width,
        )
        target_height = min(
            round(screen_height * INITIAL_WINDOW_SCREEN_HEIGHT_RATIO),
            available_height,
        )
        window_width = max(MIN_WINDOW_WIDTH, target_width)
        window_height = max(MIN_WINDOW_HEIGHT, target_height)

        self.root.minsize(MIN_WINDOW_WIDTH, MIN_WINDOW_HEIGHT)
        x = monitor_x + max(0, (screen_width - window_width) // 2)
        y = monitor_y + max(0, (screen_height - window_height) // 2)

        try:
            self.root.attributes("-alpha", 0.0)
        except (tk.TclError, RuntimeError):
            pass
        self.root.geometry(f"{int(window_width)}x{int(window_height)}")
        self.root.update_idletasks()
        self.root.deiconify()
        self.root.update_idletasks()
        self._move_window_to(self.root, x, y)
        try:
            self.root.attributes("-alpha", 1.0)
        except (tk.TclError, RuntimeError):
            pass

    def _center_dialog_on_root(self, dialog):
        dialog.update_idletasks()
        dialog_width = dialog.winfo_width()
        dialog_height = dialog.winfo_height()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog_width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog_height) // 2

        monitor_x, monitor_y, monitor_width, monitor_height = self._current_monitor_geometry()
        max_x = monitor_x + monitor_width - dialog_width
        max_y = monitor_y + monitor_height - dialog_height
        if max_x >= monitor_x:
            x = min(max(x, monitor_x), max_x)
        if max_y >= monitor_y:
            y = min(max(y, monitor_y), max_y)

        self._move_window_to(dialog, x, y)
        dialog.lift(self.root)

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
        self.header_frame = tk.Frame(self.root, bg=self.gbg)
        self.header_frame.grid(column=0, row=0, sticky="ew", padx=20, pady=(18, 4))
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.title_label = tk.Label(
            self.header_frame,
            text=f"AstroClocks v{APP_VERSION}",
            foreground=self.fg,
            background=self.gbg,
            font=Font(family="Segoe UI", size=self.header_title_font_size, weight="bold"),
            anchor="w",
        )
        self.title_label.grid(column=0, row=0, sticky="w")

        self.subtitle_label = tk.Label(
            self.header_frame,
            text=self._tr("app.subtitle"),
            foreground=self.muted,
            background=self.gbg,
            font=Font(family="Segoe UI", size=11),
            anchor="w",
        )
        self.subtitle_label.grid(column=0, row=1, sticky="w", pady=(0, 4))

        header_actions = tk.Frame(self.header_frame, bg=self.gbg)
        header_actions.grid(column=1, row=0, rowspan=2, sticky="e")

        self.connectivity_label = tk.Label(
            header_actions,
            text=self._tr("network.checking"),
            foreground=self.muted,
            background=self.gbg,
            font=Font(family="Segoe UI", size=10, weight="bold"),
            anchor="e",
        )
        self.connectivity_label.grid(column=0, row=0, padx=(0, 14), sticky="e")

        self.header_settings_button = tk.Button(
            header_actions,
            text=self._tr("button.settings"),
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
        self.header_settings_button.grid(column=1, row=0, padx=(0, 8), sticky="e")

        self.about_button = tk.Button(
            header_actions,
            text=self._tr("button.about"),
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
            command=self.open_about_dialog,
        )
        self.about_button.grid(column=2, row=0, padx=(0, 8), sticky="e")

        self.fullscreen_button = tk.Button(
            header_actions,
            text=self._tr("button.fullscreen"),
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
        self.fullscreen_button.grid(column=3, row=0, padx=(0, 8), sticky="e")

        self.quit_button = tk.Button(
            header_actions,
            text=self._tr("button.quit"),
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
            command=self.root.destroy,
        )
        self.quit_button.grid(column=4, row=0, sticky="e")

    def open_about_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(self._tr("about.title"))
        apply_app_icon(dialog)
        dialog.configure(bg=self.gbg)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()

        body = tk.Frame(
            dialog,
            bg=self.card_bg,
            padx=24,
            pady=20,
            highlightbackground=self.card_edge,
            highlightthickness=1,
            bd=0,
        )
        body.grid(column=0, row=0, padx=12, pady=12, sticky="nsew")
        body.grid_columnconfigure(1, weight=1)

        tk.Label(
            body,
            text="AstroClocks",
            bg=self.card_bg,
            fg=self.fg,
            font=Font(family="Segoe UI", size=20, weight="bold"),
        ).grid(column=0, row=0, columnspan=2, sticky="w")
        tk.Label(
            body,
            text=f"v{APP_VERSION} | {self._release_date_text()}",
            bg=self.card_bg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10),
        ).grid(column=0, row=1, columnspan=2, sticky="w", pady=(2, 14))

        tk.Frame(body, bg=self.card_edge, height=1).grid(
            column=0, row=2, columnspan=2, sticky="ew", pady=(0, 14)
        )

        label_font = Font(family="Segoe UI", size=10, weight="bold")
        value_font = Font(family="Segoe UI", size=11)
        email_font = Font(family="Segoe UI", size=11, underline=True)

        def add_row(row, label, value, link=False):
            tk.Label(
                body,
                text=f"{label} :",
                bg=self.card_bg,
                fg=self.muted,
                font=label_font,
            ).grid(column=0, row=row, sticky="e", padx=(0, 14), pady=4)
            value_label = tk.Label(
                body,
                text=value,
                bg=self.card_bg,
                fg=self.accent if link else self.text,
                font=email_font if link else value_font,
                cursor="hand2" if link else "",
            )
            value_label.grid(column=1, row=row, sticky="w", pady=4)
            if link:
                value_label.bind(
                    "<Button-1>", lambda _event: webbrowser.open(f"mailto:{APP_EMAIL}")
                )

        add_row(3, self._tr("about.author"), APP_AUTHOR)
        add_row(4, self._tr("about.email"), APP_EMAIL, link=True)
        add_row(5, self._tr("about.phone"), APP_PHONE)

        actions = tk.Frame(body, bg=self.card_bg)
        actions.grid(column=0, row=6, columnspan=2, sticky="e", pady=(18, 0))
        self._build_button(actions, self._tr("button.close"), dialog.destroy).grid(
            column=0, row=0
        )

        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        dialog.bind("<Return>", lambda _event: dialog.destroy())
        self._center_dialog_on_root(dialog)
        dialog.focus_set()

    def _build_labelframe(
        self,
        title_key,
        column,
        row,
        padx=10,
        pady=10,
        relief="raised",
        bd=None,
        rowspan=1,
        title_kwargs=None,
        parent=None,
    ):
        parent = parent or self.main_tab
        title_kwargs = title_kwargs or {}
        title_values = title_kwargs() if callable(title_kwargs) else title_kwargs
        shell = tk.Frame(
            parent,
            background=self.card_bg,
            highlightbackground=self.card_edge,
            highlightcolor=self.accent,
            highlightthickness=2 if bd else 1,
            bd=0,
        )
        shell.grid(column=column, row=row, rowspan=rowspan, padx=padx, pady=pady, sticky="nsew")
        shell.grid_columnconfigure(0, weight=1)
        shell.grid_rowconfigure(1, weight=1)

        title_label = tk.Label(
            shell,
            text=self._tr(title_key, **title_values).upper(),
            foreground=self.muted,
            background=self.card_bg,
            font=Font(family="Segoe UI", size=10, weight="bold"),
            anchor="w",
        )
        title_label.grid(column=0, row=0, padx=14, pady=(9, 3), sticky="ew")
        self.labelframe_title_labels.append((title_label, title_key, title_kwargs))

        body = tk.Frame(shell, background=self.card_bg)
        body.grid(column=0, row=1, padx=10, pady=(0, 8), sticky="nsew")
        return body

    def _build_button(self, parent, text, command):
        return tk.Button(
            parent,
            text=text,
            bg=self.button_bg,
            fg=self.text,
            activebackground=self.accent,
            activeforeground=self.ebg,
            disabledforeground=self.muted,
            font=Font(family="Segoe UI", size=11, weight="bold"),
            relief="flat",
            bd=0,
            padx=12,
            pady=7,
            cursor="hand2",
            command=command,
        )

    def _register_translated_widget(self, widget, key, **kwargs):
        self.translated_widgets.append((widget, key, kwargs))
        widget.config(text=self._tr(key, **kwargs))
        return widget

    def _build_inline_checkbutton(self, parent, variable, text, command=None):
        return tk.Checkbutton(
            parent,
            text=text,
            variable=variable,
            command=command,
            bg=self.card_bg,
            fg=self.text,
            disabledforeground=self.muted,
            activebackground=self.card_bg,
            activeforeground=self.text,
            selectcolor=self.ebg,
            font=Font(family="Segoe UI", size=10),
            anchor="w",
            justify="left",
            relief="flat",
            bd=0,
            cursor="hand2",
        )

    def _schedule_connectivity_check(self, delay_ms=1000):
        self.root.after(delay_ms, self._start_connectivity_check)

    def _start_connectivity_check(self):
        if self.connectivity_check_pending:
            self._schedule_connectivity_check()
            return

        self.connectivity_check_pending = True
        threading.Thread(target=self._run_connectivity_check, daemon=True).start()

    def _run_connectivity_check(self):
        is_online = False
        try:
            with socket.create_connection(("aladin.cds.unistra.fr", 443), timeout=0.8):
                is_online = True
        except OSError:
            is_online = False

        try:
            self.root.after(0, lambda: self._apply_connectivity_result(is_online))
        except (tk.TclError, RuntimeError):
            pass

    def _apply_connectivity_result(self, is_online):
        self.connectivity_check_pending = False
        self.network_online = is_online

        if self.connectivity_label is not None:
            text_key = "network.connected" if is_online else "network.offline"
            self.connectivity_label.config(
                text=self._tr(text_key),
                foreground=self.success if is_online else self.danger,
            )

        self._update_aladin_button_state()
        self._schedule_connectivity_check()

    def _update_aladin_button_state(self):
        if self.aladin_button is None:
            return

        is_offline = self.network_online is False
        self.aladin_button.config(
            state=tk.DISABLED if is_offline else tk.NORMAL,
            cursor="arrow" if is_offline else "hand2",
        )

    def _hour_angle_title_kwargs(self):
        suffix = self._tr("frame.hour_angle_offset_suffix") if self.hour_angle_offset_enabled else ""
        return {"suffix": suffix}

    def _declination_title_kwargs(self):
        suffix = (
            self._tr("frame.declination_offset_suffix")
            if self.declination_offset_enabled
            else ""
        )
        return {"suffix": suffix}

    def _create_frames(self):
        self._create_header()
        self._create_tabs()
        self.lf_long = self._build_labelframe("frame.site", 0, 1)
        self.lf_search = self._build_labelframe("frame.search", 1, 1)
        self.lf_sky = self._build_labelframe("frame.sky", 2, 1, rowspan=5, bd=6)
        self.lf_local = self._build_labelframe(
            "frame.local_time", 0, 2, title_kwargs=self._local_time_title_kwargs
        )
        self.lf_utc = self._build_labelframe("frame.utc", 1, 2)
        self.lf_alpha = self._build_labelframe("frame.alpha", 0, 3)
        self.lf_delta = self._build_labelframe("frame.delta", 1, 3)
        self.lf_gmst = self._build_labelframe("frame.gmst", 0, 4)
        self.lf_lst = self._build_labelframe("frame.lst", 1, 4)
        self.lf_ha = self._build_labelframe(
            "frame.hour_angle",
            0,
            5,
            relief="ridge",
            bd=6,
            title_kwargs=self._hour_angle_title_kwargs,
        )
        self.lf_dec = self._build_labelframe(
            "frame.declination",
            1,
            5,
            relief="ridge",
            bd=6,
            title_kwargs=self._declination_title_kwargs,
        )
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

    def _create_tabs(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(column=0, row=1, sticky="nsew", padx=10, pady=(0, 10))

        self.main_tab = tk.Frame(self.notebook, bg=self.gbg)
        self.visibility_tab = tk.Frame(self.notebook, bg=self.gbg)
        self.double_star_tab = tk.Frame(self.notebook, bg=self.gbg)

        self.notebook.add(self.main_tab, text=self._tr("tab.main"))
        self.notebook.add(self.visibility_tab, text=self._tr("tab.visibility"))
        self.notebook.add(self.double_star_tab, text=self._tr("tab.double_stars"))
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        for column in range(3):
            self.main_tab.grid_columnconfigure(column, weight=1, uniform="main")
        for row in range(1, 6):
            self.main_tab.grid_rowconfigure(row, weight=1)

        self.visibility_tab.grid_columnconfigure(0, weight=1)
        self.visibility_tab.grid_rowconfigure(0, weight=1)
        self.double_star_tab.grid_columnconfigure(0, weight=0)
        self.double_star_tab.grid_columnconfigure(1, weight=1)
        self.double_star_tab.grid_rowconfigure(0, weight=1)

    def _on_tab_changed(self, _event=None):
        if self.notebook is None or self.double_star_tree is None:
            return
        if self.notebook.select() == str(self.double_star_tab):
            self.root.after_idle(self._update_double_tree_separators)

    def _create_site_widgets(self):
        self.site_info_font = Font(family="Segoe UI", size=10)
        self.site_info_name_font = Font(family="Segoe UI", size=10, weight="bold")
        self.site_info_text = tk.Text(
            self.lf_long,
            height=6,
            bg=self.ebg,
            fg=self.fg,
            font=self.site_info_font,
            relief="flat",
            bd=0,
            padx=8,
            pady=5,
            wrap="word",
            cursor="arrow",
            takefocus=0,
        )
        self.site_info_text.tag_configure(
            "site-name",
            foreground=self.text,
            font=self.site_info_name_font,
        )
        self.site_info_text.config(state=tk.DISABLED)
        self.site_info_text.grid(column=0, row=0, columnspan=2, padx=8, pady=(4, 6), sticky="nsew")
        self.site_info_text.bind("<Configure>", self._resize_site_info_text)
        self.lf_long.grid_columnconfigure(0, weight=1)
        self.lf_long.grid_columnconfigure(1, weight=1)
        self.lf_long.grid_rowconfigure(0, weight=1)

    def _resize_site_info_text(self, _event=None):
        if self.site_info_text is None or self.site_info_font is None:
            return

        lines = self.site_info_lines or ("Observing Site",) * 6
        max_line_length = max(32, *(len(str(line)) for line in lines))
        available_width = max(1, self.site_info_text.winfo_width() - 24)
        available_height = max(1, self.site_info_text.winfo_height() - 14)
        width_limited_size = available_width / (max_line_length * 0.55)
        height_limited_size = available_height / (max(1, len(lines)) * 1.55)
        target_size = int(max(9, min(17, width_limited_size, height_limited_size)))

        if self.site_info_font.cget("size") == target_size:
            return
        self.site_info_font.configure(size=target_size)
        if self.site_info_name_font is not None:
            self.site_info_name_font.configure(size=target_size)

    def _object_type_display(self, object_type_code):
        return self._tr(f"object_type.{object_type_code}")

    def _selected_object_type_code(self):
        selected_label = self.combo_box.get()
        return self.object_type_label_to_code.get(selected_label, selected_label)

    def _set_object_type_values(self, selected_code=None):
        if selected_code is None and hasattr(self, "combo_box"):
            selected_code = self._selected_object_type_code()
        if selected_code not in OBJECT_TYPE_CODES:
            selected_code = "Star, Deep Sky Object"

        values = [self._object_type_display(code) for code in OBJECT_TYPE_CODES]
        self.object_type_label_to_code = dict(zip(values, OBJECT_TYPE_CODES))
        self.combo_box["values"] = values
        self.combo_box.set(self._object_type_display(selected_code))

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

        self.search_button = self._build_button(
            self.lf_search, self._tr("button.search"), self.search_coordinates
        )
        self.search_button.grid(column=1, row=1, padx=8, pady=8, sticky="ew")

        self.aladin_button = self._build_button(
            self.lf_search,
            self._tr("button.aladin", value=self.aladin_fov_deg),
            self.show_sky_view,
        )
        self.aladin_button.grid(column=1, row=0, padx=8, pady=8, sticky="ew")
        self._update_aladin_button_state()

        self.combo_box = ttk.Combobox(
            self.lf_search,
            font=Font(family="Segoe UI", size=13),
        )
        self.combo_box.grid(column=0, row=1, padx=8, pady=8, sticky="ew")
        self.combo_box["state"] = "readonly"
        self._set_object_type_values("Star, Deep Sky Object")

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
            font=Font(family="Consolas", size=self.clock_font_size, weight="bold"),
            background=self.ebg,
            foreground=self.fg,
            anchor="center",
            padx=10,
            pady=6,
        )
        label.pack(fill="both", expand=True, padx=8, pady=6)
        self.clock_labels.append(label)
        return label

    def _create_coordinate_widgets(self):
        self.alpha_hh = tk.StringVar(value=0)
        self.alpha_mm = tk.StringVar(value=0)
        self.alpha_ss = tk.StringVar(value=0)
        self.delta_dd = tk.StringVar(value=0)
        self.delta_mm = tk.StringVar(value=0)
        self.delta_ss = tk.StringVar(value=0)
        self.coordinate_spinboxes = []
        self.coordinate_unit_labels = []

        self._build_spinbox(self.lf_alpha, self.alpha_hh, 0, 23, 0)
        self._build_coordinate_unit_label(self.lf_alpha, "h", 1)
        self._build_spinbox(self.lf_alpha, self.alpha_mm, 0, 59, 2)
        self._build_coordinate_unit_label(self.lf_alpha, "m", 3)
        self._build_spinbox(self.lf_alpha, self.alpha_ss, 0, 59, 4)
        self._build_coordinate_unit_label(self.lf_alpha, "s", 5)

        self._build_spinbox(self.lf_delta, self.delta_dd, -90, 90, 0)
        self._build_coordinate_unit_label(self.lf_delta, "d", 1)
        self._build_spinbox(self.lf_delta, self.delta_mm, 0, 59, 2)
        self._build_coordinate_unit_label(self.lf_delta, "m", 3)
        self._build_spinbox(self.lf_delta, self.delta_ss, 0, 59, 4)
        self._build_coordinate_unit_label(self.lf_delta, "s", 5)

        self.alpha_set_button = self._build_button(
            self.lf_alpha, self._tr("button.set"), self._activate_target_from_controls
        )
        self.alpha_set_button.grid(column=6, row=0, padx=(8, 8), pady=8, sticky="ew")

        self.delta_set_button = self._build_button(
            self.lf_delta, self._tr("button.set"), self._activate_target_from_controls
        )
        self.delta_set_button.grid(column=6, row=0, padx=(8, 8), pady=8, sticky="ew")

        for frame in (self.lf_alpha, self.lf_delta):
            for column in (0, 2, 4):
                frame.grid_columnconfigure(column, weight=1)
            for column in (1, 3, 5, 6):
                frame.grid_columnconfigure(column, weight=0)

    def _build_spinbox(self, parent, variable, minimum, maximum, column, row=0):
        spinbox = tk.Spinbox(
            parent,
            from_=minimum,
            to=maximum,
            textvariable=variable,
            wrap=True,
            font=Font(family="Consolas", size=self.coord_font_size, weight="bold"),
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
            command=self._activate_target_from_controls,
        )
        spinbox.grid(
            column=column,
            row=row,
            ipadx=1,
            ipady=5,
            padx=(8, 3),
            pady=7,
            sticky="ew",
        )
        self.coordinate_spinboxes.append(spinbox)
        return spinbox

    def _build_coordinate_unit_label(self, parent, text, column, row=0):
        label = tk.Label(
            parent,
            text=text,
            bg=self.card_bg,
            fg=self.fg,
            font=Font(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
        )
        label.grid(column=column, row=row, padx=(0, 7), pady=7, sticky="w")
        self.coordinate_unit_labels.append(label)
        return label

    def _update_dynamic_fonts(self, _event=None):
        try:
            self._update_header_layout()
            self._update_coordinate_font_size()
            self._update_clock_font_size()
            self._update_angle_font_size()
        except tk.TclError:
            return

    def _update_header_layout(self):
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        if width <= 1 or height <= 1:
            return

        if width < 1230 or height < 820:
            title_size = 16
            show_subtitle = False
            header_padding = (12, 2)
        elif width < 1360 or height < 900:
            title_size = 18
            show_subtitle = False
            header_padding = (14, 3)
        else:
            title_size = 21
            show_subtitle = True
            header_padding = (18, 4)

        if title_size != self.header_title_font_size:
            self.header_title_font_size = title_size
            self.title_label.config(font=Font(family="Segoe UI", size=title_size, weight="bold"))

        if show_subtitle:
            self.subtitle_label.grid(column=0, row=1, sticky="w", pady=(0, 4))
        else:
            self.subtitle_label.grid_remove()

        self.header_frame.grid_configure(pady=header_padding)

    def _update_coordinate_font_size(self):
        available_width = min(self.lf_alpha.winfo_width(), self.lf_delta.winfo_width())
        if available_width <= 1:
            return

        if available_width < 340:
            size = 12
        elif available_width < 380:
            size = 14
        elif available_width < 430:
            size = 16
        elif available_width < 500:
            size = 20
        elif available_width < 620:
            size = 22
        else:
            size = 24

        if size != self.coord_font_size:
            self.coord_font_size = size
            spinbox_font = Font(family="Consolas", size=size, weight="bold")
            unit_font = Font(
                family="Segoe UI",
                size=max(10, min(14, round(size * 0.62))),
                weight="bold",
            )
            for spinbox in getattr(self, "coordinate_spinboxes", ()):
                spinbox.config(font=spinbox_font)
            for label in getattr(self, "coordinate_unit_labels", ()):
                label.config(font=unit_font)

    def _update_clock_font_size(self):
        if not self.clock_labels:
            return

        available_width = min(label.master.winfo_width() for label in self.clock_labels)
        available_height = min(label.master.winfo_height() for label in self.clock_labels)
        if available_width <= 1 or available_height <= 1:
            return

        size_by_height = round((available_height - 18) * 0.58)
        size_by_width = round((available_width - 20) / 5.2)
        size = max(18, min(40, size_by_height, size_by_width))
        if size == self.clock_font_size:
            return

        self.clock_font_size = size
        clock_font = Font(family="Consolas", size=size, weight="bold")
        for label in self.clock_labels:
            label.config(font=clock_font)

    def _update_angle_font_size(self):
        if not self.angle_labels:
            return

        available_width = min(label.master.winfo_width() for label in self.angle_labels)
        available_height = min(label.master.winfo_height() for label in self.angle_labels)
        if available_width <= 1 or available_height <= 1:
            return

        size_by_height = round((available_height - 14) * 0.58)
        size_by_width = round((available_width - 18) / 8.8)
        preferred_min = min(28, self.clock_font_size + 4)
        size = max(preferred_min, min(44, size_by_height, size_by_width))
        if size == self.angle_font_size:
            return

        self.angle_font_size = size
        angle_font = Font(family="Consolas", size=size, weight="bold")
        for label in self.angle_labels:
            label.config(font=angle_font)

    def _create_hour_angle_widgets(self):
        self.lbl_hour_angle = tk.Label(
            self.lf_ha,
            text="06h 00m 00s",
            bg=self.ebg,
            fg=self.fg,
            font=Font(family="Consolas", size=self.angle_font_size, weight="bold"),
            padx=10,
            pady=5,
        )
        self.lbl_hour_angle.grid(column=0, row=0, ipadx=1, ipady=1, padx=8, pady=6, sticky="nsew")
        self.angle_labels.append(self.lbl_hour_angle)

        self.lbl_dec_angle = tk.Label(
            self.lf_dec,
            text=compute_declination_display(
                0,
                0,
                0,
                apply_offset=self.declination_offset_enabled,
            ),
            bg=self.ebg,
            fg=self.fg,
            font=Font(family="Consolas", size=self.angle_font_size, weight="bold"),
            padx=10,
            pady=5,
        )
        self.lbl_dec_angle.grid(column=0, row=0, ipadx=1, ipady=1, padx=8, pady=6, sticky="nsew")
        self.angle_labels.append(self.lbl_dec_angle)

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

        self.sky_status = tk.Text(
            self.lf_sky,
            bg=self.card_bg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10),
            height=3,
            relief="flat",
            bd=0,
            padx=6,
            pady=4,
            wrap="word",
            cursor="arrow",
            takefocus=0,
        )
        self.sky_status.tag_configure("danger", foreground=self.danger)
        self.sky_status.config(state=tk.DISABLED)
        self.sky_status.grid(column=0, row=1, padx=8, pady=(2, 8), sticky="ew")

    def _create_visibility_widgets(self):
        self.lf_visibility = self._build_labelframe(
            "frame.visibility",
            0,
            0,
            parent=self.visibility_tab,
            padx=12,
            pady=12,
        )
        self.lf_visibility.grid_columnconfigure(0, weight=1)
        self.lf_visibility.grid_rowconfigure(0, weight=1)
        self.lf_visibility.grid_rowconfigure(1, weight=0)

        self.visibility_canvas = tk.Canvas(
            self.lf_visibility,
            bg=self.ebg,
            highlightthickness=0,
            bd=0,
        )
        self.visibility_canvas.grid(column=0, row=0, padx=8, pady=8, sticky="nsew")
        self.visibility_canvas.bind("<Configure>", lambda _event: self._update_visibility_chart())
        self.visibility_canvas.bind("<Motion>", self._on_visibility_motion)
        self.visibility_canvas.bind("<Leave>", self._clear_visibility_hover)

        self.visibility_status = tk.Text(
            self.lf_visibility,
            bg=self.card_bg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10),
            height=3,
            relief="flat",
            bd=0,
            padx=8,
            pady=6,
            wrap="word",
            cursor="arrow",
            takefocus=0,
        )
        self.visibility_status.config(state=tk.DISABLED)
        self.visibility_status.grid(column=0, row=1, padx=8, pady=(2, 8), sticky="ew")

    def _create_double_star_widgets(self):
        controls = tk.Frame(self.double_star_tab, bg=self.card_bg)
        controls.grid(column=0, row=0, padx=(12, 8), pady=12, sticky="ns")
        controls.grid_columnconfigure(0, weight=1)

        self._register_translated_widget(
            tk.Label(
                controls,
                bg=self.card_bg,
                fg=self.muted,
                font=Font(family="Segoe UI", size=10, weight="bold"),
                anchor="w",
            ),
            "double.filters",
        ).grid(column=0, row=0, pady=(0, 10), sticky="ew")

        self.double_mag_primary_var = tk.StringVar(
            value=self._format_double_filter_number(self.settings.double_max_primary_magnitude)
        )
        self.double_mag_secondary_var = tk.StringVar(
            value=self._format_double_filter_number(self.settings.double_max_secondary_magnitude)
        )
        self.double_min_sep_var = tk.StringVar(
            value=self._format_double_filter_number(self.settings.double_min_separation)
        )
        self.double_max_sep_var = tk.StringVar(
            value=self._format_double_filter_number(self.settings.double_max_separation)
        )
        self.double_min_altitude_var = tk.StringVar(
            value=self._format_double_filter_number(self.settings.double_min_max_altitude)
        )
        self.double_visible_night_var = tk.BooleanVar(value=self.settings.double_visible_night)
        self.double_include_physical_var = tk.BooleanVar(
            value=self.settings.double_include_physical
        )
        self.double_include_noted_var = tk.BooleanVar(value=self.settings.double_include_noted)
        self.double_include_apparent_var = tk.BooleanVar(
            value=self.settings.double_include_apparent
        )
        self.double_include_uncertain_var = tk.BooleanVar(
            value=self.settings.double_include_uncertain
        )
        self.double_exclude_polar_circle_var = tk.BooleanVar(
            value=self.settings.double_exclude_polar_circle
        )
        self.double_online_var = tk.BooleanVar(value=self.settings.double_use_online)

        def add_filter(row, key, variable):
            label = tk.Label(
                controls,
                bg=self.card_bg,
                fg=self.text,
                font=Font(family="Segoe UI", size=10),
                anchor="w",
            )
            self._register_translated_widget(label, key)
            label.grid(column=0, row=row, sticky="ew", pady=(6, 2))
            entry = tk.Entry(
                controls,
                textvariable=variable,
                bg=self.ebg,
                fg=self.text,
                insertbackground=self.fg,
                font=Font(family="Segoe UI", size=11),
                relief="flat",
                highlightbackground=self.card_edge,
                highlightcolor=self.accent,
                highlightthickness=1,
                width=16,
            )
            entry.grid(column=0, row=row + 1, sticky="ew")
            entry.bind("<Return>", lambda _event: self.search_double_stars())
            entry.bind("<FocusOut>", self._save_double_filters_if_valid)

        add_filter(1, "double.max_primary", self.double_mag_primary_var)
        add_filter(3, "double.max_secondary", self.double_mag_secondary_var)
        add_filter(5, "double.min_sep", self.double_min_sep_var)
        add_filter(7, "double.max_sep", self.double_max_sep_var)
        add_filter(9, "double.min_max_altitude", self.double_min_altitude_var)

        self._register_translated_widget(
            self._build_inline_checkbutton(
                controls,
                self.double_visible_night_var,
                self._tr("double.visible_night"),
                self.search_double_stars,
            ),
            "double.visible_night",
        ).grid(column=0, row=11, pady=(12, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                controls,
                self.double_include_physical_var,
                self._tr("double.include_physical"),
                self.search_double_stars,
            ),
            "double.include_physical",
        ).grid(column=0, row=12, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                controls,
                self.double_include_noted_var,
                self._tr("double.include_noted"),
                self.search_double_stars,
            ),
            "double.include_noted",
        ).grid(column=0, row=13, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                controls,
                self.double_include_apparent_var,
                self._tr("double.include_apparent"),
                self.search_double_stars,
            ),
            "double.include_apparent",
        ).grid(column=0, row=14, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                controls,
                self.double_include_uncertain_var,
                self._tr("double.include_uncertain"),
                self.search_double_stars,
            ),
            "double.include_uncertain",
        ).grid(column=0, row=15, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                controls,
                self.double_exclude_polar_circle_var,
                self._tr("double.exclude_polar_circle"),
                self.search_double_stars,
            ),
            "double.exclude_polar_circle",
        ).grid(column=0, row=16, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                controls,
                self.double_online_var,
                self._tr("double.use_online"),
                self.search_double_stars,
            ),
            "double.use_online",
        ).grid(column=0, row=17, pady=(4, 0), sticky="ew")

        self.double_search_button = self._build_button(
            controls,
            self._tr("button.search"),
            self.search_double_stars,
        )
        self.double_search_button.grid(column=0, row=18, pady=(14, 8), sticky="ew")

        self.double_set_button = self._build_button(
            controls,
            self._tr("double.set_target"),
            self.set_selected_double_star_target,
        )
        self.double_set_button.grid(column=0, row=19, pady=(0, 12), sticky="ew")

        self.double_reset_button = self._build_button(
            controls,
            self._tr("double.reset_filters"),
            self.reset_double_star_filters,
        )
        self.double_reset_button.grid(column=0, row=20, pady=(0, 12), sticky="ew")

        self.double_status_label = tk.Label(
            controls,
            bg=self.card_bg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=9),
            justify="left",
            wraplength=220,
            anchor="nw",
        )
        self.double_status_label.grid(column=0, row=21, sticky="ew")

        results_frame = self._build_labelframe(
            "frame.double_stars",
            1,
            0,
            parent=self.double_star_tab,
            padx=(8, 12),
            pady=12,
        )
        results_frame.grid_columnconfigure(0, weight=1)
        results_frame.grid_rowconfigure(0, weight=1)

        columns = (
            "name",
            "designation",
            "nature",
            "magnitudes",
            "separation",
            "pa",
            "orb6_separation",
            "orb6_pa",
            "max_altitude",
            "last_observation_year",
            "observation_count",
            "wds_note",
            "orbit",
        )
        self.double_star_tree = ttk.Treeview(
            results_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.double_star_tree.grid(column=0, row=0, sticky="nsew", padx=(8, 0), pady=8)
        scrollbar = ttk.Scrollbar(
            results_frame,
            orient="vertical",
            command=self.double_star_tree.yview,
            style="Dark.Vertical.TScrollbar",
        )
        scrollbar.grid(column=1, row=0, sticky="ns", padx=(0, 8), pady=8)
        horizontal_scrollbar = ttk.Scrollbar(
            results_frame,
            orient="horizontal",
            command=self._double_tree_xview,
            style="Dark.Horizontal.TScrollbar",
        )
        horizontal_scrollbar.grid(column=0, row=1, sticky="ew", padx=(8, 0), pady=(0, 8))
        self.double_star_tree.configure(
            yscrollcommand=scrollbar.set,
            xscrollcommand=lambda first, last: self._on_double_tree_xscroll(
                horizontal_scrollbar,
                first,
                last,
            ),
        )
        self.double_star_tree.bind("<Double-1>", self._on_double_tree_double_click)
        self.double_star_tree.bind(
            "<Configure>",
            lambda _event: self.root.after_idle(self._update_double_tree_separators),
        )
        self.double_star_tree.bind("<ButtonRelease-1>", self._on_double_tree_click)
        self.double_star_tree.bind("<Motion>", self._on_double_tree_motion)
        self.double_star_tree.bind("<Leave>", self._on_double_tree_leave)
        self.double_star_tree.tag_configure("odd", background="#0e151b")
        self.double_star_tree.tag_configure("even", background=self.ebg)

        column_widths = {
            "name": 155,
            "designation": 320,
            "nature": 110,
            "magnitudes": 100,
            "separation": 74,
            "pa": 64,
            "orb6_separation": 78,
            "orb6_pa": 68,
            "max_altitude": 90,
            "last_observation_year": 75,
            "observation_count": 75,
            "wds_note": 110,
            "orbit": 95,
        }
        column_min_widths = {
            "name": 130,
            "designation": 260,
            "nature": 95,
            "magnitudes": 90,
            "separation": 68,
            "pa": 58,
            "orb6_separation": 72,
            "orb6_pa": 62,
            "max_altitude": 85,
            "last_observation_year": 65,
            "observation_count": 65,
            "wds_note": 95,
            "orbit": 85,
        }
        for column, width in column_widths.items():
            anchor = "center" if column in {"orbit", "wds_note"} else "w"
            self.double_star_tree.column(
                column,
                width=width,
                minwidth=column_min_widths[column],
                anchor=anchor,
            )

        self._refresh_double_star_headings()
        self._update_double_tree_separators()
        self.search_double_stars(allow_online=False)

    def _parse_clock_hours(self, value):
        hours, minutes, seconds = value.split(":")
        return float(hours) + (float(minutes) / 60) + (float(seconds) / 3600)

    def _format_offset_hours(self, offset_hours):
        total_minutes = int(round(offset_hours * 60))
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"+{hours:02d}h{minutes:02d}"

    def _configured_timezone_offset(self, utc_time):
        tzinfo = resolve_timezone(self.timezone_name)
        if tzinfo is None:
            return None

        local_time = utc_time.astimezone(tzinfo)
        offset = local_time.utcoffset() or datetime.timedelta()
        dst = local_time.dst() or datetime.timedelta()
        offset -= dst
        if self.daylight_saving_enabled and bool(self.timezone_name):
            offset += datetime.timedelta(hours=1)
        return offset

    def _local_datetime_from_utc(self, utc_time):
        utc_time = utc_time.astimezone(datetime.timezone.utc)
        try:
            offset = self._configured_timezone_offset(utc_time)
        except ValueError:
            offset = None

        if offset is None:
            return utc_time.astimezone()
        return (utc_time + offset).replace(tzinfo=datetime.timezone(offset))

    def _visibility_window_context(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        local_now = self._local_datetime_from_utc(now_utc)
        local_noon = local_now.replace(hour=12, minute=0, second=0, microsecond=0)
        if local_now < local_noon:
            local_noon -= datetime.timedelta(days=1)
        start_utc = local_noon.astimezone(datetime.timezone.utc)
        current_offset_hours = (now_utc - start_utc).total_seconds() / 3600
        return start_utc, max(0, min(24, current_offset_hours)), local_noon.date()

    def _visibility_time_label(self, start_utc, offset_hours):
        state = compute_clock_state(
            self.longitude,
            self.alpha_hh.get(),
            self.alpha_mm.get(),
            self.alpha_ss.get(),
            hour_angle_offset_hours=6 if self.hour_angle_offset_enabled else 0,
            timezone_name=self.timezone_name,
            daylight_saving_enabled=self.daylight_saving_enabled,
            now_utc=start_utc + datetime.timedelta(hours=offset_hours),
        )
        return state["local"][:5]

    def _set_visibility_status(self, text):
        if self.visibility_status is None:
            return

        self.visibility_status.config(state=tk.NORMAL)
        self.visibility_status.delete("1.0", tk.END)
        self.visibility_status.insert("1.0", text)
        self.visibility_status.config(state=tk.DISABLED)

    def _visibility_state_at_time(self, sample_time):
        state = compute_clock_state(
            self.longitude,
            self.alpha_hh.get(),
            self.alpha_mm.get(),
            self.alpha_ss.get(),
            hour_angle_offset_hours=6 if self.hour_angle_offset_enabled else 0,
            timezone_name=self.timezone_name,
            daylight_saving_enabled=self.daylight_saving_enabled,
            now_utc=sample_time,
        )
        return state, self._parse_clock_hours(state["lst"])

    def _visibility_sample_from_position(self, position, sample_time, offset_hours):
        _state, lst_hours = self._visibility_state_at_time(sample_time)
        hour_angle = self._normalize_hour_angle(lst_hours - position["ra_hours"])
        return {
            "offset_hours": offset_hours,
            "altitude": position["altitude"],
            "azimuth": position["azimuth"],
            "hour_angle": hour_angle,
            "utc": sample_time,
            "ra_hours": position["ra_hours"],
            "declination": position["declination"],
        }

    def _visibility_sample_at_offset(self, ra_hours, declination, start_utc, offset_hours):
        sample_time = start_utc + datetime.timedelta(hours=offset_hours)
        if self.target_solar_system_name:
            positions = compute_solar_system_body_positions(
                self.target_solar_system_name,
                self.latitude,
                self.longitude,
                [sample_time],
            )
            if positions:
                return self._visibility_sample_from_position(
                    positions[0],
                    sample_time,
                    offset_hours,
                )

        _state, lst_hours = self._visibility_state_at_time(sample_time)
        altitude, azimuth, hour_angle = self._equatorial_to_horizontal(
            ra_hours,
            declination,
            lst_hours,
        )
        return {
            "offset_hours": offset_hours,
            "altitude": altitude,
            "azimuth": azimuth,
            "hour_angle": hour_angle,
            "utc": sample_time,
        }

    def _visibility_samples(self, ra_hours, declination, start_utc):
        offsets = [step / 2 for step in range(49)]
        if self.target_solar_system_name:
            utc_datetimes = [
                start_utc + datetime.timedelta(hours=offset)
                for offset in offsets
            ]
            positions = compute_solar_system_body_positions(
                self.target_solar_system_name,
                self.latitude,
                self.longitude,
                utc_datetimes,
            )
            if positions:
                return [
                    self._visibility_sample_from_position(position, sample_time, offset)
                    for position, sample_time, offset in zip(positions, utc_datetimes, offsets)
                ]

        return [
            self._visibility_sample_at_offset(ra_hours, declination, start_utc, offset)
            for offset in offsets
        ]

    def _refine_visibility_extreme(self, ra_hours, declination, samples, find_max=True):
        if not samples:
            return None

        selector = max if find_max else min
        best_index = selector(
            range(len(samples)),
            key=lambda index: samples[index]["altitude"],
        )
        left_index = max(0, best_index - 1)
        right_index = min(len(samples) - 1, best_index + 1)
        left = samples[left_index]["offset_hours"]
        right = samples[right_index]["offset_hours"]
        if left == right:
            return samples[best_index]

        start_utc = samples[0]["utc"]

        def sample_at(offset_hours):
            return self._visibility_sample_at_offset(
                ra_hours,
                declination,
                start_utc,
                max(0, min(24, offset_hours)),
            )

        low = left
        high = right
        for _iteration in range(32):
            first = low + (high - low) / 3
            second = high - (high - low) / 3
            first_altitude = sample_at(first)["altitude"]
            second_altitude = sample_at(second)["altitude"]
            if find_max:
                if first_altitude < second_altitude:
                    low = first
                else:
                    high = second
            else:
                if first_altitude > second_altitude:
                    low = first
                else:
                    high = second

        candidates = [
            samples[best_index],
            sample_at(left),
            sample_at(right),
            sample_at((low + high) / 2),
        ]
        return selector(candidates, key=lambda sample: sample["altitude"])

    def _visibility_samples_with_extrema(self, samples, *extrema):
        by_offset = {round(sample["offset_hours"], 6): sample for sample in samples}
        for sample in extrema:
            if sample is not None:
                by_offset[round(sample["offset_hours"], 6)] = sample
        return sorted(by_offset.values(), key=lambda sample: sample["offset_hours"])

    def _visibility_sun_samples(self, start_utc):
        offsets = [step / 4 for step in range(97)]
        utc_datetimes = [start_utc + datetime.timedelta(hours=offset) for offset in offsets]
        altitudes = compute_sun_altitudes(self.latitude, self.longitude, utc_datetimes)
        return [
            {"offset_hours": offset, "altitude": altitude}
            for offset, altitude in zip(offsets, altitudes)
        ]

    def _twilight_phase_for_sun_altitude(self, altitude):
        if altitude >= 0:
            return "day"
        if altitude >= -6:
            return "civil"
        if altitude >= -12:
            return "nautical"
        if altitude >= -18:
            return "astronomical"
        return "night"

    def _draw_visibility_twilight_zones(
        self,
        canvas,
        start_utc,
        plot_left,
        plot_right,
        plot_top,
        plot_bottom,
        x_from_offset,
    ):
        sun_samples = self._visibility_sun_samples(start_utc)
        events = []

        for first, second in zip(sun_samples, sun_samples[1:]):
            first_point = (first["offset_hours"], first["altitude"])
            second_point = (second["offset_hours"], second["altitude"])
            breakpoints = [first_point]
            altitude_delta = second_point[1] - first_point[1]

            if altitude_delta:
                low_altitude = min(first_point[1], second_point[1])
                high_altitude = max(first_point[1], second_point[1])
                for threshold in (-18, -12, -6, 0):
                    if low_altitude < threshold < high_altitude:
                        ratio = (threshold - first_point[1]) / altitude_delta
                        offset = first_point[0] + ratio * (second_point[0] - first_point[0])
                        breakpoints.append((offset, threshold))
                        rising = second_point[1] > first_point[1]
                        if threshold == 0:
                            events.append(
                                (
                                    offset,
                                    "visibility.sunrise" if rising else "visibility.sunset",
                                    self.fg,
                                    plot_top + 14,
                                )
                            )
                        elif threshold == -18:
                            events.append(
                                (
                                    offset,
                                    "visibility.dawn" if rising else "visibility.twilight",
                                    self.muted,
                                    plot_top + 32,
                                )
                            )

            breakpoints.append(second_point)
            breakpoints.sort(key=lambda point: point[0])

            for start, end in zip(breakpoints, breakpoints[1:]):
                if start == end:
                    continue

                phase = self._twilight_phase_for_sun_altitude((start[1] + end[1]) / 2)
                color = TWILIGHT_PHASE_COLORS.get(phase)
                if color is None:
                    continue

                x1 = max(plot_left, min(plot_right, x_from_offset(start[0])))
                x2 = max(plot_left, min(plot_right, x_from_offset(end[0])))
                if x2 - x1 < 0.5:
                    continue

                canvas.create_rectangle(
                    x1,
                    plot_top,
                    x2,
                    plot_bottom,
                    fill=color,
                    outline="",
                )
                if x2 - x1 >= 120:
                    canvas.create_text(
                        (x1 + x2) / 2,
                        plot_bottom - 14,
                        text=self._tr(f"visibility.phase.{phase}"),
                        fill=self.muted,
                        font=Font(family="Segoe UI", size=8),
                    )

        for offset, key, color, label_y in events:
            x = x_from_offset(offset)
            if x < plot_left or x > plot_right:
                continue

            canvas.create_line(x, plot_top, x, plot_bottom, fill=color, dash=(4, 5))
            label = f"{self._tr(key)} {self._visibility_time_label(start_utc, offset)}"
            anchor = "e" if x > plot_right - 110 else "w"
            label_x = x - 6 if anchor == "e" else x + 6
            canvas.create_text(
                label_x,
                label_y,
                text=label,
                fill=color,
                font=Font(family="Segoe UI", size=8, weight="bold"),
                anchor=anchor,
            )

    def _visibility_color_for_altitude(self, altitude):
        if altitude < 0:
            return None
        if altitude < 10:
            return TARGET_LOW_ALTITUDE_COLOR
        return self.success

    def _draw_visibility_curve(
        self,
        canvas,
        samples,
        x_from_offset,
        y_from_altitude,
        past_until_offset=None,
    ):
        current_color = None
        current_segment = []
        past_color = "#75808a"

        def draw_current_segment():
            if current_color is None or len(current_segment) < 2:
                return
            coordinates = [coordinate for point in current_segment for coordinate in point]
            canvas.create_line(coordinates, fill=current_color, width=3)

        def canvas_point(sample_point):
            offset_hours, altitude = sample_point
            return x_from_offset(offset_hours), y_from_altitude(altitude)

        for first, second in zip(samples, samples[1:]):
            first_point = (first["offset_hours"], first["altitude"])
            second_point = (second["offset_hours"], second["altitude"])
            breakpoints = [first_point]
            altitude_delta = second_point[1] - first_point[1]
            offset_delta = second_point[0] - first_point[0]

            if altitude_delta:
                low_altitude = min(first_point[1], second_point[1])
                high_altitude = max(first_point[1], second_point[1])
                for threshold in (0, 10):
                    if low_altitude < threshold < high_altitude:
                        ratio = (threshold - first_point[1]) / altitude_delta
                        offset = first_point[0] + ratio * (second_point[0] - first_point[0])
                        breakpoints.append((offset, threshold))
            if (
                past_until_offset is not None
                and offset_delta
                and min(first_point[0], second_point[0])
                < past_until_offset
                < max(first_point[0], second_point[0])
            ):
                ratio = (past_until_offset - first_point[0]) / offset_delta
                altitude = first_point[1] + ratio * altitude_delta
                breakpoints.append((past_until_offset, altitude))

            breakpoints.append(second_point)
            breakpoints.sort(key=lambda point: point[0])

            for start, end in zip(breakpoints, breakpoints[1:]):
                if start == end:
                    continue

                color = self._visibility_color_for_altitude((start[1] + end[1]) / 2)
                if (
                    color is not None
                    and past_until_offset is not None
                    and (start[0] + end[0]) / 2 < past_until_offset
                ):
                    color = past_color
                start_canvas = canvas_point(start)
                end_canvas = canvas_point(end)

                if color != current_color:
                    draw_current_segment()
                    current_color = color
                    current_segment = [] if color is None else [start_canvas]
                elif current_segment and current_segment[-1] != start_canvas:
                    current_segment.append(start_canvas)

                if color is not None:
                    current_segment.append(end_canvas)

        draw_current_segment()

    def _visibility_sample_at_canvas_x(self, x, y):
        chart = self.visibility_chart_geometry
        if chart is None:
            return None

        if (
            x < chart["plot_left"]
            or x > chart["plot_right"]
            or y < chart["plot_top"]
            or y > chart["plot_bottom"]
        ):
            return None

        offset_hours = ((x - chart["plot_left"]) / chart["plot_width"]) * 24
        offset_hours = max(0, min(24, offset_hours))
        samples = self.visibility_curve_points
        if len(samples) < 2:
            return None

        for first, second in zip(samples, samples[1:]):
            first_offset = first["offset_hours"]
            second_offset = second["offset_hours"]
            if second_offset == first_offset:
                continue

            low_offset = min(first_offset, second_offset)
            high_offset = max(first_offset, second_offset)
            if offset_hours < low_offset or offset_hours > high_offset:
                continue

            ratio = (offset_hours - first_offset) / (second_offset - first_offset)
            altitude = first["altitude"] + ratio * (second["altitude"] - first["altitude"])
            if altitude < 0:
                return None

            x_curve = chart["plot_left"] + (offset_hours / 24) * chart["plot_width"]
            y_curve = chart["plot_bottom"] - (altitude / 90) * chart["plot_height"]
            return {
                "offset_hours": offset_hours,
                "altitude": altitude,
                "x": x_curve,
                "y": y_curve,
            }

        return None

    def _on_visibility_motion(self, event):
        self.visibility_hover_position = (event.x, event.y)
        self._update_visibility_hover()

    def _clear_visibility_hover(self, _event=None):
        self.visibility_hover_position = None
        if self.visibility_canvas is not None:
            self.visibility_canvas.delete("visibility-hover")

    def _update_visibility_hover(self):
        if self.visibility_canvas is None or self.visibility_hover_position is None:
            return

        self.visibility_canvas.delete("visibility-hover")
        x, y = self.visibility_hover_position
        sample = self._visibility_sample_at_canvas_x(x, y)
        if sample is None:
            return

        chart = self.visibility_chart_geometry
        label = self._tr(
            "visibility.hover",
            time=self._visibility_time_label(chart["start_utc"], sample["offset_hours"]),
            altitude=sample["altitude"],
        )
        label_font = Font(family="Segoe UI", size=9, weight="bold")
        text_width = label_font.measure(label)
        text_height = label_font.metrics("linespace")
        padding_x = 8
        padding_y = 5
        label_width = text_width + padding_x * 2
        label_height = text_height + padding_y * 2

        label_x = sample["x"] + 12
        if label_x + label_width > chart["plot_right"] - 4:
            label_x = sample["x"] - 12 - label_width
        label_x = max(chart["plot_left"] + 4, min(chart["plot_right"] - label_width - 4, label_x))

        label_y = sample["y"] - label_height - 12
        if label_y < chart["plot_top"] + 4:
            label_y = sample["y"] + 12
        label_y = max(chart["plot_top"] + 4, min(chart["plot_bottom"] - label_height - 4, label_y))

        self.visibility_canvas.create_line(
            sample["x"],
            chart["plot_top"],
            sample["x"],
            chart["plot_bottom"],
            fill=self.accent,
            dash=(2, 5),
            tags="visibility-hover",
        )
        self.visibility_canvas.create_line(
            chart["plot_left"],
            sample["y"],
            chart["plot_right"],
            sample["y"],
            fill=self.card_edge,
            dash=(2, 7),
            tags="visibility-hover",
        )
        self.visibility_canvas.create_oval(
            sample["x"] - 6,
            sample["y"] - 6,
            sample["x"] + 6,
            sample["y"] + 6,
            fill=self.accent,
            outline=self.ebg,
            width=2,
            tags="visibility-hover",
        )
        self.visibility_canvas.create_rectangle(
            label_x,
            label_y,
            label_x + label_width,
            label_y + label_height,
            fill=self.card_bg,
            outline=self.accent,
            tags="visibility-hover",
        )
        self.visibility_canvas.create_text(
            label_x + padding_x,
            label_y + padding_y,
            text=label,
            fill=self.text,
            font=label_font,
            anchor="nw",
            tags="visibility-hover",
        )

    def _update_visibility_chart(self, state=None):
        if self.visibility_canvas is None or self.visibility_status is None:
            return

        width = self.visibility_canvas.winfo_width()
        height = self.visibility_canvas.winfo_height()
        if width < 120 or height < 120:
            return

        if not self.target_active:
            cache_key = ("inactive", width, height, self.language)
            if cache_key == self.visibility_cache_key:
                return
            self.visibility_cache_key = cache_key
            self.visibility_curve_points = []
            self.visibility_chart_geometry = None
            self.visibility_canvas.delete("all")
            self.visibility_canvas.create_text(
                width / 2,
                height / 2,
                text=self._tr("visibility.no_target"),
                fill=self.muted,
                font=Font(family="Segoe UI", size=13, weight="bold"),
            )
            self._set_visibility_status(self._tr("visibility.no_target"))
            return

        self._sanitize_coordinate_values()
        ra_hours, declination = self._current_target_coordinates()
        start_utc, current_offset_hours, local_date = self._visibility_window_context()
        minute_bucket = int(time.time() // 60)
        cache_key = (
            width,
            height,
            minute_bucket,
            local_date.isoformat(),
            self.timezone_name,
            self.daylight_saving_enabled,
            self.target_solar_system_name,
            round(ra_hours, 5),
            round(declination, 5),
            round(self.latitude, 5),
            round(self.longitude, 5),
        )
        if cache_key == self.visibility_cache_key:
            return

        self.visibility_cache_key = cache_key
        samples = self._visibility_samples(ra_hours, declination, start_utc)
        max_sample = self._refine_visibility_extreme(ra_hours, declination, samples, find_max=True)
        current_sample = self._visibility_sample_at_offset(
            ra_hours,
            declination,
            start_utc,
            current_offset_hours,
        )
        curve_samples = self._visibility_samples_with_extrema(samples, max_sample, current_sample)
        maximum_time = self._visibility_time_label(start_utc, max_sample["offset_hours"])

        canvas = self.visibility_canvas
        canvas.delete("all")
        margin_left = 58
        margin_right = 24
        margin_top = 24
        margin_bottom = 46
        plot_left = margin_left
        plot_right = width - margin_right
        plot_top = margin_top
        plot_bottom = height - margin_bottom
        plot_width = max(1, plot_right - plot_left)
        plot_height = max(1, plot_bottom - plot_top)
        min_altitude = 0
        max_altitude = 90

        def x_from_offset(offset_hours):
            return plot_left + (offset_hours / 24) * plot_width

        def y_from_altitude(altitude):
            altitude = max(min_altitude, min(max_altitude, altitude))
            return plot_bottom - ((altitude - min_altitude) / (max_altitude - min_altitude)) * plot_height

        self.visibility_curve_points = curve_samples
        self.visibility_chart_geometry = {
            "start_utc": start_utc,
            "current_offset_hours": current_offset_hours,
            "plot_left": plot_left,
            "plot_right": plot_right,
            "plot_top": plot_top,
            "plot_bottom": plot_bottom,
            "plot_width": plot_width,
            "plot_height": plot_height,
        }

        canvas.create_rectangle(
            plot_left,
            plot_top,
            plot_right,
            plot_bottom,
            outline=self.card_edge,
            fill=self.ebg,
        )
        self._draw_visibility_twilight_zones(
            canvas,
            start_utc,
            plot_left,
            plot_right,
            plot_top,
            plot_bottom,
            x_from_offset,
        )
        for altitude in (0, 10, 30, 60, 90):
            y = y_from_altitude(altitude)
            color = self.card_edge if altitude != 0 else self.fg
            dash = () if altitude == 0 else (4, 6)
            canvas.create_line(plot_left, y, plot_right, y, fill=color, dash=dash)
            canvas.create_text(
                plot_left - 10,
                y,
                text=f"{altitude:+d}\N{DEGREE SIGN}",
                fill=self.muted,
                font=Font(family="Segoe UI", size=9),
                anchor="e",
            )

        for offset in range(0, 25, 3):
            x = x_from_offset(offset)
            canvas.create_line(x, plot_top, x, plot_bottom, fill=self.card_edge, dash=(2, 7))
            canvas.create_text(
                x,
                plot_bottom + 18,
                text=self._visibility_time_label(start_utc, offset),
                fill=self.muted,
                font=Font(family="Segoe UI", size=9),
            )

        self._draw_visibility_curve(
            canvas,
            curve_samples,
            x_from_offset,
            y_from_altitude,
            past_until_offset=current_offset_hours,
        )

        current_altitude = current_sample["altitude"]
        current_x = x_from_offset(current_offset_hours)
        current_y = y_from_altitude(current_altitude)
        canvas.create_line(current_x, plot_top, current_x, plot_bottom, fill=self.accent, dash=(5, 5))
        if current_altitude >= 0:
            canvas.create_oval(
                current_x - 5,
                current_y - 5,
                current_x + 5,
                current_y + 5,
                fill=self.accent,
                outline=self.ebg,
            )

        max_x = x_from_offset(max_sample["offset_hours"])
        max_y = y_from_altitude(max_sample["altitude"])
        if max_sample["altitude"] >= 0:
            canvas.create_line(max_x, max_y, max_x, plot_bottom, fill=self.fg, dash=(3, 6))
            canvas.create_oval(max_x - 4, max_y - 4, max_x + 4, max_y + 4, fill=self.fg, outline="")
            max_label_anchor = "e" if max_x > plot_right - 100 else "w"
            max_label_x = max_x - 8 if max_label_anchor == "e" else max_x + 8
            max_label_y = max(plot_top + 14, max_y - 14)
            canvas.create_text(
                max_label_x,
                max_label_y,
                text=self._tr("visibility.max_label", time=maximum_time),
                fill=self.fg,
                font=Font(family="Segoe UI", size=9, weight="bold"),
                anchor=max_label_anchor,
            )
        else:
            canvas.create_text(
                (plot_left + plot_right) / 2,
                (plot_top + plot_bottom) / 2,
                text=self._tr("visibility.below_horizon"),
                fill=self.muted,
                font=Font(family="Segoe UI", size=13, weight="bold"),
            )
        canvas.create_text(
            plot_left,
            plot_top - 6,
            text=self._tr("visibility.title"),
            fill=self.text,
            font=Font(family="Segoe UI", size=11, weight="bold"),
            anchor="w",
        )
        canvas.create_text(
            plot_right,
            plot_top - 6,
            text=self._tr("visibility.axis"),
            fill=self.muted,
            font=Font(family="Segoe UI", size=9),
            anchor="e",
        )

        self._set_visibility_status(
            self._tr(
                "visibility.status",
                current=current_altitude,
                maximum=max_sample["altitude"],
                maximum_time=maximum_time,
            )
        )
        self._update_visibility_hover()

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
        x = center_x - sky_radius * math.sin(azimuth_rad)
        y = center_y - sky_radius * math.cos(azimuth_rad)
        return x, y

    def _project_target(self, center_x, center_y, radius, altitude, azimuth):
        plotted_altitude = max(0, min(90, altitude))
        sky_radius = ((90 - plotted_altitude) / 90) * radius
        azimuth_rad = math.radians(azimuth)
        x = center_x - sky_radius * math.sin(azimuth_rad)
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
        if self.sky_show_altaz_grid:
            for altitude in (15, 30, 45, 60, 75):
                ring_radius = ((90 - altitude) / 90) * radius
                canvas.create_oval(
                    center_x - ring_radius,
                    center_y - ring_radius,
                    center_x + ring_radius,
                    center_y + ring_radius,
                    outline=grid_color,
                    dash=(4, 5),
                )
                if altitude in (30, 60):
                    canvas.create_text(
                        center_x + ring_radius - 6,
                        center_y - 8,
                        text=f"{altitude}\N{DEGREE SIGN}",
                        fill=self.muted,
                        font=Font(family="Segoe UI", size=8),
                        anchor="e",
                    )

        cardinal_labels = (
            (0, self._tr("direction.north_short")),
            (90, self._tr("direction.east_short")),
            (180, self._tr("direction.south_short")),
            (270, self._tr("direction.west_short")),
        )
        for azimuth, label in cardinal_labels:
            azimuth_rad = math.radians(azimuth)
            x = center_x - radius * math.sin(azimuth_rad)
            y = center_y - radius * math.cos(azimuth_rad)
            if self.sky_show_altaz_grid:
                line_options = {"fill": grid_color, "dash": (4, 5)}
                canvas.create_line(center_x, center_y, x, y, **line_options)
            label_x = center_x - (radius + 16) * math.sin(azimuth_rad)
            label_y = center_y - (radius + 16) * math.cos(azimuth_rad)
            canvas.create_text(
                label_x,
                label_y,
                text=label,
                fill=self.muted,
                font=Font(family="Segoe UI", size=10, weight="bold"),
                anchor="center",
            )

    def _draw_equatorial_grid(self, canvas, center_x, center_y, radius, lst_hours):
        grid_color = "#263d4b"

        def draw_segment(points):
            if len(points) < 2:
                return
            flattened = [coordinate for point in points for coordinate in point]
            canvas.create_line(flattened, fill=grid_color, dash=(2, 7), width=1)

        def draw_visible_curve(values, sample_horizontal):
            segment = []
            previous = None

            for value in values:
                altitude, azimuth = sample_horizontal(value)
                point = self._project_horizontal_point(
                    center_x,
                    center_y,
                    radius,
                    altitude,
                    azimuth,
                )

                if previous is not None:
                    previous_value, previous_altitude = previous
                    previous_visible = previous_altitude >= 0
                    current_visible = altitude >= 0
                    if previous_visible != current_visible and altitude != previous_altitude:
                        ratio = previous_altitude / (previous_altitude - altitude)
                        horizon_value = previous_value + (value - previous_value) * ratio
                        _horizon_altitude, horizon_azimuth = sample_horizontal(horizon_value)
                        horizon_point = self._project_horizontal_point(
                            center_x,
                            center_y,
                            radius,
                            0,
                            horizon_azimuth,
                        )
                        if previous_visible:
                            segment.append(horizon_point)
                            draw_segment(segment)
                            segment = []
                        else:
                            segment = [horizon_point]

                if point is not None:
                    segment.append(point)

                previous = (value, altitude)

            draw_segment(segment)

        for declination in (-60, -30, 0, 30, 60):
            def sample_declination_circle(ra_hours, declination=declination):
                altitude, azimuth, _hour_angle = self._equatorial_to_horizontal(
                    ra_hours,
                    declination,
                    lst_hours,
                )
                return altitude, azimuth

            draw_visible_curve(
                [step / 8 for step in range(24 * 8 + 1)],
                sample_declination_circle,
            )

        for ra_hours in range(0, 24, 3):
            def sample_hour_circle(declination, ra_hours=ra_hours):
                altitude, azimuth, _hour_angle = self._equatorial_to_horizontal(
                    ra_hours,
                    declination,
                    lst_hours,
                )
                return altitude, azimuth

            draw_visible_curve(
                range(-90, 91, 2),
                sample_hour_circle,
            )

    def _hex_to_rgb(self, color):
        color = color.lstrip("#")
        return tuple(int(color[index : index + 2], 16) for index in (0, 2, 4))

    def _sky_star_style(self, name, magnitude):
        if name in NAMED_STAR_COLORS:
            fill = NAMED_STAR_COLORS[name]
        elif magnitude < 0.5:
            fill = "#fff4c7"
        elif magnitude < 2.5:
            fill = "#d7eaff"
        else:
            fill = "#9fb2c3"

        magnitude_span = 7.7
        normalized = max(0.0, min(1.0, (6.2 - magnitude) / magnitude_span))
        visual_intensity = normalized**0.48
        sigma = 0.32 + 1.05 * visual_intensity
        peak_alpha = min(255, int((56 + 199 * visual_intensity) * SKY_STAR_BRIGHTNESS_MULTIPLIER))
        canvas_size = max(1.8, sigma * 1.9)
        return fill, self._hex_to_rgb(fill), sigma, peak_alpha, canvas_size

    def _draw_star_label(self, canvas, star):
        canvas.create_text(
            star["x"] + 7,
            star["y"] - 7,
            text=star["name"],
            fill="#b8c8d6",
            font=Font(family="Segoe UI", size=8),
            anchor="w",
        )

    def _draw_star_catalog_canvas(self, canvas, stars):
        self.sky_star_image = None
        for star in stars:
            x = star["x"]
            y = star["y"]
            size = star["size"]
            canvas.create_oval(
                x - size,
                y - size,
                x + size,
                y + size,
                fill=star["fill"],
                outline="",
            )

    def _star_stamp(self, rgb, sigma, peak_alpha, diameter, center_x, center_y):
        q_sigma = round(sigma * 8) / 8
        q_alpha = max(0, min(255, int(round(peak_alpha / 8) * 8)))
        q_center_x = round(center_x * SKY_STAR_SUBPIXEL_STEPS) / SKY_STAR_SUBPIXEL_STEPS
        q_center_y = round(center_y * SKY_STAR_SUBPIXEL_STEPS) / SKY_STAR_SUBPIXEL_STEPS
        key = (rgb, q_sigma, q_alpha, diameter, q_center_x, q_center_y)
        stamp = self.sky_star_stamp_cache.get(key)
        if stamp is not None:
            return stamp

        pixels = bytearray(diameter * diameter * 4)
        sigma_sq = 2 * q_sigma * q_sigma
        red, green, blue = rgb
        offset = 0
        for y in range(diameter):
            dy = y + 0.5 - q_center_y
            for x in range(diameter):
                dx = x + 0.5 - q_center_x
                alpha = int(q_alpha * math.exp(-((dx * dx + dy * dy) / sigma_sq)))
                pixels[offset] = red
                pixels[offset + 1] = green
                pixels[offset + 2] = blue
                pixels[offset + 3] = alpha
                offset += 4

        stamp = Image.frombytes("RGBA", (diameter, diameter), bytes(pixels))
        self.sky_star_stamp_cache[key] = stamp

        if len(self.sky_star_stamp_cache) > 4096:
            self.sky_star_stamp_cache.clear()

        return stamp

    def _draw_star_catalog_antialiased(self, canvas, stars):
        if Image is None or ImageDraw is None or ImageTk is None:
            return False

        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 0 or height <= 0:
            return False

        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        for star in stars:
            diameter = max(5, int(math.ceil(star["sigma"] * 5.2)))
            left = int(math.floor(star["x"] - diameter / 2))
            top = int(math.floor(star["y"] - diameter / 2))
            stamp = self._star_stamp(
                star["rgb"],
                star["sigma"],
                star["peak_alpha"],
                diameter,
                star["x"] - left,
                star["y"] - top,
            )
            paste_x = max(0, left)
            paste_y = max(0, top)
            paste_right = min(width, left + diameter)
            paste_bottom = min(height, top + diameter)
            if paste_x >= paste_right or paste_y >= paste_bottom:
                continue

            if paste_x != left or paste_y != top or paste_right != left + diameter or paste_bottom != top + diameter:
                stamp = stamp.crop(
                    (
                        paste_x - left,
                        paste_y - top,
                        paste_right - left,
                        paste_bottom - top,
                    )
                )
            image.alpha_composite(stamp, (paste_x, paste_y))

        self.sky_star_image = ImageTk.PhotoImage(image)
        canvas.create_image(0, 0, image=self.sky_star_image, anchor="nw")
        return True

    def _draw_star_catalog(self, canvas, center_x, center_y, radius, lst_hours):
        self.sky_star_points = []
        stars_to_draw = []
        for name, ra_hours, declination, magnitude in self.named_stars_jnow:
            if magnitude > self.sky_magnitude_limit:
                break

            altitude, azimuth, hour_angle = self._equatorial_to_horizontal(
                ra_hours,
                declination,
                lst_hours,
            )
            point = self._project_horizontal_point(center_x, center_y, radius, altitude, azimuth)
            if point is None:
                continue

            x, y = point
            fill, rgb, sigma, peak_alpha, canvas_size = self._sky_star_style(name, magnitude)
            star = {
                "name": name,
                "x": x,
                "y": y,
                "ra_hours": ra_hours,
                "declination": declination,
                "altitude": altitude,
                "azimuth": azimuth,
                "hour_angle": hour_angle,
                "magnitude": magnitude,
                "size": canvas_size,
                "fill": fill,
                "rgb": rgb,
                "sigma": sigma,
                "peak_alpha": peak_alpha,
            }
            self.sky_star_points.append(star)
            stars_to_draw.append(star)

        if not self._draw_star_catalog_antialiased(canvas, stars_to_draw):
            self._draw_star_catalog_canvas(canvas, stars_to_draw)

        for star in stars_to_draw:
            magnitude = star["magnitude"]
            if magnitude <= SKY_STAR_LABEL_MAX_MAGNITUDE:
                self._draw_star_label(canvas, star)

    def _solar_system_positions(self):
        cache_key = (
            int(time.time() // SOLAR_SYSTEM_CACHE_SECONDS),
            round(self.latitude, 5),
            round(self.longitude, 5),
        )
        if cache_key == self.solar_system_cache_key:
            return self.solar_system_cache

        try:
            self.solar_system_cache = compute_solar_system_positions(
                self.latitude,
                self.longitude,
            )
            self.solar_system_cache_key = cache_key
        except Exception:
            self.solar_system_cache = []
            self.solar_system_cache_key = cache_key
        return self.solar_system_cache

    def _draw_solar_system_objects(self, canvas, center_x, center_y, radius, lst_hours):
        self.sky_solar_system_points = []
        if not self.sky_show_solar_system:
            return

        for body in self._solar_system_positions():
            altitude, azimuth, hour_angle = self._equatorial_to_horizontal(
                body["ra_hours"],
                body["declination"],
                lst_hours,
            )
            point = self._project_horizontal_point(center_x, center_y, radius, altitude, azimuth)
            if point is None:
                continue

            x, y = point
            name = body["name"]
            label = self._tr(f"solar.{name}")
            fill = SOLAR_SYSTEM_BODY_COLORS.get(name, self.accent)
            size = 6 if name in {"Sun", "Moon"} else 4
            canvas.create_oval(
                x - size,
                y - size,
                x + size,
                y + size,
                fill=fill,
                outline=self.ebg,
                width=1,
            )
            canvas.create_text(
                x + size + 5,
                y,
                text=label,
                fill=fill,
                font=Font(family="Segoe UI", size=8, weight="bold"),
                anchor="w",
            )
            self.sky_solar_system_points.append(
                {
                    "name": name,
                    "label": label,
                    "kind": "solar",
                    "hover_color": fill,
                    "x": x,
                    "y": y,
                    "ra_hours": body["ra_hours"],
                    "declination": body["declination"],
                    "altitude": altitude,
                    "azimuth": azimuth,
                    "hour_angle": hour_angle,
                    "size": size,
                }
            )

    def _draw_target_marker(self, canvas, center_x, center_y, radius, altitude, azimuth):
        x, y, visible = self._project_target(center_x, center_y, radius, altitude, azimuth)
        if visible and altitude < 10:
            marker_color = TARGET_LOW_ALTITUDE_COLOR
        else:
            marker_color = self.success if visible else self.danger
        canvas.create_oval(x - 11, y - 11, x + 11, y + 11, outline=marker_color, width=2)
        canvas.create_line(x - 17, y, x + 17, y, fill=marker_color, width=2)
        canvas.create_line(x, y - 17, x, y + 17, fill=marker_color, width=2)
        canvas.create_text(
            x,
            y + 26,
            text=self._tr("sky.target"),
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

    def _format_signed_hms_compact(self, hours):
        sign = "-" if hours < 0 else "+"
        total_seconds = int(round(abs(hours) * 3600))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{sign}{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _format_signed_dms_compact(self, degrees_value):
        sign = "-" if degrees_value < 0 else "+"
        total_seconds = int(round(abs(degrees_value) * 3600))
        degrees = min(90, total_seconds // 3600)
        minutes = 0 if degrees == 90 else (total_seconds % 3600) // 60
        seconds = 0 if degrees == 90 else total_seconds % 60
        return f"{sign}{degrees:02d}:{minutes:02d}:{seconds:02d}"

    def _format_unsigned_hms_compact(self, hours_value):
        total_seconds = int(round((hours_value % 24) * 3600)) % (24 * 3600)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _format_jnow_horizontal_status(
        self,
        ra_hours,
        declination,
        altitude,
        azimuth,
        hour_angle,
    ):
        return (
            f"JNow : RA = {self._format_unsigned_hms_compact(ra_hours)} ; "
            f"DEC = {self._format_signed_dms_compact(declination)} | "
            f"Alt = {altitude:+.2f}\N{DEGREE SIGN} ; "
            f"Az = {azimuth:05.1f}\N{DEGREE SIGN} | "
            f"HA = {self._format_signed_hms_compact(hour_angle)}"
        )

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

    def _set_coordinate_fields(self, ra_hours, dec_degrees):
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

    def _current_solar_system_target(self, lst_hours):
        if not self.target_solar_system_name:
            return None

        for body in self._solar_system_positions():
            if body["name"] != self.target_solar_system_name:
                continue

            target = dict(body)
            altitude, azimuth, hour_angle = self._equatorial_to_horizontal(
                body["ra_hours"],
                body["declination"],
                lst_hours,
            )
            target["altitude"] = altitude
            target["azimuth"] = azimuth
            target["hour_angle"] = hour_angle
            return target

        return None

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
        azimuth = math.degrees(math.atan2(-dx, -dy)) % 360
        ra_hours, declination, hour_angle = self._horizontal_to_equatorial(
            altitude,
            azimuth,
            self.sky_geometry["lst_hours"],
        )
        return ra_hours, declination, hour_angle, altitude, azimuth

    def _nearest_sky_object(self, x, y):
        nearest = None
        nearest_distance = 999
        for sky_object in [*self.sky_star_points, *self.sky_solar_system_points]:
            distance = ((sky_object["x"] - x) ** 2 + (sky_object["y"] - y) ** 2) ** 0.5
            if distance < nearest_distance:
                nearest = sky_object
                nearest_distance = distance

        if nearest is not None and nearest_distance <= max(12, nearest["size"] + 8):
            return nearest
        return None

    def _draw_hover_overlay(self, x, y, sky_object=None):
        if self.sky_canvas is None:
            return

        self.sky_canvas.delete("sky-hover")
        color = sky_object.get("hover_color", self.fg) if sky_object else self.accent
        if sky_object:
            x = sky_object["x"]
            y = sky_object["y"]

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

        if not sky_object:
            return

        label = sky_object.get("label", sky_object["name"])
        label_font = Font(family="Segoe UI", size=9, weight="bold")
        canvas_width = self.sky_canvas.winfo_width()
        canvas_height = self.sky_canvas.winfo_height()
        margin = 8
        offset = 18
        padding_x = 7
        padding_y = 4
        text_width = label_font.measure(label)

        label_x = x + offset
        label_anchor = "w"
        if label_x + text_width + padding_x > canvas_width - margin:
            label_x = x - offset
            label_anchor = "e"

        label_y = y - 20
        if label_y - padding_y < margin:
            label_y = min(canvas_height - margin, y + 20)

        text_id = self.sky_canvas.create_text(
            label_x,
            label_y,
            text=label,
            fill=self.text,
            font=label_font,
            anchor=label_anchor,
            tags="sky-hover",
        )
        bbox = self.sky_canvas.bbox(text_id)
        if bbox:
            rect_id = self.sky_canvas.create_rectangle(
                bbox[0] - padding_x,
                bbox[1] - padding_y,
                bbox[2] + padding_x,
                bbox[3] + padding_y,
                fill=self.ebg,
                outline=color,
                width=1,
                tags="sky-hover",
            )
            self.sky_canvas.tag_lower(rect_id, text_id)

    def _set_sky_status(self, text, highlights=()):
        if self.sky_status is None:
            return

        self.sky_status.config(state=tk.NORMAL)
        self.sky_status.delete("1.0", tk.END)
        self.sky_status.insert("1.0", text)
        self.sky_status.tag_remove("danger", "1.0", tk.END)
        for highlight in highlights:
            if not highlight:
                continue
            start = "1.0"
            while True:
                index = self.sky_status.search(highlight, start, tk.END)
                if not index:
                    break
                end = f"{index}+{len(highlight)}c"
                self.sky_status.tag_add("danger", index, end)
                start = end
        self.sky_status.config(state=tk.DISABLED)

    def _sky_inactive_status(self):
        return self._tr("sky.no_target", count=len(self.sky_star_points))

    def _update_sky_hover(self):
        if self.sky_hover_position is None:
            if self.sky_canvas is not None:
                self.sky_canvas.delete("sky-hover")
            self._set_sky_status(self.sky_base_status, self.sky_base_status_highlights)
            return

        x, y = self.sky_hover_position
        coordinates = self._sky_coordinates_from_canvas(x, y)
        if coordinates is None:
            self.sky_canvas.delete("sky-hover")
            self._set_sky_status(self.sky_base_status, self.sky_base_status_highlights)
            return

        sky_object = self._nearest_sky_object(x, y)
        self._draw_hover_overlay(x, y, sky_object)

        if sky_object:
            jnow_status = self._format_jnow_horizontal_status(
                sky_object["ra_hours"],
                sky_object["declination"],
                sky_object["altitude"],
                sky_object["azimuth"],
                sky_object["hour_angle"],
            )
            label = f"{sky_object.get('label', sky_object['name'])} | {jnow_status}"
            if "magnitude" in sky_object:
                label = f"{label} | mag {sky_object['magnitude']:.2f}"
        else:
            ra_hours, declination, hour_angle, altitude, azimuth = coordinates
            jnow_status = self._format_jnow_horizontal_status(
                ra_hours,
                declination,
                altitude,
                azimuth,
                hour_angle,
            )
            label = f"{self._tr('sky.pointer')} | {jnow_status}"

        now = time.monotonic()
        if now - self.sky_last_status_update_time >= 0.12:
            self.sky_last_status_update_time = now
            self._set_sky_status(
                f"{label}\n{self.sky_base_status}",
                self.sky_base_status_highlights,
            )

    def _run_sky_hover_update(self):
        self.sky_hover_update_pending = False
        self._update_sky_hover()

    def _set_target_from_coordinates(self, ra_hours, dec_degrees, label, solar_system_name=None):
        self.target_active = True
        self.target_solar_system_name = solar_system_name
        self._set_coordinate_fields(ra_hours, dec_degrees)
        self.update_value(preserve_solar_target=solar_system_name is not None)
        self._set_result_text(
            self._tr(
                "result.target_coordinates",
                label=label,
                ra=self._format_ra(ra_hours),
                dec=self._format_dec(dec_degrees),
            ),
            foreground=self.success,
        )

    def _on_sky_motion(self, event):
        self.sky_hover_position = (event.x, event.y)
        if not self.sky_hover_update_pending:
            self.sky_hover_update_pending = True
            self.root.after(16, self._run_sky_hover_update)

    def _on_sky_leave(self, _event):
        self.sky_hover_position = None
        self.sky_hover_update_pending = False
        if self.sky_canvas is not None:
            self.sky_canvas.delete("sky-hover")
        if self.sky_status is not None:
            self.sky_last_status_update_time = 0
            self._set_sky_status(self.sky_base_status, self.sky_base_status_highlights)

    def _on_sky_click(self, event):
        self.sky_hover_position = (event.x, event.y)
        coordinates = self._sky_coordinates_from_canvas(event.x, event.y)
        if coordinates is None:
            return

        sky_object = self._nearest_sky_object(event.x, event.y)
        if sky_object:
            target_label_key = (
                "sky.target_set_body"
                if sky_object.get("kind") == "solar"
                else "sky.target_set_star"
            )
            self._set_target_from_coordinates(
                sky_object["ra_hours"],
                sky_object["declination"],
                self._tr(target_label_key, name=sky_object.get("label", sky_object["name"])),
                solar_system_name=(
                    sky_object["name"] if sky_object.get("kind") == "solar" else None
                ),
            )
            return

        ra_hours, declination, _hour_angle, _altitude, _azimuth = coordinates
        self._set_target_from_coordinates(
            ra_hours,
            declination,
            self._tr("sky.target_set"),
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
                hour_angle_offset_hours=6 if self.hour_angle_offset_enabled else 0,
                timezone_name=self.timezone_name,
                daylight_saving_enabled=self.daylight_saving_enabled,
            )

        center_x = width / 2
        center_y = height / 2 - 10
        radius = max(40, min(width * 0.43, height * 0.38))
        lst_hours = self._parse_clock_hours(state["lst"])
        target_key = None
        if self.target_active:
            target_key = (
                self.target_solar_system_name,
                self.alpha_hh.get(),
                self.alpha_mm.get(),
                self.alpha_ss.get(),
                self.delta_dd.get(),
                self.delta_mm.get(),
                self.delta_ss.get(),
            )
        refresh_seconds = (
            SKY_MAP_ANTIALIASED_REFRESH_SECONDS
            if Image is not None and ImageDraw is not None and ImageTk is not None
            else SKY_MAP_CANVAS_REFRESH_SECONDS
        )
        sidereal_second_bucket = int(self._parse_clock_hours(state["lst"]) * 3600 / refresh_seconds)
        cache_key = (
            width,
            height,
            int(time.time() // refresh_seconds),
            sidereal_second_bucket,
            round(self.sky_magnitude_limit, 2),
            self.sky_show_altaz_grid,
            self.sky_show_equatorial_grid,
            self.sky_show_solar_system,
            self.language,
            target_key,
        )
        if cache_key == self.sky_map_cache_key:
            return

        self.sky_map_cache_key = cache_key
        self.sky_canvas.delete("all")

        self.sky_geometry = {
            "center_x": center_x,
            "center_y": center_y,
            "radius": radius,
            "lst_hours": lst_hours,
        }
        self._draw_sky_grid(self.sky_canvas, center_x, center_y, radius)
        if self.sky_show_equatorial_grid:
            self._draw_equatorial_grid(self.sky_canvas, center_x, center_y, radius, lst_hours)
        self._draw_star_catalog(self.sky_canvas, center_x, center_y, radius, lst_hours)
        self._draw_solar_system_objects(self.sky_canvas, center_x, center_y, radius, lst_hours)

        if not self.target_active:
            self.sky_base_status = self._sky_inactive_status()
            self.sky_base_status_highlights = ()
            self._set_sky_status(self.sky_base_status)
            self._update_sky_hover()
            return

        solar_target = self._current_solar_system_target(lst_hours)
        if solar_target is not None:
            target_ra_hours = solar_target["ra_hours"]
            target_declination = solar_target["declination"]
            target_altitude = solar_target["altitude"]
            target_azimuth = solar_target["azimuth"]
            target_hour_angle = solar_target["hour_angle"]
            self._set_coordinate_fields(target_ra_hours, target_declination)
        else:
            target_ra_hours, target_declination = self._current_target_coordinates()
            target_altitude, target_azimuth, target_hour_angle = self._equatorial_to_horizontal(
                target_ra_hours,
                target_declination,
                lst_hours,
            )
        target_visible = self._draw_target_marker(
            self.sky_canvas,
            center_x,
            center_y,
            radius,
            target_altitude,
            target_azimuth,
        )

        if target_altitude >= 10:
            chart_note = self._tr("sky.above_horizon")
        elif target_altitude >= 0:
            chart_note = self._tr("sky.low_horizon")
        else:
            chart_note = self._tr("sky.below_horizon")
        altitude_text = f"{target_altitude:+.2f}"
        self.sky_base_status = self._tr(
            "sky.status",
            ha=self._format_signed_hms_compact(target_hour_angle),
            dec=self._format_signed_dms_compact(target_declination),
            altitude=altitude_text,
            azimuth=f"{target_azimuth:05.1f}",
            note=chart_note,
            count=len(self.sky_star_points),
        )
        self.sky_base_status_highlights = (
            () if target_visible else (f"Alt = {altitude_text}\N{DEGREE SIGN}", chart_note)
        )
        self._set_sky_status(self.sky_base_status, self.sky_base_status_highlights)
        self._update_sky_hover()

    def _set_result_text(self, text, foreground=None):
        self.result_text.config(state=tk.NORMAL, foreground=foreground or self.text)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(1.0, text)
        self.result_text.config(state=tk.DISABLED)

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
        if self.network_online is False:
            self._set_result_text(self._tr("result.aladin_offline"), foreground=self.danger)
            return

        self._sanitize_coordinate_values()
        self.update_value(activate_target=self.target_active)

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
            self._set_result_text(self._tr("result.aladin_unavailable"), foreground=self.danger)
            return

        self._set_result_text(
            self._tr(
                "result.aladin_opened",
                ra_deg=ra_deg,
                dec_deg=dec_deg,
                fov=self.aladin_fov_deg,
            )
        )

    def _activate_target_from_controls(self):
        self.update_value(activate_target=True)

    def update_value(self, activate_target=True, preserve_solar_target=False):
        if activate_target:
            self.target_active = True
            if not preserve_solar_target:
                self.target_solar_system_name = None
        self._sanitize_coordinate_values()
        self.lbl_dec_angle.config(
            text=compute_declination_display(
                self.delta_dd.get(),
                self.delta_mm.get(),
                self.delta_ss.get(),
                apply_offset=self.declination_offset_enabled,
            )
        )
        self.visibility_cache_key = None
        self.sky_map_cache_key = None
        self._update_sky_map()
        self._update_visibility_chart()

    def update_site_labels(self):
        local_now = self._local_datetime_from_utc(datetime.datetime.now(datetime.timezone.utc))
        date_format = "%d/%m/%Y" if self.language == "fr" else "%Y-%m-%d"
        lines = [
            self.site_name,
            self._tr("site.country", value=self.country or self._tr("settings.custom_site")),
            self._tr("site.timezone", value=self._timezone_label()),
            self._tr("site.local_date", value=local_now.strftime(date_format)),
            self._tr(
                "site.latitude",
                value=format_latitude_display(
                    self.latitude,
                    self._tr("direction.north_short"),
                    self._tr("direction.south_short"),
                ),
            ),
            self._tr(
                "site.longitude",
                value=format_longitude_display(
                    self.longitude,
                    self._tr("direction.east_short"),
                    self._tr("direction.west_short"),
                ),
            ),
        ]
        lines_key = tuple(lines)
        if lines_key == self.site_info_lines:
            return
        self.site_info_lines = lines_key
        self.site_info_text.config(state=tk.NORMAL)
        self.site_info_text.delete("1.0", tk.END)
        self.site_info_text.insert("1.0", f"{lines[0]}\n", "site-name")
        self.site_info_text.insert(tk.END, "\n".join(lines[1:]))
        self.site_info_text.config(state=tk.DISABLED)
        self._resize_site_info_text()
        if self.aladin_button is not None:
            self.aladin_button.config(text=self._tr("button.aladin", value=self.aladin_fov_deg))

    def _update_search_button_state(self):
        if self.search_button is None:
            return

        if self.coordinate_search_pending:
            self.search_button.config(text=self._tr("button.searching"), state=tk.DISABLED)
        else:
            self.search_button.config(text=self._tr("button.search"), state=tk.NORMAL)

    def _refresh_language_texts(self):
        if self.notebook is not None:
            self.notebook.tab(self.main_tab, text=self._tr("tab.main"))
            self.notebook.tab(self.visibility_tab, text=self._tr("tab.visibility"))
            self.notebook.tab(self.double_star_tab, text=self._tr("tab.double_stars"))
        self.subtitle_label.config(text=self._tr("app.subtitle"))
        self.header_settings_button.config(text=self._tr("button.settings"))
        self.about_button.config(text=self._tr("button.about"))
        self.fullscreen_button.config(text=self._tr("button.fullscreen"))
        self.quit_button.config(text=self._tr("button.quit"))
        if self.connectivity_label is not None:
            if self.network_online is None:
                self.connectivity_label.config(text=self._tr("network.checking"))
            else:
                text_key = "network.connected" if self.network_online else "network.offline"
                self.connectivity_label.config(text=self._tr(text_key))
        self._update_search_button_state()
        self.alpha_set_button.config(text=self._tr("button.set"))
        self.delta_set_button.config(text=self._tr("button.set"))
        self.double_search_button.config(text=self._tr("button.search"))
        self.double_set_button.config(text=self._tr("double.set_target"))
        if self.double_reset_button is not None:
            self.double_reset_button.config(text=self._tr("double.reset_filters"))
        for widget, key, kwargs in self.translated_widgets:
            widget.config(text=self._tr(key, **kwargs))
        self._refresh_double_star_headings()

        for title_label, title_key, title_kwargs in self.labelframe_title_labels:
            title_values = title_kwargs() if callable(title_kwargs) else title_kwargs
            title_label.config(text=self._tr(title_key, **title_values).upper())

        self._set_object_type_values()
        self.update_site_labels()
        self.update_value(
            activate_target=self.target_active,
            preserve_solar_target=self.target_solar_system_name is not None,
        )

    def _save_current_settings(self):
        double_filter_settings = self._current_double_filter_settings()
        self.settings = AppSettings(
            site_name=self.site_name,
            country=self.country,
            latitude=self.latitude,
            longitude=self.longitude,
            aladin_fov_deg=self.aladin_fov_deg,
            sky_magnitude_limit=self.sky_magnitude_limit,
            sky_show_altaz_grid=self.sky_show_altaz_grid,
            sky_show_equatorial_grid=self.sky_show_equatorial_grid,
            sky_show_solar_system=self.sky_show_solar_system,
            timezone_name=self.timezone_name,
            daylight_saving_enabled=self.daylight_saving_enabled,
            language=self.language,
            hour_angle_offset_enabled=self.hour_angle_offset_enabled,
            declination_offset_enabled=self.declination_offset_enabled,
            **double_filter_settings,
        )
        save_app_settings(self.settings)

    def _current_double_filter_settings(self):
        def read_float(variable_name, current_value):
            variable = getattr(self, variable_name, None)
            if variable is None or not is_float(variable.get()):
                return current_value
            return float(variable.get())

        visible_night_var = getattr(self, "double_visible_night_var", None)
        include_physical_var = getattr(self, "double_include_physical_var", None)
        include_noted_var = getattr(self, "double_include_noted_var", None)
        include_apparent_var = getattr(self, "double_include_apparent_var", None)
        include_uncertain_var = getattr(self, "double_include_uncertain_var", None)
        exclude_polar_circle_var = getattr(self, "double_exclude_polar_circle_var", None)
        online_var = getattr(self, "double_online_var", None)

        return {
            "double_max_primary_magnitude": read_float(
                "double_mag_primary_var",
                self.settings.double_max_primary_magnitude,
            ),
            "double_max_secondary_magnitude": read_float(
                "double_mag_secondary_var",
                self.settings.double_max_secondary_magnitude,
            ),
            "double_min_separation": read_float(
                "double_min_sep_var",
                self.settings.double_min_separation,
            ),
            "double_max_separation": read_float(
                "double_max_sep_var",
                self.settings.double_max_separation,
            ),
            "double_min_max_altitude": read_float(
                "double_min_altitude_var",
                self.settings.double_min_max_altitude,
            ),
            "double_visible_night": (
                visible_night_var.get()
                if visible_night_var is not None
                else self.settings.double_visible_night
            ),
            "double_include_physical": (
                include_physical_var.get()
                if include_physical_var is not None
                else self.settings.double_include_physical
            ),
            "double_include_noted": (
                include_noted_var.get()
                if include_noted_var is not None
                else self.settings.double_include_noted
            ),
            "double_include_apparent": (
                include_apparent_var.get()
                if include_apparent_var is not None
                else self.settings.double_include_apparent
            ),
            "double_include_uncertain": (
                include_uncertain_var.get()
                if include_uncertain_var is not None
                else self.settings.double_include_uncertain
            ),
            "double_exclude_polar_circle": (
                exclude_polar_circle_var.get()
                if exclude_polar_circle_var is not None
                else self.settings.double_exclude_polar_circle
            ),
            "double_use_online": (
                online_var.get() if online_var is not None else self.settings.double_use_online
            ),
        }

    def _save_double_filters_if_valid(self, _event=None):
        variables = (
            self.double_mag_primary_var,
            self.double_mag_secondary_var,
            self.double_min_sep_var,
            self.double_max_sep_var,
            self.double_min_altitude_var,
        )
        if not all(is_float(variable.get()) for variable in variables):
            return
        self._save_current_settings()

    def _parse_float_setting(self, value, label, minimum, maximum):
        if not is_float(value):
            raise ValueError(self._tr("error.must_be_number", label=label))

        numeric_value = float(value)
        if numeric_value < minimum or numeric_value > maximum:
            raise ValueError(
                self._tr(
                    "error.out_of_range",
                    label=label,
                    minimum=minimum,
                    maximum=maximum,
                )
            )

        return numeric_value

    def open_settings_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title(self._tr("settings.title"))
        apply_app_icon(dialog)
        dialog.configure(bg=self.gbg)
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.resizable(False, False)

        preset_lookup = {preset_label(preset): preset for preset in LOCATION_PRESETS}
        preset_values = list(preset_lookup)
        language_lookup = {label: code for code, label in LANGUAGE_OPTIONS}

        preset_var = tk.StringVar(value="")
        site_var = tk.StringVar(value=self.site_name)
        country_var = tk.StringVar(value=self.country)
        language_var = tk.StringVar(value=LANGUAGE_NAMES.get(self.language, LANGUAGE_NAMES["en"]))
        latitude_var = tk.StringVar(value=f"{self.latitude:.5f}")
        longitude_var = tk.StringVar(value=f"{self.longitude:.5f}")
        timezone_options = self._timezone_options()
        default_timezone = "Europe/Paris" if "Europe/Paris" in timezone_options else "UTC"
        timezone_var = tk.StringVar(value=self.timezone_name or default_timezone)
        timezone_auto_var = tk.BooleanVar(value=not bool(self.timezone_name))
        daylight_saving_var = tk.BooleanVar(value=self.daylight_saving_enabled)
        fov_var = tk.StringVar(value=f"{self.aladin_fov_deg:.2f}")
        sky_magnitude_limit_var = tk.StringVar(value=f"{self.sky_magnitude_limit:.1f}")
        sky_show_altaz_grid_var = tk.BooleanVar(value=self.sky_show_altaz_grid)
        sky_show_equatorial_grid_var = tk.BooleanVar(value=self.sky_show_equatorial_grid)
        sky_show_solar_system_var = tk.BooleanVar(value=self.sky_show_solar_system)
        hour_angle_offset_var = tk.BooleanVar(value=self.hour_angle_offset_enabled)
        declination_offset_var = tk.BooleanVar(value=self.declination_offset_enabled)

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

        def build_checkbutton(parent, variable, text, command=None):
            return tk.Checkbutton(
                parent,
                text=text,
                variable=variable,
                command=command,
                bg=self.gbg,
                fg=self.text,
                disabledforeground=self.muted,
                activebackground=self.gbg,
                activeforeground=self.fg,
                selectcolor=self.ebg,
                font=Font(family="Segoe UI", size=10),
                anchor="w",
                relief="flat",
            )

        add_label(0, self._tr("settings.preset"))
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
            country_var.set(preset["country"])
            latitude_var.set(f"{preset['latitude']:.5f}")
            longitude_var.set(f"{preset['longitude']:.5f}")

        preset_combo.bind("<<ComboboxSelected>>", apply_preset)

        add_label(1, self._tr("settings.site_name"))
        build_entry(1, site_var)

        add_label(2, self._tr("settings.country"))
        build_entry(2, country_var)

        add_label(3, self._tr("settings.language"))
        language_combo = ttk.Combobox(
            body,
            textvariable=language_var,
            values=[label for _code, label in LANGUAGE_OPTIONS],
            font=Font(family="Segoe UI", size=10),
            width=42,
        )
        language_combo.grid(column=1, row=3, pady=7, sticky="ew")
        language_combo["state"] = "readonly"

        add_label(4, self._tr("settings.latitude"))
        build_entry(4, latitude_var)
        add_label(5, self._tr("settings.longitude"))
        build_entry(5, longitude_var)
        add_label(6, self._tr("settings.timezone"))
        timezone_options_frame = tk.Frame(body, bg=self.gbg)
        timezone_options_frame.grid(column=1, row=6, pady=7, sticky="ew")
        timezone_options_frame.grid_columnconfigure(0, weight=1)
        timezone_combo = ttk.Combobox(
            timezone_options_frame,
            textvariable=timezone_var,
            values=timezone_options,
            font=Font(family="Segoe UI", size=10),
            width=42,
        )
        daylight_saving_check = None

        def sync_timezone_state():
            is_auto_timezone = timezone_auto_var.get()
            timezone_combo.config(state="disabled" if is_auto_timezone else "readonly")
            if daylight_saving_check is not None:
                daylight_saving_check.config(state=tk.DISABLED if is_auto_timezone else tk.NORMAL)

        build_checkbutton(
            timezone_options_frame,
            timezone_auto_var,
            self._tr("settings.timezone_auto"),
            sync_timezone_state,
        ).grid(column=0, row=0, sticky="w")
        timezone_combo.grid(column=0, row=1, pady=(5, 0), sticky="ew")
        daylight_saving_check = build_checkbutton(
            timezone_options_frame,
            daylight_saving_var,
            self._tr("settings.daylight_saving"),
        )
        daylight_saving_check.grid(column=0, row=2, pady=(5, 0), sticky="w")
        sync_timezone_state()

        add_label(7, self._tr("settings.aladin_fov"))
        build_entry(7, fov_var)

        add_label(8, self._tr("settings.sky_map"))
        sky_options = tk.Frame(body, bg=self.gbg)
        sky_options.grid(column=1, row=8, pady=7, sticky="ew")
        sky_options.grid_columnconfigure(0, weight=1)
        magnitude_frame = tk.Frame(sky_options, bg=self.gbg)
        magnitude_frame.grid(column=0, row=0, sticky="ew")
        magnitude_frame.grid_columnconfigure(1, weight=1)
        tk.Label(
            magnitude_frame,
            text=self._tr("settings.sky_magnitude_limit"),
            bg=self.gbg,
            fg=self.text,
            font=Font(family="Segoe UI", size=10),
            anchor="w",
        ).grid(column=0, row=0, padx=(0, 10), sticky="w")
        tk.Entry(
            magnitude_frame,
            textvariable=sky_magnitude_limit_var,
            bg=self.ebg,
            fg=self.text,
            insertbackground=self.fg,
            font=Font(family="Segoe UI", size=10),
            relief="flat",
            highlightbackground=self.card_edge,
            highlightcolor=self.accent,
            highlightthickness=1,
            width=8,
        ).grid(column=1, row=0, sticky="w")
        build_checkbutton(
            sky_options,
            sky_show_altaz_grid_var,
            self._tr("settings.sky_show_altaz_grid"),
        ).grid(column=0, row=1, sticky="w", pady=(5, 0))
        build_checkbutton(
            sky_options,
            sky_show_equatorial_grid_var,
            self._tr("settings.sky_show_equatorial_grid"),
        ).grid(column=0, row=2, sticky="w", pady=(4, 0))
        build_checkbutton(
            sky_options,
            sky_show_solar_system_var,
            self._tr("settings.sky_show_solar_system"),
        ).grid(column=0, row=3, sticky="w", pady=(4, 0))

        add_label(9, self._tr("settings.instrument"))
        instrument_options = tk.Frame(body, bg=self.gbg)
        instrument_options.grid(column=1, row=9, pady=7, sticky="ew")
        build_checkbutton(
            instrument_options,
            hour_angle_offset_var,
            self._tr("settings.hour_angle_offset"),
        ).pack(anchor="w")
        build_checkbutton(
            instrument_options,
            declination_offset_var,
            self._tr("settings.declination_offset"),
        ).pack(anchor="w", pady=(4, 0))

        hint = tk.Label(
            body,
            text=self._tr("settings.hint"),
            bg=self.gbg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=9),
            anchor="w",
        )
        hint.grid(column=0, row=10, columnspan=2, pady=(2, 12), sticky="ew")

        actions = tk.Frame(body, bg=self.gbg)
        actions.grid(column=0, row=11, columnspan=2, sticky="e")

        def reset_defaults():
            site_var.set(DEFAULT_SITE_NAME)
            country_var.set(DEFAULT_COUNTRY)
            latitude_var.set(f"{DEFAULT_LATITUDE:.5f}")
            longitude_var.set(f"{DEFAULT_LONGITUDE:.5f}")
            timezone_auto_var.set(True)
            timezone_var.set(default_timezone)
            daylight_saving_var.set(DEFAULT_DAYLIGHT_SAVING_ENABLED)
            sync_timezone_state()
            fov_var.set(f"{DEFAULT_ALADIN_FOV_DEG:.2f}")
            sky_magnitude_limit_var.set(f"{DEFAULT_SKY_MAGNITUDE_LIMIT:.1f}")
            sky_show_altaz_grid_var.set(DEFAULT_SKY_SHOW_ALTAZ_GRID)
            sky_show_equatorial_grid_var.set(DEFAULT_SKY_SHOW_EQUATORIAL_GRID)
            sky_show_solar_system_var.set(DEFAULT_SKY_SHOW_SOLAR_SYSTEM)
            hour_angle_offset_var.set(DEFAULT_HOUR_ANGLE_OFFSET_ENABLED)
            declination_offset_var.set(DEFAULT_DECLINATION_OFFSET_ENABLED)

        def apply_settings():
            try:
                latitude = self._parse_float_setting(
                    latitude_var.get(), self._tr("settings.latitude"), -90, 90
                )
                longitude = self._parse_float_setting(
                    longitude_var.get(), self._tr("settings.longitude"), -180, 180
                )
                fov = self._parse_float_setting(
                    fov_var.get(), self._tr("settings.aladin_fov"), 0.01, 180
                )
                sky_magnitude_limit = self._parse_float_setting(
                    sky_magnitude_limit_var.get(),
                    self._tr("settings.sky_magnitude_limit"),
                    -2,
                    MAX_SKY_MAGNITUDE_LIMIT,
                )
            except ValueError as exc:
                messagebox.showerror(self._tr("settings.invalid_title"), str(exc), parent=dialog)
                return

            timezone_name = DEFAULT_TIMEZONE_NAME
            if not timezone_auto_var.get():
                try:
                    timezone_name = self._validate_timezone_name(timezone_var.get())
                except ValueError:
                    messagebox.showerror(
                        self._tr("settings.invalid_title"),
                        self._tr("settings.timezone_invalid", value=timezone_var.get()),
                        parent=dialog,
                    )
                    return
                if not timezone_name:
                    messagebox.showerror(
                        self._tr("settings.invalid_title"),
                        self._tr("settings.timezone_invalid", value=timezone_var.get()),
                        parent=dialog,
                    )
                    return

            selected_language = language_lookup.get(language_var.get(), self.language)
            self.language = selected_language
            self.site_name = site_var.get().strip() or self._tr("settings.custom_site")
            self.country = country_var.get().strip() or DEFAULT_COUNTRY
            self.latitude = latitude
            self.longitude = longitude
            self.timezone_name = timezone_name
            self.daylight_saving_enabled = (
                daylight_saving_var.get() if timezone_name else DEFAULT_DAYLIGHT_SAVING_ENABLED
            )
            self.aladin_fov_deg = fov
            self.sky_magnitude_limit = sky_magnitude_limit
            self.sky_show_altaz_grid = sky_show_altaz_grid_var.get()
            self.sky_show_equatorial_grid = sky_show_equatorial_grid_var.get()
            self.sky_show_solar_system = sky_show_solar_system_var.get()
            self.solar_system_cache_key = None
            self.hour_angle_offset_enabled = hour_angle_offset_var.get()
            self.declination_offset_enabled = declination_offset_var.get()
            self._save_current_settings()
            self._refresh_language_texts()
            dialog.destroy()

        self._build_button(actions, self._tr("button.default"), reset_defaults).grid(
            column=0, row=0, padx=(0, 8)
        )
        self._build_button(actions, self._tr("button.cancel"), dialog.destroy).grid(
            column=1, row=0, padx=(0, 8)
        )
        self._build_button(actions, self._tr("button.apply"), apply_settings).grid(column=2, row=0)

        dialog.bind("<Return>", lambda _event: apply_settings())
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self._center_dialog_on_root(dialog)

    def _double_star_heading_keys(self):
        headings = {
            "name": "double.column.name",
            "designation": "double.column.designation",
            "nature": "double.column.nature",
            "magnitudes": "double.column.magnitudes",
            "separation": "double.column.separation",
            "pa": "double.column.pa",
            "orb6_separation": "double.column.orb6_separation",
            "orb6_pa": "double.column.orb6_pa",
            "max_altitude": "double.column.max_altitude",
            "last_observation_year": "double.column.last_observation_year",
            "observation_count": "double.column.observation_count",
            "wds_note": "double.column.wds_note",
            "orbit": "double.column.orbit",
        }
        return headings

    def _refresh_double_star_headings(self):
        if self.double_star_tree is None:
            return

        headings = self._double_star_heading_keys()
        for column, key in headings.items():
            label = self._tr(key)
            if column == self.double_sort_column:
                label = f"{label} {'v' if self.double_sort_reverse else '^'}"
            self.double_star_tree.heading(
                column,
                text=label,
                command=lambda selected_column=column: self._sort_double_star_table(
                    selected_column
                ),
            )

    def _format_double_filter_number(self, value):
        return f"{float(value):g}"

    def _default_double_filters(self):
        return {
            "max_primary": DEFAULT_DOUBLE_MAX_PRIMARY_MAGNITUDE,
            "max_secondary": DEFAULT_DOUBLE_MAX_SECONDARY_MAGNITUDE,
            "min_sep": DEFAULT_DOUBLE_MIN_SEPARATION,
            "max_sep": DEFAULT_DOUBLE_MAX_SEPARATION,
            "min_altitude": DEFAULT_DOUBLE_MIN_MAX_ALTITUDE,
            "visible_night": DEFAULT_DOUBLE_VISIBLE_NIGHT,
            "include_physical": DEFAULT_DOUBLE_INCLUDE_PHYSICAL,
            "include_noted": DEFAULT_DOUBLE_INCLUDE_NOTED,
            "include_apparent": DEFAULT_DOUBLE_INCLUDE_APPARENT,
            "include_uncertain": DEFAULT_DOUBLE_INCLUDE_UNCERTAIN,
            "exclude_polar_circle": DEFAULT_DOUBLE_EXCLUDE_POLAR_CIRCLE,
            "use_online": DEFAULT_DOUBLE_USE_ONLINE,
        }

    def _apply_double_filter_controls(self, filters):
        self.double_mag_primary_var.set(self._format_double_filter_number(filters["max_primary"]))
        self.double_mag_secondary_var.set(
            self._format_double_filter_number(filters["max_secondary"])
        )
        self.double_min_sep_var.set(self._format_double_filter_number(filters["min_sep"]))
        self.double_max_sep_var.set(self._format_double_filter_number(filters["max_sep"]))
        self.double_min_altitude_var.set(
            self._format_double_filter_number(filters["min_altitude"])
        )
        self.double_visible_night_var.set(filters["visible_night"])
        self.double_include_physical_var.set(filters["include_physical"])
        self.double_include_noted_var.set(filters["include_noted"])
        self.double_include_apparent_var.set(filters["include_apparent"])
        self.double_include_uncertain_var.set(filters["include_uncertain"])
        self.double_exclude_polar_circle_var.set(filters["exclude_polar_circle"])
        self.double_online_var.set(filters["use_online"])

    def reset_double_star_filters(self):
        self._apply_double_filter_controls(self._default_double_filters())
        self._save_current_settings()
        self.search_double_stars()

    def _sort_double_star_table(self, column):
        if column == self.double_sort_column:
            self.double_sort_reverse = not self.double_sort_reverse
        else:
            self.double_sort_column = column
            self.double_sort_reverse = False
        self._refresh_double_star_headings()
        self._populate_double_star_tree()

    def _double_sort_value(self, star):
        column = self.double_sort_column
        if column == "name":
            return str(star.get("name", "")).casefold()
        if column == "designation":
            return str(star.get("designation", "")).casefold()
        if column == "nature":
            return self._double_star_nature_label(star).casefold()
        if column == "magnitudes":
            return (star["mag_primary"], star["mag_secondary"])
        if column == "separation":
            return star["separation"]
        if column == "pa":
            return star["position_angle"]
        if column == "orb6_separation":
            return star.get("orb6_current_separation")
        if column == "orb6_pa":
            return star.get("orb6_current_pa")
        if column == "max_altitude":
            return star.get("max_altitude")
        if column == "last_observation_year":
            return star.get("last_observation_year")
        if column == "observation_count":
            return star.get("observation_count")
        if column == "wds_note":
            return 0 if self._double_has_wds_note(star) else 1
        if column == "orbit":
            return 0 if star.get("orb6_has_orbit") else 1
        return str(star.get("name", "")).casefold()

    def _double_tree_xview(self, *args):
        if self.double_star_tree is None:
            return
        self.double_star_tree.xview(*args)
        self.root.after_idle(self._update_double_tree_separators)

    def _on_double_tree_xscroll(self, scrollbar, first, last):
        scrollbar.set(first, last)
        self.root.after_idle(self._update_double_tree_separators)

    def _update_double_tree_separators(self):
        if self.double_star_tree is None:
            return

        for separator in self.double_tree_separators:
            separator.destroy()
        self.double_tree_separators = []

        tree_height = self.double_star_tree.winfo_height()
        if tree_height <= 1:
            return

        total_width = sum(
            self.double_star_tree.column(column, "width")
            for column in self.double_star_tree["columns"]
        )
        if total_width <= 0:
            return

        visible_width = self.double_star_tree.winfo_width()
        first_fraction = self.double_star_tree.xview()[0]
        scroll_offset = total_width * first_fraction
        x_position = -scroll_offset
        for column in self.double_star_tree["columns"][:-1]:
            x_position += self.double_star_tree.column(column, "width")
            if x_position <= 0 or x_position >= visible_width:
                continue
            separator = tk.Frame(
                self.double_star_tree,
                bg=self.card_edge,
                width=1,
                bd=0,
                highlightthickness=0,
            )
            separator.place(x=x_position, y=0, width=1, height=tree_height)
            separator.lift()
            self.double_tree_separators.append(separator)

    def _double_filter_value(self, variable, label_key, minimum, maximum):
        return self._parse_float_setting(
            variable.get(),
            self._tr(label_key),
            minimum,
            maximum,
        )

    def _read_double_star_filters(self):
        try:
            max_primary = self._double_filter_value(
                self.double_mag_primary_var,
                "double.max_primary",
                -2,
                20,
            )
            max_secondary = self._double_filter_value(
                self.double_mag_secondary_var,
                "double.max_secondary",
                -2,
                20,
            )
            min_sep = self._double_filter_value(
                self.double_min_sep_var,
                "double.min_sep",
                0,
                10000,
            )
            max_sep = self._double_filter_value(
                self.double_max_sep_var,
                "double.max_sep",
                0,
                10000,
            )
            min_altitude = self._double_filter_value(
                self.double_min_altitude_var,
                "double.min_max_altitude",
                -90,
                90,
            )
        except ValueError as exc:
            messagebox.showerror(self._tr("settings.invalid_title"), str(exc), parent=self.root)
            return None

        if min_sep > max_sep:
            min_sep, max_sep = max_sep, min_sep
            self.double_min_sep_var.set(self._format_double_filter_number(min_sep))
            self.double_max_sep_var.set(self._format_double_filter_number(max_sep))

        return {
            "max_primary": max_primary,
            "max_secondary": max_secondary,
            "min_sep": min_sep,
            "max_sep": max_sep,
            "min_altitude": min_altitude,
            "visible_night": self.double_visible_night_var.get(),
            "include_physical": self.double_include_physical_var.get(),
            "include_noted": self.double_include_noted_var.get(),
            "include_apparent": self.double_include_apparent_var.get(),
            "include_uncertain": self.double_include_uncertain_var.get(),
            "exclude_polar_circle": self.double_exclude_polar_circle_var.get(),
            "use_online": self.double_online_var.get(),
        }

    def _double_stars_to_jnow(self, stars):
        normalized = []
        for star in stars:
            normalized_star = dict(star)
            normalized_star.setdefault("source", "Local")
            normalized_star.setdefault("physical_status", "binary")
            normalized.append(normalized_star)

        try:
            catalog = [
                (index, star["ra_hours"], star["declination"], star["mag_primary"])
                for index, star in enumerate(normalized)
            ]
            converted = convert_star_catalog_j2000_to_jnow(catalog)
        except Exception:
            return normalized

        for index, converted_star in enumerate(converted):
            normalized[index]["ra_hours"] = converted_star[1]
            normalized[index]["declination"] = converted_star[2]
        return normalized

    def _double_visibility_context(self):
        start_utc = datetime.datetime.now(datetime.timezone.utc)
        offsets = [step / 2 for step in range(49)]
        utc_datetimes = [start_utc + datetime.timedelta(hours=offset) for offset in offsets]
        sun_altitudes = compute_sun_altitudes(self.latitude, self.longitude, utc_datetimes)
        context = []
        for offset, sample_time, sun_altitude in zip(offsets, utc_datetimes, sun_altitudes):
            state = compute_clock_state(
                self.longitude,
                self.alpha_hh.get(),
                self.alpha_mm.get(),
                self.alpha_ss.get(),
                hour_angle_offset_hours=6 if self.hour_angle_offset_enabled else 0,
                timezone_name=self.timezone_name,
                daylight_saving_enabled=self.daylight_saving_enabled,
                now_utc=sample_time,
            )
            context.append(
                {
                    "offset_hours": offset,
                    "lst_hours": self._parse_clock_hours(state["lst"]),
                    "sun_altitude": sun_altitude,
                }
            )
        return context

    def _double_star_visibility_metrics(self, star, visibility_context):
        if not visibility_context:
            return {
                "max_altitude": None,
                "max_night_altitude": None,
                "visible_at_night": False,
            }

        max_altitude = None
        max_night_altitude = None
        visible_at_night = False
        for sample in visibility_context:
            altitude, _azimuth, _hour_angle = self._equatorial_to_horizontal(
                star["ra_hours"],
                star["declination"],
                sample["lst_hours"],
            )
            if max_altitude is None or altitude > max_altitude:
                max_altitude = altitude
            if sample["sun_altitude"] > DOUBLE_NIGHT_SUN_MAX_ALTITUDE:
                continue
            if max_night_altitude is None or altitude > max_night_altitude:
                max_night_altitude = altitude
            if altitude >= DOUBLE_NIGHT_TARGET_MIN_ALTITUDE:
                visible_at_night = True

        return {
            "max_altitude": max_altitude,
            "max_night_altitude": max_night_altitude,
            "visible_at_night": visible_at_night,
        }

    def _double_note_flags(self, star):
        return set(str(star.get("notes", "") or "").strip().upper())

    def _double_has_wds_note(self, star):
        wds = str(star.get("wds", "")).strip()
        if not wds or "N" not in self._double_note_flags(star):
            return False
        cached_notes = self.double_wds_note_cache.get(wds)
        if cached_notes == []:
            return False
        return True

    def _double_filter_group(self, star):
        note_flags = self._double_note_flags(star)
        if note_flags & DOUBLE_UNCERTAIN_NOTE_FLAGS:
            return "uncertain"
        if note_flags & DOUBLE_APPARENT_NOTE_FLAGS:
            return "apparent"
        if note_flags & DOUBLE_PHYSICAL_NOTE_FLAGS:
            return "physical"

        status = star.get("physical_status", "unknown")
        if status == "binary":
            return "physical"
        if status == "apparent":
            return "apparent"
        if note_flags & DOUBLE_NOTED_NOTE_FLAGS:
            return "noted"
        return "unknown"

    def _double_group_allowed(self, star, filters):
        group = self._double_filter_group(star)
        if group == "physical":
            return filters["include_physical"]
        if group == "noted":
            return filters["include_noted"]
        if group == "apparent":
            return filters["include_apparent"]
        if group == "uncertain":
            return filters["include_uncertain"]
        if group == "unknown":
            return filters["include_uncertain"]
        return False

    def _double_filter_separation(self, star):
        current_separation = star.get("orb6_current_separation")
        if current_separation is not None:
            return current_separation
        return star["separation"]

    def _filter_double_star_list(self, stars, filters, visibility_context=None):
        if visibility_context is None:
            visibility_context = self._double_visibility_context()

        filtered = []
        for star in self._double_stars_to_jnow(stars):
            star.update(self._double_star_visibility_metrics(star, visibility_context))
            if not self._double_group_allowed(star, filters):
                continue
            if filters["exclude_polar_circle"] and star["declination"] > 60:
                continue
            if star["mag_primary"] > filters["max_primary"]:
                continue
            if star["mag_secondary"] > filters["max_secondary"]:
                continue
            if not (
                filters["min_sep"] <= self._double_filter_separation(star) <= filters["max_sep"]
            ):
                continue
            max_altitude = star.get("max_altitude")
            if max_altitude is None or max_altitude < filters["min_altitude"]:
                continue
            if filters["visible_night"] and not star.get("visible_at_night"):
                continue
            filtered.append(star)
        return filtered

    def _double_star_key(self, star):
        if star.get("wds"):
            return ("wds", star["wds"], star.get("designation", ""))
        return (
            "local",
            star.get("designation", star.get("name", "")),
            round(star["ra_hours"], 4),
            round(star["declination"], 4),
        )

    def _merge_double_star_results(self, *star_lists):
        merged = {}
        for stars in star_lists:
            for star in stars:
                merged[self._double_star_key(star)] = star
        return list(merged.values())

    def _double_local_catalog(self):
        return self._merge_double_star_results(DOUBLE_STARS, self.double_wds_cached_stars)

    def _enrich_double_star_orbits(self, stars, orb6_index):
        if not orb6_index and not self.double_orb6_orbit_index:
            return list(stars), 0
        try:
            return enrich_double_stars_with_orb6(
                stars,
                orb6_index,
                datetime.datetime.now(datetime.timezone.utc),
                orbit_index=self.double_orb6_orbit_index,
            )
        except Exception:
            return list(stars), 0

    def _double_orb6_status_note(self, count, orb6_index):
        if not count:
            return None
        if orb6_index and orb6_index.get("from_cache"):
            return self._tr("double.orb6_cached", count=count)
        return self._tr("double.orb6_loaded", count=count)

    def _double_star_nature_label(self, star):
        group = self._double_filter_group(star)
        if group == "physical":
            return self._tr("double.nature.binary")
        if group == "noted":
            return self._tr("double.nature.noted")
        if group == "apparent":
            return self._tr("double.nature.apparent")
        if group == "uncertain":
            return self._tr("double.nature.uncertain")
        return self._tr("double.nature.unknown")

    def _format_double_separation(self, star):
        separation = float(star["separation"])
        if star.get("separation_precision") is not None:
            decimals = int(star["separation_precision"])
        elif star.get("wds") or str(star.get("source", "")).startswith("WDS"):
            decimals = 1
        elif abs(separation * 10 - round(separation * 10)) > 1e-9:
            decimals = 2
        else:
            decimals = 1
        decimals = max(0, min(3, decimals))
        return f"{separation:.{decimals}f}\""

    def _format_double_orb6_separation(self, star):
        separation = star.get("orb6_current_separation")
        if separation is None:
            return ""
        decimals = int(star.get("orb6_separation_precision", 3))
        decimals = max(1, min(4, decimals))
        return f"{float(separation):.{decimals}f}\""

    def _format_double_orb6_pa(self, star):
        position_angle = star.get("orb6_current_pa")
        if position_angle is None:
            return ""
        return f"{float(position_angle):.1f}\N{DEGREE SIGN}"

    def _format_double_max_altitude(self, star):
        altitude = star.get("max_altitude")
        if altitude is None:
            return ""
        return f"{float(altitude):+.1f}\N{DEGREE SIGN}"

    def _format_double_optional_int(self, value):
        if value is None:
            return ""
        return str(value)

    def _format_double_magnitudes(self, star):
        return f"{star['mag_primary']:.2f} / {star['mag_secondary']:.2f}"

    def _format_double_designation(self, star):
        parts = []
        designation = str(star.get("designation", "")).strip()
        if designation:
            parts.append(designation)

        aliases = []
        for key in ("proper_name", "common_name"):
            value = str(star.get(key, "")).strip()
            if value and value not in aliases:
                aliases.append(value)
        if aliases:
            parts.append(" / ".join(aliases))

        for key, label in (("hd", "HD"), ("hip", "HIP"), ("hr", "HR")):
            value = star.get(key)
            if value:
                parts.append(f"{label} {value}")
        return " | ".join(parts)

    def _double_orbit_cell_text(self, star):
        if not star.get("orb6_has_orbit"):
            return ""
        return f"[{self._tr('double.orbit.open')}]"

    def _double_wds_note_cell_text(self, star):
        if not self._double_has_wds_note(star):
            return ""
        return f"[{self._tr('double.wds_note.open')}]"

    def _double_optional_numeric_sort_key(self, star):
        value = self._double_sort_value(star)
        name = str(star.get("name", "")).casefold()
        if value is None:
            return (1, 0, name)
        value = float(value)
        if self.double_sort_reverse:
            value = -value
        return (0, value, name)

    def _populate_double_star_tree(self):
        if self.double_sort_column in {
            "orb6_separation",
            "orb6_pa",
            "max_altitude",
            "last_observation_year",
            "observation_count",
            "wds_note",
            "orbit",
        }:
            self.double_star_results.sort(key=self._double_optional_numeric_sort_key)
        else:
            self.double_star_results.sort(
                key=lambda star: (
                    self._double_sort_value(star),
                    str(star.get("name", "")).casefold(),
                ),
                reverse=self.double_sort_reverse,
            )

        for item in self.double_star_tree.get_children():
            self.double_star_tree.delete(item)

        for index, star in enumerate(self.double_star_results):
            self.double_star_tree.insert(
                "",
                "end",
                iid=str(index),
                values=(
                    star["name"],
                    self._format_double_designation(star),
                    self._double_star_nature_label(star),
                    self._format_double_magnitudes(star),
                    self._format_double_separation(star),
                    f"{star['position_angle']:.0f}\N{DEGREE SIGN}",
                    self._format_double_orb6_separation(star),
                    self._format_double_orb6_pa(star),
                    self._format_double_max_altitude(star),
                    self._format_double_optional_int(star.get("last_observation_year")),
                    self._format_double_optional_int(star.get("observation_count")),
                    self._double_wds_note_cell_text(star),
                    self._double_orbit_cell_text(star),
                ),
                tags=("even" if index % 2 == 0 else "odd",),
            )
        self._update_double_tree_separators()

    def _double_tree_column_at(self, event):
        if self.double_star_tree is None:
            return None
        column_id = self.double_star_tree.identify_column(event.x)
        if not column_id or not column_id.startswith("#"):
            return None
        try:
            index = int(column_id[1:]) - 1
        except ValueError:
            return None
        columns = tuple(self.double_star_tree["columns"])
        if index < 0 or index >= len(columns):
            return None
        return columns[index]

    def _double_star_from_tree_row(self, row_id):
        if not row_id:
            return None
        try:
            index = int(row_id)
        except ValueError:
            return None
        if index < 0 or index >= len(self.double_star_results):
            return None
        return self.double_star_results[index]

    def _on_double_tree_click(self, event):
        self.root.after_idle(self._update_double_tree_separators)
        if self.double_star_tree.identify_region(event.x, event.y) != "cell":
            return
        column = self._double_tree_column_at(event)
        star = self._double_star_from_tree_row(self.double_star_tree.identify_row(event.y))
        if column == "orbit" and star is not None and star.get("orb6_has_orbit"):
            self.open_double_star_orbit_window(star)
            return
        if column == "wds_note" and star is not None and self._double_has_wds_note(star):
            self.open_double_star_wds_note_window(star)

    def _on_double_tree_double_click(self, event):
        if self._double_tree_column_at(event) in {"orbit", "wds_note"}:
            return "break"
        self.set_selected_double_star_target()
        return "break"

    def _on_double_tree_motion(self, event):
        if self.double_star_tree is None:
            return
        row_id = self.double_star_tree.identify_row(event.y)
        star = self._double_star_from_tree_row(row_id)
        column = self._double_tree_column_at(event)
        is_clickable_cell = (
            self.double_star_tree.identify_region(event.x, event.y) == "cell"
            and star is not None
            and (
                (column == "orbit" and star.get("orb6_has_orbit"))
                or (column == "wds_note" and self._double_has_wds_note(star))
            )
        )
        self.double_star_tree.configure(cursor="hand2" if is_clickable_cell else "")

    def _on_double_tree_leave(self, _event=None):
        if self.double_star_tree is not None:
            self.double_star_tree.configure(cursor="")

    def _render_double_star_results(self, stars, total, source_key, note=None):
        self.double_star_results = list(stars)
        self._populate_double_star_tree()

        status = self._tr(
            "double.result_count",
            count=len(self.double_star_results),
            total=total,
            source=self._tr(source_key),
        )
        if note:
            status = f"{status}\n{note}"
        self.double_status_label.config(
            text=status,
        )

    def search_double_stars(self, allow_online=True):
        filters = self._read_double_star_filters()
        if filters is None:
            return
        self._save_current_settings()

        self.double_search_generation += 1
        generation = self.double_search_generation
        visibility_context = self._double_visibility_context()
        local_catalog = self._double_local_catalog()
        local_source, _local_orb6_matches = self._enrich_double_star_orbits(
            local_catalog,
            self.double_orb6_index,
        )
        local_results = self._filter_double_star_list(
            local_source,
            filters,
            visibility_context,
        )
        self._render_double_star_results(
            local_results,
            len(local_catalog),
            "double.source.local",
        )

        if not allow_online or not filters["use_online"]:
            return

        if self.network_online is False:
            notes = [self._tr("double.online_offline")]
            local_orb6_count = sum(
                1 for star in local_results if star.get("orb6_current_separation") is not None
            )
            orb6_note = self._double_orb6_status_note(
                local_orb6_count,
                self.double_orb6_index,
            )
            if orb6_note:
                notes.append(orb6_note)
            self._render_double_star_results(
                local_results,
                len(local_catalog),
                "double.source.local",
                "\n".join(notes),
            )
            return

        self.double_remote_search_pending = True
        self.double_status_label.config(
            text=(
                f"{self.double_status_label.cget('text')}\n"
                f"{self._tr('double.searching_online')}"
            )
        )
        threading.Thread(
            target=self._run_double_star_online_search,
            args=(generation, filters),
            daemon=True,
        ).start()

    def _run_double_star_online_search(self, generation, filters):
        try:
            remote_results = fetch_wds_double_stars(
                filters["max_primary"],
                filters["max_secondary"],
                filters["min_sep"],
                filters["max_sep"],
                include_physical=filters["include_physical"],
                include_noted=filters["include_noted"],
                include_apparent=filters["include_apparent"],
                include_uncertain=filters["include_uncertain"],
                timeout=5,
            )
            error = None
        except Exception as exc:
            remote_results = []
            error = str(exc)

        try:
            orb6_index = fetch_orb6_ephemerides(timeout=5)
            orb6_error = orb6_index.get("fetch_error")
        except Exception as exc:
            orb6_index = None
            orb6_error = str(exc)

        try:
            orb6_orbit_index = fetch_orb6_orbits(timeout=5)
            orb6_orbit_error = orb6_orbit_index.get("fetch_error")
        except Exception as exc:
            orb6_orbit_index = None
            orb6_orbit_error = str(exc)

        try:
            self.root.after(
                0,
                lambda: self._apply_double_star_online_results(
                    generation,
                    filters,
                    remote_results,
                    error,
                    orb6_index,
                    orb6_error,
                    orb6_orbit_index,
                    orb6_orbit_error,
                ),
            )
        except (tk.TclError, RuntimeError):
            self.double_remote_search_pending = False

    def _apply_double_star_online_results(
        self,
        generation,
        filters,
        remote_results,
        error,
        orb6_index=None,
        orb6_error=None,
        orb6_orbit_index=None,
        orb6_orbit_error=None,
    ):
        if generation != self.double_search_generation:
            return

        self.double_remote_search_pending = False
        if orb6_index is not None:
            self.double_orb6_index = orb6_index
        if orb6_orbit_index is not None:
            self.double_orb6_orbit_index = orb6_orbit_index
        active_orb6_index = orb6_index or self.double_orb6_index
        visibility_context = self._double_visibility_context()
        if not error:
            self.double_wds_cached_stars = merge_cached_wds_double_stars(remote_results)
        local_catalog = self._double_local_catalog()
        local_source, _local_orb6_matches = self._enrich_double_star_orbits(
            local_catalog,
            active_orb6_index,
        )
        local_results = self._filter_double_star_list(
            local_source,
            filters,
            visibility_context,
        )
        if error:
            notes = [self._tr("double.online_error", error=error)]
            local_orb6_count = sum(
                1 for star in local_results if star.get("orb6_current_separation") is not None
            )
            if local_orb6_count:
                orb6_note = self._double_orb6_status_note(
                    local_orb6_count,
                    active_orb6_index,
                )
                if orb6_note:
                    notes.append(orb6_note)
            elif orb6_error:
                notes.append(self._tr("double.orb6_error", error=orb6_error))
            self._render_double_star_results(
                local_results,
                len(local_catalog),
                "double.source.local",
                "\n".join(notes),
            )
            return

        remote_source, _remote_orb6_matches = self._enrich_double_star_orbits(
            remote_results,
            active_orb6_index,
        )
        remote_filtered = self._filter_double_star_list(
            remote_source,
            filters,
            visibility_context,
        )
        combined = self._merge_double_star_results(local_results, remote_filtered)
        combined_catalog_total = len(self._merge_double_star_results(local_catalog, remote_source))
        notes = [
            self._tr("double.online_loaded", count=len(remote_filtered)),
            self._tr("double.wds_cache_updated", count=len(self.double_wds_cached_stars)),
        ]
        orb6_count = sum(
            1 for star in combined if star.get("orb6_current_separation") is not None
        )
        if orb6_count:
            orb6_note = self._double_orb6_status_note(orb6_count, active_orb6_index)
            if orb6_note:
                notes.append(orb6_note)
        elif orb6_error:
            notes.append(self._tr("double.orb6_error", error=orb6_error))
        self._render_double_star_results(
            combined,
            combined_catalog_total,
            "double.source.wds",
            "\n".join(notes),
        )

    def _selected_double_star(self):
        if self.double_star_tree is None:
            return None

        selection = self.double_star_tree.selection()
        if not selection:
            return None

        index = int(selection[0])
        if index < 0 or index >= len(self.double_star_results):
            return None
        return self.double_star_results[index]

    def set_selected_double_star_target(self):
        star = self._selected_double_star()
        if star is None:
            self.double_status_label.config(text=self._tr("double.no_selection"))
            return

        self._set_target_from_coordinates(
            star["ra_hours"],
            star["declination"],
            self._tr("double.target_set", name=star["name"]),
        )
        self.notebook.select(self.main_tab)

    def _current_decimal_year(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        start = datetime.datetime(now.year, 1, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(now.year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        return now.year + (now - start).total_seconds() / (end - start).total_seconds()

    def _decimal_year_to_datetime(self, decimal_year):
        year = int(math.floor(decimal_year))
        if year < 1 or year > 9998:
            return None
        fraction = decimal_year - year
        start = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
        end = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        return start + (end - start) * fraction

    def _format_orbit_epoch_label(self, orbit, decimal_year):
        date = self._decimal_year_to_datetime(decimal_year)
        if date is None:
            return f"{decimal_year:.1f}"
        if orbit["period_years"] > 5:
            return str(date.year)
        return f"{date.month:02d}/{date.year}"

    def _format_orbit_hover_date(self, decimal_year):
        date = self._decimal_year_to_datetime(decimal_year)
        if date is None:
            return f"{decimal_year:.3f}"
        return date.strftime("%Y-%m-%d")

    def _orbit_plot_position(self, point, center_x, center_y, scale):
        return center_x + point["east"] * scale, center_y + point["north"] * scale

    def open_double_star_orbit_window(self, star):
        orbit = star.get("orb6_orbit")
        if not orbit:
            self.double_status_label.config(text=self._tr("double.orbit.unavailable"))
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self._tr("double.orbit.title", name=star["name"]))
        dialog.configure(bg=self.gbg)
        dialog.transient(self.root)
        apply_app_icon(dialog)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = tk.Frame(dialog, bg=self.gbg)
        header.grid(column=0, row=0, padx=14, pady=(12, 4), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text=f"{star['name']} - {star['designation']}",
            bg=self.gbg,
            fg=self.fg,
            font=Font(family="Segoe UI", size=14, weight="bold"),
            anchor="w",
        ).grid(column=0, row=0, sticky="ew")
        tk.Label(
            header,
            text=self._tr(
                "double.orbit.elements",
                period=orbit["period_years"],
                semimajor=orbit["semimajor_arcsec"],
                eccentricity=orbit["eccentricity"],
                grade=orbit["grade"],
                reference=orbit.get("reference", ""),
            ),
            bg=self.gbg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10),
            anchor="w",
        ).grid(column=0, row=1, sticky="ew")

        canvas = tk.Canvas(
            dialog,
            bg=self.ebg,
            highlightthickness=1,
            highlightbackground=self.card_edge,
            bd=0,
            width=620,
            height=560,
        )
        canvas.grid(column=0, row=1, padx=14, pady=8, sticky="nsew")

        footer = tk.Frame(dialog, bg=self.gbg)
        footer.grid(column=0, row=2, padx=14, pady=(0, 12), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        status_label = tk.Label(
            footer,
            text="",
            bg=self.gbg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10),
            anchor="w",
        )
        status_label.grid(column=0, row=0, sticky="ew")
        self._build_button(footer, self._tr("button.close"), dialog.destroy).grid(
            column=1,
            row=0,
            padx=(10, 0),
        )

        state = {
            "canvas": canvas,
            "status_label": status_label,
            "star": star,
            "orbit": orbit,
            "screen_points": [],
        }
        canvas.bind("<Configure>", lambda _event: self._draw_double_star_orbit(state))
        canvas.bind("<Motion>", lambda event: self._on_double_orbit_motion(event, state))
        canvas.bind("<Leave>", lambda _event: self._clear_double_orbit_hover(state))
        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self._center_dialog_on_root(dialog)
        self._draw_double_star_orbit(state)

    def _set_wds_note_text(self, text_widget, content):
        text_widget.config(state=tk.NORMAL)
        text_widget.delete(1.0, tk.END)
        text_widget.insert(tk.END, content)
        text_widget.config(state=tk.DISABLED)

    def _format_wds_note_rows(self, notes):
        if not notes:
            return self._tr("double.wds_note.empty")

        groups = []
        current_designation = None
        current_lines = []
        for note in notes:
            designation = note.get("designation", "")
            reference = note.get("reference", "")
            if designation != current_designation:
                if current_lines:
                    groups.append((current_designation, current_lines))
                current_designation = designation
                current_lines = []
            text = note.get("text", "")
            if reference:
                text = f"[{reference}] {text}"
            current_lines.append(text)
        if current_lines:
            groups.append((current_designation, current_lines))

        blocks = []
        for designation, lines in groups:
            content = "\n".join(line for line in lines if line)
            blocks.append(f"{designation}\n{content}" if designation else content)
        return "\n\n".join(blocks)

    def _load_wds_note_rows(self, dialog, text_widget, wds):
        try:
            notes = fetch_wds_notes(wds, timeout=10)
            error = None
        except Exception as exc:
            notes = []
            error = str(exc)

        def apply_result():
            if not dialog.winfo_exists():
                return
            if error:
                self._set_wds_note_text(
                    text_widget,
                    self._tr("double.wds_note.error", error=error),
                )
                return
            self.double_wds_note_cache[wds] = notes
            self._set_wds_note_text(text_widget, self._format_wds_note_rows(notes))
            if not notes:
                self._populate_double_star_tree()

        try:
            self.root.after(0, apply_result)
        except (tk.TclError, RuntimeError):
            pass

    def open_double_star_wds_note_window(self, star):
        wds = str(star.get("wds", "")).strip()
        if not wds:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title(self._tr("double.wds_note.title", name=star["name"]))
        dialog.configure(bg=self.gbg)
        dialog.transient(self.root)
        apply_app_icon(dialog)
        dialog.grid_columnconfigure(0, weight=1)
        dialog.grid_rowconfigure(1, weight=1)

        header = tk.Frame(dialog, bg=self.gbg)
        header.grid(column=0, row=0, padx=14, pady=(14, 8), sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        tk.Label(
            header,
            text=f"{star['name']} - {self._format_double_designation(star)}",
            bg=self.gbg,
            fg=self.fg,
            font=Font(family="Segoe UI", size=13, weight="bold"),
            anchor="w",
        ).grid(column=0, row=0, sticky="ew")
        tk.Label(
            header,
            text=self._tr("double.wds_note.source", wds=wds),
            bg=self.gbg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10),
            anchor="w",
        ).grid(column=0, row=1, sticky="ew", pady=(3, 0))

        body = tk.Frame(dialog, bg=self.gbg)
        body.grid(column=0, row=1, padx=14, pady=8, sticky="nsew")
        body.grid_columnconfigure(0, weight=1)
        body.grid_rowconfigure(0, weight=1)
        text_widget = tk.Text(
            body,
            bg=self.ebg,
            fg=self.text,
            insertbackground=self.fg,
            relief="flat",
            highlightthickness=1,
            highlightbackground=self.card_edge,
            highlightcolor=self.accent,
            wrap=tk.WORD,
            width=78,
            height=14,
            font=Font(family="Segoe UI", size=10),
        )
        text_widget.grid(column=0, row=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            body,
            orient="vertical",
            command=text_widget.yview,
            style="Dark.Vertical.TScrollbar",
        )
        scrollbar.grid(column=1, row=0, sticky="ns")
        text_widget.configure(yscrollcommand=scrollbar.set)

        footer = tk.Frame(dialog, bg=self.gbg)
        footer.grid(column=0, row=2, padx=14, pady=(0, 12), sticky="ew")
        footer.grid_columnconfigure(0, weight=1)
        self._build_button(
            footer,
            self._tr("double.wds_note.open_url"),
            lambda: webbrowser.open_new_tab(build_wds_notes_url(wds)),
        ).grid(column=1, row=0, padx=(0, 8))
        self._build_button(footer, self._tr("button.close"), dialog.destroy).grid(
            column=2,
            row=0,
        )

        dialog.bind("<Escape>", lambda _event: dialog.destroy())
        self._center_dialog_on_root(dialog)

        cached_notes = self.double_wds_note_cache.get(wds)
        if cached_notes is not None:
            self._set_wds_note_text(text_widget, self._format_wds_note_rows(cached_notes))
        else:
            self._set_wds_note_text(text_widget, self._tr("double.wds_note.loading"))
            threading.Thread(
                target=self._load_wds_note_rows,
                args=(dialog, text_widget, wds),
                daemon=True,
            ).start()

    def _draw_double_star_orbit(self, state):
        canvas = state["canvas"]
        orbit = state["orbit"]
        status_label = state["status_label"]
        width = max(1, canvas.winfo_width())
        height = max(1, canvas.winfo_height())
        canvas.delete("all")

        points = sample_orbit_points(orbit, count=720)
        current_year = self._current_decimal_year()
        current = orbit_position_at_year(orbit, current_year)
        max_extent = max(
            0.001,
            *(abs(point["east"]) for point in points),
            *(abs(point["north"]) for point in points),
            abs(current["east"]),
            abs(current["north"]),
        )
        margin = 58
        scale = min((width - margin * 2) / (2 * max_extent), (height - margin * 2) / (2 * max_extent))
        center_x = width / 2
        center_y = height / 2

        canvas.create_line(
            center_x,
            margin / 2,
            center_x,
            height - margin / 2,
            fill=self.card_edge,
            dash=(4, 4),
        )
        canvas.create_line(
            margin / 2,
            center_y,
            width - margin / 2,
            center_y,
            fill=self.card_edge,
            dash=(4, 4),
        )
        canvas.create_text(
            center_x,
            height - 18,
            text=self._tr("direction.north_short"),
            fill=self.muted,
            font=Font(family="Segoe UI", size=10, weight="bold"),
        )
        canvas.create_text(
            width - 20,
            center_y,
            text=self._tr("direction.east_short"),
            fill=self.muted,
            font=Font(family="Segoe UI", size=10, weight="bold"),
        )

        coordinates = []
        screen_points = []
        for point in points:
            x_position, y_position = self._orbit_plot_position(point, center_x, center_y, scale)
            coordinates.extend((x_position, y_position))
            screen_points.append((x_position, y_position, point))
        if len(coordinates) >= 4:
            canvas.create_line(
                *coordinates,
                fill=self.accent,
                width=2,
                smooth=True,
            )

        canvas.create_oval(
            center_x - 4,
            center_y - 4,
            center_x + 4,
            center_y + 4,
            fill=self.text,
            outline=self.ebg,
        )

        marker_count = 8 if orbit["period_years"] > 5 else 10
        start_year = points[0]["year"]
        for index in range(marker_count):
            marker_year = start_year + orbit["period_years"] * index / marker_count
            marker = orbit_position_at_year(orbit, marker_year)
            marker_x, marker_y = self._orbit_plot_position(marker, center_x, center_y, scale)
            canvas.create_oval(
                marker_x - 3,
                marker_y - 3,
                marker_x + 3,
                marker_y + 3,
                fill=self.fg,
                outline=self.ebg,
            )
            canvas.create_text(
                marker_x + 6,
                marker_y - 6,
                text=self._format_orbit_epoch_label(orbit, marker_year),
                fill=self.text,
                font=Font(family="Segoe UI", size=8),
                anchor="sw",
            )

        current_x, current_y = self._orbit_plot_position(current, center_x, center_y, scale)
        canvas.create_oval(
            current_x - 6,
            current_y - 6,
            current_x + 6,
            current_y + 6,
            fill=self.fg,
            outline=self.text,
            width=2,
        )
        canvas.create_text(
            current_x + 8,
            current_y + 8,
            text=self._tr("double.orbit.now"),
            fill=self.fg,
            font=Font(family="Segoe UI", size=9, weight="bold"),
            anchor="nw",
        )
        status_label.config(
            text=self._tr(
                "double.orbit.status",
                date=self._format_orbit_hover_date(current_year),
                rho=current["rho"],
                theta=current["theta"],
            )
        )
        state["screen_points"] = screen_points

    def _on_double_orbit_motion(self, event, state):
        canvas = state["canvas"]
        points = state.get("screen_points", [])
        if not points:
            return
        nearest = min(
            points,
            key=lambda item: (item[0] - event.x) ** 2 + (item[1] - event.y) ** 2,
        )
        distance_squared = (nearest[0] - event.x) ** 2 + (nearest[1] - event.y) ** 2
        if distance_squared > 16 ** 2:
            self._clear_double_orbit_hover(state)
            return

        x_position, y_position, point = nearest
        text = self._tr(
            "double.orbit.hover",
            date=self._format_orbit_hover_date(point["year"]),
            rho=point["rho"],
            theta=point["theta"],
        )
        canvas.delete("orbit_hover")
        canvas.create_oval(
            x_position - 5,
            y_position - 5,
            x_position + 5,
            y_position + 5,
            fill=self.success,
            outline=self.text,
            tags=("orbit_hover",),
        )
        padding = 8
        text_x = x_position + 12
        text_y = y_position - 28
        text_item = canvas.create_text(
            text_x,
            text_y,
            text=text,
            anchor="nw",
            fill=self.ebg,
            font=Font(family="Segoe UI", size=9, weight="bold"),
            tags=("orbit_hover",),
        )
        bbox = canvas.bbox(text_item)
        if bbox is not None:
            rect_padding_x = 5
            rect_padding_y = 3
            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()
            dx = 0
            dy = 0
            if bbox[2] + rect_padding_x > canvas_width - padding:
                dx = canvas_width - padding - rect_padding_x - bbox[2]
            if bbox[0] - rect_padding_x + dx < padding:
                dx += padding - (bbox[0] - rect_padding_x + dx)
            if bbox[3] + rect_padding_y > canvas_height - padding:
                dy = canvas_height - padding - rect_padding_y - bbox[3]
            if bbox[1] - rect_padding_y + dy < padding:
                dy += padding - (bbox[1] - rect_padding_y + dy)
            if dx or dy:
                canvas.move(text_item, dx, dy)
                bbox = canvas.bbox(text_item)
            if bbox is None:
                state["status_label"].config(text=text)
                return
            rect = canvas.create_rectangle(
                bbox[0] - rect_padding_x,
                bbox[1] - rect_padding_y,
                bbox[2] + rect_padding_x,
                bbox[3] + rect_padding_y,
                fill=self.accent,
                outline=self.accent,
                tags=("orbit_hover",),
            )
            canvas.tag_lower(rect, text_item)
        state["status_label"].config(text=text)

    def _clear_double_orbit_hover(self, state):
        state["canvas"].delete("orbit_hover")

    def _coordinate_result_message(self, result):
        if result.get("source") == "imcce":
            return self._tr(
                "result.imcce_coordinates",
                ra=result.get("source_ra", ""),
                dec=result.get("source_dec", ""),
            )
        if result.get("source") == "sesame":
            return self._tr(
                "result.sesame_coordinates",
                ra=result.get("source_ra", ""),
                dec=result.get("source_dec", ""),
            )
        return result["message"]

    def _apply_coordinate_result(self, result):
        self._set_result_text(self._coordinate_result_message(result))
        self.alpha_hh.set(result["alpha_hh"])
        self.alpha_mm.set(result["alpha_mm"])
        self.alpha_ss.set(result["alpha_ss"])
        self.delta_dd.set(result["delta_dd"])
        self.delta_mm.set(result["delta_mm"])
        self.delta_ss.set(result["delta_ss"])
        self.update_value()

    def _start_coordinate_search(self, selected_type, object_name):
        self.coordinate_search_generation += 1
        generation = self.coordinate_search_generation
        self.coordinate_search_pending = True
        self._update_search_button_state()
        self._set_result_text(self._tr("result.searching", object_name=object_name), self.muted)
        threading.Thread(
            target=self._run_coordinate_search,
            args=(generation, selected_type, object_name),
            daemon=True,
        ).start()

    def _run_coordinate_search(self, generation, selected_type, object_name):
        try:
            if selected_type in {
                "Asteroid",
                "Comet",
                "Dwarf Planet",
                "Planet",
                "Natural Satellite",
            }:
                result = resolve_solar_system_coordinates(selected_type, object_name)
            else:
                result = resolve_deep_sky_coordinates(object_name)
            error_key = None
            error_detail = None
        except name_resolve.NameResolveError:
            result = None
            error_key = "result.object_not_found"
            error_detail = None
        except Exception as exc:
            result = None
            error_key = (
                "result.ephemerides_error"
                if selected_type
                in {"Asteroid", "Comet", "Dwarf Planet", "Planet", "Natural Satellite"}
                else "result.search_error"
            )
            error_detail = str(exc)

        try:
            self.root.after(
                0,
                lambda: self._apply_coordinate_search_result(
                    generation,
                    result,
                    error_key,
                    error_detail,
                ),
            )
        except (tk.TclError, RuntimeError):
            self.coordinate_search_pending = False

    def _apply_coordinate_search_result(self, generation, result, error_key, error_detail):
        if generation != self.coordinate_search_generation:
            return

        self.coordinate_search_pending = False
        self._update_search_button_state()
        if error_key is not None:
            values = {"error": error_detail} if error_detail else {}
            self._set_result_text(self._tr(error_key, **values), foreground=self.danger)
            return

        self._apply_coordinate_result(result)

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

        selected_type = self._selected_object_type_code()
        object_name = self.search_entry.get().strip()

        if self.coordinate_search_pending:
            return

        if selected_type in solar_system_types:
            if not object_name:
                self._set_result_text("")
                return
            self._start_coordinate_search(selected_type, object_name)
            return

        if object_name.lower() in solar_system:
            self._set_result_text(self._tr("result.object_type_error"), foreground=self.danger)
            return

        if not selected_type:
            self._set_result_text(self._tr("result.no_object_type"), foreground=self.danger)
            return

        if not object_name:
            self._set_result_text("")
            return

        self._start_coordinate_search(selected_type, object_name)

    def clocks(self):
        self._sanitize_coordinate_values()
        state = compute_clock_state(
            self.longitude,
            self.alpha_hh.get(),
            self.alpha_mm.get(),
            self.alpha_ss.get(),
            hour_angle_offset_hours=6 if self.hour_angle_offset_enabled else 0,
            timezone_name=self.timezone_name,
            daylight_saving_enabled=self.daylight_saving_enabled,
        )

        self.update_site_labels()
        self.label_local.config(text=state["local"])
        self.label_utc.config(text=state["utc"])
        self.label_gmst.config(text=state["gmst"])
        self.label_lst.config(text=state["lst"])
        self.lbl_hour_angle.config(text=state["hour_angle"])
        try:
            self._update_sky_map(state)
            self._update_visibility_chart(state)
        except Exception as exc:
            if self.sky_status is not None:
                self._set_sky_status(self._tr("sky.unavailable", error=exc))
        finally:
            self.root.after(CLOCK_REFRESH_MS, self.clocks)

    def _start_iers_download(self):
        threading.Thread(target=self._download_iers_data, daemon=True).start()

    def _download_iers_data(self):
        try:
            download_IERS_A()
        except Exception:
            pass

    def run(self):
        self._start_iers_download()
        self.clocks()
        self.root.mainloop()


def _create_loading_window():
    root = tk.Tk()
    root.withdraw()
    apply_app_icon(root, default=True)
    window = tk.Toplevel(root)
    window.withdraw()
    window.title("AstroClocks")
    apply_app_icon(window)
    window.configure(bg="#101419")
    window.resizable(False, False)
    width = 440
    height = 170
    tk.Label(
        window,
        text=f"AstroClocks v{APP_VERSION}",
        bg="#101419",
        fg="#f6c451",
        font=Font(family="Segoe UI", size=22, weight="bold"),
    ).pack(pady=(26, 8))
    status_var = tk.StringVar(value="Initialisation...")
    tk.Label(
        window,
        textvariable=status_var,
        bg="#101419",
        fg="#edf3f8",
        font=Font(family="Segoe UI", size=11),
    ).pack(pady=(4, 18))
    tk.Label(
        window,
        text="Veuillez patienter",
        bg="#101419",
        fg="#93a6b7",
        font=Font(family="Segoe UI", size=9),
    ).pack()
    startup_monitor_geometry = center_window_on_pointer_monitor(
        window,
        width,
        height,
        use_work_area=True,
    )
    root._astroclocks_startup_monitor_geometry = startup_monitor_geometry
    window.deiconify()
    window.lift()
    window.update()
    return root, window, status_var


def main(root=None, loading_window=None, loading_status_var=None):
    if root is None and loading_window is None and loading_status_var is None:
        root, loading_window, loading_status_var = _create_loading_window()
    app = AstroClocksApp(
        root=root,
        loading_window=loading_window,
        loading_status_var=loading_status_var,
    )
    app.run()
