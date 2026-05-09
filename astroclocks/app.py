import datetime
import math
import os
import queue
import socket
import tempfile
import threading
import tkinter as tk
import time
import webbrowser
from pathlib import Path
from tkinter import ttk
from tkinter.font import Font
from zoneinfo import available_timezones

from astroplan import download_IERS_A
from astropy.coordinates import name_resolve
from astroclocks import app_deep_sky, app_dialogs, app_star_search, updater
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from astroclocks.astronomy import (
    compute_clock_state,
    compute_declination_display,
    compute_sun_altitudes,
    compute_solar_system_body_positions,
    compute_solar_system_positions,
    convert_star_catalog_j2000_to_jnow,
    format_timezone_label,
    j2000_to_jnow_coordinates,
    jnow_to_j2000_coordinates,
    resolve_deep_sky_coordinates,
    resolve_local_solar_system_coordinates,
    resolve_solar_system_coordinates,
    resolve_timezone,
)
from astroclocks.double_star_catalog import (
    DOUBLE_STARS,
    clear_cached_wds_double_stars,
    fetch_wds_double_stars,
    load_cached_wds_double_stars,
    merge_cached_wds_double_stars,
)
from astroclocks.deep_sky_catalog import load_cached_simbad_deep_sky_objects
from astroclocks.i18n import translate
from astroclocks.local_object_catalog import resolve_local_object_coordinates
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
    DEFAULT_DOUBLE_TRANSIT_NIGHT,
    DEFAULT_DOUBLE_USE_ONLINE,
    DEFAULT_DOUBLE_VISIBLE_NIGHT,
    DEFAULT_DEEP_SKY_CATEGORY,
    DEFAULT_TIMEZONE_NAME,
    format_latitude_display,
    format_longitude_display,
    load_app_settings,
    save_app_settings,
)
from astroclocks.star_sprites import StarRenderStats, StarSpriteCache
from astroclocks.star_catalog import SKY_STARS_J2000
from astroclocks.utils import is_float, resource_path
from astroclocks.windowing import (
    apply_windows_title_bar_theme,
    center_window_on_pointer_monitor,
    current_monitor_geometry as window_current_monitor_geometry,
    fallback_screen_geometry as window_fallback_screen_geometry,
    monitor_geometry as window_monitor_geometry,
    monitor_geometry_from_handle as window_monitor_geometry_from_handle,
    monitor_geometry_from_point as window_monitor_geometry_from_point,
    move_window_to as window_move_window_to,
    pointer_monitor_geometry as window_pointer_monitor_geometry,
)
from astroclocks.version import APP_RELEASE_DATE, APP_VERSION
APP_AUTHOR = "Yannis Benazza"
APP_EMAIL = "yannis.benazza@obspm.fr"
APP_PHONE = "01 45 07 71 59"
CLOCK_REFRESH_HZ = 15
CLOCK_REFRESH_MS = round(1000 / CLOCK_REFRESH_HZ)
SKY_MAP_ANTIALIASED_REFRESH_SECONDS = 8
SKY_MAP_CANVAS_REFRESH_SECONDS = 8
SKY_STAR_BRIGHTNESS_MULTIPLIER = 1.27
SKY_RENDER_DEBUG = os.environ.get("ASTROCLOCKS_SKY_RENDER_DEBUG") == "1"
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
OFFLINE_OBJECT_TYPE_CODES = ("Star, Deep Sky Object",)
LOCAL_SOLAR_SYSTEM_OBJECT_TYPE_CODES = ("Planet", "Natural Satellite")


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
        self._apply_native_window_chrome(self.root)
        if self.loading_window is not None:
            self._apply_native_window_chrome(self.loading_window)
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
        self.named_stars_jnow = []
        self.named_stars_loading = False
        self.named_stars_result_queue = queue.Queue()
        self.sky_geometry = None
        self.sky_map_cache_key = None
        self.sky_star_image = None
        self.sky_sprite_cache = (
            StarSpriteCache(Image, brightness_multiplier=SKY_STAR_BRIGHTNESS_MULTIPLIER)
            if Image is not None
            else None
        )
        self.sky_render_stats = StarRenderStats()
        self.sky_star_points = []
        self.sky_solar_system_points = []
        self.sky_hover_position = None
        self.sky_hover_update_pending = False
        self.sky_last_status_update_time = 0
        self.sky_base_status = ""
        self.sky_base_status_highlights = ()
        self.target_jnow_cache_key = None
        self.target_jnow_cache = None
        self.solar_system_cache_key = None
        self.solar_system_cache = []
        self.target_active = False
        self.target_solar_system_name = None
        self.target_display_name = ""
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
        self.site_info_resize_job = None
        self.dynamic_font_update_job = None
        self.sky_map_resize_job = None
        self.visibility_chart_resize_job = None
        self.notebook = None
        self.main_tab = None
        self.visibility_tab = None
        self.double_star_tab = None
        self.deep_sky_tab = None
        self.star_search_tab = None
        self.visibility_canvas = None
        self.visibility_status = None
        self.visibility_cache_key = None
        self.visibility_curve_points = []
        self.visibility_chart_geometry = None
        self.visibility_hover_position = None
        self.visibility_start_date = None
        self.visibility_compute_generation = 0
        self.visibility_compute_pending = False
        self.visibility_date_var = None
        self.visibility_previous_button = None
        self.visibility_next_button = None
        self.visibility_calendar_button = None
        self.double_star_results = []
        self.double_star_tree = None
        self.double_apply_button = None
        self.double_search_button = None
        self.double_orbit_recompute_button = None
        self.double_reset_button = None
        self.double_clear_cache_button = None
        self.double_advanced_button = None
        self.double_advanced_frame = None
        self.double_advanced_options_visible = False
        self.double_tree_separators = []
        self.double_tree_separator_refresh_pending = False
        self.double_tree_render_job = None
        self.double_status_label = None
        self.double_sort_column = "name"
        self.double_sort_reverse = False
        self.double_star_tab_initialized = False
        self.double_star_initial_load_started = False
        self.double_search_generation = 0
        self.double_remote_search_pending = False
        self.double_orb6_index = None
        self.double_orb6_orbit_index = None
        self.double_wds_note_cache = {}
        self.double_wds_cached_stars = []
        self.deep_sky_results = []
        self.deep_sky_tree = None
        self.deep_sky_apply_button = None
        self.deep_sky_online_button = None
        self.deep_sky_reset_button = None
        self.deep_sky_set_button = None
        self.deep_sky_clear_cache_button = None
        self.deep_sky_magnitude_band_combo = None
        self.deep_sky_status_label = None
        self.deep_sky_tree_separators = []
        self.deep_sky_tree_separator_refresh_pending = False
        self.deep_sky_sort_column = "name"
        self.deep_sky_sort_reverse = False
        self.deep_sky_tab_initialized = False
        self.deep_sky_initial_load_started = False
        self.deep_sky_search_generation = 0
        self.deep_sky_search_pending = False
        self.deep_sky_simbad_cached_objects = []
        self.deep_sky_category_label_to_code = {}
        self.deep_sky_magnitude_band_var = None
        self.deep_sky_magnitude_entries = []
        self.star_search_results = []
        self.star_search_tree = None
        self.star_search_apply_button = None
        self.star_search_online_button = None
        self.star_search_set_button = None
        self.star_search_reset_button = None
        self.star_search_clear_cache_button = None
        self.star_search_status_label = None
        self.star_search_tree_separators = []
        self.star_search_tree_separator_refresh_pending = False
        self.star_search_sort_column = "name"
        self.star_search_sort_reverse = False
        self.star_search_tab_initialized = False
        self.star_search_initial_load_started = False
        self.star_search_cache_loaded = False
        self.star_search_generation = 0
        self.star_search_pending = False
        self.star_search_cached_stars = []
        self.star_search_spectral_var = None
        self.star_search_band_var = None
        self.star_search_min_mag_var = None
        self.star_search_max_mag_var = None
        self.star_search_min_altitude_var = None
        self.star_search_visible_night_var = None
        self.coordinate_search_generation = 0
        self.coordinate_search_pending = False
        self.translated_widgets = []
        self.deferred_startup_scheduled = False

        self._set_loading_status("Chargement du cache ORB6...")
        self.double_orb6_index = load_cached_orb6_ephemerides()
        self.double_orb6_orbit_index = load_cached_orb6_orbits()
        self.double_wds_cached_stars = load_cached_wds_double_stars()
        self.deep_sky_simbad_cached_objects = load_cached_simbad_deep_sky_objects()

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
        self._set_loading_status("Préparation des onglets de recherche...")
        self._preload_search_tab_widgets()
        self._set_loading_status("Conversion du catalogue d'étoiles...")
        self._load_named_star_catalog_for_startup()
        self.update_site_labels()
        self.update_value(activate_target=False)
        self._schedule_connectivity_check(0)
        self._set_loading_status("Affichage de la fenêtre...")
        self._place_initial_window()
        self._update_dynamic_fonts()
        try:
            self.root.update()
        except (tk.TclError, RuntimeError):
            pass
        self._close_loading_window()

        self.root.bind("<Return>", lambda event: self.search_coordinates())
        self.root.bind("<Configure>", self._schedule_dynamic_font_update)

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

    def _schedule_deferred_startup_work(self):
        if self.deferred_startup_scheduled:
            return
        self.deferred_startup_scheduled = True
        self.root.after(0, self._start_deferred_startup_work)

    def _start_deferred_startup_work(self):
        self._start_named_star_catalog_conversion()

    def _preload_search_tab_widgets(self):
        if not self.double_star_tab_initialized:
            self._create_double_star_widgets()
            self.double_star_tab_initialized = True
        if not self.deep_sky_tab_initialized:
            self._create_deep_sky_widgets()
            self.deep_sky_tab_initialized = True
        if not self.star_search_tab_initialized:
            self._create_star_search_widgets()
            self.star_search_tab_initialized = True

    def _load_named_star_catalog_for_startup(self):
        if self.named_stars_jnow:
            return
        self.named_stars_loading = True
        try:
            self.named_stars_jnow = convert_star_catalog_j2000_to_jnow(SKY_STARS_J2000)
        except Exception:
            self.named_stars_jnow = []
        self.named_stars_loading = False
        self.sky_map_cache_key = None

    def _start_named_star_catalog_conversion(self):
        if self.named_stars_loading or self.named_stars_jnow:
            return
        self.named_stars_loading = True
        threading.Thread(target=self._load_named_star_catalog_jnow, daemon=True).start()
        self.root.after(50, self._poll_named_star_catalog_conversion)

    def _load_named_star_catalog_jnow(self):
        try:
            converted = convert_star_catalog_j2000_to_jnow(SKY_STARS_J2000)
        except Exception:
            converted = []
        self.named_stars_result_queue.put(converted)

    def _poll_named_star_catalog_conversion(self):
        if not self.named_stars_loading:
            return
        try:
            converted = self.named_stars_result_queue.get_nowait()
        except queue.Empty:
            self.root.after(50, self._poll_named_star_catalog_conversion)
            return
        self._apply_named_star_catalog_jnow(converted)

    def _apply_named_star_catalog_jnow(self, converted):
        self.named_stars_loading = False
        self.named_stars_jnow = converted
        self.sky_map_cache_key = None
        try:
            self._update_sky_map()
        except (tk.TclError, RuntimeError):
            pass

    def _release_date_text(self):
        return f"{self._tr(f'about.month.{APP_RELEASE_DATE.month}')} {APP_RELEASE_DATE.year}"

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

    def _apply_native_window_chrome(self, window):
        try:
            apply_windows_title_bar_theme(
                window,
                caption_color=self.gbg,
                text_color=self.text,
                border_color=self.card_edge,
                immersive_dark=True,
            )
        except Exception:
            pass

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
        self._apply_native_window_chrome(self.root)
        self._move_window_to(self.root, x, y)
        try:
            self.root.attributes("-alpha", 1.0)
        except (tk.TclError, RuntimeError):
            pass

    def _center_dialog_on_root(self, dialog):
        dialog.update_idletasks()
        dialog_width = max(dialog.winfo_width(), dialog.winfo_reqwidth())
        dialog_height = max(dialog.winfo_height(), dialog.winfo_reqheight())
        x = self.root.winfo_rootx() + (self.root.winfo_width() - dialog_width) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - dialog_height) // 2

        monitor_x, monitor_y, monitor_width, monitor_height = self._current_monitor_geometry(
            use_work_area=True
        )
        max_x = monitor_x + monitor_width - dialog_width
        max_y = monitor_y + monitor_height - dialog_height
        if max_x >= monitor_x:
            x = min(max(x, monitor_x), max_x)
        else:
            x = monitor_x
        if max_y >= monitor_y:
            y = min(max(y, monitor_y), max_y)
        else:
            y = monitor_y

        self._apply_native_window_chrome(dialog)
        self._move_window_to(dialog, x, y)
        dialog.lift(self.root)

    def _place_dialog_below_widget(self, dialog, widget, x_offset=0, y_offset=6):
        dialog.update_idletasks()
        dialog_width = max(dialog.winfo_width(), dialog.winfo_reqwidth())
        dialog_height = max(dialog.winfo_height(), dialog.winfo_reqheight())
        x = widget.winfo_rootx() + x_offset
        y = widget.winfo_rooty() + widget.winfo_height() + y_offset

        monitor_x, monitor_y, monitor_width, monitor_height = self._current_monitor_geometry(
            use_work_area=True
        )
        max_x = monitor_x + monitor_width - dialog_width
        max_y = monitor_y + monitor_height - dialog_height
        if max_x >= monitor_x:
            x = min(max(x, monitor_x), max_x)
        else:
            x = monitor_x
        if max_y >= monitor_y:
            y = min(max(y, monitor_y), max_y)
        else:
            y = monitor_y

        self._apply_native_window_chrome(dialog)
        self._move_window_to(dialog, x, y)
        dialog.lift(self.root)

    def _reveal_dialog(self, dialog, anchor=None, focus=False):
        anchor = anchor or self.root
        alpha_supported = False
        try:
            dialog.attributes("-alpha", 0.0)
            alpha_supported = True
        except (tk.TclError, RuntimeError):
            pass

        dialog.deiconify()
        self._apply_native_window_chrome(dialog)
        dialog.lift(anchor)
        try:
            dialog.update_idletasks()
            dialog.update()
        except (tk.TclError, RuntimeError):
            pass
        if focus:
            try:
                dialog.focus_set()
            except (tk.TclError, RuntimeError):
                pass
        if alpha_supported:
            try:
                dialog.attributes("-alpha", 1.0)
            except (tk.TclError, RuntimeError):
                pass

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
        app_dialogs.open_about_dialog(
            self,
            APP_VERSION,
            self._release_date_text(),
            APP_AUTHOR,
            APP_EMAIL,
            APP_PHONE,
        )

    def check_for_updates(self, timeout=10):
        return updater.check_for_updates(APP_VERSION, timeout=timeout)

    def download_update_installer(self, release, timeout=30):
        return updater.download_installer(release, timeout=timeout)

    def launch_update_installer(self, installer_path):
        updater.launch_installer(installer_path)

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
        self._update_online_controls_state()
        self._schedule_connectivity_check()

    def _update_aladin_button_state(self):
        if self.aladin_button is None:
            return

        is_offline = self.network_online is False
        self.aladin_button.config(
            state=tk.DISABLED if is_offline else tk.NORMAL,
            cursor="arrow" if is_offline else "hand2",
        )

    def _update_online_controls_state(self):
        is_offline = self.network_online is False
        if self.combo_box is not None:
            self._set_object_type_values()
        for button in (self.double_search_button, self.double_orbit_recompute_button):
            if button is None:
                continue
            button.config(
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
        self.deep_sky_tab = tk.Frame(self.notebook, bg=self.gbg)
        self.star_search_tab = tk.Frame(self.notebook, bg=self.gbg)

        self.notebook.add(self.main_tab, text=self._tr("tab.main"))
        self.notebook.add(self.visibility_tab, text=self._tr("tab.visibility"))
        self.notebook.add(self.double_star_tab, text=self._tr("tab.double_stars"))
        self.notebook.add(self.deep_sky_tab, text=self._tr("tab.deep_sky"))
        self.notebook.add(self.star_search_tab, text=self._tr("tab.star_search"))
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
        self.deep_sky_tab.grid_columnconfigure(0, weight=0)
        self.deep_sky_tab.grid_columnconfigure(1, weight=1)
        self.deep_sky_tab.grid_rowconfigure(0, weight=1)
        self.star_search_tab.grid_columnconfigure(0, weight=0)
        self.star_search_tab.grid_columnconfigure(1, weight=1)
        self.star_search_tab.grid_rowconfigure(0, weight=1)

    def _on_tab_changed(self, _event=None):
        if self.notebook is None:
            return
        selected_tab = self.notebook.select()
        if selected_tab == str(self.double_star_tab):
            self._ensure_double_star_tab_initialized()
            self._schedule_initial_double_star_load()
        if selected_tab == str(self.deep_sky_tab):
            self._ensure_deep_sky_tab_initialized()
            self._schedule_initial_deep_sky_load()
        if selected_tab == str(self.star_search_tab):
            self._ensure_star_search_tab_initialized()
            self._schedule_initial_star_search_load()
        if self.double_star_tree is not None and selected_tab == str(self.double_star_tab):
            self.root.after_idle(self._update_double_tree_separators)
        if self.deep_sky_tree is not None and selected_tab == str(self.deep_sky_tab):
            self.root.after_idle(self._update_deep_sky_tree_separators)
        if self.star_search_tree is not None and selected_tab == str(self.star_search_tab):
            self.root.after_idle(self._update_star_search_tree_separators)

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
        self.site_info_text.bind("<Configure>", self._schedule_site_info_resize)
        self.lf_long.grid_columnconfigure(0, weight=1)
        self.lf_long.grid_columnconfigure(1, weight=1)
        self.lf_long.grid_rowconfigure(0, weight=1)

    def _schedule_site_info_resize(self, _event=None, delay=90):
        if self.site_info_text is None:
            return
        if self.site_info_resize_job is not None:
            try:
                self.root.after_cancel(self.site_info_resize_job)
            except (tk.TclError, RuntimeError):
                pass
        try:
            self.site_info_resize_job = self.root.after(delay, self._resize_site_info_text)
        except (tk.TclError, RuntimeError):
            self.site_info_resize_job = None

    def _site_info_required_visual_lines(self, lines, font, bold_font, available_width):
        visual_lines = 0
        for index, line in enumerate(lines):
            line_font = bold_font if index == 0 else font
            words = str(line).split(" ")
            if not words:
                visual_lines += 1
                continue

            current_width = 0
            wrapped_lines = 1
            space_width = line_font.measure(" ")
            for word in words:
                word_width = line_font.measure(word)
                if current_width and current_width + space_width + word_width > available_width:
                    wrapped_lines += 1
                    current_width = word_width
                else:
                    current_width += word_width if current_width == 0 else space_width + word_width
            visual_lines += wrapped_lines
        return visual_lines

    def _resize_site_info_text(self):
        self.site_info_resize_job = None
        if self.site_info_text is None or self.site_info_font is None:
            return

        try:
            lines = self.site_info_lines or ("Observing Site",) * 6
            pad_x = int(self.site_info_text.cget("padx"))
            pad_y = int(self.site_info_text.cget("pady"))
            available_width = self.site_info_text.winfo_width() - (pad_x * 2) - 8
            available_height = self.site_info_text.winfo_height() - (pad_y * 2) - 8
        except (tk.TclError, RuntimeError, ValueError):
            return

        if available_width < 40 or available_height < 30:
            return

        target_size = 5
        for candidate_size in range(19, 4, -1):
            candidate_font = Font(family="Segoe UI", size=candidate_size)
            candidate_name_font = Font(family="Segoe UI", size=candidate_size, weight="bold")
            visual_line_count = self._site_info_required_visual_lines(
                lines,
                candidate_font,
                candidate_name_font,
                available_width,
            )
            line_height = max(
                candidate_font.metrics("linespace"),
                candidate_name_font.metrics("linespace"),
            )
            needed_height = visual_line_count * (line_height + 1)
            if needed_height <= available_height:
                target_size = candidate_size
                break

        if self.site_info_font.cget("size") == target_size:
            return
        try:
            self.site_info_font.configure(size=target_size)
            if self.site_info_name_font is not None:
                self.site_info_name_font.configure(size=target_size)
        except (tk.TclError, RuntimeError):
            return

    def _object_type_display(self, object_type_code):
        return self._tr(f"object_type.{object_type_code}")

    def _selected_object_type_code(self):
        selected_label = self.combo_box.get()
        return self.object_type_label_to_code.get(selected_label, selected_label)

    def _set_object_type_values(self, selected_code=None):
        if selected_code is None and hasattr(self, "combo_box"):
            selected_code = self._selected_object_type_code()
        available_codes = (
            (*LOCAL_SOLAR_SYSTEM_OBJECT_TYPE_CODES, *OFFLINE_OBJECT_TYPE_CODES)
            if self.network_online is False
            else OBJECT_TYPE_CODES
        )
        if selected_code not in available_codes:
            selected_code = "Star, Deep Sky Object"

        values = [self._object_type_display(code) for code in available_codes]
        self.object_type_label_to_code = dict(zip(values, available_codes))
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

        self._build_spinbox(self.lf_delta, self.delta_dd, -89, 89, 0)
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
            font=Font(family="Consolas", size=self.coord_font_size, weight="bold"),
            anchor="w",
        )
        label.grid(column=column, row=row, padx=(0, 7), pady=7, sticky="w")
        self.coordinate_unit_labels.append(label)
        return label

    def _schedule_dynamic_font_update(self, _event=None, delay=90):
        if self.dynamic_font_update_job is not None:
            try:
                self.root.after_cancel(self.dynamic_font_update_job)
            except (tk.TclError, RuntimeError):
                pass
        try:
            self.dynamic_font_update_job = self.root.after(delay, self._update_dynamic_fonts)
        except (tk.TclError, RuntimeError):
            self.dynamic_font_update_job = None

    def _update_dynamic_fonts(self):
        self.dynamic_font_update_job = None
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
            for spinbox in getattr(self, "coordinate_spinboxes", ()):
                spinbox.config(font=spinbox_font)
            for label in getattr(self, "coordinate_unit_labels", ()):
                label.config(font=spinbox_font)

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
        self.sky_canvas.bind("<Configure>", self._schedule_sky_map_resize)
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
        self.lf_visibility.grid_rowconfigure(0, weight=0)
        self.lf_visibility.grid_rowconfigure(1, weight=1)
        self.lf_visibility.grid_rowconfigure(2, weight=0)

        visibility_controls = tk.Frame(self.lf_visibility, bg=self.card_bg)
        visibility_controls.grid(column=0, row=0, padx=8, pady=(6, 0), sticky="ew")
        visibility_controls.grid_columnconfigure(4, weight=1)

        self.visibility_date_var = tk.StringVar(value="")
        self.visibility_previous_button = self._build_button(
            visibility_controls,
            self._tr("visibility.previous_day"),
            lambda: self._shift_visibility_window(-1),
        )
        self.visibility_previous_button.grid(column=0, row=0, padx=(0, 6), sticky="w")
        self.visibility_next_button = self._build_button(
            visibility_controls,
            self._tr("visibility.next_day"),
            lambda: self._shift_visibility_window(1),
        )
        self.visibility_next_button.grid(column=1, row=0, padx=(0, 12), sticky="w")
        self.visibility_calendar_button = self._build_button(
            visibility_controls,
            self._tr("visibility.pick_date"),
            self._open_visibility_calendar,
        )
        self.visibility_calendar_button.grid(column=2, row=0, padx=(0, 8), sticky="w")
        tk.Label(
            visibility_controls,
            textvariable=self.visibility_date_var,
            bg=self.card_bg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=10, weight="bold"),
            anchor="w",
        ).grid(column=3, row=0, sticky="w")

        self.visibility_canvas = tk.Canvas(
            self.lf_visibility,
            bg=self.ebg,
            highlightthickness=0,
            bd=0,
        )
        self.visibility_canvas.grid(column=0, row=1, padx=8, pady=8, sticky="nsew")
        self.visibility_canvas.bind("<Configure>", self._schedule_visibility_chart_resize)
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
        self.visibility_status.grid(column=0, row=2, padx=8, pady=(2, 8), sticky="ew")

    def _schedule_sky_map_resize(self, _event=None, delay=110):
        if self.sky_map_resize_job is not None:
            try:
                self.root.after_cancel(self.sky_map_resize_job)
            except (tk.TclError, RuntimeError):
                pass
        try:
            self.sky_map_resize_job = self.root.after(delay, self._update_sky_map_from_resize)
        except (tk.TclError, RuntimeError):
            self.sky_map_resize_job = None

    def _update_sky_map_from_resize(self):
        self.sky_map_resize_job = None
        try:
            self._update_sky_map()
        except (tk.TclError, RuntimeError):
            return

    def _schedule_visibility_chart_resize(self, _event=None, delay=110):
        if self.visibility_chart_resize_job is not None:
            try:
                self.root.after_cancel(self.visibility_chart_resize_job)
            except (tk.TclError, RuntimeError):
                pass
        try:
            self.visibility_chart_resize_job = self.root.after(
                delay,
                self._update_visibility_chart_from_resize,
            )
        except (tk.TclError, RuntimeError):
            self.visibility_chart_resize_job = None

    def _update_visibility_chart_from_resize(self):
        self.visibility_chart_resize_job = None
        try:
            self._update_visibility_chart()
        except (tk.TclError, RuntimeError):
            return

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
        self.double_transit_night_var = tk.BooleanVar(value=self.settings.double_transit_night)
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

        def add_filter(parent, row, key, variable, column=0, columnspan=1):
            label = tk.Label(
                parent,
                bg=self.card_bg,
                fg=self.text,
                font=Font(family="Segoe UI", size=10),
                anchor="w",
            )
            self._register_translated_widget(label, key)
            label.grid(column=column, row=row, columnspan=columnspan, sticky="ew", pady=(6, 2))
            entry = tk.Entry(
                parent,
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
            entry.grid(column=column, row=row + 1, columnspan=columnspan, sticky="ew")
            entry.bind("<Return>", lambda _event: self.search_double_stars(allow_online=False))
            entry.bind("<FocusOut>", self._save_double_filters_if_valid)
            return entry

        add_filter(controls, 1, "double.max_primary", self.double_mag_primary_var)
        add_filter(controls, 3, "double.max_secondary", self.double_mag_secondary_var)

        separation_frame = tk.Frame(controls, bg=self.card_bg)
        separation_frame.grid(column=0, row=5, sticky="ew")
        separation_frame.grid_columnconfigure(0, weight=1)
        separation_frame.grid_columnconfigure(1, weight=1)
        add_filter(separation_frame, 0, "double.min_sep", self.double_min_sep_var, column=0)
        add_filter(separation_frame, 0, "double.max_sep", self.double_max_sep_var, column=1)

        add_filter(controls, 6, "double.min_max_altitude", self.double_min_altitude_var)

        self._register_translated_widget(
            self._build_inline_checkbutton(
                controls,
                self.double_visible_night_var,
                self._tr("double.visible_night"),
                self._save_double_filters_if_valid,
            ),
            "double.visible_night",
        ).grid(column=0, row=8, pady=(12, 0), sticky="ew")

        self.double_advanced_button = self._build_button(
            controls,
            self._double_advanced_button_text(),
            self._toggle_double_advanced_options,
        )
        self.double_advanced_button.grid(column=0, row=9, pady=(10, 0), sticky="ew")

        self.double_advanced_frame = tk.Frame(controls, bg=self.card_bg)
        self.double_advanced_frame.grid_columnconfigure(0, weight=1)
        self._register_translated_widget(
            self._build_inline_checkbutton(
                self.double_advanced_frame,
                self.double_transit_night_var,
                self._tr("double.transit_night"),
                self._save_double_filters_if_valid,
            ),
            "double.transit_night",
        ).grid(column=0, row=0, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                self.double_advanced_frame,
                self.double_include_physical_var,
                self._tr("double.include_physical"),
                self._save_double_filters_if_valid,
            ),
            "double.include_physical",
        ).grid(column=0, row=1, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                self.double_advanced_frame,
                self.double_include_noted_var,
                self._tr("double.include_noted"),
                self._save_double_filters_if_valid,
            ),
            "double.include_noted",
        ).grid(column=0, row=2, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                self.double_advanced_frame,
                self.double_include_apparent_var,
                self._tr("double.include_apparent"),
                self._save_double_filters_if_valid,
            ),
            "double.include_apparent",
        ).grid(column=0, row=3, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                self.double_advanced_frame,
                self.double_include_uncertain_var,
                self._tr("double.include_uncertain"),
                self._save_double_filters_if_valid,
            ),
            "double.include_uncertain",
        ).grid(column=0, row=4, pady=(4, 0), sticky="ew")
        self._register_translated_widget(
            self._build_inline_checkbutton(
                self.double_advanced_frame,
                self.double_exclude_polar_circle_var,
                self._tr("double.exclude_polar_circle"),
                self._save_double_filters_if_valid,
            ),
            "double.exclude_polar_circle",
        ).grid(column=0, row=5, pady=(4, 0), sticky="ew")

        self.double_apply_button = self._build_button(
            controls,
            self._tr("double.apply_filters"),
            lambda: self.search_double_stars(allow_online=False),
        )
        self.double_apply_button.grid(column=0, row=11, pady=(14, 6), sticky="ew")

        self.double_search_button = self._build_button(
            controls,
            self._tr("double.online_search"),
            lambda: self.search_double_stars(allow_online=True),
        )
        self.double_search_button.grid(column=0, row=12, pady=(0, 6), sticky="ew")

        self.double_orbit_recompute_button = self._build_button(
            controls,
            self._tr("double.recalculate_orbits"),
            lambda: self.search_double_stars(allow_online=False, refresh_orbits=True),
        )
        self.double_orbit_recompute_button.grid(column=0, row=13, pady=(0, 8), sticky="ew")

        self.double_set_button = self._build_button(
            controls,
            self._tr("double.set_target"),
            self.set_selected_double_star_target,
        )
        self.double_set_button.grid(column=0, row=14, pady=(0, 6), sticky="ew")

        self.double_clear_cache_button = self._build_button(
            controls,
            self._tr("button.clear_cache"),
            self.clear_double_star_cache,
        )
        self.double_clear_cache_button.grid(column=0, row=15, pady=(0, 6), sticky="ew")

        self.double_reset_button = self._build_button(
            controls,
            self._tr("double.reset_filters"),
            self.reset_double_star_filters,
        )
        self.double_reset_button.grid(column=0, row=16, pady=(0, 12), sticky="ew")

        self.double_status_label = tk.Label(
            controls,
            bg=self.card_bg,
            fg=self.muted,
            font=Font(family="Segoe UI", size=9),
            justify="left",
            wraplength=220,
            anchor="nw",
        )
        self.double_status_label.grid(column=0, row=17, sticky="ew")

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
            "transit_time",
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
            lambda _event: self._schedule_double_tree_separator_refresh(),
        )
        self.double_star_tree.bind("<ButtonRelease-1>", self._on_double_tree_click)
        self.double_star_tree.bind(
            "<B1-Motion>",
            lambda _event: self._schedule_double_tree_separator_refresh(),
        )
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
            "transit_time": 82,
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
            "transit_time": 74,
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
        if self.double_status_label is not None:
            self.double_status_label.config(text=self._tr("double.loading_objects"))


    def _double_advanced_button_text(self):
        key = (
            "double.advanced_options_hide"
            if self.double_advanced_options_visible
            else "double.advanced_options_show"
        )
        return self._tr(key)

    def _toggle_double_advanced_options(self):
        self.double_advanced_options_visible = not self.double_advanced_options_visible
        if self.double_advanced_frame is not None:
            if self.double_advanced_options_visible:
                self.double_advanced_frame.grid(column=0, row=10, sticky="ew", pady=(4, 0))
            else:
                self.double_advanced_frame.grid_remove()
        if self.double_advanced_button is not None:
            self.double_advanced_button.config(text=self._double_advanced_button_text())

    def _restore_double_star_cached_results(self):
        stars = []
        for star in self._double_local_catalog():
            cached_star = dict(star)
            cached_star["coordinate_frame"] = "j2000"
            stars.append(cached_star)
        source_key = "double.source.wds" if self.double_wds_cached_stars else "double.source.local"
        note = self._tr(
            "double.cache_restored",
            count=len(self.double_wds_cached_stars),
        )
        self._render_double_star_results(stars, len(stars), source_key, note)

    def _ensure_double_star_tab_initialized(self):
        if self.double_star_tab_initialized:
            return
        self._create_double_star_widgets()
        self.double_star_tab_initialized = True



    def _schedule_initial_double_star_load(self):
        if self.double_star_initial_load_started:
            return
        self.double_star_initial_load_started = True
        self.root.after(120, self._restore_double_star_cached_results)



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

    def _format_local_date(self, date_value):
        return date_value.strftime("%d/%m/%Y" if self.language == "fr" else "%Y-%m-%d")

    def _target_display_label(self):
        return self.target_display_name or self._tr("sky.target")

    def _default_visibility_start_date(self, now_utc=None):
        now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
        local_now = self._local_datetime_from_utc(now_utc)
        local_noon = local_now.replace(hour=12, minute=0, second=0, microsecond=0)
        if local_now < local_noon:
            local_noon -= datetime.timedelta(days=1)
        return local_noon.date()

    def _visibility_start_utc_for_date(self, start_date):
        approximate_noon_utc = datetime.datetime.combine(
            start_date,
            datetime.time(12, 0),
            tzinfo=datetime.timezone.utc,
        )
        try:
            offset = self._configured_timezone_offset(approximate_noon_utc)
        except ValueError:
            offset = None
        if offset is None:
            offset = self._local_datetime_from_utc(approximate_noon_utc).utcoffset()
        offset = offset or datetime.timedelta()
        local_noon = datetime.datetime.combine(
            start_date,
            datetime.time(12, 0),
            tzinfo=datetime.timezone(offset),
        )
        return local_noon.astimezone(datetime.timezone.utc)

    def _set_visibility_start_date(self, start_date):
        self.visibility_start_date = start_date
        self.visibility_cache_key = None
        self._update_visibility_date_label()
        self._update_visibility_chart()

    def _shift_visibility_window(self, days):
        start_date = self.visibility_start_date or self._default_visibility_start_date()
        self._set_visibility_start_date(start_date + datetime.timedelta(days=days))

    def _update_visibility_date_label(self, start_date=None):
        if self.visibility_date_var is None:
            return
        start_date = start_date or self.visibility_start_date or self._default_visibility_start_date()
        end_date = start_date + datetime.timedelta(days=1)
        self.visibility_date_var.set(
            self._tr(
                "visibility.date_range",
                start_date=self._format_local_date(start_date),
                end_date=self._format_local_date(end_date),
            )
        )

    def _open_visibility_calendar(self):
        app_dialogs.open_visibility_calendar(self)

    def _visibility_window_context(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        local_date = self.visibility_start_date or self._default_visibility_start_date(now_utc)
        start_utc = self._visibility_start_utc_for_date(local_date)
        raw_offset_hours = (now_utc - start_utc).total_seconds() / 3600
        self._update_visibility_date_label(local_date)
        return start_utc, max(0, min(24, raw_offset_hours)), local_date, 0 <= raw_offset_hours <= 24

    def _visibility_time_label(self, start_utc, offset_hours):
        state = self._clock_state_at_time(
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
        state = self._clock_state_at_time(now_utc=sample_time)
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

    def _visibility_samples_for_solar_body(self, body_name, start_utc):
        offsets = [step / 12 for step in range(289)]
        utc_datetimes = [
            start_utc + datetime.timedelta(hours=offset)
            for offset in offsets
        ]
        positions = compute_solar_system_body_positions(
            body_name,
            self.latitude,
            self.longitude,
            utc_datetimes,
        )
        if not positions:
            return []
        return [
            self._visibility_sample_from_position(position, sample_time, offset)
            for position, sample_time, offset in zip(positions, utc_datetimes, offsets)
        ]

    def _curve_extreme_sample(self, samples, start_utc, find_max=True):
        if not samples:
            return None

        selector = max if find_max else min
        best_index = selector(
            range(len(samples)),
            key=lambda index: samples[index]["altitude"],
        )
        if best_index == 0 or best_index == len(samples) - 1:
            return samples[best_index]

        previous_sample = samples[best_index - 1]
        best_sample = samples[best_index]
        next_sample = samples[best_index + 1]
        y_previous = previous_sample["altitude"]
        y_best = best_sample["altitude"]
        y_next = next_sample["altitude"]
        curvature = y_previous - (2 * y_best) + y_next
        if abs(curvature) < 1e-9:
            return best_sample
        if (find_max and curvature >= 0) or (not find_max and curvature <= 0):
            return best_sample

        relative_offset = 0.5 * (y_previous - y_next) / curvature
        if not -1 <= relative_offset <= 1:
            return best_sample

        step_hours = best_sample["offset_hours"] - previous_sample["offset_hours"]
        peak_offset = best_sample["offset_hours"] + (relative_offset * step_hours)
        peak_sample = self._interpolated_visibility_sample(samples, start_utc, peak_offset)
        if peak_sample is None:
            return best_sample
        peak_sample["altitude"] = y_best - (0.25 * (y_previous - y_next) * relative_offset)
        return peak_sample

    def _interpolated_visibility_sample(self, samples, start_utc, offset_hours):
        if not samples:
            return None

        bounded_offset = max(0, min(24, offset_hours))
        if bounded_offset <= samples[0]["offset_hours"]:
            base = dict(samples[0])
            base["offset_hours"] = bounded_offset
            base["utc"] = start_utc + datetime.timedelta(hours=bounded_offset)
            return base
        if bounded_offset >= samples[-1]["offset_hours"]:
            base = dict(samples[-1])
            base["offset_hours"] = bounded_offset
            base["utc"] = start_utc + datetime.timedelta(hours=bounded_offset)
            return base

        previous_sample = samples[0]
        next_sample = samples[-1]
        for first, second in zip(samples, samples[1:]):
            if first["offset_hours"] <= bounded_offset <= second["offset_hours"]:
                previous_sample = first
                next_sample = second
                break

        span = next_sample["offset_hours"] - previous_sample["offset_hours"]
        ratio = 0 if span == 0 else (bounded_offset - previous_sample["offset_hours"]) / span

        def interpolate(key):
            return previous_sample[key] + (next_sample[key] - previous_sample[key]) * ratio

        sample_time = start_utc + datetime.timedelta(hours=bounded_offset)
        result = {
            "offset_hours": bounded_offset,
            "altitude": interpolate("altitude"),
            "azimuth": interpolate("azimuth"),
            "utc": sample_time,
        }
        if "ra_hours" in previous_sample and "ra_hours" in next_sample:
            ra_hours = interpolate("ra_hours")
            declination = interpolate("declination")
            _state, lst_hours = self._visibility_state_at_time(sample_time)
            result["ra_hours"] = ra_hours
            result["declination"] = declination
            result["hour_angle"] = self._normalize_hour_angle(lst_hours - ra_hours)
        else:
            result["hour_angle"] = interpolate("hour_angle")
        return result

    def _refine_visibility_extreme(self, ra_hours, declination, samples, find_max=True):
        if not samples:
            return None

        selector = max if find_max else min
        best_index = selector(
            range(len(samples)),
            key=lambda index: samples[index]["altitude"],
        )
        if self.target_solar_system_name:
            return samples[best_index]

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

    def _start_visibility_chart_compute(
        self,
        cache_key,
        width,
        height,
        ra_hours,
        declination,
        start_utc,
        current_offset_hours,
        local_date,
        current_in_window,
        body_name,
    ):
        self.visibility_compute_generation += 1
        generation = self.visibility_compute_generation
        self.visibility_compute_pending = True
        self.visibility_cache_key = ("pending", cache_key)
        has_previous_chart = bool(self.visibility_curve_points and self.visibility_chart_geometry)
        if has_previous_chart:
            self.visibility_canvas.delete("visibility-hover")
        else:
            self.visibility_curve_points = []
            self.visibility_chart_geometry = None
            self.visibility_canvas.delete("all")
            self.visibility_canvas.create_text(
                width / 2,
                height / 2,
                text=self._tr("visibility.calculating"),
                fill=self.muted,
                font=Font(family="Segoe UI", size=13, weight="bold"),
            )
        self._set_visibility_status(self._tr("visibility.calculating"))
        threading.Thread(
            target=self._run_visibility_chart_compute,
            args=(
                generation,
                cache_key,
                width,
                height,
                ra_hours,
                declination,
                start_utc,
                current_offset_hours,
                local_date,
                current_in_window,
                body_name,
            ),
            daemon=True,
        ).start()

    def _run_visibility_chart_compute(
        self,
        generation,
        cache_key,
        width,
        height,
        ra_hours,
        declination,
        start_utc,
        current_offset_hours,
        local_date,
        current_in_window,
        body_name,
    ):
        try:
            samples = self._visibility_samples_for_solar_body(body_name, start_utc)
            max_sample = self._curve_extreme_sample(samples, start_utc, find_max=True)
            current_sample = self._interpolated_visibility_sample(
                samples,
                start_utc,
                current_offset_hours,
            )
            error = None
        except Exception as exc:
            samples = []
            max_sample = None
            current_sample = None
            error = str(exc)

        try:
            self.root.after(
                0,
                lambda: self._apply_visibility_chart_compute(
                    generation,
                    cache_key,
                    width,
                    height,
                    start_utc,
                    current_offset_hours,
                    local_date,
                    current_in_window,
                    samples,
                    max_sample,
                    current_sample,
                    error,
                ),
            )
        except (tk.TclError, RuntimeError):
            self.visibility_compute_pending = False

    def _apply_visibility_chart_compute(
        self,
        generation,
        cache_key,
        width,
        height,
        start_utc,
        current_offset_hours,
        local_date,
        current_in_window,
        samples,
        max_sample,
        current_sample,
        error,
    ):
        if generation != self.visibility_compute_generation:
            return
        self.visibility_compute_pending = False
        if error is not None:
            self.visibility_cache_key = None
            self._set_visibility_status(self._tr("sky.unavailable", error=error))
            return
        if cache_key[0] != self.visibility_canvas.winfo_width() or cache_key[1] != self.visibility_canvas.winfo_height():
            self.visibility_cache_key = None
            self._schedule_visibility_chart_resize(delay=10)
            return
        if max_sample is None or current_sample is None:
            self.visibility_cache_key = None
            return
        self.visibility_cache_key = cache_key
        self._draw_visibility_chart_result(
            width,
            height,
            start_utc,
            current_offset_hours,
            local_date,
            current_in_window,
            samples,
            max_sample,
            current_sample,
        )

    def _draw_visibility_chart_result(
        self,
        width,
        height,
        start_utc,
        current_offset_hours,
        local_date,
        current_in_window,
        samples,
        max_sample,
        current_sample,
    ):
        curve_samples = self._visibility_samples_with_extrema(samples, max_sample, current_sample)
        maximum_time = self._visibility_time_label(start_utc, max_sample["offset_hours"])
        target_label = self._target_display_label()
        end_date = local_date + datetime.timedelta(days=1)
        start_date_text = self._format_local_date(local_date)
        end_date_text = self._format_local_date(end_date)
        title_text = self._tr(
            "visibility.title_named",
            target=target_label,
            start_date=start_date_text,
            end_date=end_date_text,
        )

        canvas = self.visibility_canvas
        canvas.delete("all")
        margin_left = 58
        margin_right = 24
        margin_top = 50
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
            "current_in_window": current_in_window,
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
            past_until_offset=current_offset_hours if current_in_window else None,
        )

        current_altitude = current_sample["altitude"]
        if current_in_window:
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
            canvas.create_oval(
                max_x - 4,
                max_y - 4,
                max_x + 4,
                max_y + 4,
                fill=self.fg,
                outline="",
            )
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
            16,
            text=title_text,
            fill=self.text,
            font=Font(family="Segoe UI", size=11, weight="bold"),
            anchor="w",
            width=plot_width,
        )
        canvas.create_text(
            plot_right,
            plot_top - 8,
            text=self._tr("visibility.axis"),
            fill=self.muted,
            font=Font(family="Segoe UI", size=9),
            anchor="e",
        )

        status_key = (
            "visibility.status_named"
            if current_in_window
            else "visibility.status_named_window"
        )
        self._set_visibility_status(
            self._tr(
                status_key,
                target=target_label,
                start_date=start_date_text,
                end_date=end_date_text,
                current=current_altitude,
                maximum=max_sample["altitude"],
                maximum_time=maximum_time,
            )
        )
        self._update_visibility_hover()

    def _update_visibility_chart(self, state=None):
        if self.visibility_canvas is None or self.visibility_status is None:
            return

        width = self.visibility_canvas.winfo_width()
        height = self.visibility_canvas.winfo_height()
        if width < 120 or height < 120:
            return
        self._update_visibility_date_label()

        if not self.target_active:
            cache_key = ("inactive", width, height, self.language)
            if cache_key == self.visibility_cache_key:
                return
            if self.visibility_compute_pending:
                self.visibility_compute_generation += 1
                self.visibility_compute_pending = False
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
        start_utc, current_offset_hours, local_date, current_in_window = (
            self._visibility_window_context()
        )
        minute_bucket = int(time.time() // 60)
        cache_key = (
            width,
            height,
            minute_bucket,
            local_date.isoformat(),
            self.timezone_name,
            self.daylight_saving_enabled,
            self.target_solar_system_name,
            self._target_display_label(),
            round(ra_hours, 5),
            round(declination, 5),
            round(self.latitude, 5),
            round(self.longitude, 5),
        )
        if cache_key == self.visibility_cache_key:
            return

        if self.target_solar_system_name:
            pending_key = ("pending", cache_key)
            if self.visibility_compute_pending and self.visibility_cache_key == pending_key:
                return
            self._start_visibility_chart_compute(
                cache_key,
                width,
                height,
                ra_hours,
                declination,
                start_utc,
                current_offset_hours,
                local_date,
                current_in_window,
                self.target_solar_system_name,
            )
            return

        if self.visibility_compute_pending:
            self.visibility_compute_generation += 1
            self.visibility_compute_pending = False
        self.visibility_cache_key = cache_key
        samples = self._visibility_samples(ra_hours, declination, start_utc)
        max_sample = self._refine_visibility_extreme(ra_hours, declination, samples, find_max=True)
        current_sample = self._visibility_sample_at_offset(
            ra_hours,
            declination,
            start_utc,
            current_offset_hours,
        )
        if max_sample is None or current_sample is None:
            return
        self._draw_visibility_chart_result(
            width,
            height,
            start_utc,
            current_offset_hours,
            local_date,
            current_in_window,
            samples,
            max_sample,
            current_sample,
        )

    def _current_input_coordinates(self):
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

    def _current_target_coordinates(self, now_utc=None):
        ra_hours, dec_degrees = self._current_input_coordinates()
        utc_key = None
        if now_utc is not None:
            utc_key = now_utc.astimezone(datetime.timezone.utc).strftime("%Y-%m-%dT%H")
        cache_key = (
            round(ra_hours, 8),
            round(dec_degrees, 8),
            utc_key,
        )
        if cache_key != self.target_jnow_cache_key:
            self.target_jnow_cache_key = cache_key
            self.target_jnow_cache = j2000_to_jnow_coordinates(
                ra_hours,
                dec_degrees,
                now_utc=now_utc,
            )
        return self.target_jnow_cache

    def _current_jnow_coordinate_fields(self, now_utc=None):
        ra_hours, dec_degrees = self._current_target_coordinates(now_utc=now_utc)
        return self._coordinates_to_fields(ra_hours, dec_degrees)

    def _clock_state_at_time(self, now_utc=None, alpha_fields=(0, 0, 0)):
        alpha_hh, alpha_mm, alpha_ss = alpha_fields
        return compute_clock_state(
            self.longitude,
            alpha_hh,
            alpha_mm,
            alpha_ss,
            hour_angle_offset_hours=6 if self.hour_angle_offset_enabled else 0,
            timezone_name=self.timezone_name,
            daylight_saving_enabled=self.daylight_saving_enabled,
            now_utc=now_utc,
        )

    def _compute_target_clock_state(self, now_utc=None):
        alpha_hh, alpha_mm, alpha_ss, _delta_dd, _delta_mm, _delta_ss = (
            self._current_jnow_coordinate_fields(now_utc=now_utc)
        )
        return self._clock_state_at_time(
            now_utc=now_utc,
            alpha_fields=(alpha_hh, alpha_mm, alpha_ss),
        )

    def _normalize_hour_angle(self, hours):
        return ((hours + 12) % 24) - 12

    def _display_hour_angle(self, ra_hours, lst_hours=None):
        if lst_hours is None and self.sky_geometry is not None:
            lst_hours = self.sky_geometry.get("lst_hours")
        if lst_hours is None:
            _state, lst_hours = self._visibility_state_at_time(
                datetime.datetime.now(datetime.timezone.utc)
            )
        return (lst_hours - ra_hours) % 24

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

    def _sky_star_color(self, name, magnitude):
        if name in NAMED_STAR_COLORS:
            fill = NAMED_STAR_COLORS[name]
        elif magnitude < 0.5:
            fill = "#fff4c7"
        elif magnitude < 2.5:
            fill = "#d7eaff"
        else:
            fill = "#9fb2c3"
        return fill, self._hex_to_rgb(fill)

    def _sky_star_style(self, name, magnitude):
        fill, rgb = self._sky_star_color(name, magnitude)
        if self.sky_sprite_cache is None:
            return None, fill, rgb, max(1.2, 2.8 - min(2.0, magnitude * 0.25))

        self.sky_sprite_cache.configure(magnitude_limit=self.sky_magnitude_limit)
        style = self.sky_sprite_cache.style_for(fill, rgb, magnitude)
        return style, fill, rgb, style.canvas_size

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

    def _draw_solar_system_canvas(self, canvas, solar_objects):
        for sky_object in solar_objects:
            x = sky_object["x"]
            y = sky_object["y"]
            size = sky_object["size"]
            canvas.create_oval(
                x - size,
                y - size,
                x + size,
                y + size,
                fill=sky_object["hover_color"],
                outline=self.ebg,
                width=1,
            )

    def _draw_solar_system_label(self, canvas, sky_object):
        canvas.create_text(
            sky_object["x"] + 7,
            sky_object["y"] - 7,
            text=sky_object["label"],
            fill=sky_object["hover_color"],
            font=Font(family="Segoe UI", size=8, weight="bold"),
            anchor="w",
        )

    def _draw_sky_object_labels(self, canvas, stars, solar_objects):
        for star in stars:
            if star["magnitude"] <= SKY_STAR_LABEL_MAX_MAGNITUDE:
                self._draw_star_label(canvas, star)
        for sky_object in solar_objects:
            self._draw_solar_system_label(canvas, sky_object)

    def _draw_sky_objects_raster(self, canvas, stars, solar_objects, considered_count):
        if Image is None or ImageTk is None or self.sky_sprite_cache is None:
            return False

        width = int(canvas.winfo_width())
        height = int(canvas.winfo_height())
        if width <= 0 or height <= 0:
            return False

        started_at = time.perf_counter()
        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        drawn = 0
        for star in stars:
            sprite = star.get("sprite")
            if sprite is not None and self.sky_sprite_cache.composite_sprite(image, sprite, star["x"], star["y"]):
                drawn += 1

        outline_rgb = self._hex_to_rgb(self.ebg)
        for sky_object in solar_objects:
            size = sky_object["size"]
            outline = self.sky_sprite_cache.sprite_for(outline_rgb, size + 1, 168)
            sprite = self.sky_sprite_cache.sprite_for(sky_object["rgb"], size, 255)
            self.sky_sprite_cache.composite_sprite(image, outline, sky_object["x"], sky_object["y"])
            if self.sky_sprite_cache.composite_sprite(image, sprite, sky_object["x"], sky_object["y"]):
                drawn += 1

        self.sky_star_image = ImageTk.PhotoImage(image)
        canvas.create_image(0, 0, image=self.sky_star_image, anchor="nw")
        self.sky_render_stats = StarRenderStats(
            considered=considered_count,
            projected=len(stars),
            drawn=drawn,
            render_ms=(time.perf_counter() - started_at) * 1000,
            sprite_cache_size=self.sky_sprite_cache.sprite_count,
        )
        if SKY_RENDER_DEBUG:
            print(
                "sky-render "
                f"considered={self.sky_render_stats.considered} "
                f"projected={self.sky_render_stats.projected} "
                f"drawn={self.sky_render_stats.drawn} "
                f"sprites={self.sky_render_stats.sprite_cache_size} "
                f"ms={self.sky_render_stats.render_ms:.2f}"
            )
        return True

    def _collect_star_catalog(self, center_x, center_y, radius, lst_hours):
        self.sky_star_points = []
        stars_to_draw = []
        considered_count = 0
        for name, ra_hours, declination, magnitude in self.named_stars_jnow:
            if magnitude > self.sky_magnitude_limit:
                break
            considered_count += 1

            altitude, azimuth, hour_angle = self._equatorial_to_horizontal(
                ra_hours,
                declination,
                lst_hours,
            )
            point = self._project_horizontal_point(center_x, center_y, radius, altitude, azimuth)
            if point is None:
                continue

            x, y = point
            style, fill, rgb, canvas_size = self._sky_star_style(name, magnitude)
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
                "sprite": style.sprite if style is not None else None,
                "sprite_radius": style.radius_px if style is not None else canvas_size,
                "sprite_alpha": style.alpha if style is not None else 255,
            }
            self.sky_star_points.append(star)
            stars_to_draw.append(star)

        return stars_to_draw, considered_count

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

    def _collect_solar_system_objects(self, center_x, center_y, radius, lst_hours):
        self.sky_solar_system_points = []
        if not self.sky_show_solar_system:
            return []

        solar_objects = []
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
            size = 12 if name in {"Sun", "Moon"} else 5
            sky_object = {
                "name": name,
                "label": label,
                "kind": "solar",
                "hover_color": fill,
                "rgb": self._hex_to_rgb(fill),
                "x": x,
                "y": y,
                "ra_hours": body["ra_hours"],
                "declination": body["declination"],
                "altitude": altitude,
                "azimuth": azimuth,
                "hour_angle": hour_angle,
                "size": size,
            }
            self.sky_solar_system_points.append(sky_object)
            solar_objects.append(sky_object)

        return solar_objects

    def _draw_target_marker(self, canvas, center_x, center_y, radius, altitude, azimuth, label):
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
            text=label,
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
        hour_angle=None,
    ):
        return (
            f"JNow : RA = {self._format_unsigned_hms_compact(ra_hours)} ; "
            f"DEC = {self._format_signed_dms_compact(declination)} | "
            f"Alt = {altitude:+.2f}\N{DEGREE SIGN} ; "
            f"Az = {azimuth:05.1f}\N{DEGREE SIGN} | "
            f"{self._tr('sky.hour_angle_short')} = "
            f"{self._format_unsigned_hms_compact(self._display_hour_angle(ra_hours))}"
        )

    def _coordinates_to_fields(self, ra_hours, dec_degrees):
        total_ra_seconds = int(round((ra_hours % 24) * 3600)) % (24 * 3600)
        alpha_hh = total_ra_seconds // 3600
        alpha_mm = (total_ra_seconds % 3600) // 60
        alpha_ss = total_ra_seconds % 60

        max_declination = 89 + (59 / 60) + (59 / 3600)
        dec_degrees = max(-max_declination, min(max_declination, dec_degrees))
        total_dec_seconds = int(round(abs(dec_degrees) * 3600))
        total_dec_seconds = min(total_dec_seconds, (89 * 3600) + (59 * 60) + 59)
        delta_dd = total_dec_seconds // 3600
        delta_mm = (total_dec_seconds % 3600) // 60
        delta_ss = total_dec_seconds % 60
        if dec_degrees < 0:
            delta_dd = "-0" if delta_dd == 0 else -delta_dd

        return alpha_hh, alpha_mm, alpha_ss, delta_dd, delta_mm, delta_ss

    def _set_coordinate_fields(self, ra_hours, dec_degrees, frame="jnow"):
        if frame == "jnow":
            ra_hours, dec_degrees = jnow_to_j2000_coordinates(ra_hours, dec_degrees)
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

    def _set_target_from_coordinates(
        self,
        ra_hours,
        dec_degrees,
        label,
        solar_system_name=None,
        display_name=None,
    ):
        self.target_active = True
        self.target_solar_system_name = solar_system_name
        self.target_display_name = display_name or self._tr("sky.target")
        self.visibility_start_date = None
        self._update_visibility_date_label()
        self._set_coordinate_fields(ra_hours, dec_degrees)
        j2000_ra_hours, j2000_dec_degrees = jnow_to_j2000_coordinates(ra_hours, dec_degrees)
        self.update_value(preserve_solar_target=solar_system_name is not None)
        self._set_result_text(
            self._tr(
                "result.target_coordinates",
                label=label,
                ra=self._format_ra(j2000_ra_hours),
                dec=self._format_dec(j2000_dec_degrees),
                jnow_ra=self._format_ra(ra_hours),
                jnow_dec=self._format_dec(dec_degrees),
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
                display_name=sky_object.get("label", sky_object["name"]),
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
            display_name=self._tr("sky.target"),
        )

    def _update_sky_map(self, state=None):
        if self.sky_canvas is None or self.sky_status is None:
            return

        width = self.sky_canvas.winfo_width()
        height = self.sky_canvas.winfo_height()
        if width < 80 or height < 80:
            return

        if state is None:
            state = self._compute_target_clock_state()

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
                self._target_display_label(),
            )
        refresh_seconds = (
            SKY_MAP_ANTIALIASED_REFRESH_SECONDS
            if Image is not None and ImageTk is not None
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
        stars_to_draw, considered_count = self._collect_star_catalog(
            center_x, center_y, radius, lst_hours
        )
        solar_objects = self._collect_solar_system_objects(center_x, center_y, radius, lst_hours)
        if not self._draw_sky_objects_raster(
            self.sky_canvas,
            stars_to_draw,
            solar_objects,
            considered_count,
        ):
            self._draw_star_catalog_canvas(self.sky_canvas, stars_to_draw)
            self._draw_solar_system_canvas(self.sky_canvas, solar_objects)
        self._draw_sky_object_labels(self.sky_canvas, stars_to_draw, solar_objects)

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
            self._target_display_label(),
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
            target=self._target_display_label(),
            ha=self._format_unsigned_hms_compact(
                self._display_hour_angle(target_ra_hours, lst_hours)
            ),
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
        old_values = (
            str(self.alpha_hh.get()),
            str(self.alpha_mm.get()),
            str(self.alpha_ss.get()),
            str(self.delta_dd.get()),
            str(self.delta_mm.get()),
            str(self.delta_ss.get()),
        )
        self.alpha_hh.set(self._sanitize_int(self.alpha_hh.get(), 0, 23))
        self.alpha_mm.set(self._sanitize_int(self.alpha_mm.get(), 0, 59))
        self.alpha_ss.set(self._sanitize_int(self.alpha_ss.get(), 0, 59))
        delta_dd, delta_mm, delta_ss = self._sanitize_declination_fields(
            self.delta_dd.get(),
            self.delta_mm.get(),
            self.delta_ss.get(),
        )
        self.delta_dd.set(delta_dd)
        self.delta_mm.set(delta_mm)
        self.delta_ss.set(delta_ss)
        new_values = (
            str(self.alpha_hh.get()),
            str(self.alpha_mm.get()),
            str(self.alpha_ss.get()),
            str(self.delta_dd.get()),
            str(self.delta_mm.get()),
            str(self.delta_ss.get()),
        )
        if new_values != old_values:
            self.target_jnow_cache_key = None

    def _sanitize_declination_fields(self, degrees, minutes, seconds):
        degrees_text = str(degrees).strip()
        try:
            sanitized_degrees = int(degrees_text)
        except ValueError:
            sanitized_degrees = 0

        if sanitized_degrees >= 90:
            return "89", "59", "59"
        if sanitized_degrees <= -90:
            return "-89", "59", "59"

        sanitized_degrees = max(-89, min(89, sanitized_degrees))
        sanitized_minutes = self._sanitize_int(minutes, 0, 59)
        sanitized_seconds = self._sanitize_int(seconds, 0, 59)
        if sanitized_degrees == 0 and degrees_text.startswith("-"):
            sanitized_degrees = "-0"
        return str(sanitized_degrees), sanitized_minutes, sanitized_seconds

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
            ra_hours, dec_deg = self._current_input_coordinates()
            ra_deg = (ra_hours % 24) * 15
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
        self.target_display_name = self._tr("sky.target")
        self.visibility_start_date = None
        self._update_visibility_date_label()
        self.update_value(activate_target=True)

    def update_value(self, activate_target=True, preserve_solar_target=False):
        if activate_target:
            self.target_active = True
            if not preserve_solar_target:
                self.target_solar_system_name = None
                if not self.target_display_name:
                    self.target_display_name = self._tr("sky.target")
        self._sanitize_coordinate_values()
        _alpha_hh, _alpha_mm, _alpha_ss, delta_dd, delta_mm, delta_ss = (
            self._current_jnow_coordinate_fields()
        )
        self.lbl_dec_angle.config(
            text=compute_declination_display(
                delta_dd,
                delta_mm,
                delta_ss,
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
            self.notebook.tab(self.deep_sky_tab, text=self._tr("tab.deep_sky"))
            self.notebook.tab(self.star_search_tab, text=self._tr("tab.star_search"))
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
        if self.double_apply_button is not None:
            self.double_apply_button.config(text=self._tr("double.apply_filters"))
        if self.double_search_button is not None:
            self.double_search_button.config(text=self._tr("double.online_search"))
        if self.double_orbit_recompute_button is not None:
            self.double_orbit_recompute_button.config(text=self._tr("double.recalculate_orbits"))
        if self.double_advanced_button is not None:
            self.double_advanced_button.config(text=self._double_advanced_button_text())
        if self.double_set_button is not None:
            self.double_set_button.config(text=self._tr("double.set_target"))
        if self.double_reset_button is not None:
            self.double_reset_button.config(text=self._tr("double.reset_filters"))
        if self.double_clear_cache_button is not None:
            self.double_clear_cache_button.config(text=self._tr("button.clear_cache"))
        if self.deep_sky_apply_button is not None:
            self.deep_sky_apply_button.config(text=self._tr("deep_sky.apply_filters"))
        if self.deep_sky_online_button is not None:
            self.deep_sky_online_button.config(text=self._tr("deep_sky.online_search"))
        if self.deep_sky_set_button is not None:
            self.deep_sky_set_button.config(text=self._tr("deep_sky.set_target"))
        if self.deep_sky_reset_button is not None:
            self.deep_sky_reset_button.config(text=self._tr("deep_sky.reset_filters"))
        if self.deep_sky_clear_cache_button is not None:
            self.deep_sky_clear_cache_button.config(text=self._tr("button.clear_cache"))
        if self.star_search_apply_button is not None:
            self.star_search_apply_button.config(text=self._tr("star_search.apply_filters"))
        if self.star_search_online_button is not None:
            self.star_search_online_button.config(text=self._tr("star_search.online_search"))
        if self.star_search_set_button is not None:
            self.star_search_set_button.config(text=self._tr("star_search.set_target"))
        if self.star_search_reset_button is not None:
            self.star_search_reset_button.config(text=self._tr("star_search.reset_filters"))
        if self.star_search_clear_cache_button is not None:
            self.star_search_clear_cache_button.config(text=self._tr("button.clear_cache"))
        if self.visibility_previous_button is not None:
            self.visibility_previous_button.config(text=self._tr("visibility.previous_day"))
        if self.visibility_next_button is not None:
            self.visibility_next_button.config(text=self._tr("visibility.next_day"))
        if self.visibility_calendar_button is not None:
            self.visibility_calendar_button.config(text=self._tr("visibility.pick_date"))
        for widget, key, kwargs in self.translated_widgets:
            widget.config(text=self._tr(key, **kwargs))
        self._refresh_double_star_headings()

        for title_label, title_key, title_kwargs in self.labelframe_title_labels:
            title_values = title_kwargs() if callable(title_kwargs) else title_kwargs
            title_label.config(text=self._tr(title_key, **title_values).upper())

        self._set_object_type_values()
        self._set_deep_sky_category_values()
        self._refresh_deep_sky_headings()
        self._refresh_star_search_headings()
        self.update_site_labels()
        self.update_value(
            activate_target=self.target_active,
            preserve_solar_target=self.target_solar_system_name is not None,
        )

    def _save_current_settings(self):
        double_filter_settings = self._current_double_filter_settings()
        deep_sky_filter_settings = self._current_deep_sky_filter_settings()
        star_search_filter_settings = self._current_star_search_filter_settings()
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
            **deep_sky_filter_settings,
            **star_search_filter_settings,
        )
        save_app_settings(self.settings)

    def _current_double_filter_settings(self):
        def read_float(variable_name, current_value):
            variable = getattr(self, variable_name, None)
            if variable is None or not is_float(variable.get()):
                return current_value
            return float(variable.get())

        visible_night_var = getattr(self, "double_visible_night_var", None)
        transit_night_var = getattr(self, "double_transit_night_var", None)
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
            "double_transit_night": (
                transit_night_var.get()
                if transit_night_var is not None
                else self.settings.double_transit_night
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

    def _current_deep_sky_filter_settings(self):
        def read_float(variable_name, current_value):
            variable = getattr(self, variable_name, None)
            if variable is None or not is_float(variable.get()):
                return current_value
            return float(variable.get())

        category = DEFAULT_DEEP_SKY_CATEGORY
        if getattr(self, "deep_sky_category_var", None) is not None:
            category = self.deep_sky_category_label_to_code.get(
                self.deep_sky_category_var.get(),
                getattr(self.settings, "deep_sky_category", DEFAULT_DEEP_SKY_CATEGORY),
            )
        visible_night_var = getattr(self, "deep_sky_visible_night_var", None)
        transit_night_var = getattr(self, "deep_sky_transit_night_var", None)
        exclude_polar_circle_var = getattr(self, "deep_sky_exclude_polar_circle_var", None)
        exclude_suspect_magnitudes_var = getattr(
            self,
            "deep_sky_exclude_suspect_magnitudes_var",
            None,
        )

        return {
            "deep_sky_category": category,
            "deep_sky_min_magnitude": read_float(
                "deep_sky_min_mag_var",
                self.settings.deep_sky_min_magnitude,
            ),
            "deep_sky_max_magnitude": read_float(
                "deep_sky_max_mag_var",
                self.settings.deep_sky_max_magnitude,
            ),
            "deep_sky_min_max_altitude": read_float(
                "deep_sky_min_altitude_var",
                self.settings.deep_sky_min_max_altitude,
            ),
            "deep_sky_visible_night": (
                visible_night_var.get()
                if visible_night_var is not None
                else self.settings.deep_sky_visible_night
            ),
            "deep_sky_transit_night": (
                transit_night_var.get()
                if transit_night_var is not None
                else self.settings.deep_sky_transit_night
            ),
            "deep_sky_exclude_polar_circle": (
                exclude_polar_circle_var.get()
                if exclude_polar_circle_var is not None
                else self.settings.deep_sky_exclude_polar_circle
            ),
            "deep_sky_exclude_suspect_magnitudes": (
                exclude_suspect_magnitudes_var.get()
                if exclude_suspect_magnitudes_var is not None
                else self.settings.deep_sky_exclude_suspect_magnitudes
            ),
            "deep_sky_magnitude_band": self._current_deep_sky_magnitude_band(),
        }

    def _save_deep_sky_filters_if_valid(self, _event=None):
        variables = [self.deep_sky_min_altitude_var]
        if self._deep_sky_uses_magnitude_filter():
            variables.extend((self.deep_sky_min_mag_var, self.deep_sky_max_mag_var))
        if not all(is_float(variable.get()) for variable in variables):
            return
        self._save_current_settings()

    def _current_star_search_filter_settings(self):
        def read_float(variable_name, current_value):
            variable = getattr(self, variable_name, None)
            if variable is None or not is_float(variable.get()):
                return current_value
            return float(variable.get())

        visible_night_var = getattr(self, "star_search_visible_night_var", None)
        transit_night_var = getattr(self, "star_search_transit_night_var", None)
        exclude_polar_circle_var = getattr(self, "star_search_exclude_polar_circle_var", None)
        exclude_suspect_magnitudes_var = getattr(
            self,
            "star_search_exclude_suspect_magnitudes_var",
            None,
        )
        return {
            "star_search_spectral_type": self._current_star_search_spectral_type(),
            "star_search_magnitude_band": self._current_star_search_magnitude_band(),
            "star_search_min_magnitude": read_float(
                "star_search_min_mag_var",
                self.settings.star_search_min_magnitude,
            ),
            "star_search_max_magnitude": read_float(
                "star_search_max_mag_var",
                self.settings.star_search_max_magnitude,
            ),
            "star_search_min_max_altitude": read_float(
                "star_search_min_altitude_var",
                self.settings.star_search_min_max_altitude,
            ),
            "star_search_visible_night": (
                visible_night_var.get()
                if visible_night_var is not None
                else self.settings.star_search_visible_night
            ),
            "star_search_transit_night": (
                transit_night_var.get()
                if transit_night_var is not None
                else self.settings.star_search_transit_night
            ),
            "star_search_exclude_polar_circle": (
                exclude_polar_circle_var.get()
                if exclude_polar_circle_var is not None
                else self.settings.star_search_exclude_polar_circle
            ),
            "star_search_exclude_suspect_magnitudes": (
                exclude_suspect_magnitudes_var.get()
                if exclude_suspect_magnitudes_var is not None
                else self.settings.star_search_exclude_suspect_magnitudes
            ),
        }



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
        app_dialogs.open_settings_dialog(self)

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
            "transit_time": "double.column.transit_time",
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
            "transit_night": DEFAULT_DOUBLE_TRANSIT_NIGHT,
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
        self.double_transit_night_var.set(filters["transit_night"])
        self.double_include_physical_var.set(filters["include_physical"])
        self.double_include_noted_var.set(filters["include_noted"])
        self.double_include_apparent_var.set(filters["include_apparent"])
        self.double_include_uncertain_var.set(filters["include_uncertain"])
        self.double_exclude_polar_circle_var.set(filters["exclude_polar_circle"])
        self.double_online_var.set(filters["use_online"])

    def reset_double_star_filters(self):
        self._apply_double_filter_controls(self._default_double_filters())
        self._save_current_settings()
        self.search_double_stars(allow_online=False)

    def clear_double_star_cache(self):
        clear_cached_wds_double_stars()
        self.double_wds_cached_stars = []
        self.double_status_label.config(text=self._tr("double.cache_cleared"))
        self.search_double_stars(allow_online=False)

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
        if column == "transit_time":
            return star.get("meridian_transit_sort_timestamp")
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
        self._schedule_double_tree_separator_refresh()

    def _on_double_tree_xscroll(self, scrollbar, first, last):
        scrollbar.set(first, last)
        self._schedule_double_tree_separator_refresh()

    def _schedule_double_tree_separator_refresh(self):
        if self.double_tree_separator_refresh_pending or self.double_star_tree is None:
            return
        self.double_tree_separator_refresh_pending = True

        def refresh():
            self.double_tree_separator_refresh_pending = False
            self._update_double_tree_separators()

        self.root.after_idle(refresh)

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
            app_dialogs.show_error_dialog(
                self,
                self._tr("settings.invalid_title"),
                str(exc),
                parent=self.root,
            )
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
            "transit_night": self.double_transit_night_var.get(),
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
            normalized_star.setdefault("coordinate_frame", "j2000")
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
            normalized[index]["coordinate_frame"] = "jnow"
        return normalized

    def _double_search_context(self):
        alpha_hh, alpha_mm, alpha_ss, _delta_dd, _delta_mm, _delta_ss = (
            self._current_jnow_coordinate_fields()
        )
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "alpha_hh": alpha_hh,
            "alpha_mm": alpha_mm,
            "alpha_ss": alpha_ss,
            "hour_angle_offset_hours": 6 if self.hour_angle_offset_enabled else 0,
            "timezone_name": self.timezone_name,
            "daylight_saving_enabled": self.daylight_saving_enabled,
        }

    def _double_visibility_context(self, search_context=None):
        if search_context is None:
            search_context = self._double_search_context()
        start_utc = datetime.datetime.now(datetime.timezone.utc)
        offsets = [step / 2 for step in range(49)]
        utc_datetimes = [start_utc + datetime.timedelta(hours=offset) for offset in offsets]
        sun_altitudes = compute_sun_altitudes(
            search_context["latitude"],
            search_context["longitude"],
            utc_datetimes,
        )
        context = []
        for offset, sample_time, sun_altitude in zip(offsets, utc_datetimes, sun_altitudes):
            state = compute_clock_state(
                search_context["longitude"],
                search_context["alpha_hh"],
                search_context["alpha_mm"],
                search_context["alpha_ss"],
                hour_angle_offset_hours=search_context["hour_angle_offset_hours"],
                timezone_name=search_context["timezone_name"],
                daylight_saving_enabled=search_context["daylight_saving_enabled"],
                now_utc=sample_time,
            )
            context.append(
                {
                    "offset_hours": offset,
                    "lst_hours": self._parse_clock_hours(state["lst"]),
                    "sun_altitude": sun_altitude,
                    "utc_datetime": sample_time,
                    "local_datetime": self._local_datetime_from_utc(sample_time),
                }
            )
        return context

    def _search_visibility_metrics(
        self,
        ra_hours,
        declination,
        visibility_context,
        night_sun_max_altitude,
        night_target_min_altitude,
    ):
        if not visibility_context:
            return {
                "max_altitude": None,
                "max_night_altitude": None,
                "visible_at_night": False,
                "meridian_transit_at_night": False,
                "meridian_transit_local_datetime": None,
                "meridian_transit_local_minutes": None,
                "meridian_transit_sort_timestamp": None,
            }

        max_altitude = None
        max_night_altitude = None
        visible_at_night = False
        meridian_transit_at_night = False
        meridian_transit_local_datetime = None
        best_hour_angle_distance = None
        best_transit_local_datetime = None
        previous_night_hour_angle = None
        previous_night_local_datetime = None
        for sample in visibility_context:
            altitude, _azimuth, hour_angle = self._equatorial_to_horizontal(
                ra_hours,
                declination,
                sample["lst_hours"],
            )
            hour_angle = self._normalize_hour_angle(hour_angle)
            hour_angle_distance = abs(hour_angle)
            if max_altitude is None or altitude > max_altitude:
                max_altitude = altitude
            if sample["sun_altitude"] > night_sun_max_altitude:
                previous_night_hour_angle = None
                previous_night_local_datetime = None
                continue
            if max_night_altitude is None or altitude > max_night_altitude:
                max_night_altitude = altitude
            if altitude >= night_target_min_altitude:
                visible_at_night = True
            if (
                best_hour_angle_distance is None
                or hour_angle_distance < best_hour_angle_distance
            ):
                best_hour_angle_distance = hour_angle_distance
                best_transit_local_datetime = sample.get("local_datetime")
            if abs(hour_angle) <= 0.25:
                meridian_transit_at_night = True
                if meridian_transit_local_datetime is None:
                    meridian_transit_local_datetime = sample.get("local_datetime")
            elif previous_night_hour_angle is not None:
                if (
                    previous_night_hour_angle <= 0 <= hour_angle
                    and (hour_angle - previous_night_hour_angle) <= 1.0
                ) or (
                    hour_angle <= 0 <= previous_night_hour_angle
                    and (previous_night_hour_angle - hour_angle) <= 1.0
                ):
                    meridian_transit_at_night = True
                    if meridian_transit_local_datetime is None:
                        previous_distance = abs(previous_night_hour_angle)
                        current_distance = hour_angle_distance
                        total_distance = previous_distance + current_distance
                        if (
                            total_distance > 0
                            and previous_night_local_datetime is not None
                            and sample.get("local_datetime") is not None
                        ):
                            span_seconds = (
                                sample["local_datetime"] - previous_night_local_datetime
                            ).total_seconds()
                            fraction = previous_distance / total_distance
                            meridian_transit_local_datetime = (
                                previous_night_local_datetime
                                + datetime.timedelta(seconds=span_seconds * fraction)
                            )
                        else:
                            meridian_transit_local_datetime = sample.get("local_datetime")
            previous_night_hour_angle = hour_angle
            previous_night_local_datetime = sample.get("local_datetime")

        if meridian_transit_local_datetime is None:
            meridian_transit_local_datetime = best_transit_local_datetime

        meridian_transit_local_minutes = None
        meridian_transit_sort_timestamp = None
        if meridian_transit_local_datetime is not None:
            meridian_transit_local_minutes = (
                meridian_transit_local_datetime.hour * 60
                + meridian_transit_local_datetime.minute
                + meridian_transit_local_datetime.second / 60.0
            )
            meridian_transit_sort_timestamp = (
                meridian_transit_local_datetime.astimezone(datetime.timezone.utc).timestamp()
            )

        return {
            "max_altitude": max_altitude,
            "max_night_altitude": max_night_altitude,
            "visible_at_night": visible_at_night,
            "meridian_transit_at_night": meridian_transit_at_night,
            "meridian_transit_local_datetime": meridian_transit_local_datetime,
            "meridian_transit_local_minutes": meridian_transit_local_minutes,
            "meridian_transit_sort_timestamp": meridian_transit_sort_timestamp,
        }

    def _double_star_visibility_metrics(self, star, visibility_context):
        return self._search_visibility_metrics(
            star["ra_hours"],
            star["declination"],
            visibility_context,
            DOUBLE_NIGHT_SUN_MAX_ALTITUDE,
            DOUBLE_NIGHT_TARGET_MIN_ALTITUDE,
        )

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
            if filters.get("exclude_polar_circle", False) and star["declination"] > 60:
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
            if filters.get("visible_night", False) and not star.get("visible_at_night"):
                continue
            if filters.get("transit_night", False) and not star.get("meridian_transit_at_night"):
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

    def _enrich_double_star_orbits(self, stars, orb6_index, orbit_index=None):
        active_orbit_index = orbit_index if orbit_index is not None else self.double_orb6_orbit_index
        if not orb6_index and not active_orbit_index:
            return list(stars), 0
        try:
            return enrich_double_stars_with_orb6(
                stars,
                orb6_index,
                datetime.datetime.now(datetime.timezone.utc),
                orbit_index=active_orbit_index,
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

    def _format_transit_time(self, value):
        if value is None:
            return ""
        return value.strftime("%H:%M")

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

    def _cancel_double_tree_render(self):
        if self.double_tree_render_job is None:
            return
        try:
            self.root.after_cancel(self.double_tree_render_job)
        except (tk.TclError, RuntimeError):
            pass
        self.double_tree_render_job = None

    def _populate_double_star_tree(self, on_complete=None):
        if self.double_sort_column in {
            "orb6_separation",
            "orb6_pa",
            "max_altitude",
            "transit_time",
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

        self._cancel_double_tree_render()

        if self.double_star_tree is None:
            if on_complete is not None:
                on_complete()
            return

        for item in self.double_star_tree.get_children():
            self.double_star_tree.delete(item)

        batch_size = 250

        def insert_batch(start_index=0):
            end_index = min(start_index + batch_size, len(self.double_star_results))
            for index in range(start_index, end_index):
                star = self.double_star_results[index]
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
                        self._format_transit_time(
                            star.get("meridian_transit_local_datetime")
                        ),
                        self._format_double_optional_int(star.get("last_observation_year")),
                        self._format_double_optional_int(star.get("observation_count")),
                        self._double_wds_note_cell_text(star),
                        self._double_orbit_cell_text(star),
                    ),
                    tags=("even" if index % 2 == 0 else "odd",),
                )

            if end_index < len(self.double_star_results):
                self.double_tree_render_job = self.root.after(1, lambda: insert_batch(end_index))
                return

            self.double_tree_render_job = None
            self._update_double_tree_separators()
            if on_complete is not None:
                on_complete()

        insert_batch()

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
        self._schedule_double_tree_separator_refresh()
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

        status = self._tr(
            "double.result_count",
            count=len(self.double_star_results),
            total=total,
            source=self._tr(source_key),
        )
        if note:
            status = f"{status}\n{note}"
        self._populate_double_star_tree(
            on_complete=lambda: self.double_status_label.config(text=status)
            if self.double_status_label is not None
            else None
        )

    def search_double_stars(self, allow_online=False, refresh_orbits=False):
        filters = self._read_double_star_filters()
        if filters is None:
            return
        self._save_current_settings()

        self.double_search_generation += 1
        generation = self.double_search_generation
        search_context = self._double_search_context()
        self.double_remote_search_pending = allow_online or refresh_orbits
        if allow_online:
            status_key = "double.searching_online"
        elif refresh_orbits:
            status_key = "double.recalculating_orbits"
        else:
            status_key = "double.filtering"
        self.double_status_label.config(
            text=self._tr(status_key)
        )
        threading.Thread(
            target=self._run_double_star_search,
            args=(generation, filters, allow_online, search_context, refresh_orbits),
            daemon=True,
        ).start()

    def _run_double_star_search(
        self,
        generation,
        filters,
        allow_online,
        search_context,
        refresh_orbits=False,
    ):
        try:
            visibility_context = self._double_visibility_context(search_context)
            notes = []
            orb6_index = self.double_orb6_index
            orb6_orbit_index = self.double_orb6_orbit_index

            if refresh_orbits:
                try:
                    orb6_index = fetch_orb6_ephemerides(timeout=8)
                    orb6_error = orb6_index.get("fetch_error")
                except Exception as exc:
                    orb6_index = self.double_orb6_index
                    orb6_error = str(exc)

                try:
                    orb6_orbit_index = fetch_orb6_orbits(timeout=8)
                    orb6_orbit_error = orb6_orbit_index.get("fetch_error")
                except Exception as exc:
                    orb6_orbit_index = self.double_orb6_orbit_index
                    orb6_orbit_error = str(exc)

                if orb6_error:
                    notes.append(self._tr("double.orb6_error", error=orb6_error))
                if orb6_orbit_error:
                    notes.append(self._tr("double.orb6_orbit_error", error=orb6_orbit_error))

            local_catalog = self._double_local_catalog()
            source_key = "double.source.wds" if self.double_wds_cached_stars else "double.source.local"
            wds_cached_stars = None

            if allow_online and self.network_online is False:
                notes = [self._tr("double.online_offline")]
            elif allow_online:
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
                    wds_cached_stars = merge_cached_wds_double_stars(remote_results)
                    local_catalog = self._merge_double_star_results(DOUBLE_STARS, wds_cached_stars)
                    source_key = "double.source.wds"
                    notes.extend(
                        [
                            self._tr("double.online_loaded", count=len(remote_results)),
                            self._tr("double.wds_cache_updated", count=len(wds_cached_stars)),
                        ]
                    )
                except Exception as exc:
                    notes.append(self._tr("double.online_error", error=str(exc)))

            local_source, _local_orb6_matches = self._enrich_double_star_orbits(
                local_catalog,
                orb6_index,
                orb6_orbit_index,
            )
            local_results = self._filter_double_star_list(
                local_source,
                filters,
                visibility_context,
            )
            orb6_count = sum(
                1 for star in local_results if star.get("orb6_current_separation") is not None
            )
            orb6_note = self._double_orb6_status_note(orb6_count, orb6_index)
            if orb6_note:
                notes.append(orb6_note)
            self._queue_double_star_search_results(
                generation,
                {
                    "stars": local_results,
                    "total": len(local_catalog),
                    "source_key": source_key,
                    "note": "\n".join(notes),
                    "wds_cached_stars": wds_cached_stars,
                    "orb6_index": orb6_index if refresh_orbits else None,
                    "orb6_orbit_index": orb6_orbit_index if refresh_orbits else None,
                },
            )
        except Exception as exc:
            self._queue_double_star_search_results(
                generation,
                {
                    "stars": [],
                    "total": 0,
                    "source_key": "double.source.local",
                    "note": self._tr("double.online_error", error=str(exc)),
                },
            )

    def _queue_double_star_search_results(self, generation, payload):
        try:
            self.root.after(
                0,
                lambda: self._apply_double_star_search_results(generation, payload),
            )
        except (tk.TclError, RuntimeError):
            self.double_remote_search_pending = False

    def _apply_double_star_search_results(self, generation, payload):
        if generation != self.double_search_generation:
            return
        self.double_remote_search_pending = False
        if payload.get("wds_cached_stars") is not None:
            self.double_wds_cached_stars = payload["wds_cached_stars"]
        if payload.get("orb6_index") is not None:
            self.double_orb6_index = payload["orb6_index"]
        if payload.get("orb6_orbit_index") is not None:
            self.double_orb6_orbit_index = payload["orb6_orbit_index"]
        self._render_double_star_results(
            payload["stars"],
            payload["total"],
            payload["source_key"],
            payload.get("note"),
        )

    def _run_double_star_online_search(self, generation, filters, visibility_context=None):
        if visibility_context is None:
            visibility_context = self._double_visibility_context()
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

        active_orb6_index = orb6_index or self.double_orb6_index
        active_orbit_index = orb6_orbit_index or self.double_orb6_orbit_index
        wds_cached_stars = None
        if not error:
            wds_cached_stars = merge_cached_wds_double_stars(remote_results)
            local_catalog = self._merge_double_star_results(DOUBLE_STARS, wds_cached_stars)
        else:
            local_catalog = self._double_local_catalog()

        local_source, _local_orb6_matches = self._enrich_double_star_orbits(
            local_catalog,
            active_orb6_index,
            active_orbit_index,
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
            self._queue_double_star_search_results(
                generation,
                {
                    "stars": local_results,
                    "total": len(local_catalog),
                    "source_key": "double.source.local",
                    "note": "\n".join(notes),
                    "orb6_index": orb6_index,
                    "orb6_orbit_index": orb6_orbit_index,
                },
            )
            return

        remote_source, _remote_orb6_matches = self._enrich_double_star_orbits(
            remote_results,
            active_orb6_index,
            active_orbit_index,
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
            self._tr("double.wds_cache_updated", count=len(wds_cached_stars)),
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
        self._queue_double_star_search_results(
            generation,
            {
                "stars": combined,
                "total": combined_catalog_total,
                "source_key": "double.source.wds",
                "note": "\n".join(notes),
                "wds_cached_stars": wds_cached_stars,
                "orb6_index": orb6_index,
                "orb6_orbit_index": orb6_orbit_index,
            },
        )

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

        ra_hours = star["ra_hours"]
        declination = star["declination"]
        if star.get("coordinate_frame") == "j2000":
            ra_hours, declination = j2000_to_jnow_coordinates(ra_hours, declination)
        self._set_target_from_coordinates(
            ra_hours,
            declination,
            self._tr("double.target_set", name=star["name"]),
            display_name=star["name"],
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

    def _orbit_label_anchor(self, x_direction, y_direction):
        vertical = ""
        horizontal = ""
        if y_direction > 0.35:
            vertical = "n"
        elif y_direction < -0.35:
            vertical = "s"
        if x_direction > 0.35:
            horizontal = "w"
        elif x_direction < -0.35:
            horizontal = "e"
        return vertical + horizontal or "center"

    def _orbit_external_label_position(
        self,
        x_position,
        y_position,
        center_x,
        center_y,
        screen_points,
        gap=14,
    ):
        if not screen_points:
            x_direction = x_position - center_x
            y_direction = y_position - center_y
            length = math.hypot(x_direction, y_direction) or 1.0
            x_unit = x_direction / length
            y_unit = y_direction / length
            return (
                x_position + x_unit * gap,
                y_position + y_unit * gap,
                self._orbit_label_anchor(x_unit, y_unit),
                x_unit,
                y_unit,
            )

        nearest_index = min(
            range(len(screen_points)),
            key=lambda index: (
                (screen_points[index][0] - x_position) ** 2
                + (screen_points[index][1] - y_position) ** 2
            ),
        )
        previous_point = screen_points[(nearest_index - 1) % len(screen_points)]
        next_point = screen_points[(nearest_index + 1) % len(screen_points)]
        tangent_x = next_point[0] - previous_point[0]
        tangent_y = next_point[1] - previous_point[1]

        centroid_x = sum(point_x for point_x, _point_y, _point in screen_points) / len(
            screen_points
        )
        centroid_y = sum(point_y for _point_x, point_y, _point in screen_points) / len(
            screen_points
        )
        outward_x = x_position - centroid_x
        outward_y = y_position - centroid_y

        normal_x = -tangent_y
        normal_y = tangent_x
        if normal_x * outward_x + normal_y * outward_y < 0:
            normal_x = -normal_x
            normal_y = -normal_y
        length = math.hypot(normal_x, normal_y)
        if length < 1e-6:
            normal_x = outward_x
            normal_y = outward_y
            length = math.hypot(normal_x, normal_y)
        if length < 1e-6:
            normal_x = 0.0
            normal_y = -1.0
            length = 1.0

        x_unit = normal_x / length
        y_unit = normal_y / length
        return (
            x_position + x_unit * gap,
            y_position + y_unit * gap,
            self._orbit_label_anchor(x_unit, y_unit),
            x_unit,
            y_unit,
        )

    def _keep_canvas_item_in_bounds(self, canvas, item, padding=8):
        bbox = canvas.bbox(item)
        if bbox is None:
            return 0, 0
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        dx = 0
        dy = 0
        if bbox[0] < padding:
            dx = padding - bbox[0]
        elif bbox[2] > canvas_width - padding:
            dx = canvas_width - padding - bbox[2]
        if bbox[1] < padding:
            dy = padding - bbox[1]
        elif bbox[3] > canvas_height - padding:
            dy = canvas_height - padding - bbox[3]
        if dx or dy:
            canvas.move(item, dx, dy)
        return dx, dy

    def open_double_star_orbit_window(self, star):
        app_dialogs.open_double_star_orbit_window(self, star)

    def _set_wds_note_text(self, text_widget, content):
        app_dialogs._set_wds_note_text(self, text_widget, content)

    def _format_wds_note_rows(self, notes):
        return app_dialogs._format_wds_note_rows(self, notes)

    def _load_wds_note_rows(self, dialog, text_widget, wds):
        app_dialogs._load_wds_note_rows(self, dialog, text_widget, wds)

    def open_double_star_wds_note_window(self, star):
        app_dialogs.open_double_star_wds_note_window(self, star)

    def _draw_double_star_orbit(self, state):
        app_dialogs._draw_double_star_orbit(self, state)

    def _on_double_orbit_motion(self, event, state):
        app_dialogs._on_double_orbit_motion(self, event, state)

    def _clear_double_orbit_hover(self, state):
        app_dialogs._clear_double_orbit_hover(self, state)

    def _coordinate_result_message(self, result):
        if result.get("source") == "imcce":
            return self._tr(
                "result.imcce_coordinates",
                ra=result.get("source_ra", ""),
                dec=result.get("source_dec", ""),
            )
        if result.get("source") == "local_solar":
            return self._tr(
                "result.local_solar_coordinates",
                ra=result.get("source_ra", ""),
                dec=result.get("source_dec", ""),
            )
        if result.get("source") == "sesame":
            return self._tr(
                "result.sesame_coordinates",
                ra=result.get("source_ra", ""),
                dec=result.get("source_dec", ""),
            )
        if result.get("source") == "local":
            return self._tr(
                "result.local_coordinates",
                ra=result.get("source_ra", ""),
                dec=result.get("source_dec", ""),
                source=result.get("source_catalog", ""),
                note=result.get("source_note", ""),
            )
        return result["message"]

    def _apply_coordinate_result(self, result):
        self._set_result_text(self._coordinate_result_message(result))
        ra_hours = (
            float(result["alpha_hh"])
            + (float(result["alpha_mm"]) / 60)
            + (float(result["alpha_ss"]) / 3600)
        )
        dec_sign = -1 if str(result["delta_dd"]).strip().startswith("-") else 1
        dec_degrees = dec_sign * (
            abs(float(result["delta_dd"]))
            + (float(result["delta_mm"]) / 60)
            + (float(result["delta_ss"]) / 3600)
        )
        result_frame = "jnow" if result.get("source") in {"imcce", "local_solar"} else "j2000"
        self._set_coordinate_fields(ra_hours, dec_degrees, frame=result_frame)
        searched_name = result.get("display_name") or self.search_entry.get().strip()
        self.target_display_name = searched_name or self._tr("sky.target")
        self.target_solar_system_name = result.get("solar_system_name")
        self.visibility_start_date = None
        self._update_visibility_date_label()
        self.update_value(preserve_solar_target=self.target_solar_system_name is not None)

    def _start_coordinate_search(self, selected_type, object_name, fallback_result=None):
        self.coordinate_search_generation += 1
        generation = self.coordinate_search_generation
        self.coordinate_search_pending = True
        self._update_search_button_state()
        self._set_result_text(self._tr("result.searching", object_name=object_name), self.muted)
        threading.Thread(
            target=self._run_coordinate_search,
            args=(generation, selected_type, object_name, fallback_result),
            daemon=True,
        ).start()

    def _run_coordinate_search(self, generation, selected_type, object_name, fallback_result=None):
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
            result = fallback_result
            error_key = None if fallback_result is not None else "result.object_not_found"
            error_detail = None
        except Exception as exc:
            result = fallback_result
            error_key = None
            if fallback_result is None:
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

        if result is None:
            self._set_result_text(self._tr("result.object_not_found"), foreground=self.danger)
            return

        self._apply_coordinate_result(result)

    def _solar_system_search_type_for_local_result(self, result):
        if result is None:
            return "Planet"
        if result.get("solar_system_name") == "Moon":
            return "Natural Satellite"
        return "Planet"

    def search_coordinates(self):
        solar_system = [
            "sun",
            "soleil",
            "mercure",
            "mercury",
            "venus",
            "vénus",
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
            local_solar_result = resolve_local_solar_system_coordinates(
                object_name,
                latitude=self.latitude,
                longitude=self.longitude,
            )
            if self.network_online is False:
                if local_solar_result is not None:
                    self._apply_coordinate_result(local_solar_result)
                else:
                    self._set_result_text(self._tr("result.online_search_offline"), foreground=self.danger)
                return
            self._start_coordinate_search(selected_type, object_name, fallback_result=local_solar_result)
            return

        local_solar_result = resolve_local_solar_system_coordinates(
            object_name,
            latitude=self.latitude,
            longitude=self.longitude,
        )
        if local_solar_result is not None:
            if self.network_online is False:
                self._apply_coordinate_result(local_solar_result)
            else:
                self._start_coordinate_search(
                    self._solar_system_search_type_for_local_result(local_solar_result),
                    object_name,
                    fallback_result=local_solar_result,
                )
            return

        if object_name.lower() in solar_system:
            self._set_result_text(
                self._tr("result.online_search_offline")
                if self.network_online is False
                else self._tr("result.object_type_error"),
                foreground=self.danger,
            )
            return

        if not selected_type:
            self._set_result_text(self._tr("result.no_object_type"), foreground=self.danger)
            return

        if not object_name:
            self._set_result_text("")
            return

        local_result = resolve_local_object_coordinates(object_name)
        if self.network_online is False:
            if local_result is not None:
                self._apply_coordinate_result(local_result)
            else:
                self._set_result_text(
                    self._tr("result.local_object_not_found_offline"),
                    foreground=self.danger,
                )
            return

        self._start_coordinate_search(selected_type, object_name, fallback_result=local_result)

    def clocks(self):
        self._sanitize_coordinate_values()
        state = self._compute_target_clock_state()

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


app_deep_sky.install_deep_sky_methods(AstroClocksApp)
app_star_search.install_star_search_methods(AstroClocksApp)


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
    apply_windows_title_bar_theme(
        window,
        caption_color="#101419",
        text_color="#edf3f8",
        border_color="#2b3a45",
        immersive_dark=True,
    )
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
    apply_windows_title_bar_theme(
        window,
        caption_color="#101419",
        text_color="#edf3f8",
        border_color="#2b3a45",
        immersive_dark=True,
    )
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
