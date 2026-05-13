"""Object-search UI and coordinate-resolution helpers for AstroClocks."""

import threading
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

from astropy.coordinates import name_resolve

from astroclocks.astronomy import (
    resolve_deep_sky_coordinates,
    resolve_local_solar_system_coordinates,
    resolve_solar_system_coordinates,
)
from astroclocks.local_object_catalog import resolve_local_object_coordinates


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


def _with_search_fallback(result, reason):
    if result is None:
        return None
    fallback_result = dict(result)
    fallback_result["_search_fallback_reason"] = reason
    return fallback_result


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


def _set_result_text(self, text, foreground=None):
    self.result_text.config(state=tk.NORMAL, foreground=foreground or self.text)
    self.result_text.delete(1.0, tk.END)
    self.result_text.insert(1.0, text)
    self.result_text.config(state=tk.DISABLED)


def _update_search_button_state(self):
    if self.search_button is None:
        return

    if self.coordinate_search_pending:
        self.search_button.config(text=self._tr("button.searching"), state=tk.DISABLED)
    else:
        self.search_button.config(text=self._tr("button.search"), state=tk.NORMAL)


def _coordinate_result_message(self, result):
    if result.get("source") == "imcce":
        message = self._tr(
            "result.imcce_coordinates",
            ra=result.get("source_ra", ""),
            dec=result.get("source_dec", ""),
        )
    elif result.get("source") == "local_solar":
        message = self._tr(
            "result.local_solar_coordinates",
            ra=result.get("source_ra", ""),
            dec=result.get("source_dec", ""),
        )
    elif result.get("source") == "sesame":
        message = self._tr(
            "result.sesame_coordinates",
            ra=result.get("source_ra", ""),
            dec=result.get("source_dec", ""),
        )
    elif result.get("source") == "local":
        message = self._tr(
            "result.local_coordinates",
            ra=result.get("source_ra", ""),
            dec=result.get("source_dec", ""),
            source=result.get("source_catalog", ""),
            note=result.get("source_note", ""),
        )
    else:
        message = result["message"]
    fallback_reason = result.get("_search_fallback_reason")
    if fallback_reason == "not_found":
        message = f"{message}\n{self._tr('result.local_fallback_not_found')}"
    elif fallback_reason == "error":
        message = f"{message}\n{self._tr('result.local_fallback_error')}"
    return message


def _apply_coordinate_result(self, result):
    result_message = self._coordinate_result_message(result)
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
    preserve_solar_target = result.get("source") == "local_solar"
    self.target_solar_system_name = (
        result.get("solar_system_name") if preserve_solar_target else None
    )
    self.visibility_start_date = None
    self._update_visibility_date_label()
    self.update_value(preserve_solar_target=preserve_solar_target)
    self._set_result_text(result_message, foreground=self._current_target_status_color())


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
        result = _with_search_fallback(fallback_result, "not_found")
        error_key = None if fallback_result is not None else "result.object_not_found"
        error_detail = None
    except Exception as exc:
        result = _with_search_fallback(fallback_result, "error")
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

    active_latitude, active_longitude = self._active_site_coordinates()
    if selected_type in solar_system_types:
        if not object_name:
            self._set_result_text("")
            return
        local_solar_result = resolve_local_solar_system_coordinates(
            object_name,
            latitude=active_latitude,
            longitude=active_longitude,
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
        latitude=active_latitude,
        longitude=active_longitude,
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


def install_object_search_methods(app_class):
    app_class._with_search_fallback = staticmethod(_with_search_fallback)
    app_class._selected_object_type_code = _selected_object_type_code
    app_class._set_object_type_values = _set_object_type_values
    app_class._create_search_widgets = _create_search_widgets
    app_class._set_result_text = _set_result_text
    app_class._update_search_button_state = _update_search_button_state
    app_class._coordinate_result_message = _coordinate_result_message
    app_class._apply_coordinate_result = _apply_coordinate_result
    app_class._start_coordinate_search = _start_coordinate_search
    app_class._run_coordinate_search = _run_coordinate_search
    app_class._apply_coordinate_search_result = _apply_coordinate_search_result
    app_class._solar_system_search_type_for_local_result = _solar_system_search_type_for_local_result
    app_class.search_coordinates = search_coordinates
