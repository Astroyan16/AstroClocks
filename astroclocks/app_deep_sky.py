"""Deep-sky tab UI and search helpers for AstroClocks."""

import datetime
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

from astroclocks import app_dialogs
from astroclocks.astronomy import j2000_to_jnow_coordinates
from astroclocks.deep_sky_catalog import (
    DEEP_SKY_CATEGORY_ORDER,
    clear_cached_simbad_deep_sky_objects,
    deep_sky_search_objects,
    fetch_simbad_deep_sky_objects,
    merge_cached_simbad_deep_sky_objects,
    merge_deep_sky_objects,
    normalize_deep_sky_magnitude_band,
)
from astroclocks.settings import (
    DEFAULT_DEEP_SKY_CATEGORY,
    DEFAULT_DEEP_SKY_MAX_MAGNITUDE,
    DEFAULT_DEEP_SKY_MAGNITUDE_BAND,
    DEFAULT_DEEP_SKY_MIN_MAGNITUDE,
    DEFAULT_DEEP_SKY_MIN_MAX_ALTITUDE,
    DEFAULT_DEEP_SKY_EXCLUDE_POLAR_CIRCLE,
    DEFAULT_DEEP_SKY_EXCLUDE_SUSPECT_MAGNITUDES,
    DEFAULT_DEEP_SKY_TRANSIT_NIGHT,
    DEFAULT_DEEP_SKY_VISIBLE_NIGHT,
    DEEP_SKY_MAGNITUDE_BANDS,
)


DEEP_SKY_NIGHT_SUN_MAX_ALTITUDE = -6
DEEP_SKY_NIGHT_TARGET_MIN_ALTITUDE = 10


