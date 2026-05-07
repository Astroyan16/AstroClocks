"""Star-search tab UI and search helpers for AstroClocks."""

import threading
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

from astroclocks import app_dialogs
from astroclocks.astronomy import convert_star_catalog_j2000_to_jnow
from astroclocks.settings import (
    DEFAULT_STAR_SEARCH_EXCLUDE_POLAR_CIRCLE,
    DEFAULT_STAR_SEARCH_EXCLUDE_SUSPECT_MAGNITUDES,
    DEFAULT_STAR_SEARCH_MAX_MAGNITUDE,
    DEFAULT_STAR_SEARCH_MAGNITUDE_BAND,
    DEFAULT_STAR_SEARCH_MIN_MAGNITUDE,
    DEFAULT_STAR_SEARCH_MIN_MAX_ALTITUDE,
    DEFAULT_STAR_SEARCH_SPECTRAL_TYPE,
    DEFAULT_STAR_SEARCH_TRANSIT_NIGHT,
    DEFAULT_STAR_SEARCH_VISIBLE_NIGHT,
    STAR_SEARCH_MAGNITUDE_BANDS,
    STAR_SEARCH_SPECTRAL_TYPES,
)
from astroclocks.star_search_catalog import (
    clear_cached_simbad_stars,
    fetch_simbad_stars,
    load_cached_simbad_stars,
    local_star_search_objects,
    merge_cached_simbad_stars,
    merge_star_search_objects,
    normalize_star_magnitude_band,
    normalize_star_spectral_type,
)
from astroclocks.utils import is_float


