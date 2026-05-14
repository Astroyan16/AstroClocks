"""Sky-map UI, rendering, and interaction helpers for AstroClocks."""

import math
import os
import time
import tkinter as tk
from tkinter.font import Font

from astroclocks import app_visibility
from astroclocks.astronomy import compute_solar_system_positions
from astroclocks.star_sprites import StarRenderStats

try:
    from PIL import Image, ImageTk
except ImportError:
    Image = None
    ImageTk = None


SKY_MAP_ANTIALIASED_REFRESH_SECONDS = 8
SKY_MAP_CANVAS_REFRESH_SECONDS = 8
SKY_RENDER_DEBUG = os.environ.get("ASTROCLOCKS_SKY_RENDER_DEBUG") == "1"
SOLAR_SYSTEM_CACHE_SECONDS = 10
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


def _create_sky_widgets(self):
    self.lf_sky.grid_columnconfigure(0, weight=1)
    self.lf_sky.grid_rowconfigure(0, weight=1)
    self.lf_sky.grid_rowconfigure(1, weight=0)
    self.lf_sky.grid_rowconfigure(2, weight=0)
    self.sky_status_payload = None

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
        height=5,
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

    self.sky_mount_controls_frame = tk.Frame(self.lf_sky, bg=self.card_bg)
    self.sky_mount_controls_frame.grid(column=0, row=2, padx=8, pady=(0, 8), sticky="ew")
    self.sky_mount_controls_frame.grid_columnconfigure(0, weight=1)

    self.sky_mount_status_label = tk.Label(
        self.sky_mount_controls_frame,
        text="",
        bg=self.card_bg,
        fg=self.muted,
        font=Font(family="Segoe UI", size=10, weight="bold"),
        anchor="w",
        justify="left",
    )
    self.sky_mount_status_label.grid(column=0, row=0, sticky="ew", pady=(0, 6))

    self.sky_mount_buttons_frame = tk.Frame(self.sky_mount_controls_frame, bg=self.card_bg)
    self.sky_mount_buttons_frame.grid(column=0, row=1, sticky="w")
    self.sky_mount_goto_button = self._build_button(
        self.sky_mount_buttons_frame,
        self._tr("mount.control.goto"),
        lambda: self._run_mount_control_action(self.slew_mount_to_target),
    )
    self.sky_mount_goto_button.grid(column=0, row=0, padx=(0, 8))
    self.sky_mount_abort_button = self._build_button(
        self.sky_mount_buttons_frame,
        self._tr("mount.control.abort"),
        lambda: self._run_mount_control_action(self.abort_mount_slew),
    )
    self.sky_mount_abort_button.grid(column=1, row=0)
    self._refresh_sky_mount_controls()


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