def _create_deep_sky_widgets(self):
    controls = tk.Frame(self.deep_sky_tab, bg=self.card_bg)
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
        "deep_sky.filters",
    ).grid(column=0, row=0, pady=(0, 10), sticky="ew")

    self.deep_sky_category_var = tk.StringVar()
    self.deep_sky_magnitude_band_var = tk.StringVar(
        value=self._current_deep_sky_magnitude_band()
    )
    self.deep_sky_min_mag_var = tk.StringVar(
        value=self._format_double_filter_number(self.settings.deep_sky_min_magnitude)
    )
    self.deep_sky_max_mag_var = tk.StringVar(
        value=self._format_double_filter_number(self.settings.deep_sky_max_magnitude)
    )
    self.deep_sky_min_altitude_var = tk.StringVar(
        value=self._format_double_filter_number(self.settings.deep_sky_min_max_altitude)
    )
    self.deep_sky_visible_night_var = tk.BooleanVar(
        value=self.settings.deep_sky_visible_night
    )
    self.deep_sky_transit_night_var = tk.BooleanVar(
        value=self.settings.deep_sky_transit_night
    )
    self.deep_sky_exclude_polar_circle_var = tk.BooleanVar(
        value=self.settings.deep_sky_exclude_polar_circle
    )
    self.deep_sky_exclude_suspect_magnitudes_var = tk.BooleanVar(
        value=self.settings.deep_sky_exclude_suspect_magnitudes
    )

    category_label = tk.Label(
        controls,
        text=self._tr("deep_sky.category"),
        bg=self.card_bg,
        fg=self.text,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
    )
    self._register_translated_widget(category_label, "deep_sky.category")
    category_label.grid(column=0, row=1, sticky="ew", pady=(6, 2))

    self.deep_sky_category_combo = ttk.Combobox(
        controls,
        textvariable=self.deep_sky_category_var,
        state="readonly",
        style="Dark.TCombobox",
        width=24,
    )
    self.deep_sky_category_combo.grid(column=0, row=2, sticky="ew")
    self.deep_sky_category_combo.bind(
        "<<ComboboxSelected>>",
        self._on_deep_sky_category_changed,
    )

    magnitude_band_label = tk.Label(
        controls,
        text=self._tr("deep_sky.magnitude_band"),
        bg=self.card_bg,
        fg=self.text,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
    )
    self._register_translated_widget(magnitude_band_label, "deep_sky.magnitude_band")
    magnitude_band_label.grid(column=0, row=3, sticky="ew", pady=(6, 2))

    self.deep_sky_magnitude_band_combo = ttk.Combobox(
        controls,
        textvariable=self.deep_sky_magnitude_band_var,
        state="readonly",
        style="Dark.TCombobox",
        width=24,
        values=DEEP_SKY_MAGNITUDE_BANDS,
    )
    self.deep_sky_magnitude_band_combo.grid(column=0, row=4, sticky="ew")
    self.deep_sky_magnitude_band_combo.bind(
        "<<ComboboxSelected>>",
        self._on_deep_sky_magnitude_band_changed,
    )

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
        entry.bind("<Return>", lambda _event: self.search_deep_sky_objects())
        entry.bind("<FocusOut>", self._save_deep_sky_filters_if_valid)
        return entry

    magnitude_frame = tk.Frame(controls, bg=self.card_bg)
    magnitude_frame.grid(column=0, row=5, sticky="ew")
    magnitude_frame.grid_columnconfigure(0, weight=1)
    magnitude_frame.grid_columnconfigure(1, weight=1)
    self.deep_sky_magnitude_entries = [
        add_filter(
            magnitude_frame,
            0,
            "deep_sky.min_magnitude",
            self.deep_sky_min_mag_var,
            column=0,
        ),
        add_filter(
            magnitude_frame,
            0,
            "deep_sky.max_magnitude",
            self.deep_sky_max_mag_var,
            column=1,
        ),
    ]

    add_filter(controls, 7, "deep_sky.min_max_altitude", self.deep_sky_min_altitude_var)

    self._register_translated_widget(
        self._build_inline_checkbutton(
            controls,
            self.deep_sky_visible_night_var,
            self._tr("deep_sky.visible_night"),
            self._save_deep_sky_filters_if_valid,
        ),
        "deep_sky.visible_night",
    ).grid(column=0, row=9, pady=(12, 0), sticky="ew")
    self._register_translated_widget(
        self._build_inline_checkbutton(
            controls,
            self.deep_sky_transit_night_var,
            self._tr("deep_sky.transit_night"),
            self._save_deep_sky_filters_if_valid,
        ),
        "deep_sky.transit_night",
    ).grid(column=0, row=10, pady=(4, 0), sticky="ew")
    self._register_translated_widget(
        self._build_inline_checkbutton(
            controls,
            self.deep_sky_exclude_polar_circle_var,
            self._tr("deep_sky.exclude_polar_circle"),
            self._save_deep_sky_filters_if_valid,
        ),
        "deep_sky.exclude_polar_circle",
    ).grid(column=0, row=11, pady=(4, 0), sticky="ew")
    self._register_translated_widget(
        self._build_inline_checkbutton(
            controls,
            self.deep_sky_exclude_suspect_magnitudes_var,
            self._tr("deep_sky.exclude_suspect_magnitudes"),
            self._save_deep_sky_filters_if_valid,
        ),
        "deep_sky.exclude_suspect_magnitudes",
    ).grid(column=0, row=12, pady=(4, 0), sticky="ew")

    self.deep_sky_apply_button = self._build_button(
        controls,
        self._tr("deep_sky.apply_filters"),
        lambda: self.search_deep_sky_objects(allow_online=False),
    )
    self.deep_sky_apply_button.grid(column=0, row=13, pady=(14, 6), sticky="ew")

    self.deep_sky_online_button = self._build_button(
        controls,
        self._tr("deep_sky.online_search"),
        lambda: self.search_deep_sky_objects(allow_online=True),
    )
    self.deep_sky_online_button.grid(column=0, row=14, pady=(0, 6), sticky="ew")

    self.deep_sky_set_button = self._build_button(
        controls,
        self._tr("deep_sky.set_target"),
        self.set_selected_deep_sky_target,
    )
    self.deep_sky_set_button.grid(column=0, row=15, pady=(0, 6), sticky="ew")

    self.deep_sky_clear_cache_button = self._build_button(
        controls,
        self._tr("button.clear_cache"),
        self.clear_deep_sky_cache,
    )
    self.deep_sky_clear_cache_button.grid(column=0, row=16, pady=(0, 6), sticky="ew")

    self.deep_sky_reset_button = self._build_button(
        controls,
        self._tr("deep_sky.reset_filters"),
        self.reset_deep_sky_filters,
    )
    self.deep_sky_reset_button.grid(column=0, row=17, pady=(0, 12), sticky="ew")

    self.deep_sky_status_label = tk.Label(
        controls,
        bg=self.card_bg,
        fg=self.muted,
        font=Font(family="Segoe UI", size=9),
        justify="left",
        wraplength=220,
        anchor="nw",
    )
    self.deep_sky_status_label.grid(column=0, row=18, sticky="ew")

    results_frame = self._build_labelframe(
        "frame.deep_sky",
        1,
        0,
        parent=self.deep_sky_tab,
        padx=(8, 12),
        pady=12,
    )
    results_frame.grid_columnconfigure(0, weight=1)
    results_frame.grid_rowconfigure(0, weight=1)

    columns = (
        "name",
        "aliases",
        "type",
        "magnitude",
        "max_altitude",
        "max_night_altitude",
        "transit_time",
        "ra",
        "declination",
        "source",
    )
    self.deep_sky_tree = ttk.Treeview(
        results_frame,
        columns=columns,
        show="headings",
        selectmode="browse",
    )
    self.deep_sky_tree.grid(column=0, row=0, sticky="nsew", padx=(8, 0), pady=8)
    scrollbar = ttk.Scrollbar(
        results_frame,
        orient="vertical",
        command=self.deep_sky_tree.yview,
        style="Dark.Vertical.TScrollbar",
    )
    scrollbar.grid(column=1, row=0, sticky="ns", padx=(0, 8), pady=8)
    horizontal_scrollbar = ttk.Scrollbar(
        results_frame,
        orient="horizontal",
        command=self._deep_sky_tree_xview,
        style="Dark.Horizontal.TScrollbar",
    )
    horizontal_scrollbar.grid(column=0, row=1, sticky="ew", padx=(8, 0), pady=(0, 8))
    self.deep_sky_tree.configure(
        yscrollcommand=scrollbar.set,
        xscrollcommand=lambda first, last: self._on_deep_sky_tree_xscroll(
            horizontal_scrollbar,
            first,
            last,
        ),
    )
    self.deep_sky_tree.bind("<Double-1>", lambda _event: self.set_selected_deep_sky_target())
    self.deep_sky_tree.bind(
        "<Configure>",
        lambda _event: self._schedule_deep_sky_tree_separator_refresh(),
    )
    self.deep_sky_tree.bind(
        "<ButtonRelease-1>",
        lambda _event: self._schedule_deep_sky_tree_separator_refresh(),
    )
    self.deep_sky_tree.bind(
        "<B1-Motion>",
        lambda _event: self._schedule_deep_sky_tree_separator_refresh(),
    )
    self.deep_sky_tree.tag_configure("odd", background="#0e151b")
    self.deep_sky_tree.tag_configure("even", background=self.ebg)

    column_widths = {
        "name": 145,
        "aliases": 260,
        "type": 145,
        "magnitude": 90,
        "max_altitude": 90,
        "max_night_altitude": 95,
        "transit_time": 82,
        "ra": 95,
        "declination": 95,
        "source": 170,
    }
    column_min_widths = {
        "name": 120,
        "aliases": 180,
        "type": 120,
        "magnitude": 80,
        "max_altitude": 85,
        "max_night_altitude": 90,
        "transit_time": 74,
        "ra": 85,
        "declination": 85,
        "source": 130,
    }
    for column, width in column_widths.items():
        anchor = "center" if column in {"magnitude", "max_altitude", "max_night_altitude", "transit_time"} else "w"
        self.deep_sky_tree.column(
            column,
            width=width,
            minwidth=column_min_widths[column],
            anchor=anchor,
        )

    self._set_deep_sky_category_values(self.settings.deep_sky_category)
    self._refresh_deep_sky_headings()
    self._update_deep_sky_tree_separators()
    if self.deep_sky_status_label is not None:
        self.deep_sky_status_label.config(text=self._tr("deep_sky.loading_objects"))
    self._update_deep_sky_search_buttons_state()