def _create_star_search_widgets(self):
    controls = tk.Frame(self.star_search_tab, bg=self.card_bg)
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
        "star_search.filters",
    ).grid(column=0, row=0, pady=(0, 10), sticky="ew")

    self.star_search_spectral_var = tk.StringVar(value=self.settings.star_search_spectral_type)
    self.star_search_band_var = tk.StringVar(value=self.settings.star_search_magnitude_band)
    self.star_search_min_mag_var = tk.StringVar(
        value=self._format_double_filter_number(self.settings.star_search_min_magnitude)
    )
    self.star_search_max_mag_var = tk.StringVar(
        value=self._format_double_filter_number(self.settings.star_search_max_magnitude)
    )
    self.star_search_min_altitude_var = tk.StringVar(
        value=self._format_double_filter_number(self.settings.star_search_min_max_altitude)
    )
    self.star_search_visible_night_var = tk.BooleanVar(
        value=self.settings.star_search_visible_night
    )
    self.star_search_transit_night_var = tk.BooleanVar(
        value=self.settings.star_search_transit_night
    )
    self.star_search_exclude_polar_circle_var = tk.BooleanVar(
        value=self.settings.star_search_exclude_polar_circle
    )
    self.star_search_exclude_suspect_magnitudes_var = tk.BooleanVar(
        value=self.settings.star_search_exclude_suspect_magnitudes
    )

    def add_combo(row, key, variable, values):
        label = tk.Label(
            controls,
            bg=self.card_bg,
            fg=self.text,
            font=Font(family="Segoe UI", size=10),
            anchor="w",
        )
        self._register_translated_widget(label, key)
        label.grid(column=0, row=row, sticky="ew", pady=(6, 2))
        combo = ttk.Combobox(
            controls,
            textvariable=variable,
            state="readonly",
            style="Dark.TCombobox",
            width=24,
            values=values,
        )
        combo.grid(column=0, row=row + 1, sticky="ew")
        combo.bind("<<ComboboxSelected>>", self._save_star_search_filters_if_valid)
        return combo

    add_combo(1, "star_search.spectral_type", self.star_search_spectral_var, STAR_SEARCH_SPECTRAL_TYPES)
    add_combo(3, "star_search.magnitude_band", self.star_search_band_var, STAR_SEARCH_MAGNITUDE_BANDS)

    def add_filter(parent, row, key, variable, column=0):
        label = tk.Label(
            parent,
            bg=self.card_bg,
            fg=self.text,
            font=Font(family="Segoe UI", size=10),
            anchor="w",
        )
        self._register_translated_widget(label, key)
        label.grid(column=column, row=row, sticky="ew", pady=(6, 2))
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
        entry.grid(column=column, row=row + 1, sticky="ew")
        entry.bind("<Return>", lambda _event: self.search_stars(allow_online=False))
        entry.bind("<FocusOut>", self._save_star_search_filters_if_valid)
        return entry

    magnitude_frame = tk.Frame(controls, bg=self.card_bg)
    magnitude_frame.grid(column=0, row=5, sticky="ew")
    magnitude_frame.grid_columnconfigure(0, weight=1)
    magnitude_frame.grid_columnconfigure(1, weight=1)
    add_filter(magnitude_frame, 0, "star_search.min_magnitude", self.star_search_min_mag_var, column=0)
    add_filter(magnitude_frame, 0, "star_search.max_magnitude", self.star_search_max_mag_var, column=1)
    add_filter(controls, 7, "star_search.min_max_altitude", self.star_search_min_altitude_var)

    self._register_translated_widget(
        self._build_inline_checkbutton(
            controls,
            self.star_search_visible_night_var,
            self._tr("star_search.visible_night"),
            self._save_star_search_filters_if_valid,
        ),
        "star_search.visible_night",
    ).grid(column=0, row=9, pady=(12, 0), sticky="ew")
    self._register_translated_widget(
        self._build_inline_checkbutton(
            controls,
            self.star_search_transit_night_var,
            self._tr("star_search.transit_night"),
            self._save_star_search_filters_if_valid,
        ),
        "star_search.transit_night",
    ).grid(column=0, row=10, pady=(4, 0), sticky="ew")
    self._register_translated_widget(
        self._build_inline_checkbutton(
            controls,
            self.star_search_exclude_polar_circle_var,
            self._tr("star_search.exclude_polar_circle"),
            self._save_star_search_filters_if_valid,
        ),
        "star_search.exclude_polar_circle",
    ).grid(column=0, row=11, pady=(4, 0), sticky="ew")
    self._register_translated_widget(
        self._build_inline_checkbutton(
            controls,
            self.star_search_exclude_suspect_magnitudes_var,
            self._tr("star_search.exclude_suspect_magnitudes"),
            self._save_star_search_filters_if_valid,
        ),
        "star_search.exclude_suspect_magnitudes",
    ).grid(column=0, row=12, pady=(4, 0), sticky="ew")

    self.star_search_apply_button = self._build_button(
        controls,
        self._tr("star_search.apply_filters"),
        lambda: self.search_stars(allow_online=False),
    )
    self.star_search_apply_button.grid(column=0, row=13, pady=(14, 6), sticky="ew")

    self.star_search_online_button = self._build_button(
        controls,
        self._tr("star_search.online_search"),
        lambda: self.search_stars(allow_online=True),
    )
    self.star_search_online_button.grid(column=0, row=14, pady=(0, 6), sticky="ew")

    self.star_search_set_button = self._build_button(
        controls,
        self._tr("star_search.set_target"),
        self.set_selected_star_target,
    )
    self.star_search_set_button.grid(column=0, row=15, pady=(0, 6), sticky="ew")

    self.star_search_clear_cache_button = self._build_button(
        controls,
        self._tr("button.clear_cache"),
        self.clear_star_search_cache,
    )
    self.star_search_clear_cache_button.grid(column=0, row=16, pady=(0, 6), sticky="ew")

    self.star_search_reset_button = self._build_button(
        controls,
        self._tr("star_search.reset_filters"),
        self.reset_star_search_filters,
    )
    self.star_search_reset_button.grid(column=0, row=17, pady=(0, 12), sticky="ew")

    self.star_search_status_label = tk.Label(
        controls,
        bg=self.card_bg,
        fg=self.muted,
        font=Font(family="Segoe UI", size=9),
        justify="left",
        wraplength=220,
        anchor="nw",
    )
    self.star_search_status_label.grid(column=0, row=18, sticky="ew")

    results_frame = self._build_labelframe(
        "frame.star_search",
        1,
        0,
        parent=self.star_search_tab,
        padx=(8, 12),
        pady=12,
    )
    results_frame.grid_columnconfigure(0, weight=1)
    results_frame.grid_rowconfigure(0, weight=1)

    columns = (
        "name",
        "designation",
        "spectral_type",
        "magnitude",
        "max_altitude",
        "max_night_altitude",
        "transit_time",
        "ra",
        "declination",
        "source",
    )
    self.star_search_tree = ttk.Treeview(results_frame, columns=columns, show="headings", selectmode="browse")
    self.star_search_tree.grid(column=0, row=0, sticky="nsew", padx=(8, 0), pady=8)
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.star_search_tree.yview, style="Dark.Vertical.TScrollbar")
    scrollbar.grid(column=1, row=0, sticky="ns", padx=(0, 8), pady=8)
    horizontal_scrollbar = ttk.Scrollbar(results_frame, orient="horizontal", command=self._star_search_tree_xview, style="Dark.Horizontal.TScrollbar")
    horizontal_scrollbar.grid(column=0, row=1, sticky="ew", padx=(8, 0), pady=(0, 8))
    self.star_search_tree.configure(
        yscrollcommand=scrollbar.set,
        xscrollcommand=lambda first, last: self._on_star_search_tree_xscroll(horizontal_scrollbar, first, last),
    )
    self.star_search_tree.bind("<Double-1>", lambda _event: self.set_selected_star_target())
    self.star_search_tree.bind("<Configure>", lambda _event: self._schedule_star_search_tree_separator_refresh())
    self.star_search_tree.bind("<ButtonRelease-1>", lambda _event: self._schedule_star_search_tree_separator_refresh())
    self.star_search_tree.bind("<B1-Motion>", lambda _event: self._schedule_star_search_tree_separator_refresh())
    self.star_search_tree.tag_configure("odd", background="#0e151b")
    self.star_search_tree.tag_configure("even", background=self.ebg)

    column_widths = {
        "name": 180,
        "designation": 240,
        "spectral_type": 150,
        "magnitude": 90,
        "max_altitude": 90,
        "max_night_altitude": 95,
        "transit_time": 82,
        "ra": 95,
        "declination": 95,
        "source": 170,
    }
    for column, width in column_widths.items():
        anchor = "center" if column in {"magnitude", "max_altitude", "max_night_altitude", "transit_time"} else "w"
        self.star_search_tree.column(column, width=width, minwidth=min(width, 120), anchor=anchor)

    self._refresh_star_search_headings()
    self._update_star_search_tree_separators()
    self.star_search_status_label.config(text=self._tr("star_search.loading_cache"))

