"""Double-star tab UI, filtering, and orbit helpers for AstroClocks."""

import datetime
import math
import threading
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

from astroclocks import app_dialogs
from astroclocks.astronomy import (
    compute_clock_state,
    compute_sun_altitudes,
    convert_star_catalog_j2000_to_jnow,
    j2000_to_jnow_coordinates,
)
from astroclocks.double_star_catalog import (
    DOUBLE_STARS,
    clear_cached_wds_double_stars,
    fetch_wds_double_stars,
    merge_cached_wds_double_stars,
)
from astroclocks.orbit_catalog import (
    enrich_double_stars_with_orb6,
    fetch_orb6_ephemerides,
    fetch_orb6_orbits,
)
from astroclocks.settings import (
    DEFAULT_DOUBLE_EXCLUDE_POLAR_CIRCLE,
    DEFAULT_DOUBLE_INCLUDE_APPARENT,
    DEFAULT_DOUBLE_INCLUDE_NOTED,
    DEFAULT_DOUBLE_INCLUDE_PHYSICAL,
    DEFAULT_DOUBLE_INCLUDE_UNCERTAIN,
    DEFAULT_DOUBLE_MAX_PRIMARY_MAGNITUDE,
    DEFAULT_DOUBLE_MAX_SECONDARY_MAGNITUDE,
    DEFAULT_DOUBLE_MAX_SEPARATION,
    DEFAULT_DOUBLE_MIN_MAX_ALTITUDE,
    DEFAULT_DOUBLE_MIN_SEPARATION,
    DEFAULT_DOUBLE_TRANSIT_NIGHT,
    DEFAULT_DOUBLE_USE_ONLINE,
    DEFAULT_DOUBLE_VISIBLE_NIGHT,
)
from astroclocks.utils import is_float


DOUBLE_NIGHT_SUN_MAX_ALTITUDE = -6
DOUBLE_NIGHT_TARGET_MIN_ALTITUDE = 10
DOUBLE_PHYSICAL_NOTE_FLAGS = frozenset({"O", "C", "Z", "T", "V"})
DOUBLE_NOTED_NOTE_FLAGS = frozenset({"N"})
DOUBLE_APPARENT_NOTE_FLAGS = frozenset({"Y", "S", "U"})
DOUBLE_UNCERTAIN_NOTE_FLAGS = frozenset({"I", "X"})


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

