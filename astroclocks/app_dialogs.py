"""Dialog windows for AstroClocks.

The functions in this module receive the main ``AstroClocksApp`` instance as
``app`` so the visual styling, translations, callbacks, and cached state stay
owned by the application while the dialog construction lives outside app.py.
"""

import calendar
import datetime
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from tkinter.font import Font

from astroclocks.double_star_catalog import build_wds_notes_url, fetch_wds_notes
from astroclocks.i18n import LANGUAGE_NAMES, LANGUAGE_OPTIONS
from astroclocks.orbit_catalog import orbit_position_at_year, sample_orbit_points
from astroclocks.settings import (
    COORDINATE_SOURCE_APP,
    COORDINATE_SOURCE_MOUNT,
    DEFAULT_ALADIN_FOV_DEG,
    DEFAULT_COUNTRY,
    DEFAULT_COORDINATE_SOURCE,
    DEFAULT_DAYLIGHT_SAVING_ENABLED,
    DEFAULT_DECLINATION_OFFSET_ENABLED,
    DEFAULT_HOUR_ANGLE_OFFSET_ENABLED,
    DEFAULT_LATITUDE,
    DEFAULT_LONGITUDE,
    DEFAULT_MOUNT_SHOW_RETICLE,
    DEFAULT_SITE_NAME,
    DEFAULT_SKY_MAGNITUDE_LIMIT,
    DEFAULT_SKY_SHOW_ALTAZ_GRID,
    DEFAULT_SKY_SHOW_EQUATORIAL_GRID,
    DEFAULT_SKY_SHOW_SOLAR_SYSTEM,
    DEFAULT_TIMEZONE_NAME,
    MAX_SKY_MAGNITUDE_LIMIT,
)
from astroclocks.sites import LOCATION_PRESETS, preset_label
from astroclocks.utils import resource_path


def _apply_app_icon(window, default=False):
    icon_path = resource_path("AppIcon.ico")
    try:
        if default:
            window.iconbitmap(default=icon_path)
        window.iconbitmap(icon_path)
    except (tk.TclError, TypeError):
        pass