def _ensure_star_search_tab_initialized(self):
    if self.star_search_tab_initialized:
        return
    self._create_star_search_widgets()
    self.star_search_tab_initialized = True

def _schedule_initial_star_search_load(self):
    if self.star_search_initial_load_started:
        return
    self.star_search_initial_load_started = True
    self.root.after(120, lambda: self.search_stars(allow_online=False))

def _save_star_search_filters_if_valid(self, _event=None):
    variables = (
        self.star_search_min_mag_var,
        self.star_search_max_mag_var,
        self.star_search_min_altitude_var,
    )
    if not all(is_float(variable.get()) for variable in variables):
        return
    self._refresh_star_search_headings()
    self._save_current_settings()

def _current_star_search_spectral_type(self):
    spectral_var = getattr(self, "star_search_spectral_var", None)
    value = (
        spectral_var.get()
        if spectral_var is not None
        else getattr(
            self.settings,
            "star_search_spectral_type",
            DEFAULT_STAR_SEARCH_SPECTRAL_TYPE,
        )
    )
    return normalize_star_spectral_type(value)

def _current_star_search_magnitude_band(self):
    band_var = getattr(self, "star_search_band_var", None)
    value = (
        band_var.get()
        if band_var is not None
        else getattr(
            self.settings,
            "star_search_magnitude_band",
            DEFAULT_STAR_SEARCH_MAGNITUDE_BAND,
        )
    )
    return normalize_star_magnitude_band(value)

def _default_star_search_filters(self):
    return {
        "spectral_type": DEFAULT_STAR_SEARCH_SPECTRAL_TYPE,
        "magnitude_band": DEFAULT_STAR_SEARCH_MAGNITUDE_BAND,
        "min_magnitude": DEFAULT_STAR_SEARCH_MIN_MAGNITUDE,
        "max_magnitude": DEFAULT_STAR_SEARCH_MAX_MAGNITUDE,
        "min_altitude": DEFAULT_STAR_SEARCH_MIN_MAX_ALTITUDE,
        "visible_night": DEFAULT_STAR_SEARCH_VISIBLE_NIGHT,
        "transit_night": DEFAULT_STAR_SEARCH_TRANSIT_NIGHT,
        "exclude_polar_circle": DEFAULT_STAR_SEARCH_EXCLUDE_POLAR_CIRCLE,
        "exclude_suspect_magnitudes": DEFAULT_STAR_SEARCH_EXCLUDE_SUSPECT_MAGNITUDES,
    }