def _update_deep_sky_search_buttons_state(self):
    search_pending = bool(self.deep_sky_search_pending)
    online_available = self.network_online is not False
    self._set_button_enabled(self.deep_sky_apply_button, not search_pending)
    self._set_button_enabled(
        self.deep_sky_online_button,
        (not search_pending) and online_available,
    )
    self._set_button_enabled(self.deep_sky_reset_button, not search_pending)
    self._set_button_enabled(self.deep_sky_clear_cache_button, not search_pending)


def _ensure_deep_sky_tab_initialized(self):
    if self.deep_sky_tab_initialized:
        return
    self._create_deep_sky_widgets()
    self.deep_sky_tab_initialized = True

def _schedule_initial_deep_sky_load(self):
    if self.deep_sky_initial_load_started:
        return
    self.deep_sky_initial_load_started = True
    self.root.after(120, lambda: self.search_deep_sky_objects(allow_online=False))

def _deep_sky_uses_magnitude_filter(self, category=None):
    active_category = category or self._current_deep_sky_category_code()
    return active_category != "dark_nebula"

def _on_deep_sky_category_changed(self, _event=None):
    self._update_deep_sky_magnitude_filter_state()
    self._save_deep_sky_filters_if_valid()

def _on_deep_sky_magnitude_band_changed(self, _event=None):
    self._refresh_deep_sky_headings()
    self._save_deep_sky_filters_if_valid()

def _update_deep_sky_magnitude_filter_state(self):
    state = tk.NORMAL if self._deep_sky_uses_magnitude_filter() else tk.DISABLED
    for entry in getattr(self, "deep_sky_magnitude_entries", ()):
        entry.config(
            state=state,
            disabledbackground=self.card_edge,
            disabledforeground=self.muted,
        )
    if self.deep_sky_magnitude_band_combo is not None:
        self.deep_sky_magnitude_band_combo.config(
            state="readonly" if state == tk.NORMAL else tk.DISABLED
        )