def _center_dialog_on_window(app, dialog, parent=None):
    anchor = parent or app.root
    dialog.update_idletasks()
    dialog_width = max(dialog.winfo_width(), dialog.winfo_reqwidth())
    dialog_height = max(dialog.winfo_height(), dialog.winfo_reqheight())

    x = anchor.winfo_rootx() + (anchor.winfo_width() - dialog_width) // 2
    y = anchor.winfo_rooty() + (anchor.winfo_height() - dialog_height) // 2

    anchor_center_x = anchor.winfo_rootx() + (anchor.winfo_width() // 2)
    anchor_center_y = anchor.winfo_rooty() + (anchor.winfo_height() // 2)
    monitor_x, monitor_y, monitor_width, monitor_height = app._monitor_geometry_from_point(
        anchor_center_x,
        anchor_center_y,
        use_work_area=True,
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

    app._apply_native_window_chrome(dialog)
    app._move_window_to(dialog, x, y)
    dialog.lift(anchor)


def show_error_dialog(app, title, message, parent=None):
    anchor = parent or app.root
    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(title)
    _apply_app_icon(dialog)
    dialog.configure(bg=app.gbg)
    dialog.resizable(False, False)
    dialog.transient(anchor)
    dialog.grab_set()
    app._apply_native_window_chrome(dialog)

    body = tk.Frame(
        dialog,
        bg=app.card_bg,
        padx=18,
        pady=18,
        highlightbackground=app.card_edge,
        highlightthickness=1,
        bd=0,
    )
    body.grid(column=0, row=0, padx=12, pady=12, sticky="nsew")
    body.grid_columnconfigure(1, weight=1)

    icon_canvas = tk.Canvas(
        body,
        width=44,
        height=44,
        bg=app.card_bg,
        highlightthickness=0,
        bd=0,
    )
    icon_canvas.grid(column=0, row=0, padx=(0, 14), sticky="n")
    icon_canvas.create_oval(4, 4, 40, 40, fill=app.danger, outline=app.danger)
    icon_canvas.create_text(
        22,
        22,
        text="!",
        fill=app.ebg,
        font=Font(family="Segoe UI", size=20, weight="bold"),
    )

    text_frame = tk.Frame(body, bg=app.card_bg)
    text_frame.grid(column=1, row=0, sticky="ew")
    tk.Label(
        text_frame,
        text=title,
        bg=app.card_bg,
        fg=app.fg,
        font=Font(family="Segoe UI", size=12, weight="bold"),
        anchor="w",
    ).grid(column=0, row=0, sticky="ew")
    tk.Label(
        text_frame,
        text=message,
        bg=app.card_bg,
        fg=app.text,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
        justify="left",
        wraplength=360,
    ).grid(column=0, row=1, sticky="ew", pady=(8, 0))

    actions = tk.Frame(body, bg=app.card_bg)
    actions.grid(column=0, row=1, columnspan=2, sticky="e", pady=(18, 0))
    app._build_button(actions, app._tr("button.close"), dialog.destroy).grid(column=0, row=0)

    dialog.bind("<Return>", lambda _event: dialog.destroy())
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    _center_dialog_on_window(app, dialog, anchor)
    app._reveal_dialog(dialog, anchor=anchor, focus=True)


def open_about_dialog(
    app,
    app_version,
    release_date_text,
    author,
    email,
    phone,
    initial_update_result=None,
):
    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(app._tr("about.title"))
    _apply_app_icon(dialog)
    dialog.configure(bg=app.gbg)
    dialog.resizable(False, False)
    dialog.transient(app.root)
    dialog.grab_set()
    app._apply_native_window_chrome(dialog)

    body = tk.Frame(
        dialog,
        bg=app.card_bg,
        padx=24,
        pady=20,
        highlightbackground=app.card_edge,
        highlightthickness=1,
        bd=0,
    )
    body.grid(column=0, row=0, padx=12, pady=12, sticky="nsew")
    body.grid_columnconfigure(1, weight=1)

    tk.Label(
        body,
        text="AstroClocks",
        bg=app.card_bg,
        fg=app.fg,
        font=Font(family="Segoe UI", size=20, weight="bold"),
    ).grid(column=0, row=0, columnspan=2, sticky="w")
    tk.Label(
        body,
        text=f"v{app_version} | {release_date_text}",
        bg=app.card_bg,
        fg=app.muted,
        font=Font(family="Segoe UI", size=10),
    ).grid(column=0, row=1, columnspan=2, sticky="w", pady=(2, 2))
    tk.Label(
        body,
        text=app._tr("about.license_inline"),
        bg=app.card_bg,
        fg=app.muted,
        font=Font(family="Segoe UI", size=9),
        anchor="w",
    ).grid(column=0, row=2, columnspan=2, sticky="w", pady=(0, 14))

    tk.Frame(body, bg=app.card_edge, height=1).grid(
        column=0, row=3, columnspan=2, sticky="ew", pady=(0, 14)
    )

    label_font = Font(family="Segoe UI", size=10, weight="bold")
    value_font = Font(family="Segoe UI", size=11)
    email_font = Font(family="Segoe UI", size=11, underline=True)
    section_font = Font(family="Segoe UI", size=11, weight="bold")
    status_var = tk.StringVar(value=app._tr("about.update.idle"))
    version_var = tk.StringVar(value=app._tr("about.current_version", version=app_version))
    update_state = {"busy": False, "release": None}

    def add_row(row, label, value, link=False):
        tk.Label(
            body,
            text=f"{label} :",
            bg=app.card_bg,
            fg=app.muted,
            font=label_font,
        ).grid(column=0, row=row, sticky="e", padx=(0, 14), pady=4)
        value_label = tk.Label(
            body,
            text=value,
            bg=app.card_bg,
            fg=app.accent if link else app.text,
            font=email_font if link else value_font,
            cursor="hand2" if link else "",
        )
        value_label.grid(column=1, row=row, sticky="w", pady=4)
        if link:
            value_label.bind(
                "<Button-1>", lambda _event: webbrowser.open(f"mailto:{email}")
            )

    add_row(4, app._tr("about.author"), author)
    add_row(5, app._tr("about.email"), email, link=True)
    add_row(6, app._tr("about.phone"), phone)

    tk.Frame(body, bg=app.card_edge, height=1).grid(
        column=0, row=7, columnspan=2, sticky="ew", pady=(16, 14)
    )
    tk.Label(
        body,
        text=app._tr("about.updates"),
        bg=app.card_bg,
        fg=app.fg,
        font=section_font,
        anchor="w",
    ).grid(column=0, row=8, columnspan=2, sticky="w")
    tk.Label(
        body,
        textvariable=version_var,
        bg=app.card_bg,
        fg=app.text,
        font=value_font,
        anchor="w",
        justify="left",
    ).grid(column=0, row=9, columnspan=2, sticky="w", pady=(8, 2))
    status_label = tk.Label(
        body,
        textvariable=status_var,
        bg=app.card_bg,
        fg=app.muted,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
        justify="left",
        wraplength=420,
    )
    status_label.grid(column=0, row=10, columnspan=2, sticky="ew", pady=(0, 12))

    actions = tk.Frame(body, bg=app.card_bg)
    actions.grid(column=0, row=11, columnspan=2, sticky="e", pady=(8, 0))

    def dialog_exists():
        try:
            return bool(dialog.winfo_exists())
        except tk.TclError:
            return False

    def set_busy(is_busy):
        update_state["busy"] = is_busy
        check_button.config(state=tk.DISABLED if is_busy else tk.NORMAL)
        install_button.config(
            state=tk.DISABLED if is_busy or update_state["release"] is None else tk.NORMAL
        )

    def apply_update_result(result=None, error=None):
        if not dialog_exists():
            return
        set_busy(False)
        if error is not None:
            status_label.config(fg=app.danger)
            status_var.set(app._tr("about.update.error", error=error))
            version_var.set(app._tr("about.current_version", version=app_version))
            return
        if result is None:
            status_label.config(fg=app.danger)
            status_var.set(app._tr("about.update.error", error="Unknown update state"))
            version_var.set(app._tr("about.current_version", version=app_version))
            return
        if result.update_available:
            update_state["release"] = result.latest_release
            status_label.config(fg=app.accent)
            status_var.set(
                app._tr("about.update.available", version=result.latest_release.version)
            )
            version_var.set(
                app._tr(
                    "about.update.available_detail",
                    current=result.current_version,
                    latest=result.latest_release.version,
                )
            )
            install_button.config(state=tk.NORMAL)
            return
        update_state["release"] = None
        status_label.config(fg=app.success)
        status_var.set(app._tr("about.update.current"))
        version_var.set(app._tr("about.current_version", version=result.current_version))

    def run_update_check():
        try:
            result = app.check_for_updates()
            error = None
        except Exception as exc:
            result = None
            error = str(exc)

        try:
            app.root.after(0, lambda: apply_update_result(result=result, error=error))
        except (tk.TclError, RuntimeError):
            pass

    def check_for_updates():
        if update_state["busy"]:
            return
        update_state["release"] = None
        set_busy(True)
        status_label.config(fg=app.muted)
        status_var.set(app._tr("about.update.checking"))
        version_var.set(app._tr("about.current_version", version=app_version))
        threading.Thread(target=run_update_check, daemon=True).start()

    def finish_install(installer_path=None, error=None):
        if not dialog_exists():
            return
        if error is not None:
            set_busy(False)
            status_label.config(fg=app.danger)
            status_var.set(app._tr("about.update.error", error=error))
            return
        status_label.config(fg=app.success)
        status_var.set(
            app._tr("about.update.launching", version=update_state["release"].version)
        )
        try:
            app.launch_update_installer(installer_path)
        except Exception as exc:
            set_busy(False)
            status_label.config(fg=app.danger)
            status_var.set(app._tr("about.update.error", error=exc))
            return
        dialog.destroy()
        try:
            app.root.after(250, app.root.destroy)
        except (tk.TclError, RuntimeError):
            pass

    def run_update_install():
        try:
            installer_path = app.download_update_installer(update_state["release"])
            error = None
        except Exception as exc:
            installer_path = None
            error = str(exc)

        try:
            app.root.after(
                0,
                lambda: finish_install(installer_path=installer_path, error=error),
            )
        except (tk.TclError, RuntimeError):
            pass

    def install_update():
        if update_state["busy"] or update_state["release"] is None:
            return
        set_busy(True)
        status_label.config(fg=app.muted)
        status_var.set(
            app._tr("about.update.downloading", version=update_state["release"].version)
        )
        threading.Thread(target=run_update_install, daemon=True).start()

    check_button = app._build_button(
        actions,
        app._tr("about.update.check"),
        check_for_updates,
    )
    check_button.grid(column=0, row=0, padx=(0, 8))
    install_button = app._build_button(
        actions,
        app._tr("about.update.install"),
        install_update,
    )
    install_button.grid(column=1, row=0, padx=(0, 8))
    install_button.config(state=tk.DISABLED)
    app._build_button(actions, app._tr("button.close"), dialog.destroy).grid(
        column=2, row=0
    )

    if initial_update_result is not None:
        apply_update_result(result=initial_update_result)

    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    app._center_dialog_on_root(dialog)
    app._reveal_dialog(dialog, anchor=app.root, focus=True)

def open_visibility_calendar(app):
    selected_date = app.visibility_start_date or app._default_visibility_start_date()
    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(app._tr("visibility.calendar_title"))
    _apply_app_icon(dialog)
    dialog.configure(bg=app.gbg)
    dialog.transient(app.root)
    dialog.grab_set()
    dialog.resizable(False, False)
    app._apply_native_window_chrome(dialog)

    state = {"year": selected_date.year, "month": selected_date.month}
    header_var = tk.StringVar()
    grid_frame = tk.Frame(dialog, bg=app.gbg)

    def choose(day):
        app._set_visibility_start_date(datetime.date(state["year"], state["month"], day))
        dialog.destroy()

    def choose_today():
        app._set_visibility_start_date(app._default_visibility_start_date())
        dialog.destroy()

    def render_month():
        for child in grid_frame.winfo_children():
            child.destroy()
        month_name = app._tr(f"about.month.{state['month']}")
        header_var.set(f"{month_name} {state['year']}")
        day_names = ["Lu", "Ma", "Me", "Je", "Ve", "Sa", "Di"] if app.language == "fr" else [
            "Mo",
            "Tu",
            "We",
            "Th",
            "Fr",
            "Sa",
            "Su",
        ]
        for column, day_name in enumerate(day_names):
            tk.Label(
                grid_frame,
                text=day_name,
                bg=app.gbg,
                fg=app.muted,
                font=Font(family="Segoe UI", size=9, weight="bold"),
                width=4,
            ).grid(column=column, row=0, padx=2, pady=(0, 3))

        month_days = calendar.Calendar(firstweekday=0).monthdayscalendar(
            state["year"],
            state["month"],
        )
        for row, week in enumerate(month_days, start=1):
            for column, day in enumerate(week):
                if day == 0:
                    tk.Label(grid_frame, text="", bg=app.gbg, width=4).grid(
                        column=column,
                        row=row,
                        padx=2,
                        pady=2,
                    )
                    continue
                active = (
                    state["year"] == selected_date.year
                    and state["month"] == selected_date.month
                    and day == selected_date.day
                )
                tk.Button(
                    grid_frame,
                    text=str(day),
                    bg=app.accent if active else app.button_bg,
                    fg=app.ebg if active else app.text,
                    activebackground=app.accent,
                    activeforeground=app.ebg,
                    relief="flat",
                    bd=0,
                    width=4,
                    command=lambda selected_day=day: choose(selected_day),
                ).grid(column=column, row=row, padx=2, pady=2)

    def shift_month(delta):
        month_index = state["month"] - 1 + delta
        state["year"] += month_index // 12
        state["month"] = (month_index % 12) + 1
        render_month()

    header = tk.Frame(dialog, bg=app.gbg)
    header.grid(column=0, row=0, padx=14, pady=(14, 8), sticky="ew")
    tk.Button(
        header,
        text="<",
        bg=app.button_bg,
        fg=app.text,
        activebackground=app.accent,
        activeforeground=app.ebg,
        relief="flat",
        bd=0,
        width=4,
        command=lambda: shift_month(-1),
    ).grid(column=0, row=0)
    tk.Label(
        header,
        textvariable=header_var,
        bg=app.gbg,
        fg=app.text,
        font=Font(family="Segoe UI", size=11, weight="bold"),
        width=18,
    ).grid(column=1, row=0, padx=8)
    tk.Button(
        header,
        text=">",
        bg=app.button_bg,
        fg=app.text,
        activebackground=app.accent,
        activeforeground=app.ebg,
        relief="flat",
        bd=0,
        width=4,
        command=lambda: shift_month(1),
    ).grid(column=2, row=0)
    grid_frame.grid(column=0, row=1, padx=14, pady=(0, 10))
    footer = tk.Frame(dialog, bg=app.gbg)
    footer.grid(column=0, row=2, padx=14, pady=(0, 14), sticky="ew")
    footer.grid_columnconfigure(0, weight=1)
    footer.grid_columnconfigure(1, weight=1)
    app._build_button(footer, app._tr("visibility.today"), choose_today).grid(
        column=0,
        row=0,
        padx=(0, 4),
        sticky="ew",
    )
    app._build_button(footer, app._tr("button.cancel"), dialog.destroy).grid(
        column=1,
        row=0,
        padx=(4, 0),
        sticky="ew",
    )
    render_month()
    app._place_dialog_below_widget(dialog, app.visibility_calendar_button)
    app._reveal_dialog(dialog, anchor=app.root, focus=False)

def open_settings_dialog(app):
    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(app._tr("settings.title"))
    _apply_app_icon(dialog)
    dialog.configure(bg=app.gbg)
    dialog.transient(app.root)
    dialog.grab_set()
    dialog.resizable(False, False)
    app._apply_native_window_chrome(dialog)

    preset_lookup = {preset_label(preset): preset for preset in LOCATION_PRESETS}
    preset_values = list(preset_lookup)
    language_lookup = {label: code for code, label in LANGUAGE_OPTIONS}

    preset_var = tk.StringVar(value="")
    site_var = tk.StringVar(value=app.site_name)
    country_var = tk.StringVar(value=app.country)
    language_var = tk.StringVar(value=LANGUAGE_NAMES.get(app.language, LANGUAGE_NAMES["en"]))
    latitude_var = tk.StringVar(value=f"{app.latitude:.5f}")
    longitude_var = tk.StringVar(value=f"{app.longitude:.5f}")
    timezone_options = app._timezone_options()
    default_timezone = "Europe/Paris" if "Europe/Paris" in timezone_options else "UTC"
    timezone_var = tk.StringVar(value=app.timezone_name or default_timezone)
    timezone_auto_var = tk.BooleanVar(value=not bool(app.timezone_name))
    daylight_saving_var = tk.BooleanVar(value=app.daylight_saving_enabled)
    fov_var = tk.StringVar(value=f"{app.aladin_fov_deg:.2f}")
    sky_magnitude_limit_var = tk.StringVar(value=f"{app.sky_magnitude_limit:.1f}")
    sky_show_altaz_grid_var = tk.BooleanVar(value=app.sky_show_altaz_grid)
    sky_show_equatorial_grid_var = tk.BooleanVar(value=app.sky_show_equatorial_grid)
    sky_show_solar_system_var = tk.BooleanVar(value=app.sky_show_solar_system)
    mount_show_reticle_var = tk.BooleanVar(value=app.mount_show_reticle)
    hour_angle_offset_var = tk.BooleanVar(value=app.hour_angle_offset_enabled)
    declination_offset_var = tk.BooleanVar(value=app.declination_offset_enabled)
    coordinate_source_labels = {
        COORDINATE_SOURCE_APP: app._tr("settings.coordinate_source_app"),
        COORDINATE_SOURCE_MOUNT: app._tr("settings.coordinate_source_mount"),
    }
    coordinate_source_lookup = {
        label: code for code, label in coordinate_source_labels.items()
    }
    coordinate_source_var = tk.StringVar(
        value=coordinate_source_labels.get(
            app.coordinate_source,
            coordinate_source_labels[DEFAULT_COORDINATE_SOURCE],
        )
    )

    body = tk.Frame(dialog, bg=app.gbg, padx=18, pady=16)
    body.grid(column=0, row=0, sticky="nsew")
    body.grid_columnconfigure(0, weight=1)

    notebook = ttk.Notebook(body)
    notebook.grid(column=0, row=0, sticky="nsew")

    general_tab = tk.Frame(notebook, bg=app.gbg, padx=14, pady=14)
    sky_tab = tk.Frame(notebook, bg=app.gbg, padx=14, pady=14)
    mount_tab = tk.Frame(notebook, bg=app.gbg, padx=14, pady=14)
    for tab in (general_tab, sky_tab, mount_tab):
        tab.grid_columnconfigure(1, weight=1)

    notebook.add(general_tab, text=app._tr("settings.tab.general"))
    notebook.add(sky_tab, text=app._tr("settings.tab.sky"))
    notebook.add(mount_tab, text=app._tr("settings.tab.mount"))

    def add_label(parent, row, text):
        tk.Label(
            parent,
            text=text,
            bg=app.gbg,
            fg=app.muted,
            font=Font(family="Segoe UI", size=10, weight="bold"),
            anchor="w",
        ).grid(column=0, row=row, padx=(0, 10), pady=7, sticky="w")

    def build_entry(parent, row, variable):
        entry = tk.Entry(
            parent,
            textvariable=variable,
            bg=app.ebg,
            fg=app.text,
            insertbackground=app.fg,
            font=Font(family="Segoe UI", size=11),
            relief="flat",
            highlightbackground=app.card_edge,
            highlightcolor=app.accent,
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
            bg=app.gbg,
            fg=app.text,
            disabledforeground=app.muted,
            activebackground=app.gbg,
            activeforeground=app.fg,
            selectcolor=app.ebg,
            font=Font(family="Segoe UI", size=10),
            anchor="w",
            relief="flat",
        )

    add_label(general_tab, 0, app._tr("settings.preset"))
    preset_combo = ttk.Combobox(
        general_tab,
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

    add_label(general_tab, 1, app._tr("settings.site_name"))
    build_entry(general_tab, 1, site_var)

    add_label(general_tab, 2, app._tr("settings.country"))
    build_entry(general_tab, 2, country_var)

    add_label(general_tab, 3, app._tr("settings.language"))
    language_combo = ttk.Combobox(
        general_tab,
        textvariable=language_var,
        values=[label for _code, label in LANGUAGE_OPTIONS],
        font=Font(family="Segoe UI", size=10),
        width=42,
    )
    language_combo.grid(column=1, row=3, pady=7, sticky="ew")
    language_combo["state"] = "readonly"

    add_label(general_tab, 4, app._tr("settings.latitude"))
    build_entry(general_tab, 4, latitude_var)
    add_label(general_tab, 5, app._tr("settings.longitude"))
    build_entry(general_tab, 5, longitude_var)
    add_label(general_tab, 6, app._tr("settings.timezone"))
    timezone_options_frame = tk.Frame(general_tab, bg=app.gbg)
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
        app._tr("settings.timezone_auto"),
        sync_timezone_state,
    ).grid(column=0, row=0, sticky="w")
    timezone_combo.grid(column=0, row=1, pady=(5, 0), sticky="ew")
    daylight_saving_check = build_checkbutton(
        timezone_options_frame,
        daylight_saving_var,
        app._tr("settings.daylight_saving"),
    )
    daylight_saving_check.grid(column=0, row=2, pady=(5, 0), sticky="w")
    sync_timezone_state()

    add_label(sky_tab, 0, app._tr("settings.aladin_fov"))
    build_entry(sky_tab, 0, fov_var)

    add_label(sky_tab, 1, app._tr("settings.sky_map"))
    sky_options = tk.Frame(sky_tab, bg=app.gbg)
    sky_options.grid(column=1, row=1, pady=7, sticky="ew")
    sky_options.grid_columnconfigure(0, weight=1)
    magnitude_frame = tk.Frame(sky_options, bg=app.gbg)
    magnitude_frame.grid(column=0, row=0, sticky="ew")
    magnitude_frame.grid_columnconfigure(1, weight=1)
    tk.Label(
        magnitude_frame,
        text=app._tr("settings.sky_magnitude_limit"),
        bg=app.gbg,
        fg=app.text,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
    ).grid(column=0, row=0, padx=(0, 10), sticky="w")
    tk.Entry(
        magnitude_frame,
        textvariable=sky_magnitude_limit_var,
        bg=app.ebg,
        fg=app.text,
        insertbackground=app.fg,
        font=Font(family="Segoe UI", size=10),
        relief="flat",
        highlightbackground=app.card_edge,
        highlightcolor=app.accent,
        highlightthickness=1,
        width=8,
    ).grid(column=1, row=0, sticky="w")
    build_checkbutton(
        sky_options,
        sky_show_altaz_grid_var,
        app._tr("settings.sky_show_altaz_grid"),
    ).grid(column=0, row=1, sticky="w", pady=(5, 0))
    build_checkbutton(
        sky_options,
        sky_show_equatorial_grid_var,
        app._tr("settings.sky_show_equatorial_grid"),
    ).grid(column=0, row=2, sticky="w", pady=(4, 0))
    build_checkbutton(
        sky_options,
        sky_show_solar_system_var,
        app._tr("settings.sky_show_solar_system"),
    ).grid(column=0, row=3, sticky="w", pady=(4, 0))

    add_label(sky_tab, 2, app._tr("settings.instrument"))
    instrument_options = tk.Frame(sky_tab, bg=app.gbg)
    instrument_options.grid(column=1, row=2, pady=7, sticky="ew")
    build_checkbutton(
        instrument_options,
        hour_angle_offset_var,
        app._tr("settings.hour_angle_offset"),
    ).pack(anchor="w")
    build_checkbutton(
        instrument_options,
        declination_offset_var,
        app._tr("settings.declination_offset"),
    ).pack(anchor="w", pady=(4, 0))

    add_label(mount_tab, 0, app._tr("settings.mount_driver"))
    mount_options = tk.Frame(mount_tab, bg=app.gbg)
    mount_options.grid(column=1, row=0, pady=7, sticky="ew")
    mount_options.grid_columnconfigure(1, weight=1)

    mount_state = app.mount_settings_state()
    mount_driver_var = tk.StringVar(value=mount_state["driver_label"])
    mount_status_var = tk.StringVar(value=mount_state["status_text"])

    tk.Label(
        mount_options,
        text=app._tr("settings.mount"),
        bg=app.gbg,
        fg=app.muted,
        font=Font(family="Segoe UI", size=10, weight="bold"),
        anchor="w",
    ).grid(column=0, row=0, padx=(0, 10), sticky="w")
    mount_driver_label = tk.Label(
        mount_options,
        textvariable=mount_driver_var,
        bg=app.gbg,
        fg=app.text,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
        justify="left",
        wraplength=360,
    )
    mount_driver_label.grid(column=1, row=0, sticky="ew")
    add_label(mount_tab, 1, app._tr("settings.coordinate_source"))
    coordinate_source_combo = ttk.Combobox(
        mount_tab,
        textvariable=coordinate_source_var,
        values=[
            coordinate_source_labels[COORDINATE_SOURCE_APP],
            coordinate_source_labels[COORDINATE_SOURCE_MOUNT],
        ],
        font=Font(family="Segoe UI", size=10),
        width=42,
        state="readonly",
    )
    coordinate_source_combo.grid(column=1, row=1, pady=7, sticky="ew")
    mount_reticle_row = tk.Frame(mount_options, bg=app.gbg)
    mount_reticle_row.grid(column=0, row=1, columnspan=2, sticky="w", pady=(6, 0))
    mount_reticle_toggle = tk.Checkbutton(
        mount_reticle_row,
        text="",
        variable=mount_show_reticle_var,
        bg=app.gbg,
        fg=app.text,
        disabledforeground=app.muted,
        activebackground=app.gbg,
        activeforeground=app.fg,
        selectcolor=app.ebg,
        relief="flat",
        bd=0,
        highlightthickness=0,
        padx=0,
        pady=0,
        width=1,
    )
    mount_reticle_toggle.grid(column=0, row=0, sticky="w")
    mount_reticle_label = tk.Label(
        mount_reticle_row,
        text=app._tr("settings.mount_show_reticle"),
        bg=app.gbg,
        fg=app.text,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
        justify="left",
    )
    mount_reticle_label.grid(column=1, row=0, sticky="w", padx=(6, 0))

    def toggle_mount_reticle(_event=None):
        mount_show_reticle_var.set(not mount_show_reticle_var.get())

    mount_reticle_label.bind("<Button-1>", toggle_mount_reticle)
    mount_status_label = tk.Label(
        mount_options,
        textvariable=mount_status_var,
        bg=app.gbg,
        fg=mount_state["status_color"],
        font=Font(family="Segoe UI", size=9),
        anchor="w",
        justify="left",
        wraplength=420,
    )
    mount_status_label.grid(column=0, row=2, columnspan=2, sticky="ew", pady=(8, 6))

    mount_actions = tk.Frame(mount_options, bg=app.gbg)
    mount_actions.grid(column=0, row=3, columnspan=2, sticky="w")

    def set_mount_busy(status_text):
        mount_status_label.config(fg=app.accent)
        mount_status_var.set(status_text)
        choose_mount_button.config(state=tk.DISABLED)
        connect_mount_button.config(state=tk.DISABLED)
        disconnect_mount_button.config(state=tk.DISABLED)
        try:
            dialog.update_idletasks()
        except tk.TclError:
            pass

    def apply_mount_button_states(state):
        choose_mount_button.config(
            state=tk.NORMAL if state["available"] else tk.DISABLED
        )
        connect_mount_button.config(
            state=tk.NORMAL if state["available"] and not state["connected"] else tk.DISABLED
        )
        disconnect_mount_button.config(
            state=tk.NORMAL if state["connected"] else tk.DISABLED
        )

    def refresh_mount_state(state=None):
        state = state or app.mount_settings_state()
        mount_driver_var.set(state["driver_label"])
        mount_status_var.set(state["status_text"])
        mount_status_label.config(fg=state["status_color"])
        mount_driver_label.config(
            fg=app.text if state["driver_label"] != app._tr("mount.driver.none") else app.muted
        )
        apply_mount_button_states(state)

    def choose_mount():
        try:
            set_mount_busy(app._tr("mount.status.choosing"))
            refresh_mount_state(app.choose_ascom_mount_driver())
        except Exception as exc:
            mount_status_label.config(fg=app.danger)
            mount_status_var.set(app._tr("mount.status.error", error=exc))
            apply_mount_button_states(app.mount_settings_state())

    def connect_mount():
        try:
            set_mount_busy(app._tr("mount.status.connecting"))
            refresh_mount_state(app.connect_ascom_mount())
        except Exception as exc:
            mount_status_label.config(fg=app.danger)
            mount_status_var.set(app._tr("mount.status.error", error=exc))
            apply_mount_button_states(app.mount_settings_state())

    def disconnect_mount():
        try:
            set_mount_busy(app._tr("mount.status.disconnecting"))
            refresh_mount_state(app.disconnect_ascom_mount())
        except Exception as exc:
            mount_status_label.config(fg=app.danger)
            mount_status_var.set(app._tr("mount.status.error", error=exc))
            apply_mount_button_states(app.mount_settings_state())

    choose_mount_button = app._build_button(
        mount_actions,
        app._tr("settings.mount_choose"),
        choose_mount,
    )
    choose_mount_button.grid(column=0, row=0, padx=(0, 8))
    connect_mount_button = app._build_button(
        mount_actions,
        app._tr("settings.mount_connect"),
        connect_mount,
    )
    connect_mount_button.grid(column=1, row=0, padx=(0, 8))
    disconnect_mount_button = app._build_button(
        mount_actions,
        app._tr("settings.mount_disconnect"),
        disconnect_mount,
    )
    disconnect_mount_button.grid(column=2, row=0)
    refresh_mount_state(mount_state)

    mount_refresh_job = {"id": None}

    def refresh_mount_state_loop():
        try:
            if not dialog.winfo_exists():
                return
        except tk.TclError:
            return
        refresh_mount_state()
        try:
            mount_refresh_job["id"] = dialog.after(500, refresh_mount_state_loop)
        except tk.TclError:
            mount_refresh_job["id"] = None

    def cancel_mount_state_loop(event=None):
        if event is not None and event.widget is not dialog:
            return
        job = mount_refresh_job["id"]
        if job is None:
            return
        mount_refresh_job["id"] = None
        try:
            dialog.after_cancel(job)
        except tk.TclError:
            pass

    refresh_mount_state_loop()
    dialog.bind("<Destroy>", cancel_mount_state_loop, add="+")

    hint = tk.Label(
        body,
        text=app._tr("settings.hint"),
        bg=app.gbg,
        fg=app.muted,
        font=Font(family="Segoe UI", size=9),
        anchor="w",
    )
    hint.grid(column=0, row=1, pady=(10, 12), sticky="ew")

    actions = tk.Frame(body, bg=app.gbg)
    actions.grid(column=0, row=2, sticky="e")

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
        coordinate_source_var.set(coordinate_source_labels[DEFAULT_COORDINATE_SOURCE])
        mount_show_reticle_var.set(DEFAULT_MOUNT_SHOW_RETICLE)
        hour_angle_offset_var.set(DEFAULT_HOUR_ANGLE_OFFSET_ENABLED)
        declination_offset_var.set(DEFAULT_DECLINATION_OFFSET_ENABLED)

    def apply_settings():
        try:
            latitude = app._parse_float_setting(
                latitude_var.get(), app._tr("settings.latitude"), -90, 90
            )
            longitude = app._parse_float_setting(
                longitude_var.get(), app._tr("settings.longitude"), -180, 180
            )
            fov = app._parse_float_setting(
                fov_var.get(), app._tr("settings.aladin_fov"), 0.01, 180
            )
            sky_magnitude_limit = app._parse_float_setting(
                sky_magnitude_limit_var.get(),
                app._tr("settings.sky_magnitude_limit"),
                -2,
                MAX_SKY_MAGNITUDE_LIMIT,
            )
        except ValueError as exc:
            show_error_dialog(app, app._tr("settings.invalid_title"), str(exc), parent=dialog)
            return

        timezone_name = DEFAULT_TIMEZONE_NAME
        if not timezone_auto_var.get():
            try:
                timezone_name = app._validate_timezone_name(timezone_var.get())
            except ValueError:
                show_error_dialog(
                    app,
                    app._tr("settings.invalid_title"),
                    app._tr("settings.timezone_invalid", value=timezone_var.get()),
                    parent=dialog,
                )
                return
            if not timezone_name:
                show_error_dialog(
                    app,
                    app._tr("settings.invalid_title"),
                    app._tr("settings.timezone_invalid", value=timezone_var.get()),
                    parent=dialog,
                )
                return

        selected_language = language_lookup.get(language_var.get(), app.language)
        selected_coordinate_source = coordinate_source_lookup.get(
            coordinate_source_var.get(),
            DEFAULT_COORDINATE_SOURCE,
        )
        app.language = selected_language
        app.site_name = site_var.get().strip() or app._tr("settings.custom_site")
        app.country = country_var.get().strip() or DEFAULT_COUNTRY
        app.latitude = latitude
        app.longitude = longitude
        app.coordinate_source = selected_coordinate_source
        app.timezone_name = timezone_name
        app.daylight_saving_enabled = (
            daylight_saving_var.get() if timezone_name else DEFAULT_DAYLIGHT_SAVING_ENABLED
        )
        app.aladin_fov_deg = fov
        app.sky_magnitude_limit = sky_magnitude_limit
        app.sky_show_altaz_grid = sky_show_altaz_grid_var.get()
        app.sky_show_equatorial_grid = sky_show_equatorial_grid_var.get()
        app.sky_show_solar_system = sky_show_solar_system_var.get()
        app.mount_show_reticle = mount_show_reticle_var.get()
        app.hour_angle_offset_enabled = hour_angle_offset_var.get()
        app.declination_offset_enabled = declination_offset_var.get()
        app._invalidate_site_dependent_state()
        app._save_current_settings()
        app._refresh_language_texts()
        dialog.destroy()

    app._build_button(actions, app._tr("button.default"), reset_defaults).grid(
        column=0, row=0, padx=(0, 8)
    )
    app._build_button(actions, app._tr("button.cancel"), dialog.destroy).grid(
        column=1, row=0, padx=(0, 8)
    )
    app._build_button(actions, app._tr("button.apply"), apply_settings).grid(column=2, row=0)

    dialog.bind("<Return>", lambda _event: apply_settings())
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    app._center_dialog_on_root(dialog)
    app._reveal_dialog(dialog, anchor=app.root, focus=True)

def open_double_star_orbit_window(app, star):
    orbit = star.get("orb6_orbit")
    if not orbit:
        app.double_status_label.config(text=app._tr("double.orbit.unavailable"))
        return

    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(app._tr("double.orbit.title", name=star["name"]))
    dialog.configure(bg=app.gbg)
    dialog.transient(app.root)
    _apply_app_icon(dialog)
    app._apply_native_window_chrome(dialog)
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    header = tk.Frame(dialog, bg=app.gbg)
    header.grid(column=0, row=0, padx=14, pady=(12, 4), sticky="ew")
    header.grid_columnconfigure(0, weight=1)
    tk.Label(
        header,
        text=f"{star['name']} - {star['designation']}",
        bg=app.gbg,
        fg=app.fg,
        font=Font(family="Segoe UI", size=14, weight="bold"),
        anchor="w",
    ).grid(column=0, row=0, sticky="ew")
    tk.Label(
        header,
        text=app._tr(
            "double.orbit.elements",
            period=orbit["period_years"],
            semimajor=orbit["semimajor_arcsec"],
            eccentricity=orbit["eccentricity"],
            grade=orbit["grade"],
            reference=orbit.get("reference", ""),
        ),
        bg=app.gbg,
        fg=app.muted,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
    ).grid(column=0, row=1, sticky="ew")

    canvas = tk.Canvas(
        dialog,
        bg=app.ebg,
        highlightthickness=1,
        highlightbackground=app.card_edge,
        bd=0,
        width=620,
        height=560,
    )
    canvas.grid(column=0, row=1, padx=14, pady=8, sticky="nsew")

    footer = tk.Frame(dialog, bg=app.gbg)
    footer.grid(column=0, row=2, padx=14, pady=(0, 12), sticky="ew")
    footer.grid_columnconfigure(0, weight=1)
    today_label = tk.Label(
        footer,
        text="",
        bg=app.gbg,
        fg=app.fg,
        font=Font(family="Segoe UI", size=10, weight="bold"),
        anchor="w",
    )
    today_label.grid(column=0, row=0, sticky="ew")
    hover_label = tk.Label(
        footer,
        text=app._tr("double.orbit.cursor_empty"),
        bg=app.gbg,
        fg=app.muted,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
    )
    hover_label.grid(column=0, row=1, sticky="ew", pady=(2, 0))
    app._build_button(footer, app._tr("button.close"), dialog.destroy).grid(
        column=1,
        row=0,
        rowspan=2,
        padx=(10, 0),
    )

    state = {
        "canvas": canvas,
        "today_label": today_label,
        "hover_label": hover_label,
        "star": star,
        "orbit": orbit,
        "screen_points": [],
    }
    canvas.bind("<Configure>", lambda _event: app._draw_double_star_orbit(state))
    canvas.bind("<Motion>", lambda event: app._on_double_orbit_motion(event, state))
    canvas.bind("<Leave>", lambda _event: app._clear_double_orbit_hover(state))
    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    app._center_dialog_on_root(dialog)
    app._reveal_dialog(dialog, anchor=app.root, focus=True)
    app._draw_double_star_orbit(state)

def _set_wds_note_text(app, text_widget, content):
    text_widget.config(state=tk.NORMAL)
    text_widget.delete(1.0, tk.END)
    text_widget.insert(tk.END, content)
    text_widget.config(state=tk.DISABLED)

def _format_wds_note_rows(app, notes):
    if not notes:
        return app._tr("double.wds_note.empty")

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

def _load_wds_note_rows(app, dialog, text_widget, wds):
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
            app._set_wds_note_text(
                text_widget,
                app._tr("double.wds_note.error", error=error),
            )
            return
        app.double_wds_note_cache[wds] = notes
        app._set_wds_note_text(text_widget, app._format_wds_note_rows(notes))
        if not notes:
            app._populate_double_star_tree()

    try:
        app.root.after(0, apply_result)
    except (tk.TclError, RuntimeError):
        pass

def open_double_star_wds_note_window(app, star):
    wds = str(star.get("wds", "")).strip()
    if not wds:
        return

    dialog = tk.Toplevel(app.root)
    dialog.withdraw()
    dialog.title(app._tr("double.wds_note.title", name=star["name"]))
    dialog.configure(bg=app.gbg)
    dialog.transient(app.root)
    _apply_app_icon(dialog)
    app._apply_native_window_chrome(dialog)
    dialog.grid_columnconfigure(0, weight=1)
    dialog.grid_rowconfigure(1, weight=1)

    header = tk.Frame(dialog, bg=app.gbg)
    header.grid(column=0, row=0, padx=14, pady=(14, 8), sticky="ew")
    header.grid_columnconfigure(0, weight=1)
    tk.Label(
        header,
        text=f"{star['name']} - {app._format_double_designation(star)}",
        bg=app.gbg,
        fg=app.fg,
        font=Font(family="Segoe UI", size=13, weight="bold"),
        anchor="w",
    ).grid(column=0, row=0, sticky="ew")
    tk.Label(
        header,
        text=app._tr("double.wds_note.source", wds=wds),
        bg=app.gbg,
        fg=app.muted,
        font=Font(family="Segoe UI", size=10),
        anchor="w",
    ).grid(column=0, row=1, sticky="ew", pady=(3, 0))

    body = tk.Frame(dialog, bg=app.gbg)
    body.grid(column=0, row=1, padx=14, pady=8, sticky="nsew")
    body.grid_columnconfigure(0, weight=1)
    body.grid_rowconfigure(0, weight=1)
    text_widget = tk.Text(
        body,
        bg=app.ebg,
        fg=app.text,
        insertbackground=app.fg,
        relief="flat",
        highlightthickness=1,
        highlightbackground=app.card_edge,
        highlightcolor=app.accent,
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

    footer = tk.Frame(dialog, bg=app.gbg)
    footer.grid(column=0, row=2, padx=14, pady=(0, 12), sticky="ew")
    footer.grid_columnconfigure(0, weight=1)
    app._build_button(
        footer,
        app._tr("double.wds_note.open_url"),
        lambda: webbrowser.open_new_tab(build_wds_notes_url(wds)),
    ).grid(column=1, row=0, padx=(0, 8))
    app._build_button(footer, app._tr("button.close"), dialog.destroy).grid(
        column=2,
        row=0,
    )

    dialog.bind("<Escape>", lambda _event: dialog.destroy())
    app._center_dialog_on_root(dialog)
    app._reveal_dialog(dialog, anchor=app.root, focus=False)

    cached_notes = app.double_wds_note_cache.get(wds)
    if cached_notes is not None:
        app._set_wds_note_text(text_widget, app._format_wds_note_rows(cached_notes))
    else:
        app._set_wds_note_text(text_widget, app._tr("double.wds_note.loading"))
        threading.Thread(
            target=app._load_wds_note_rows,
            args=(dialog, text_widget, wds),
            daemon=True,
        ).start()

def _draw_double_star_orbit(app, state):
    canvas = state["canvas"]
    orbit = state["orbit"]
    today_label = state["today_label"]
    width = max(1, canvas.winfo_width())
    height = max(1, canvas.winfo_height())
    canvas.delete("all")

    points = sample_orbit_points(orbit, count=720)
    current_year = app._current_decimal_year()
    current = orbit_position_at_year(orbit, current_year)
    max_extent = max(
        0.001,
        *(abs(point["east"]) for point in points),
        *(abs(point["north"]) for point in points),
        abs(current["east"]),
        abs(current["north"]),
    )
    margin = 86
    available_width = max(20, width - margin * 2)
    available_height = max(20, height - margin * 2)
    scale = min(available_width / (2 * max_extent), available_height / (2 * max_extent))
    center_x = width / 2
    center_y = height / 2

    canvas.create_line(
        center_x,
        margin / 2,
        center_x,
        height - margin / 2,
        fill=app.card_edge,
        dash=(4, 4),
    )
    canvas.create_line(
        margin / 2,
        center_y,
        width - margin / 2,
        center_y,
        fill=app.card_edge,
        dash=(4, 4),
    )
    canvas.create_text(
        center_x,
        height - 18,
        text=app._tr("direction.north_short"),
        fill=app.muted,
        font=Font(family="Segoe UI", size=10, weight="bold"),
    )
    canvas.create_text(
        width - 20,
        center_y,
        text=app._tr("direction.east_short"),
        fill=app.muted,
        font=Font(family="Segoe UI", size=10, weight="bold"),
    )

    coordinates = []
    screen_points = []
    for point in points:
        x_position, y_position = app._orbit_plot_position(point, center_x, center_y, scale)
        coordinates.extend((x_position, y_position))
        screen_points.append((x_position, y_position, point))
    if len(coordinates) >= 4:
        canvas.create_line(
            *coordinates,
            fill=app.accent,
            width=2,
            smooth=True,
        )

    canvas.create_oval(
        center_x - 4,
        center_y - 4,
        center_x + 4,
        center_y + 4,
        fill=app.text,
        outline=app.ebg,
    )

    marker_count = 8 if orbit["period_years"] > 5 else 10
    start_year = points[0]["year"]
    for index in range(marker_count):
        marker_year = start_year + orbit["period_years"] * index / marker_count
        marker = orbit_position_at_year(orbit, marker_year)
        marker_x, marker_y = app._orbit_plot_position(marker, center_x, center_y, scale)
        canvas.create_oval(
            marker_x - 3,
            marker_y - 3,
            marker_x + 3,
            marker_y + 3,
            fill=app.fg,
            outline=app.ebg,
        )
        gap = 14
        label_x, label_y, label_anchor, x_unit, y_unit = app._orbit_external_label_position(
            marker_x,
            marker_y,
            center_x,
            center_y,
            screen_points,
            gap=gap,
        )
        label_item = canvas.create_text(
            label_x,
            label_y,
            text=app._format_orbit_epoch_label(orbit, marker_year),
            fill=app.text,
            font=Font(family="Segoe UI", size=8),
            anchor=label_anchor,
        )
        dx, dy = app._keep_canvas_item_in_bounds(canvas, label_item)
        leader_item = canvas.create_line(
            marker_x + x_unit * 5,
            marker_y + y_unit * 5,
            label_x + dx - x_unit * 2,
            label_y + dy - y_unit * 2,
            fill=app.card_edge,
        )
        canvas.tag_lower(leader_item, label_item)

    current_x, current_y = app._orbit_plot_position(current, center_x, center_y, scale)
    canvas.create_oval(
        current_x - 6,
        current_y - 6,
        current_x + 6,
        current_y + 6,
        fill=app.fg,
        outline=app.text,
        width=2,
    )
    current_gap = 18
    (
        current_label_x,
        current_label_y,
        current_label_anchor,
        current_x_unit,
        current_y_unit,
    ) = app._orbit_external_label_position(
        current_x,
        current_y,
        center_x,
        center_y,
        screen_points,
        gap=current_gap,
    )
    current_label_item = canvas.create_text(
        current_label_x,
        current_label_y,
        text=app._tr("double.orbit.now"),
        fill=app.fg,
        font=Font(family="Segoe UI", size=9, weight="bold"),
        anchor=current_label_anchor,
    )
    dx, dy = app._keep_canvas_item_in_bounds(canvas, current_label_item)
    leader_item = canvas.create_line(
        current_x + current_x_unit * 7,
        current_y + current_y_unit * 7,
        current_label_x + dx - current_x_unit * 2,
        current_label_y + dy - current_y_unit * 2,
        fill=app.card_edge,
    )
    canvas.tag_lower(leader_item, current_label_item)
    today_label.config(
        text=app._tr(
            "double.orbit.status",
            date=app._format_orbit_hover_date(current_year),
            rho=current["rho"],
            theta=current["theta"],
        )
    )
    state["screen_points"] = screen_points

def _on_double_orbit_motion(app, event, state):
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
        app._clear_double_orbit_hover(state)
        return

    x_position, y_position, point = nearest
    text = app._tr(
        "double.orbit.hover",
        date=app._format_orbit_hover_date(point["year"]),
        rho=point["rho"],
        theta=point["theta"],
    )
    canvas.delete("orbit_hover")
    canvas.create_oval(
        x_position - 5,
        y_position - 5,
        x_position + 5,
        y_position + 5,
        fill=app.success,
        outline=app.text,
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
        fill=app.ebg,
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
            state["hover_label"].config(text=text)
            return
        rect = canvas.create_rectangle(
            bbox[0] - rect_padding_x,
            bbox[1] - rect_padding_y,
            bbox[2] + rect_padding_x,
            bbox[3] + rect_padding_y,
            fill=app.accent,
            outline=app.accent,
            tags=("orbit_hover",),
        )
        canvas.tag_lower(rect, text_item)
    state["hover_label"].config(text=text)

def _clear_double_orbit_hover(app, state):
    state["canvas"].delete("orbit_hover")
    state["hover_label"].config(text=app._tr("double.orbit.cursor_empty"))