def _apply_star_search_filter_controls(self, filters):
    self.star_search_spectral_var.set(normalize_star_spectral_type(filters["spectral_type"]))
    self.star_search_band_var.set(normalize_star_magnitude_band(filters["magnitude_band"]))
    self.star_search_min_mag_var.set(self._format_double_filter_number(filters["min_magnitude"]))
    self.star_search_max_mag_var.set(self._format_double_filter_number(filters["max_magnitude"]))
    self.star_search_min_altitude_var.set(self._format_double_filter_number(filters["min_altitude"]))
    self.star_search_visible_night_var.set(filters["visible_night"])
    self.star_search_transit_night_var.set(filters["transit_night"])
    self.star_search_exclude_polar_circle_var.set(filters["exclude_polar_circle"])
    self.star_search_exclude_suspect_magnitudes_var.set(
        filters["exclude_suspect_magnitudes"]
    )
    self._refresh_star_search_headings()

def reset_star_search_filters(self):
    self._apply_star_search_filter_controls(self._default_star_search_filters())
    self._save_current_settings()
    self.search_stars(allow_online=False)

def clear_star_search_cache(self):
    clear_cached_simbad_stars()
    self.star_search_cached_stars = []
    self.star_search_cache_loaded = True
    self.star_search_status_label.config(text=self._tr("star_search.cache_cleared"))
    self.search_stars(allow_online=False)