def _deep_sky_category_values(self):
    values = []
    label_to_code = {}
    for code in DEEP_SKY_CATEGORY_ORDER:
        label = self._tr(f"deep_sky.category.{code}")
        values.append(label)
        label_to_code[label] = code
    return values, label_to_code

def _set_deep_sky_category_values(self, selected_code=None):
    if getattr(self, "deep_sky_category_combo", None) is None:
        return

    current_code = selected_code or self._current_deep_sky_category_code()
    values, label_to_code = self._deep_sky_category_values()
    self.deep_sky_category_label_to_code = label_to_code
    self.deep_sky_category_combo.config(values=values)
    selected_label = next(
        (
            label
            for label, code in label_to_code.items()
            if code == current_code
        ),
        values[0],
    )
    self.deep_sky_category_var.set(selected_label)
    self._update_deep_sky_magnitude_filter_state()

def _current_deep_sky_category_code(self):
    category_var = getattr(self, "deep_sky_category_var", None)
    label = category_var.get() if category_var is not None else ""
    return self.deep_sky_category_label_to_code.get(
        label,
        getattr(self.settings, "deep_sky_category", DEFAULT_DEEP_SKY_CATEGORY),
    )

def _current_deep_sky_magnitude_band(self):
    band_var = getattr(self, "deep_sky_magnitude_band_var", None)
    band = (
        band_var.get()
        if band_var is not None
        else getattr(
            self.settings,
            "deep_sky_magnitude_band",
            DEFAULT_DEEP_SKY_MAGNITUDE_BAND,
        )
    )
    return normalize_deep_sky_magnitude_band(band)

def _default_deep_sky_filters(self):
    return {
        "category": DEFAULT_DEEP_SKY_CATEGORY,
        "magnitude_band": DEFAULT_DEEP_SKY_MAGNITUDE_BAND,
        "min_magnitude": DEFAULT_DEEP_SKY_MIN_MAGNITUDE,
        "max_magnitude": DEFAULT_DEEP_SKY_MAX_MAGNITUDE,
        "min_altitude": DEFAULT_DEEP_SKY_MIN_MAX_ALTITUDE,
        "visible_night": DEFAULT_DEEP_SKY_VISIBLE_NIGHT,
        "transit_night": DEFAULT_DEEP_SKY_TRANSIT_NIGHT,
        "exclude_polar_circle": DEFAULT_DEEP_SKY_EXCLUDE_POLAR_CIRCLE,
        "exclude_suspect_magnitudes": DEFAULT_DEEP_SKY_EXCLUDE_SUSPECT_MAGNITUDES,
    }

def _apply_deep_sky_filter_controls(self, filters):
    self._set_deep_sky_category_values(filters["category"])
    if self.deep_sky_magnitude_band_var is not None:
        self.deep_sky_magnitude_band_var.set(
            normalize_deep_sky_magnitude_band(
                filters.get("magnitude_band", DEFAULT_DEEP_SKY_MAGNITUDE_BAND)
            )
        )
    self.deep_sky_min_mag_var.set(
        self._format_double_filter_number(filters["min_magnitude"])
    )
    self.deep_sky_max_mag_var.set(
        self._format_double_filter_number(filters["max_magnitude"])
    )
    self.deep_sky_min_altitude_var.set(
        self._format_double_filter_number(filters["min_altitude"])
    )
    self.deep_sky_visible_night_var.set(filters["visible_night"])
    self.deep_sky_transit_night_var.set(filters["transit_night"])
    self.deep_sky_exclude_polar_circle_var.set(filters["exclude_polar_circle"])
    self.deep_sky_exclude_suspect_magnitudes_var.set(
        filters["exclude_suspect_magnitudes"]
    )
    self._refresh_deep_sky_headings()

def reset_deep_sky_filters(self):
    self._apply_deep_sky_filter_controls(self._default_deep_sky_filters())
    self._save_current_settings()
    self.search_deep_sky_objects(allow_online=False)

def clear_deep_sky_cache(self):
    clear_cached_simbad_deep_sky_objects()
    self.deep_sky_simbad_cached_objects = []
    self.deep_sky_status_label.config(text=self._tr("deep_sky.cache_cleared"))
    self.search_deep_sky_objects(allow_online=False)