def install_double_star_methods(app_class):
    app_class._create_double_star_widgets = _create_double_star_widgets
    app_class._double_advanced_button_text = _double_advanced_button_text
    app_class._toggle_double_advanced_options = _toggle_double_advanced_options
    app_class._restore_double_star_cached_results = _restore_double_star_cached_results
    app_class._ensure_double_star_tab_initialized = _ensure_double_star_tab_initialized
    app_class._schedule_initial_double_star_load = _schedule_initial_double_star_load
    app_class._current_double_filter_settings = _current_double_filter_settings
    app_class._save_double_filters_if_valid = _save_double_filters_if_valid
    app_class._double_star_heading_keys = _double_star_heading_keys
    app_class._refresh_double_star_headings = _refresh_double_star_headings
    app_class._format_double_filter_number = _format_double_filter_number
    app_class._default_double_filters = _default_double_filters
    app_class._apply_double_filter_controls = _apply_double_filter_controls
    app_class.reset_double_star_filters = reset_double_star_filters
    app_class.clear_double_star_cache = clear_double_star_cache
    app_class._sort_double_star_table = _sort_double_star_table
    app_class._double_sort_value = _double_sort_value
    app_class._double_tree_xview = _double_tree_xview
    app_class._on_double_tree_xscroll = _on_double_tree_xscroll
    app_class._schedule_double_tree_separator_refresh = _schedule_double_tree_separator_refresh
    app_class._update_double_tree_separators = _update_double_tree_separators
    app_class._double_filter_value = _double_filter_value
    app_class._read_double_star_filters = _read_double_star_filters
    app_class._double_stars_to_jnow = _double_stars_to_jnow
    app_class._double_search_context = _double_search_context
    app_class._double_visibility_context = _double_visibility_context
    app_class._search_visibility_metrics = _search_visibility_metrics
    app_class._double_star_visibility_metrics = _double_star_visibility_metrics
    app_class._double_note_flags = _double_note_flags
    app_class._double_has_wds_note = _double_has_wds_note
    app_class._double_filter_group = _double_filter_group
    app_class._double_group_allowed = _double_group_allowed
    app_class._double_filter_separation = _double_filter_separation
    app_class._filter_double_star_list = _filter_double_star_list
    app_class._double_star_key = _double_star_key
    app_class._merge_double_star_results = _merge_double_star_results
    app_class._double_local_catalog = _double_local_catalog
    app_class._enrich_double_star_orbits = _enrich_double_star_orbits
    app_class._double_orb6_status_note = _double_orb6_status_note
    app_class._double_star_nature_label = _double_star_nature_label
    app_class._format_double_separation = _format_double_separation
    app_class._format_double_orb6_separation = _format_double_orb6_separation
    app_class._format_double_orb6_pa = _format_double_orb6_pa
    app_class._format_double_max_altitude = _format_double_max_altitude
    app_class._format_transit_time = _format_transit_time
    app_class._format_double_optional_int = _format_double_optional_int
    app_class._format_double_magnitudes = _format_double_magnitudes
    app_class._format_double_designation = _format_double_designation
    app_class._double_orbit_cell_text = _double_orbit_cell_text
    app_class._double_wds_note_cell_text = _double_wds_note_cell_text
    app_class._double_optional_numeric_sort_key = _double_optional_numeric_sort_key
    app_class._cancel_double_tree_render = _cancel_double_tree_render
    app_class._populate_double_star_tree = _populate_double_star_tree
    app_class._double_tree_column_at = _double_tree_column_at
    app_class._double_star_from_tree_row = _double_star_from_tree_row
    app_class._on_double_tree_click = _on_double_tree_click
    app_class._on_double_tree_double_click = _on_double_tree_double_click
    app_class._on_double_tree_motion = _on_double_tree_motion
    app_class._on_double_tree_leave = _on_double_tree_leave
    app_class._render_double_star_results = _render_double_star_results
    app_class.search_double_stars = search_double_stars
    app_class._run_double_star_search = _run_double_star_search
    app_class._queue_double_star_search_results = _queue_double_star_search_results
    app_class._apply_double_star_search_results = _apply_double_star_search_results
    app_class._run_double_star_online_search = _run_double_star_online_search
    app_class._apply_double_star_online_results = _apply_double_star_online_results
    app_class._selected_double_star = _selected_double_star
    app_class.set_selected_double_star_target = set_selected_double_star_target
    app_class._current_decimal_year = _current_decimal_year
    app_class._decimal_year_to_datetime = _decimal_year_to_datetime
    app_class._format_orbit_epoch_label = _format_orbit_epoch_label
    app_class._format_orbit_hover_date = _format_orbit_hover_date
    app_class._orbit_plot_position = _orbit_plot_position
    app_class._orbit_label_anchor = _orbit_label_anchor
    app_class._orbit_external_label_position = _orbit_external_label_position
    app_class._keep_canvas_item_in_bounds = _keep_canvas_item_in_bounds
    app_class.open_double_star_orbit_window = open_double_star_orbit_window
    app_class._set_wds_note_text = _set_wds_note_text
    app_class._format_wds_note_rows = _format_wds_note_rows
    app_class._load_wds_note_rows = _load_wds_note_rows
    app_class.open_double_star_wds_note_window = open_double_star_wds_note_window
    app_class._draw_double_star_orbit = _draw_double_star_orbit
    app_class._on_double_orbit_motion = _on_double_orbit_motion
    app_class._clear_double_orbit_hover = _clear_double_orbit_hover