def _sky_label_position(self, canvas, x, y, text, label_font, *, offset=7, margin=10):
    canvas_width = max(1, int(canvas.winfo_width()))
    canvas_height = max(1, int(canvas.winfo_height()))
    text_width = label_font.measure(text)
    line_height = max(10, int(label_font.metrics("linespace")))
    half_height = max(5, line_height // 2)

    right_x = x + offset
    right_fits = right_x + text_width <= canvas_width - margin
    left_x = x - offset
    left_fits = left_x - text_width >= margin

    if right_fits or not left_fits:
        label_x = min(right_x, canvas_width - margin - text_width)
        label_x = max(margin, label_x)
        label_anchor = "w"
    else:
        label_x = max(left_x, margin + text_width)
        label_anchor = "e"

    label_y = y - offset
    min_y = margin + half_height
    max_y = canvas_height - margin - half_height
    if label_y < min_y:
        label_y = y + offset
    label_y = min(max(label_y, min_y), max_y)
    return label_x, label_y, label_anchor


def _draw_star_label(self, canvas, star):
    label_font = Font(family="Segoe UI", size=8)
    label_x, label_y, label_anchor = self._sky_label_position(
        canvas,
        star["x"],
        star["y"],
        star["name"],
        label_font,
    )
    canvas.create_text(
        label_x,
        label_y,
        text=star["name"],
        fill="#b8c8d6",
        font=label_font,
        anchor=label_anchor,
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
    label_font = Font(family="Segoe UI", size=8, weight="bold")
    label_x, label_y, label_anchor = self._sky_label_position(
        canvas,
        sky_object["x"],
        sky_object["y"],
        sky_object["label"],
        label_font,
    )
    canvas.create_text(
        label_x,
        label_y,
        text=sky_object["label"],
        fill=sky_object["hover_color"],
        font=label_font,
        anchor=label_anchor,
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
    active_latitude, active_longitude = self._active_site_coordinates()
    cache_key = (
        int(time.time() // SOLAR_SYSTEM_CACHE_SECONDS),
        round(active_latitude, 5),
        round(active_longitude, 5),
    )
    if cache_key == self.solar_system_cache_key:
        return self.solar_system_cache

    try:
        self.solar_system_cache = compute_solar_system_positions(
            active_latitude,
            active_longitude,
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
    marker_color = self._target_marker_color(altitude, visible)
    label_font = Font(family="Segoe UI", size=9, weight="bold")
    if not visible:
        dx = x - center_x
        dy = y - center_y
        length = math.hypot(dx, dy) or 1
        ux = dx / length
        uy = dy / length
        nx = -uy
        ny = ux
        start_x = x - ux * 24
        start_y = y - uy * 24
        end_x = x + ux * 10
        end_y = y + uy * 10
        canvas.create_line(
            start_x,
            start_y,
            end_x,
            end_y,
            fill=marker_color,
            width=3,
            arrow=tk.LAST,
            arrowshape=(12, 14, 6),
        )
        canvas_width = max(1, int(canvas.winfo_width()))
        canvas_height = max(1, int(canvas.winfo_height()))
        text_width = label_font.measure(label)
        base_x = x - ux * 30
        base_y = y - uy * 30
        label_x = base_x + nx * 14
        label_y = base_y + ny * 14
        for side in (1, -1):
            candidate_x = base_x + nx * 14 * side
            candidate_y = base_y + ny * 14 * side
            if (
                14 + text_width / 2 <= candidate_x <= canvas_width - 14 - text_width / 2
                and 14 <= candidate_y <= canvas_height - 14
            ):
                label_x = candidate_x
                label_y = candidate_y
                break
        label_x = min(max(14 + text_width / 2, label_x), canvas_width - 14 - text_width / 2)
        label_y = min(max(14, label_y), canvas_height - 14)
        canvas.create_text(
            label_x,
            label_y,
            text=label,
            fill=marker_color,
            font=label_font,
            anchor="center",
        )
        return visible
    reticle_radius = max(8, min(11, int(round(radius * 0.045))))
    crosshair_half = max(reticle_radius + 4, min(17, int(round(radius * 0.07))))
    label_offset = crosshair_half + reticle_radius + 5
    canvas.create_oval(
        x - reticle_radius,
        y - reticle_radius,
        x + reticle_radius,
        y + reticle_radius,
        outline=marker_color,
        width=2,
    )
    canvas.create_line(x - crosshair_half, y, x + crosshair_half, y, fill=marker_color, width=2)
    canvas.create_line(x, y - crosshair_half, x, y + crosshair_half, fill=marker_color, width=2)
    text_width = label_font.measure(label)
    line_height = label_font.metrics("linespace")
    canvas_width = max(1, int(canvas.winfo_width()))
    canvas_height = max(1, int(canvas.winfo_height()))
    label_x = x
    label_y = y + label_offset
    if label_y + line_height / 2 > canvas_height - 8:
        label_y = y - label_offset
    min_x = 8 + text_width / 2
    max_x = max(min_x, canvas_width - 8 - text_width / 2)
    min_y = 8 + line_height / 2
    max_y = max(min_y, canvas_height - 8 - line_height / 2)
    label_x = min(max(min_x, label_x), max_x)
    label_y = min(max(min_y, label_y), max_y)
    canvas.create_text(
        label_x,
        label_y,
        text=label,
        fill=marker_color,
        font=label_font,
    )
    return visible


def _draw_mount_marker(self, canvas, center_x, center_y, radius, altitude, azimuth, label):
    x, y, visible = self._project_target(center_x, center_y, radius, altitude, azimuth)
    marker_color = self._mount_marker_color(visible)
    reticle_radius = max(6, min(9, int(round(radius * 0.04))))
    crosshair_half = max(reticle_radius + 3, min(14, int(round(radius * 0.06))))
    label_offset = crosshair_half + reticle_radius + 3
    label_font = Font(family="Segoe UI", size=9, weight="bold")
    canvas.create_oval(
        x - reticle_radius,
        y - reticle_radius,
        x + reticle_radius,
        y + reticle_radius,
        outline=marker_color,
        width=2,
    )
    canvas.create_line(x - crosshair_half, y, x + crosshair_half, y, fill=marker_color, width=2)
    canvas.create_line(x, y - crosshair_half, x, y + crosshair_half, fill=marker_color, width=2)
    text_width = label_font.measure(label)
    line_height = label_font.metrics("linespace")
    canvas_width = max(1, int(canvas.winfo_width()))
    canvas_height = max(1, int(canvas.winfo_height()))
    label_x = x
    label_y = y - label_offset
    if label_y - line_height / 2 < 8:
        label_y = y + label_offset
    min_x = 8 + text_width / 2
    max_x = max(min_x, canvas_width - 8 - text_width / 2)
    min_y = 8 + line_height / 2
    max_y = max(min_y, canvas_height - 8 - line_height / 2)
    label_x = min(max(min_x, label_x), max_x)
    label_y = min(max(min_y, label_y), max_y)
    canvas.create_text(
        label_x,
        label_y,
        text=label,
        fill=marker_color,
        font=label_font,
    )
    return visible


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
    color = self.accent
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
    if label_y + padding_y > canvas_height - margin:
        label_y = max(margin, y - 20)

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


def _set_sky_status(self, text, highlights=(), color_highlights=()):
    if self.sky_status is None:
        return
    payload = (
        text,
        tuple(highlights),
        tuple((highlight, color) for highlight, color in color_highlights),
    )
    if payload == self.sky_status_payload:
        return
    self.sky_status_payload = payload

    self.sky_status.config(state=tk.NORMAL)
    self.sky_status.delete("1.0", tk.END)
    self.sky_status.insert("1.0", text)
    self.sky_status.tag_remove("danger", "1.0", tk.END)
    for tag_name in self.sky_status.tag_names():
        if tag_name.startswith("status-color-"):
            self.sky_status.tag_remove(tag_name, "1.0", tk.END)
    for highlight, color in color_highlights:
        if not highlight or not color:
            continue
        tag_name = f"status-color-{color.lstrip('#')}"
        self.sky_status.tag_configure(tag_name, foreground=color)
        start = "1.0"
        while True:
            index = self.sky_status.search(highlight, start, tk.END)
            if not index:
                break
            end = f"{index}+{len(highlight)}c"
            self.sky_status.tag_add(tag_name, index, end)
            start = end
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
    self.sky_status.tag_raise("danger")
    self.sky_status.config(state=tk.DISABLED)


def _sky_star_count_line(self):
    return self._tr("sky.star_count", count=len(self.sky_star_points))


def _sky_inactive_status(self):
    count_line = self._sky_star_count_line()
    status = self._tr("sky.no_target")
    if not self.sky_geometry:
        return f"{count_line}\n{status}"
    mount_line = self._mount_status_line(self.sky_geometry["lst_hours"])
    if not mount_line:
        return f"{count_line}\n{status}"
    return f"{count_line}\n{status}\n{mount_line}"


def _update_sky_hover(self):
    if self.sky_hover_position is None:
        if self.sky_canvas is not None:
            self.sky_canvas.delete("sky-hover")
        self._set_sky_status(
            self.sky_base_status,
            self.sky_base_status_highlights,
            self.sky_base_status_color_highlights,
        )
        return

    x, y = self.sky_hover_position
    coordinates = self._sky_coordinates_from_canvas(x, y)
    if coordinates is None:
        self.sky_canvas.delete("sky-hover")
        self._set_sky_status(
            self.sky_base_status,
            self.sky_base_status_highlights,
            self.sky_base_status_color_highlights,
        )
        return

    sky_object = self._nearest_sky_object(x, y)
    self._draw_hover_overlay(x, y, sky_object)

    line_color = self.accent
    if sky_object:
        jnow_status = self._format_jnow_horizontal_status(
            sky_object["ra_hours"],
            sky_object["declination"],
            sky_object["altitude"],
            sky_object["azimuth"],
            sky_object["hour_angle"],
            include_hour_angle=False,
        )
        label = f"{sky_object.get('label', sky_object['name'])} | {jnow_status}"
    else:
        ra_hours, declination, hour_angle, altitude, azimuth = coordinates
        jnow_status = self._format_jnow_horizontal_status(
            ra_hours,
            declination,
            altitude,
            azimuth,
            hour_angle,
            include_hour_angle=False,
        )
        label = f"{self._tr('sky.pointer')} | {jnow_status}"

    now = time.monotonic()
    if now - self.sky_last_status_update_time >= 0.12:
        self.sky_last_status_update_time = now
        count_line = self._sky_star_count_line()
        base_status = self.sky_base_status
        if base_status.startswith(f"{count_line}\n"):
            base_status = base_status[len(count_line) + 1 :]
        self._set_sky_status(
            f"{count_line}\n{label}\n{base_status}",
            self.sky_base_status_highlights,
            (
                (count_line, self.text),
                (label, line_color),
                *self.sky_base_status_color_highlights,
            ),
        )


def _run_sky_hover_update(self):
    self.sky_hover_update_pending = False
    self._update_sky_hover()


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
        self._set_sky_status(
            self.sky_base_status,
            self.sky_base_status_highlights,
            self.sky_base_status_color_highlights,
        )


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
    center_y = height / 2
    radius = max(40, min(width * 0.45, height * 0.44))
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

    mount_coordinates = self._mount_jnow_coordinates(self.mount_last_snapshot)
    if self.mount_connected and self.mount_show_reticle and mount_coordinates is not None:
        mount_ra_hours, mount_declination = mount_coordinates
        mount_altitude, mount_azimuth, _mount_hour_angle = self._equatorial_to_horizontal(
            mount_ra_hours,
            mount_declination,
            lst_hours,
        )
        self._draw_mount_marker(
            self.sky_canvas,
            center_x,
            center_y,
            radius,
            mount_altitude,
            mount_azimuth,
            self._tr("sky.telescope"),
        )

    if not self.target_active:
        self.sky_base_status = self._sky_inactive_status()
        self.sky_base_status_highlights = ()
        self.sky_base_status_color_highlights = ((self._sky_star_count_line(), self.text),)
        mount_line = self._mount_status_line(lst_hours)
        if mount_line and mount_coordinates is not None:
            self.sky_base_status_color_highlights += (
                (mount_line, self._mount_marker_color(mount_altitude >= 0)),
            )
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
    target_status_line = self._tr(
        "sky.status",
        target=self._target_display_label(),
        ra=self._format_unsigned_hms_compact(target_ra_hours),
        dec=self._format_signed_dms_compact(target_declination),
        altitude=altitude_text,
        azimuth=f"{target_azimuth:05.1f}",
        note=chart_note,
    )
    count_line = self._sky_star_count_line()
    self.sky_base_status = f"{count_line}\n{target_status_line}"
    mount_line = self._mount_status_line(lst_hours)
    if mount_line:
        self.sky_base_status = f"{self.sky_base_status}\n{mount_line}"
    self.sky_base_status_highlights = (
        () if target_visible else (f"Alt = {altitude_text}\N{DEGREE SIGN}", chart_note)
    )
    self.sky_base_status_color_highlights = (
        (count_line, self.text),
        (target_status_line, self._target_marker_color(target_altitude, target_visible)),
    )
    if mount_line and mount_coordinates is not None:
        self.sky_base_status_color_highlights += (
            (mount_line, self._mount_marker_color(mount_altitude >= 0)),
        )
    self._set_sky_status(
        self.sky_base_status,
        self.sky_base_status_highlights,
        self.sky_base_status_color_highlights,
    )
    self._update_sky_hover()

def install_skymap_methods(app_class):
    app_class._create_sky_widgets = _create_sky_widgets
    app_class._schedule_sky_map_resize = _schedule_sky_map_resize
    app_class._update_sky_map_from_resize = _update_sky_map_from_resize
    app_class._project_horizontal_point = _project_horizontal_point
    app_class._project_target = _project_target
    app_class._draw_sky_grid = _draw_sky_grid
    app_class._draw_equatorial_grid = _draw_equatorial_grid
    app_class._hex_to_rgb = _hex_to_rgb
    app_class._sky_star_color = _sky_star_color
    app_class._sky_star_style = _sky_star_style
    app_class._sky_label_position = _sky_label_position
    app_class._draw_star_label = _draw_star_label
    app_class._draw_star_catalog_canvas = _draw_star_catalog_canvas
    app_class._draw_solar_system_canvas = _draw_solar_system_canvas
    app_class._draw_solar_system_label = _draw_solar_system_label
    app_class._draw_sky_object_labels = _draw_sky_object_labels
    app_class._draw_sky_objects_raster = _draw_sky_objects_raster
    app_class._collect_star_catalog = _collect_star_catalog
    app_class._solar_system_positions = _solar_system_positions
    app_class._collect_solar_system_objects = _collect_solar_system_objects
    app_class._draw_target_marker = _draw_target_marker
    app_class._draw_mount_marker = _draw_mount_marker
    app_class._current_solar_system_target = _current_solar_system_target
    app_class._sky_coordinates_from_canvas = _sky_coordinates_from_canvas
    app_class._nearest_sky_object = _nearest_sky_object
    app_class._draw_hover_overlay = _draw_hover_overlay
    app_class._set_sky_status = _set_sky_status
    app_class._sky_star_count_line = _sky_star_count_line
    app_class._sky_inactive_status = _sky_inactive_status
    app_class._update_sky_hover = _update_sky_hover
    app_class._run_sky_hover_update = _run_sky_hover_update
    app_class._on_sky_motion = _on_sky_motion
    app_class._on_sky_leave = _on_sky_leave
    app_class._on_sky_click = _on_sky_click
    app_class._update_sky_map = _update_sky_map