def _read_deep_sky_filters(self):
    category = self._current_deep_sky_category_code()
    magnitude_band = self._current_deep_sky_magnitude_band()
    use_magnitude = self._deep_sky_uses_magnitude_filter(category)
    try:
        if use_magnitude:
            min_magnitude = self._parse_float_setting(
                self.deep_sky_min_mag_var.get(),
                self._tr("deep_sky.min_magnitude"),
                -30,
                30,
            )
            max_magnitude = self._parse_float_setting(
                self.deep_sky_max_mag_var.get(),
                self._tr("deep_sky.max_magnitude"),
                -30,
                30,
            )
        else:
            min_magnitude = None
            max_magnitude = None
        min_altitude = self._parse_float_setting(
            self.deep_sky_min_altitude_var.get(),
            self._tr("deep_sky.min_max_altitude"),
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

    if use_magnitude and min_magnitude > max_magnitude:
        min_magnitude, max_magnitude = max_magnitude, min_magnitude
        self.deep_sky_min_mag_var.set(self._format_double_filter_number(min_magnitude))
        self.deep_sky_max_mag_var.set(self._format_double_filter_number(max_magnitude))

    return {
        "category": category,
        "magnitude_band": magnitude_band,
        "use_magnitude": use_magnitude,
        "min_magnitude": min_magnitude,
        "max_magnitude": max_magnitude,
        "min_altitude": min_altitude,
        "visible_night": self.deep_sky_visible_night_var.get(),
        "transit_night": self.deep_sky_transit_night_var.get(),
        "exclude_polar_circle": self.deep_sky_exclude_polar_circle_var.get(),
        "exclude_suspect_magnitudes": self.deep_sky_exclude_suspect_magnitudes_var.get(),
    }

def _deep_sky_heading_keys(self):
    return {
        "name": "deep_sky.column.name",
        "aliases": "deep_sky.column.aliases",
        "type": "deep_sky.column.type",
        "magnitude": "deep_sky.column.magnitude",
        "max_altitude": "deep_sky.column.max_altitude",
        "max_night_altitude": "deep_sky.column.max_night_altitude",
        "transit_time": "deep_sky.column.transit_time",
        "ra": "deep_sky.column.ra",
        "declination": "deep_sky.column.declination",
        "source": "deep_sky.column.source",
    }

def _refresh_deep_sky_headings(self):
    if self.deep_sky_tree is None:
        return

    for column, key in self._deep_sky_heading_keys().items():
        label = self._tr(key)
        if column == "magnitude":
            label = f"{label} ({self._current_deep_sky_magnitude_band()})"
        if column == self.deep_sky_sort_column:
            label = f"{label} {'v' if self.deep_sky_sort_reverse else '^'}"
        self.deep_sky_tree.heading(
            column,
            text=label,
            command=lambda selected_column=column: self._sort_deep_sky_table(
                selected_column
            ),
        )

def _sort_deep_sky_table(self, column):
    if column == self.deep_sky_sort_column:
        self.deep_sky_sort_reverse = not self.deep_sky_sort_reverse
    else:
        self.deep_sky_sort_column = column
        self.deep_sky_sort_reverse = False
    self._refresh_deep_sky_headings()
    self._populate_deep_sky_tree()

def _deep_sky_sort_value(self, sky_object):
    column = self.deep_sky_sort_column
    if column == "name":
        return str(sky_object.get("name", "")).casefold()
    if column == "aliases":
        return self._format_deep_sky_aliases(sky_object).casefold()
    if column == "type":
        return self._deep_sky_category_label(sky_object).casefold()
    if column == "magnitude":
        return sky_object.get("magnitude")
    if column == "max_altitude":
        return sky_object.get("max_altitude")
    if column == "max_night_altitude":
        return sky_object.get("max_night_altitude")
    if column == "transit_time":
        return sky_object.get("meridian_transit_sort_timestamp")
    if column == "ra":
        return sky_object.get("ra_hours")
    if column == "declination":
        return sky_object.get("declination")
    if column == "source":
        return str(sky_object.get("source", "")).casefold()
    return str(sky_object.get("name", "")).casefold()

def _deep_sky_optional_numeric_sort_key(self, sky_object):
    value = self._deep_sky_sort_value(sky_object)
    name = str(sky_object.get("name", "")).casefold()
    if value is None:
        return (1, 0, name)
    value = float(value)
    if self.deep_sky_sort_reverse:
        value = -value
    return (0, value, name)

def _deep_sky_tree_xview(self, *args):
    if self.deep_sky_tree is None:
        return
    self.deep_sky_tree.xview(*args)
    self._schedule_deep_sky_tree_separator_refresh()

def _on_deep_sky_tree_xscroll(self, scrollbar, first, last):
    scrollbar.set(first, last)
    self._schedule_deep_sky_tree_separator_refresh()

def _schedule_deep_sky_tree_separator_refresh(self):
    if self.deep_sky_tree_separator_refresh_pending or self.deep_sky_tree is None:
        return
    self.deep_sky_tree_separator_refresh_pending = True

    def refresh():
        self.deep_sky_tree_separator_refresh_pending = False
        self._update_deep_sky_tree_separators()

    self.root.after_idle(refresh)

def _update_deep_sky_tree_separators(self):
    if self.deep_sky_tree is None:
        return

    for separator in self.deep_sky_tree_separators:
        separator.destroy()
    self.deep_sky_tree_separators = []

    tree_height = self.deep_sky_tree.winfo_height()
    if tree_height <= 1:
        return

    total_width = sum(
        self.deep_sky_tree.column(column, "width")
        for column in self.deep_sky_tree["columns"]
    )
    if total_width <= 0:
        return

    visible_width = self.deep_sky_tree.winfo_width()
    first_fraction = self.deep_sky_tree.xview()[0]
    scroll_offset = total_width * first_fraction
    x_position = -scroll_offset
    for column in self.deep_sky_tree["columns"][:-1]:
        x_position += self.deep_sky_tree.column(column, "width")
        if x_position <= 0 or x_position >= visible_width:
            continue
        separator = tk.Frame(
            self.deep_sky_tree,
            bg=self.card_edge,
            width=1,
            bd=0,
            highlightthickness=0,
        )
        separator.place(x=x_position, y=0, width=1, height=tree_height)
        separator.lift()
        self.deep_sky_tree_separators.append(separator)


def _deep_sky_visibility_context(self, search_context=None):
    return self._double_visibility_context(search_context)

def _deep_sky_objects_to_jnow(self, sky_objects):
    normalized = []
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    for sky_object in sky_objects:
        item = dict(sky_object)
        if item.get("coordinate_frame") == "jnow":
            normalized.append(item)
            continue
        ra_hours, declination = j2000_to_jnow_coordinates(
            item["ra_hours"],
            item["declination"],
            now_utc=now_utc,
        )
        item["ra_hours"] = ra_hours
        item["declination"] = declination
        item["coordinate_frame"] = "jnow"
        normalized.append(item)
    return normalized

def _deep_sky_visibility_metrics(self, sky_object, visibility_context):
    return self._search_visibility_metrics(
        sky_object["ra_hours"],
        sky_object["declination"],
        visibility_context,
        DEEP_SKY_NIGHT_SUN_MAX_ALTITUDE,
        DEEP_SKY_NIGHT_TARGET_MIN_ALTITUDE,
    )

def _filter_deep_sky_list(self, sky_objects, filters, visibility_context=None):
    if visibility_context is None:
        visibility_context = self._deep_sky_visibility_context()

    candidates = []
    for sky_object in sky_objects:
        if sky_object.get("category") != filters["category"]:
            continue
        if filters.get("use_magnitude", True):
            if sky_object.get("magnitude_band") != filters["magnitude_band"]:
                continue
            magnitude = sky_object.get("magnitude")
            if magnitude is None:
                continue
            if (
                filters.get("exclude_suspect_magnitudes", False)
                and "E" in str(sky_object.get("magnitude_flag", "")).upper()
            ):
                continue
            if not filters["min_magnitude"] <= magnitude <= filters["max_magnitude"]:
                continue
        candidates.append(sky_object)

    filtered = []
    for sky_object in self._deep_sky_objects_to_jnow(candidates):
        sky_object.update(self._deep_sky_visibility_metrics(sky_object, visibility_context))
        if filters.get("exclude_polar_circle", False) and sky_object["declination"] > 60:
            continue
        max_altitude = sky_object.get("max_altitude")
        if max_altitude is None or max_altitude < filters["min_altitude"]:
            continue
        if filters.get("visible_night", False) and not sky_object.get("visible_at_night"):
            continue
        if filters.get("transit_night", False) and not sky_object.get("meridian_transit_at_night"):
            continue
        filtered.append(sky_object)
    return filtered

def _deep_sky_catalog(self, preferred_band=None):
    preferred_band = preferred_band or self._current_deep_sky_magnitude_band()
    return merge_deep_sky_objects(
        deep_sky_search_objects(preferred_band=preferred_band),
        self.deep_sky_simbad_cached_objects,
        preferred_band=preferred_band,
    )


def _deep_sky_offline_cache_note(self):
    if self.network_online is not False:
        return None
    cache_count = len(self.deep_sky_simbad_cached_objects or [])
    if cache_count <= 0:
        return None
    return self._tr("deep_sky.offline_cached", count=cache_count)

def _deep_sky_category_label(self, sky_object):
    label = self._tr(f"deep_sky.category.{sky_object.get('category', 'galaxy')}")
    morphology = str(sky_object.get("morphology", "") or "").strip()
    if sky_object.get("category") == "galaxy" and morphology:
        return f"{label} ({morphology})"
    return label

def _format_deep_sky_aliases(self, sky_object):
    aliases = [
        alias
        for alias in sky_object.get("aliases", ())
        if alias and alias != sky_object.get("name")
    ]
    return ", ".join(aliases[:3])

def _format_deep_sky_magnitude(self, sky_object):
    magnitude = sky_object.get("magnitude")
    if magnitude is None:
        return "-"
    band = sky_object.get("magnitude_band") or ""
    suffix = f" {band}" if band else ""
    return f"{magnitude:.2f}{suffix}"

def _format_deep_sky_angle(self, value):
    if value is None:
        return "-"
    return f"{value:+.1f}\N{DEGREE SIGN}"

def _format_deep_sky_ra(self, sky_object):
    total_seconds = int(round((float(sky_object["ra_hours"]) % 24) * 3600))
    total_seconds %= 24 * 3600
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def _format_deep_sky_dec(self, sky_object):
    declination = float(sky_object["declination"])
    sign = "-" if declination < 0 else "+"
    total_seconds = int(round(abs(declination) * 3600))
    degrees = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{sign}{degrees:02d}:{minutes:02d}:{seconds:02d}"

def _format_deep_sky_source(self, sky_object):
    source = str(sky_object.get("source", ""))
    if source.startswith("OpenNGC"):
        return "OpenNGC"
    return source

def _populate_deep_sky_tree(self):
    if self.deep_sky_tree is None:
        return

    if self.deep_sky_sort_column in {"magnitude", "max_altitude", "max_night_altitude", "transit_time", "ra", "declination"}:
        self.deep_sky_results.sort(key=self._deep_sky_optional_numeric_sort_key)
    else:
        self.deep_sky_results.sort(
            key=lambda sky_object: self._deep_sky_sort_value(sky_object),
            reverse=self.deep_sky_sort_reverse,
        )

    for item in self.deep_sky_tree.get_children():
        self.deep_sky_tree.delete(item)

    for index, sky_object in enumerate(self.deep_sky_results):
        self.deep_sky_tree.insert(
            "",
            "end",
            iid=str(index),
            values=(
                sky_object["name"],
                self._format_deep_sky_aliases(sky_object),
                self._deep_sky_category_label(sky_object),
                self._format_deep_sky_magnitude(sky_object),
                self._format_deep_sky_angle(sky_object.get("max_altitude")),
                self._format_deep_sky_angle(sky_object.get("max_night_altitude")),
                self._format_transit_time(
                    sky_object.get("meridian_transit_local_datetime")
                ),
                self._format_deep_sky_ra(sky_object),
                self._format_deep_sky_dec(sky_object),
                self._format_deep_sky_source(sky_object),
            ),
            tags=("odd" if index % 2 else "even",),
        )
    self._update_deep_sky_tree_separators()

def _render_deep_sky_results(self, sky_objects, total, note=None):
    self.deep_sky_results = list(sky_objects)
    self._populate_deep_sky_tree()
    status = self._tr(
        "deep_sky.result_count",
        count=len(self.deep_sky_results),
        total=total,
    )
    if note:
        status = f"{status}\n{note}"
    self.deep_sky_status_label.config(text=status)

def search_deep_sky_objects(self, allow_online=False):
    filters = self._read_deep_sky_filters()
    if filters is None:
        return

    self._save_current_settings()
    self.deep_sky_search_generation += 1
    generation = self.deep_sky_search_generation
    self.deep_sky_search_pending = True
    if allow_online and self.network_online is False:
        allow_online = False
        offline_note = self._tr("deep_sky.online_offline")
    else:
        offline_note = None
    status_key = "deep_sky.searching_online" if allow_online else "deep_sky.filtering"
    self.deep_sky_status_label.config(text=self._tr(status_key))
    self._update_deep_sky_search_buttons_state()
    search_context = self._double_search_context()
    threading.Thread(
        target=self._run_deep_sky_search,
        args=(generation, filters, search_context, allow_online, offline_note),
        daemon=True,
    ).start()

def _run_deep_sky_search(
    self,
    generation,
    filters,
    search_context,
    allow_online=False,
    offline_note=None,
):
    try:
        visibility_context = self._deep_sky_visibility_context(search_context)
        catalog = self._deep_sky_catalog(filters["magnitude_band"])
        notes = [offline_note] if offline_note else []
        offline_cache_note = self._deep_sky_offline_cache_note()
        if offline_cache_note:
            notes.append(offline_cache_note)
        simbad_cached_objects = None
        if allow_online:
            try:
                remote_objects = fetch_simbad_deep_sky_objects(
                    filters["category"],
                    filters["min_magnitude"],
                    filters["max_magnitude"],
                    filters["use_magnitude"],
                    preferred_band=filters["magnitude_band"],
                )
                simbad_cached_objects = merge_cached_simbad_deep_sky_objects(
                    remote_objects,
                    filters["category"],
                )
                catalog = merge_deep_sky_objects(
                    deep_sky_search_objects(
                        preferred_band=filters["magnitude_band"]
                    ),
                    simbad_cached_objects,
                    preferred_band=filters["magnitude_band"],
                )
                notes.append(self._tr("deep_sky.online_loaded", count=len(remote_objects)))
                notes.append(
                    self._tr(
                        "deep_sky.simbad_cache_updated",
                        count=len(simbad_cached_objects),
                    )
                )
            except Exception as exc:
                notes.append(self._tr("deep_sky.online_error", error=str(exc)))

        category_catalog = [
            sky_object
            for sky_object in catalog
            if sky_object.get("category") == filters["category"]
            and (
                not filters.get("use_magnitude", True)
                or sky_object.get("magnitude_band") == filters["magnitude_band"]
            )
        ]
        filtered = self._filter_deep_sky_list(catalog, filters, visibility_context)
        unknown_count = (
            sum(
                1
                for sky_object in category_catalog
                if sky_object.get("magnitude") is None
            )
            if filters.get("use_magnitude", True)
            else 0
        )
        note = (
            self._tr("deep_sky.unknown_magnitudes", count=unknown_count)
            if unknown_count
            else None
        )
        if note:
            notes.append(note)
        self._queue_deep_sky_search_results(
            generation,
            {
                "objects": filtered,
                "total": len(category_catalog),
                "note": "\n".join(note for note in notes if note),
                "simbad_cached_objects": simbad_cached_objects,
            },
        )
    except Exception as exc:
        self._queue_deep_sky_search_results(
            generation,
            {
                "objects": [],
                "total": 0,
                "note": self._tr("deep_sky.search_error", error=str(exc)),
            },
        )

def _queue_deep_sky_search_results(self, generation, payload):
    try:
        self.root.after(
            0,
            lambda: self._apply_deep_sky_search_results(generation, payload),
        )
    except (tk.TclError, RuntimeError):
        self.deep_sky_search_pending = False

def _apply_deep_sky_search_results(self, generation, payload):
    if generation != self.deep_sky_search_generation:
        return
    self.deep_sky_search_pending = False
    if payload.get("simbad_cached_objects") is not None:
        self.deep_sky_simbad_cached_objects = payload["simbad_cached_objects"]
    self._update_deep_sky_search_buttons_state()
    self._render_deep_sky_results(
        payload["objects"],
        payload["total"],
        payload.get("note"),
    )

def _selected_deep_sky_object(self):
    if self.deep_sky_tree is None:
        return None

    selection = self.deep_sky_tree.selection()
    if not selection:
        return None

    index = int(selection[0])
    if index < 0 or index >= len(self.deep_sky_results):
        return None
    return self.deep_sky_results[index]

def set_selected_deep_sky_target(self):
    sky_object = self._selected_deep_sky_object()
    if sky_object is None:
        self.deep_sky_status_label.config(text=self._tr("deep_sky.no_selection"))
        return

    self._set_target_from_coordinates(
        sky_object["ra_hours"],
        sky_object["declination"],
        self._tr("deep_sky.target_set", name=sky_object["name"]),
        display_name=sky_object["name"],
    )
    self.notebook.select(self.main_tab)

DEEP_SKY_METHODS = (
    _create_deep_sky_widgets,
    _update_deep_sky_search_buttons_state,
    _ensure_deep_sky_tab_initialized,
    _schedule_initial_deep_sky_load,
    _deep_sky_uses_magnitude_filter,
    _on_deep_sky_category_changed,
    _on_deep_sky_magnitude_band_changed,
    _update_deep_sky_magnitude_filter_state,
    _deep_sky_category_values,
    _set_deep_sky_category_values,
    _current_deep_sky_category_code,
    _current_deep_sky_magnitude_band,
    _default_deep_sky_filters,
    _apply_deep_sky_filter_controls,
    reset_deep_sky_filters,
    clear_deep_sky_cache,
    _read_deep_sky_filters,
    _deep_sky_heading_keys,
    _refresh_deep_sky_headings,
    _sort_deep_sky_table,
    _deep_sky_sort_value,
    _deep_sky_optional_numeric_sort_key,
    _deep_sky_tree_xview,
    _on_deep_sky_tree_xscroll,
    _schedule_deep_sky_tree_separator_refresh,
    _update_deep_sky_tree_separators,
    _deep_sky_visibility_context,
    _deep_sky_objects_to_jnow,
    _deep_sky_visibility_metrics,
    _filter_deep_sky_list,
    _deep_sky_catalog,
    _deep_sky_offline_cache_note,
    _deep_sky_category_label,
    _format_deep_sky_aliases,
    _format_deep_sky_magnitude,
    _format_deep_sky_angle,
    _format_deep_sky_ra,
    _format_deep_sky_dec,
    _format_deep_sky_source,
    _populate_deep_sky_tree,
    _render_deep_sky_results,
    search_deep_sky_objects,
    _run_deep_sky_search,
    _queue_deep_sky_search_results,
    _apply_deep_sky_search_results,
    _selected_deep_sky_object,
    set_selected_deep_sky_target,
)


def install_deep_sky_methods(app_class):
    for method in DEEP_SKY_METHODS:
        setattr(app_class, method.__name__, method)