def _read_star_search_filters(self):
    try:
        min_magnitude = self._parse_float_setting(
            self.star_search_min_mag_var.get(),
            self._tr("star_search.min_magnitude"),
            -30,
            30,
        )
        max_magnitude = self._parse_float_setting(
            self.star_search_max_mag_var.get(),
            self._tr("star_search.max_magnitude"),
            -30,
            30,
        )
        min_altitude = self._parse_float_setting(
            self.star_search_min_altitude_var.get(),
            self._tr("star_search.min_max_altitude"),
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

    if min_magnitude > max_magnitude:
        min_magnitude, max_magnitude = max_magnitude, min_magnitude
        self.star_search_min_mag_var.set(self._format_double_filter_number(min_magnitude))
        self.star_search_max_mag_var.set(self._format_double_filter_number(max_magnitude))

    return {
        "spectral_type": self._current_star_search_spectral_type(),
        "magnitude_band": self._current_star_search_magnitude_band(),
        "min_magnitude": min_magnitude,
        "max_magnitude": max_magnitude,
        "min_altitude": min_altitude,
        "visible_night": self.star_search_visible_night_var.get(),
        "transit_night": self.star_search_transit_night_var.get(),
        "exclude_polar_circle": self.star_search_exclude_polar_circle_var.get(),
        "exclude_suspect_magnitudes": self.star_search_exclude_suspect_magnitudes_var.get(),
    }

def _star_search_heading_keys(self):
    return {
        "name": "star_search.column.name",
        "designation": "star_search.column.designation",
        "spectral_type": "star_search.column.spectral_type",
        "magnitude": "star_search.column.magnitude",
        "max_altitude": "star_search.column.max_altitude",
        "max_night_altitude": "star_search.column.max_night_altitude",
        "transit_time": "star_search.column.transit_time",
        "ra": "star_search.column.ra",
        "declination": "star_search.column.declination",
        "source": "star_search.column.source",
    }

def _refresh_star_search_headings(self):
    if self.star_search_tree is None:
        return
    for column, key in self._star_search_heading_keys().items():
        label = self._tr(key)
        if column == "magnitude":
            label = f"{label} ({self._current_star_search_magnitude_band()})"
        if column == self.star_search_sort_column:
            label = f"{label} {'v' if self.star_search_sort_reverse else '^'}"
        self.star_search_tree.heading(
            column,
            text=label,
            command=lambda selected_column=column: self._sort_star_search_table(selected_column),
        )

def _sort_star_search_table(self, column):
    if column == self.star_search_sort_column:
        self.star_search_sort_reverse = not self.star_search_sort_reverse
    else:
        self.star_search_sort_column = column
        self.star_search_sort_reverse = False
    self._refresh_star_search_headings()
    self._populate_star_search_tree()

def _star_search_sort_value(self, star):
    column = self.star_search_sort_column
    if column == "name":
        return str(star.get("name", "")).casefold()
    if column == "designation":
        return self._format_star_search_designation(star).casefold()
    if column == "spectral_type":
        return str(star.get("spectral_type", "")).casefold()
    if column == "magnitude":
        return star.get("magnitude")
    if column == "max_altitude":
        return star.get("max_altitude")
    if column == "max_night_altitude":
        return star.get("max_night_altitude")
    if column == "transit_time":
        return star.get("meridian_transit_sort_timestamp")
    if column == "ra":
        return star.get("ra_hours")
    if column == "declination":
        return star.get("declination")
    if column == "source":
        return str(star.get("source", "")).casefold()
    return str(star.get("name", "")).casefold()

def _star_search_tree_xview(self, *args):
    if self.star_search_tree is None:
        return
    self.star_search_tree.xview(*args)
    self._schedule_star_search_tree_separator_refresh()

def _on_star_search_tree_xscroll(self, scrollbar, first, last):
    scrollbar.set(first, last)
    self._schedule_star_search_tree_separator_refresh()

def _schedule_star_search_tree_separator_refresh(self):
    if self.star_search_tree_separator_refresh_pending or self.star_search_tree is None:
        return
    self.star_search_tree_separator_refresh_pending = True

    def refresh():
        self.star_search_tree_separator_refresh_pending = False
        self._update_star_search_tree_separators()

    self.root.after_idle(refresh)

def _update_star_search_tree_separators(self):
    if self.star_search_tree is None:
        return
    for separator in self.star_search_tree_separators:
        separator.destroy()
    self.star_search_tree_separators = []
    tree_height = self.star_search_tree.winfo_height()
    if tree_height <= 1:
        return
    total_width = sum(
        self.star_search_tree.column(column, "width")
        for column in self.star_search_tree["columns"]
    )
    if total_width <= 0:
        return
    visible_width = self.star_search_tree.winfo_width()
    scroll_offset = total_width * self.star_search_tree.xview()[0]
    x_position = -scroll_offset
    for column in self.star_search_tree["columns"][:-1]:
        x_position += self.star_search_tree.column(column, "width")
        if x_position <= 0 or x_position >= visible_width:
            continue
        separator = tk.Frame(
            self.star_search_tree,
            bg=self.card_edge,
            width=1,
            bd=0,
            highlightthickness=0,
        )
        separator.place(x=x_position, y=0, width=1, height=tree_height)
        separator.lift()
        self.star_search_tree_separators.append(separator)

def _ensure_star_search_cache_loaded(self):
    if self.star_search_cache_loaded:
        return
    self.star_search_cached_stars = load_cached_simbad_stars()
    self.star_search_cache_loaded = True

def _star_search_catalog(self, cached_stars=None, spectral_type=None, magnitude_band=None):
    if cached_stars is None:
        cached_stars = self.star_search_cached_stars
    if spectral_type is not None:
        spectral_type = normalize_star_spectral_type(spectral_type)
    if magnitude_band is not None:
        magnitude_band = normalize_star_magnitude_band(magnitude_band)

    local_stars = local_star_search_objects()
    if spectral_type is not None:
        local_stars = [
            star for star in local_stars if star.get("spectral_class") == spectral_type
        ]

    filtered_cached_stars = list(cached_stars or [])
    if spectral_type is not None:
        filtered_cached_stars = [
            star
            for star in filtered_cached_stars
            if star.get("spectral_class") == spectral_type
        ]

    if not filtered_cached_stars:
        return merge_star_search_objects(
            local_stars,
            preferred_band=magnitude_band or self._current_star_search_magnitude_band(),
        )
    if not local_stars:
        return merge_star_search_objects(
            filtered_cached_stars,
            preferred_band=magnitude_band or self._current_star_search_magnitude_band(),
        )
    return merge_star_search_objects(
        local_stars,
        filtered_cached_stars,
        preferred_band=magnitude_band or self._current_star_search_magnitude_band(),
    )

def _stars_to_jnow(self, stars):
    normalized = []
    for star in stars:
        item = dict(star)
        item.setdefault("coordinate_frame", "j2000")
        normalized.append(item)
    try:
        catalog = [
            (index, star["ra_hours"], star["declination"], star.get("magnitude", 0))
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

def _filter_star_search_list(self, stars, filters, visibility_context=None):
    if visibility_context is None:
        visibility_context = self._deep_sky_visibility_context()
    candidates = []
    for star in stars:
        if star.get("spectral_class") != filters["spectral_type"]:
            continue
        if star.get("magnitude_band") != filters["magnitude_band"]:
            continue
        magnitude = star.get("magnitude")
        if magnitude is None:
            continue
        if (
            filters.get("exclude_suspect_magnitudes", False)
            and "E" in str(star.get("magnitude_flag", "")).upper()
        ):
            continue
        if not filters["min_magnitude"] <= magnitude <= filters["max_magnitude"]:
            continue
        candidates.append(star)

    filtered = []
    for star in self._stars_to_jnow(candidates):
        star.update(self._deep_sky_visibility_metrics(star, visibility_context))
        if filters.get("exclude_polar_circle", False) and star["declination"] > 60:
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

def _format_star_search_magnitude(self, star):
    magnitude = star.get("magnitude")
    if magnitude is None:
        return "-"
    band = star.get("magnitude_band") or ""
    suffix = f" {band}" if band else ""
    return f"{magnitude:.2f}{suffix}"

def _format_star_search_designation(self, star):
    aliases = []
    for value in star.get("aliases", ()):
        text = str(value or "").strip()
        if text and text not in aliases:
            aliases.append(text)
    return " / ".join(aliases)

def _populate_star_search_tree(self):
    if self.star_search_tree is None:
        return
    self.star_search_tree.delete(*self.star_search_tree.get_children())
    text_columns = {"name", "designation", "spectral_type", "source"}
    if self.star_search_sort_column in text_columns:
        key = self._star_search_sort_value
        reverse = self.star_search_sort_reverse
    else:
        def key(star):
            value = self._star_search_sort_value(star)
            name = str(star.get("name", "")).casefold()
            if value is None:
                return (1, 0, name)
            value = float(value)
            if self.star_search_sort_reverse:
                value = -value
            return (0, value, name)
        reverse = False
    self.star_search_results.sort(key=key, reverse=reverse)
    for index, star in enumerate(self.star_search_results):
        self.star_search_tree.insert(
            "",
            "end",
            iid=str(index),
            values=(
                star["name"],
                self._format_star_search_designation(star),
                star.get("spectral_type", ""),
                self._format_star_search_magnitude(star),
                self._format_deep_sky_angle(star.get("max_altitude")),
                self._format_deep_sky_angle(star.get("max_night_altitude")),
                self._format_transit_time(
                    star.get("meridian_transit_local_datetime")
                ),
                self._format_deep_sky_ra(star),
                self._format_deep_sky_dec(star),
                star.get("source", ""),
            ),
            tags=("odd" if index % 2 else "even",),
        )
    self._update_star_search_tree_separators()

def _render_star_search_results(self, stars, total, note=None):
    self.star_search_results = list(stars)
    self._populate_star_search_tree()
    status = self._tr("star_search.result_count", count=len(self.star_search_results), total=total)
    if note:
        status = f"{status}\n{note}"
    self.star_search_status_label.config(text=status)

def search_stars(self, allow_online=False):
    filters = self._read_star_search_filters()
    if filters is None:
        return
    self._save_current_settings()
    self._ensure_star_search_cache_loaded()
    self.star_search_generation += 1
    generation = self.star_search_generation
    self.star_search_pending = True
    if allow_online and self.network_online is False:
        allow_online = False
        offline_note = self._tr("star_search.online_offline")
    else:
        offline_note = None
    status_key = "star_search.searching_online" if allow_online else "star_search.filtering"
    self.star_search_status_label.config(text=self._tr(status_key))
    for button in (
        self.star_search_apply_button,
        self.star_search_online_button,
        self.star_search_reset_button,
        self.star_search_clear_cache_button,
    ):
        if button is not None:
            button.config(state=tk.DISABLED)
    search_context = self._double_search_context()
    threading.Thread(
        target=self._run_star_search,
        args=(generation, filters, search_context, allow_online, offline_note),
        daemon=True,
    ).start()

def _run_star_search(self, generation, filters, search_context, allow_online=False, offline_note=None):
    try:
        visibility_context = self._deep_sky_visibility_context(search_context)
        catalog = self._star_search_catalog(
            spectral_type=filters["spectral_type"],
            magnitude_band=filters["magnitude_band"],
        )
        notes = [offline_note] if offline_note else []
        cached_stars = None
        if allow_online:
            try:
                remote_stars = fetch_simbad_stars(
                    filters["spectral_type"],
                    filters["min_magnitude"],
                    filters["max_magnitude"],
                    filters["magnitude_band"],
                )
                cached_stars = merge_cached_simbad_stars(
                    remote_stars,
                    filters["spectral_type"],
                    filters["magnitude_band"],
                )
                catalog = self._star_search_catalog(
                    cached_stars,
                    spectral_type=filters["spectral_type"],
                    magnitude_band=filters["magnitude_band"],
                )
                notes.append(self._tr("star_search.online_loaded", count=len(remote_stars)))
                notes.append(self._tr("star_search.cache_updated", count=len(cached_stars)))
            except Exception as exc:
                notes.append(self._tr("star_search.online_error", error=str(exc)))
        category_catalog = [
            star
            for star in catalog
            if star.get("spectral_class") == filters["spectral_type"]
            and star.get("magnitude_band") == filters["magnitude_band"]
        ]
        filtered = self._filter_star_search_list(catalog, filters, visibility_context)
        self._queue_star_search_results(
            generation,
            {
                "stars": filtered,
                "total": len(category_catalog),
                "note": "\n".join(note for note in notes if note),
                "cached_stars": cached_stars,
            },
        )
    except Exception as exc:
        self._queue_star_search_results(
            generation,
            {
                "stars": [],
                "total": 0,
                "note": self._tr("star_search.search_error", error=str(exc)),
            },
        )

def _queue_star_search_results(self, generation, payload):
    try:
        self.root.after(0, lambda: self._apply_star_search_results(generation, payload))
    except (tk.TclError, RuntimeError):
        self.star_search_pending = False

def _apply_star_search_results(self, generation, payload):
    if generation != self.star_search_generation:
        return
    self.star_search_pending = False
    if payload.get("cached_stars") is not None:
        self.star_search_cached_stars = payload["cached_stars"]
    for button in (
        self.star_search_apply_button,
        self.star_search_online_button,
        self.star_search_reset_button,
        self.star_search_clear_cache_button,
    ):
        if button is not None:
            button.config(state=tk.NORMAL)
    self._render_star_search_results(payload["stars"], payload["total"], payload.get("note"))

def _selected_star_search_star(self):
    if self.star_search_tree is None:
        return None
    selection = self.star_search_tree.selection()
    if not selection:
        return None
    index = int(selection[0])
    if index < 0 or index >= len(self.star_search_results):
        return None
    return self.star_search_results[index]

def set_selected_star_target(self):
    star = self._selected_star_search_star()
    if star is None:
        self.star_search_status_label.config(text=self._tr("star_search.no_selection"))
        return
    self._set_target_from_coordinates(
        star["ra_hours"],
        star["declination"],
        self._tr("star_search.target_set", name=star["name"]),
        display_name=star["name"],
    )
    self.notebook.select(self.main_tab)

STAR_SEARCH_METHODS = (
    _create_star_search_widgets,
    _ensure_star_search_tab_initialized,
    _schedule_initial_star_search_load,
    _save_star_search_filters_if_valid,
    _current_star_search_spectral_type,
    _current_star_search_magnitude_band,
    _default_star_search_filters,
    _apply_star_search_filter_controls,
    reset_star_search_filters,
    clear_star_search_cache,
    _read_star_search_filters,
    _star_search_heading_keys,
    _refresh_star_search_headings,
    _sort_star_search_table,
    _star_search_sort_value,
    _star_search_tree_xview,
    _on_star_search_tree_xscroll,
    _schedule_star_search_tree_separator_refresh,
    _update_star_search_tree_separators,
    _ensure_star_search_cache_loaded,
    _star_search_catalog,
    _stars_to_jnow,
    _filter_star_search_list,
    _format_star_search_magnitude,
    _format_star_search_designation,
    _populate_star_search_tree,
    _render_star_search_results,
    search_stars,
    _run_star_search,
    _queue_star_search_results,
    _apply_star_search_results,
    _selected_star_search_star,
    set_selected_star_target,
)


def install_star_search_methods(app_class):
    for method in STAR_SEARCH_METHODS:
        setattr(app_class, method.__name__, method)
