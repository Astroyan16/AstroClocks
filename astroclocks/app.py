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
from astroclocks import (
    app_double_stars,
    app_deep_sky,
    app_dialogs,
    app_object_search,
    app_skymap,
    app_star_search,
    app_visibility,
    ascom_mount,
    updater,
)
try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None

from astroclocks.astronomy import (
    compute_clock_state,
    compute_declination_display,
    compute_solar_system_positions,
    convert_star_catalog_j2000_to_jnow,
    format_timezone_label,
    j2000_to_jnow_coordinates,
    jnow_to_j2000_coordinates,
    resolve_timezone,
)
from astroclocks.double_star_catalog import load_cached_wds_double_stars
from astroclocks.deep_sky_catalog import load_cached_simbad_deep_sky_objects
from astroclocks.i18n import translate
from astroclocks.orbit_catalog import load_cached_orb6_ephemerides, load_cached_orb6_orbits
from astroclocks.settings import (
    AppSettings,
    COORDINATE_SOURCE_APP,
    COORDINATE_SOURCE_MOUNT,
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
CONNECTIVITY_OFFLINE_FAILURE_THRESHOLD = 2
MOUNT_POLL_INTERVAL_MS = 250
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
        self.mount_accent = "#b892ff"
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
        self.mount_ascom_driver_id = self.settings.mount_ascom_driver_id
        self.mount_ascom_driver_name = self.settings.mount_ascom_driver_name
        self.coordinate_source = self.settings.coordinate_source
        self.mount_show_reticle = self.settings.mount_show_reticle
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
        self.connectivity_consecutive_failures = 0
        try:
            self.mount_ascom_available = ascom_mount.is_available()
            self.mount_availability_error = ""
        except Exception as exc:
            self.mount_ascom_available = False
            self.mount_availability_error = self._mount_error_message(exc)
        self.mount_telescope = None
        self.mount_connected = False
        self.mount_last_error = ""
        self.mount_last_snapshot = None
        self.mount_poll_job = None
        self.startup_update_check_scheduled = False
        self.startup_update_check_pending = False
        self.startup_update_check_completed = False
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
        self.sky_base_status_color_highlights = ()
        self.sky_status_payload = None
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
        try:
            self._place_initial_window()
            self._update_dynamic_fonts()
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
        self._schedule_startup_update_check()

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
        self.root.protocol("WM_DELETE_WINDOW", self._on_close_requested)
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

    def _restore_root_chrome_after_dialog_destroy(self, dialog, event=None):
        if event is not None and getattr(event, "widget", None) is not dialog:
            return
        try:
            self._apply_native_window_chrome(self.root)
        except Exception:
            pass

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
        self._apply_native_window_chrome(self.root)
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
        try:
            dialog.bind(
                "<Destroy>",
                lambda _event: self._restore_root_chrome_after_dialog_destroy(dialog, _event),
                add="+",
            )
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
        try:
            self.root.update_idletasks()
        except (tk.TclError, RuntimeError):
            pass
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
            command=self._on_close_requested,
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

    def _schedule_startup_update_check(self, delay_ms=2500):
        if self.startup_update_check_scheduled or self.startup_update_check_completed:
            return
        self.startup_update_check_scheduled = True
        self.root.after(delay_ms, self._start_startup_update_check)

    def _start_startup_update_check(self):
        self.startup_update_check_scheduled = False
        if self.startup_update_check_pending or self.startup_update_check_completed:
            return
        self.startup_update_check_pending = True
        threading.Thread(target=self._run_startup_update_check, daemon=True).start()

    def _run_startup_update_check(self):
        try:
            result = self.check_for_updates(timeout=6)
        except Exception:
            result = None

        try:
            self.root.after(0, lambda: self._apply_startup_update_check_result(result))
        except (tk.TclError, RuntimeError):
            pass

    def _apply_startup_update_check_result(self, result):
        self.startup_update_check_pending = False
        self.startup_update_check_completed = True
        if result is None or not result.update_available:
            return
        try:
            app_dialogs.open_about_dialog(
                self,
                APP_VERSION,
                self._release_date_text(),
                APP_AUTHOR,
                APP_EMAIL,
                APP_PHONE,
                initial_update_result=result,
            )
        except (tk.TclError, RuntimeError):
            pass

    def check_for_updates(self, timeout=10):
        try:
            return updater.check_for_updates(APP_VERSION, timeout=timeout)
        except Exception as exc:
            raise RuntimeError(self._update_error_message(exc)) from exc

    def download_update_installer(self, release, timeout=30):
        try:
            return updater.download_installer(release, timeout=timeout)
        except Exception as exc:
            raise RuntimeError(self._update_error_message(exc)) from exc

    def launch_update_installer(self, installer_path):
        try:
            updater.launch_installer(installer_path)
        except Exception as exc:
            raise RuntimeError(self._update_error_message(exc)) from exc

    def _on_close_requested(self):
        try:
            self.disconnect_ascom_mount(silent=True)
        finally:
            self.root.destroy()

    def _cancel_mount_poll(self):
        if self.mount_poll_job is None:
            return
        try:
            self.root.after_cancel(self.mount_poll_job)
        except (tk.TclError, RuntimeError):
            pass
        self.mount_poll_job = None

    def _schedule_mount_poll(self, delay_ms=MOUNT_POLL_INTERVAL_MS):
        self._cancel_mount_poll()
        if not self.mount_connected:
            return
        try:
            self.mount_poll_job = self.root.after(delay_ms, self._poll_ascom_mount)
        except (tk.TclError, RuntimeError):
            self.mount_poll_job = None

    def _mount_equatorial_frame_label(self, equatorial_system):
        mapping = {
            ascom_mount.EQUATORIAL_SYSTEM_TOPOCENTRIC: self._tr("mount.frame.topocentric"),
            ascom_mount.EQUATORIAL_SYSTEM_J2000: self._tr("mount.frame.j2000"),
            ascom_mount.EQUATORIAL_SYSTEM_J2050: self._tr("mount.frame.j2050"),
            ascom_mount.EQUATORIAL_SYSTEM_B1950: self._tr("mount.frame.b1950"),
        }
        return mapping.get(equatorial_system, self._tr("mount.frame.other"))

    def _coordinate_source_label(self, source_code):
        if source_code == COORDINATE_SOURCE_MOUNT:
            return self._tr("coordinate_source.mount")
        return self._tr("coordinate_source.app")

    def _mount_tracking_label(self, snapshot):
        if snapshot is None:
            return self._tr("mount.tracking.unknown")
        if snapshot.tracking is False:
            return self._tr("mount.tracking.off")

        tracking_rate = getattr(snapshot, "tracking_rate", None)
        tracking_labels = {
            ascom_mount.TRACKING_RATE_SIDEREAL: "mount.tracking.sidereal",
            ascom_mount.TRACKING_RATE_LUNAR: "mount.tracking.lunar",
            ascom_mount.TRACKING_RATE_SOLAR: "mount.tracking.solar",
            ascom_mount.TRACKING_RATE_KING: "mount.tracking.king",
        }
        if tracking_rate in tracking_labels:
            return self._tr(tracking_labels[tracking_rate])
        if snapshot.tracking is True:
            return self._tr("mount.tracking.on")
        return self._tr("mount.tracking.unknown")

    def _mount_error_message(self, error):
        text = str(error or "").strip()
        if not text:
            return self._tr("mount.error.generic")

        lower_text = text.casefold()

        if "synscan" in lower_text and (
            "not running" in lower_text
            or "not launched" in lower_text
            or "connection refused" in lower_text
            or "actively refused" in lower_text
            or "cannot connect" in lower_text
            or "can't connect" in lower_text
            or "app not connected" in lower_text
        ):
            return self._tr("mount.error.synscan_unavailable")

        exact_messages = {
            "ASCOM support requires pywin32 on Windows.": "mount.error.unavailable_pywin32",
            "The ASCOM Platform chooser is not installed on this computer.": (
                "mount.error.platform_missing"
            ),
            "No ASCOM mount driver is selected.": "mount.error.no_driver",
            "The ASCOM mount is not connected.": "mount.error.not_connected",
            "The ASCOM mount is disconnected.": "mount.error.disconnected",
        }
        if text in exact_messages:
            return self._tr(exact_messages[text])

        prefix_messages = (
            ("Unable to open the ASCOM mount chooser:", "mount.error.chooser_failed"),
            ("Unable to create the ASCOM mount driver:", "mount.error.driver_create_failed"),
            ("Unable to connect to the ASCOM mount:", "mount.error.connect_failed"),
            ("Unable to disconnect the ASCOM mount:", "mount.error.disconnect_failed"),
            (
                "Unable to read the ASCOM mount connection state:",
                "mount.error.read_state_failed",
            ),
            (
                "Unable to read the ASCOM mount coordinates:",
                "mount.error.read_coordinates_failed",
            ),
        )
        for prefix, key in prefix_messages:
            if text.startswith(prefix):
                return self._tr(key)

        return self._tr("mount.error.generic")

    def _mount_connect_error_message(self, error):
        text = str(error or "").strip()
        if not text:
            return self._tr("mount.error.connect_failed")

        lower_text = text.casefold()
        if "synscan" in lower_text and (
            "not running" in lower_text
            or "not launched" in lower_text
            or "connection refused" in lower_text
            or "actively refused" in lower_text
            or "cannot connect" in lower_text
            or "can't connect" in lower_text
            or "app not connected" in lower_text
        ):
            return self._tr("mount.error.synscan_unavailable")

        if text in {
            "The ASCOM mount is not connected.",
            "The ASCOM mount is disconnected.",
        }:
            return self._mount_error_message(error)

        for prefix in (
            "Unable to read the ASCOM mount connection state:",
            "Unable to read the ASCOM mount coordinates:",
        ):
            if text.startswith(prefix):
                return self._tr("mount.error.connect_failed")

        return self._mount_error_message(error)

    def _update_error_message(self, error):
        text = str(error or "").strip()
        if not text:
            return self._tr("update.error.generic")

        exact_messages = {
            "Update feed unavailable. GitHub releases may be private or missing.": (
                "update.error.feed_unavailable"
            ),
            "GitHub rate limit reached while accessing the update server. Please try again later.": (
                "update.error.rate_limit"
            ),
            "Update request timed out.": "update.error.timeout",
            "Unexpected update feed format.": "update.error.invalid_format",
            "Update feed returned unreadable data.": "update.error.unreadable_data",
            "Update feed returned invalid JSON.": "update.error.invalid_json",
            "Update feed contains incoherent Windows release metadata.": (
                "update.error.incoherent_release"
            ),
            "No installable public Windows release was found.": "update.error.no_release",
            "Installer metadata is invalid.": "update.error.invalid_metadata",
            "Downloaded installer is empty.": "update.error.empty_installer",
        }
        if text in exact_messages:
            return self._tr(exact_messages[text])

        prefix_messages = (
            ("Update server returned HTTP ", "update.error.http"),
            ("Network error while accessing the update server:", "update.error.network"),
            ("Unable to read the update feed:", "update.error.read_failed"),
            ("Installer not found:", "update.error.installer_not_found"),
            ("Unable to launch installer:", "update.error.launch_failed"),
        )
        for prefix, key in prefix_messages:
            if text.startswith(prefix):
                return self._tr(key)

        return self._tr("update.error.generic")

    def _mount_site_coordinates(self, snapshot=None):
        snapshot = snapshot or self.mount_last_snapshot
        if snapshot is None:
            return None
        site_latitude = getattr(snapshot, "site_latitude", None)
        site_longitude = getattr(snapshot, "site_longitude", None)
        if site_latitude is None or site_longitude is None:
            return None
        return site_latitude, site_longitude

    def _active_site_context(self):
        stored_coordinates = (self.latitude, self.longitude)
        if self.coordinate_source == COORDINATE_SOURCE_MOUNT:
            mount_coordinates = self._mount_site_coordinates()
            if mount_coordinates is not None:
                return {
                    "requested_source": COORDINATE_SOURCE_MOUNT,
                    "effective_source": COORDINATE_SOURCE_MOUNT,
                    "label": self._coordinate_source_label(COORDINATE_SOURCE_MOUNT),
                    "coordinates": mount_coordinates,
                    "fallback": False,
                }
            return {
                "requested_source": COORDINATE_SOURCE_MOUNT,
                "effective_source": COORDINATE_SOURCE_APP,
                "label": self._tr("coordinate_source.mount_fallback"),
                "coordinates": stored_coordinates,
                "fallback": True,
            }
        return {
            "requested_source": COORDINATE_SOURCE_APP,
            "effective_source": COORDINATE_SOURCE_APP,
            "label": self._coordinate_source_label(COORDINATE_SOURCE_APP),
            "coordinates": stored_coordinates,
            "fallback": False,
        }

    def _active_site_coordinates(self):
        return self._active_site_context()["coordinates"]

    def _invalidate_site_dependent_state(self):
        self.site_info_lines = None
        self.solar_system_cache_key = None
        self.sky_map_cache_key = None
        self.visibility_cache_key = None

    def _mount_jnow_coordinates(self, snapshot):
        if snapshot is None:
            return None
        if snapshot.equatorial_system == ascom_mount.EQUATORIAL_SYSTEM_J2000:
            return j2000_to_jnow_coordinates(snapshot.ra_hours, snapshot.declination)
        return snapshot.ra_hours, snapshot.declination

    def _poll_ascom_mount(self):
        self.mount_poll_job = None
        if not self.mount_connected:
            return

        previous_site_context = self._active_site_context()
        try:
            snapshot = ascom_mount.read_snapshot(
                self.mount_telescope,
                self.mount_ascom_driver_id,
                self.mount_ascom_driver_name,
            )
        except Exception as exc:
            self.mount_connected = False
            self.mount_telescope = None
            self.mount_last_snapshot = None
            self.mount_last_error = self._mount_error_message(exc)
            self._cancel_mount_poll()
            site_changed = self._active_site_context() != previous_site_context
            if site_changed:
                self._invalidate_site_dependent_state()
            self.sky_map_cache_key = None
            try:
                if site_changed:
                    self.update_site_labels()
                self._update_sky_map()
                if site_changed:
                    self._update_visibility_chart()
            except (tk.TclError, RuntimeError):
                pass
            return

        self.mount_last_snapshot = snapshot
        self.mount_last_error = ""
        site_changed = self._active_site_context() != previous_site_context
        if site_changed:
            self._invalidate_site_dependent_state()
        self.sky_map_cache_key = None
        try:
            if site_changed:
                self.update_site_labels()
            self._update_sky_map()
            if site_changed:
                self._update_visibility_chart()
        except (tk.TclError, RuntimeError):
            return
        self._schedule_mount_poll()

    def mount_settings_state(self):
        driver_name = self.mount_ascom_driver_name or self.mount_ascom_driver_id
        driver_label = driver_name or self._tr("mount.driver.none")
        has_driver = bool(driver_name)
        snapshot_ready = self.mount_last_snapshot is not None

        if not self.mount_ascom_available:
            status_text = self._tr(
                "mount.status.unavailable",
                error=self.mount_availability_error or self._tr("mount.status.unavailable_short"),
            )
            status_color = self.danger
        elif self.mount_connected and snapshot_ready:
            snapshot = self.mount_last_snapshot
            status_text = self._tr(
                "mount.status.connected_coords",
                name=snapshot.driver_name or snapshot.driver_id,
                frame=self._mount_equatorial_frame_label(snapshot.equatorial_system),
                tracking=self._mount_tracking_label(snapshot),
            )
            status_color = self.success
        elif self.mount_connected:
            status_text = self._tr(
                "mount.status.connected_pending",
                name=driver_name or self._tr("mount.driver.unnamed"),
            )
            status_color = self.accent
        elif self.mount_last_error:
            status_text = self._tr("mount.status.error", error=self.mount_last_error)
            status_color = self.danger
        elif driver_name:
            status_text = self._tr("mount.status.selected", name=driver_name)
            status_color = self.muted
        else:
            status_text = self._tr("mount.status.not_configured")
            status_color = self.muted

        return {
            "available": self.mount_ascom_available,
            "connected": self.mount_connected,
            "has_driver": has_driver,
            "snapshot_ready": snapshot_ready,
            "driver_label": driver_label,
            "status_text": status_text,
            "status_color": status_color,
        }

    def choose_ascom_mount_driver(self):
        if not self.mount_ascom_available:
            raise RuntimeError(
                self.mount_availability_error or self._tr("mount.error.unavailable")
            )
        try:
            driver_id, driver_name = ascom_mount.choose_driver(self.mount_ascom_driver_id)
        except Exception as exc:
            raise RuntimeError(self._mount_error_message(exc)) from exc
        if not driver_id:
            return self.mount_settings_state()
        if self.mount_connected and driver_id != self.mount_ascom_driver_id:
            self.disconnect_ascom_mount(silent=True)
        self.mount_ascom_driver_id = driver_id
        self.mount_ascom_driver_name = driver_name or driver_id
        self.mount_last_error = ""
        self.mount_last_snapshot = None
        self._invalidate_site_dependent_state()
        return self.mount_settings_state()

    def connect_ascom_mount(self):
        if not self.mount_ascom_available:
            raise RuntimeError(
                self.mount_availability_error or self._tr("mount.error.unavailable")
            )
        if not self.mount_ascom_driver_id:
            driver_state = self.choose_ascom_mount_driver()
            if not self.mount_ascom_driver_id:
                return driver_state
        if self.mount_connected and self.mount_telescope is not None:
            self._poll_ascom_mount()
            return self.mount_settings_state()

        previous_site_context = self._active_site_context()
        try:
            telescope, driver_name = ascom_mount.connect(self.mount_ascom_driver_id)
            snapshot = ascom_mount.read_snapshot(
                telescope,
                self.mount_ascom_driver_id,
                driver_name or self.mount_ascom_driver_id,
            )
        except Exception as exc:
            if "telescope" in locals() and telescope is not None:
                try:
                    ascom_mount.disconnect(telescope)
                except Exception:
                    pass
            error_message = self._mount_connect_error_message(exc)
            self.mount_telescope = None
            self.mount_connected = False
            self.mount_last_snapshot = None
            self.mount_last_error = error_message
            raise RuntimeError(error_message) from exc
        self.mount_telescope = telescope
        self.mount_connected = True
        self.mount_ascom_driver_name = driver_name or self.mount_ascom_driver_id
        self.mount_last_error = ""
        self.mount_last_snapshot = snapshot
        site_changed = self._active_site_context() != previous_site_context
        if site_changed:
            self._invalidate_site_dependent_state()
        self.sky_map_cache_key = None
        try:
            if site_changed:
                self.update_site_labels()
            self._update_sky_map()
            if site_changed:
                self._update_visibility_chart()
        except (tk.TclError, RuntimeError):
            pass
        self._schedule_mount_poll()
        return self.mount_settings_state()

    def disconnect_ascom_mount(self, silent=False):
        self._cancel_mount_poll()
        if self.mount_telescope is not None:
            try:
                ascom_mount.disconnect(self.mount_telescope)
            except Exception as exc:
                if not silent:
                    raise RuntimeError(self._mount_error_message(exc)) from exc
        self.mount_telescope = None
        self.mount_connected = False
        self.mount_last_snapshot = None
        if silent:
            self.mount_last_error = ""
        self._invalidate_site_dependent_state()
        self.update_site_labels()
        try:
            self._update_sky_map()
        except (tk.TclError, RuntimeError):
            pass
        return self.mount_settings_state()

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

        if is_online:
            self.connectivity_consecutive_failures = 0
            effective_online = True
        else:
            self.connectivity_consecutive_failures += 1
            if self.connectivity_consecutive_failures >= CONNECTIVITY_OFFLINE_FAILURE_THRESHOLD:
                effective_online = False
            else:
                effective_online = self.network_online

        self.network_online = effective_online

        if self.connectivity_label is not None:
            if effective_online is None:
                text_key = "network.checking"
                foreground = self.muted
            else:
                text_key = "network.connected" if effective_online else "network.offline"
                foreground = self.success if effective_online else self.danger
            self.connectivity_label.config(
                text=self._tr(text_key),
                foreground=foreground,
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
        _active_latitude, active_longitude = self._active_site_coordinates()
        return compute_clock_state(
            active_longitude,
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
        active_latitude, _active_longitude = self._active_site_coordinates()
        lat_rad = math.radians(active_latitude)

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
        active_latitude, _active_longitude = self._active_site_coordinates()
        lat_rad = math.radians(active_latitude)

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

    def _target_marker_color(self, altitude, visible=None):
        if visible is None:
            visible = altitude >= 0
        if visible and altitude < 10:
            return app_visibility.TARGET_LOW_ALTITUDE_COLOR
        return self.success if visible else self.danger

    def _mount_marker_color(self, visible):
        return self.mount_accent if visible else self.card_edge

    def _current_target_status_color(self):
        if not self.target_active:
            return self.text
        try:
            state = self._compute_target_clock_state()
            lst_hours = self._parse_clock_hours(state["lst"])
            solar_target = (
                self._current_solar_system_target(lst_hours)
                if self.target_solar_system_name
                else None
            )
            if solar_target is not None:
                altitude = solar_target["altitude"]
            else:
                ra_hours, declination = self._current_target_coordinates()
                altitude, _azimuth, _hour_angle = self._equatorial_to_horizontal(
                    ra_hours,
                    declination,
                    lst_hours,
                )
            return self._target_marker_color(altitude, altitude >= 0)
        except Exception:
            return self.success

    def _format_jnow_horizontal_status(
        self,
        ra_hours,
        declination,
        altitude,
        azimuth,
        hour_angle=None,
        include_hour_angle=True,
    ):
        status = (
            f"JNow : RA = {self._format_unsigned_hms_compact(ra_hours)} ; "
            f"DEC = {self._format_signed_dms_compact(declination)} | "
            f"Alt = {altitude:+.2f}\N{DEGREE SIGN} ; "
            f"Az = {azimuth:05.1f}\N{DEGREE SIGN}"
        )
        if include_hour_angle:
            status = (
                f"{status} | {self._tr('sky.hour_angle_short')} = "
                f"{self._format_unsigned_hms_compact(self._display_hour_angle(ra_hours))}"
            )
        return status

    def _mount_status_line(self, lst_hours):
        mount_coordinates = self._mount_jnow_coordinates(self.mount_last_snapshot)
        if not self.mount_connected or mount_coordinates is None:
            return ""

        mount_ra_hours, mount_declination = mount_coordinates
        mount_altitude, mount_azimuth, _mount_hour_angle = self._equatorial_to_horizontal(
            mount_ra_hours,
            mount_declination,
            lst_hours,
        )
        return self._tr(
            "sky.mount_status",
            label=self._tr("sky.telescope"),
            ra=self._format_unsigned_hms_compact(mount_ra_hours),
            dec=self._format_signed_dms_compact(mount_declination),
            altitude=f"{mount_altitude:+.2f}",
            azimuth=f"{mount_azimuth:05.1f}",
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
            foreground=self._current_target_status_color(),
        )

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
        if self.aladin_button is not None:
            self.aladin_button.config(text=self._tr("button.aladin", value=self.aladin_fov_deg))
        active_site = self._active_site_context()
        active_latitude, active_longitude = active_site["coordinates"]
        site_title = self.site_name
        if active_site["effective_source"] == COORDINATE_SOURCE_MOUNT:
            site_title = self._tr("site.mount_location")
        lines = [
            site_title,
            self._tr("site.country", value=self.country or self._tr("settings.custom_site")),
            self._tr("site.timezone", value=self._timezone_label()),
            self._tr("site.local_date", value=local_now.strftime(date_format)),
            self._tr(
                "site.latitude",
                value=format_latitude_display(
                    active_latitude,
                    self._tr("direction.north_short"),
                    self._tr("direction.south_short"),
                ),
            ),
            self._tr(
                "site.longitude",
                value=format_longitude_display(
                    active_longitude,
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
            mount_ascom_driver_id=self.mount_ascom_driver_id,
            mount_ascom_driver_name=self.mount_ascom_driver_name,
            coordinate_source=self.coordinate_source,
            mount_show_reticle=self.mount_show_reticle,
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

app_visibility.install_visibility_methods(AstroClocksApp)
app_double_stars.install_double_star_methods(AstroClocksApp)
app_deep_sky.install_deep_sky_methods(AstroClocksApp)
app_object_search.install_object_search_methods(AstroClocksApp)
app_skymap.install_skymap_methods(AstroClocksApp)
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
