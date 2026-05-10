"""Visibility chart UI and rendering helpers for AstroClocks."""

import datetime
import threading
import time
import tkinter as tk
from tkinter.font import Font

from astroclocks import app_dialogs
from astroclocks.astronomy import compute_solar_system_body_positions, compute_sun_altitudes


TARGET_LOW_ALTITUDE_COLOR = "#f6c451"
TWILIGHT_PHASE_COLORS = {
    "day": "#243744",
    "civil": "#20303c",
    "nautical": "#1a2732",
    "astronomical": "#141f29",
}


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

def install_visibility_methods(app_class):
    app_class._create_visibility_widgets = _create_visibility_widgets
    app_class._schedule_visibility_chart_resize = _schedule_visibility_chart_resize
    app_class._update_visibility_chart_from_resize = _update_visibility_chart_from_resize
    app_class._default_visibility_start_date = _default_visibility_start_date
    app_class._visibility_start_utc_for_date = _visibility_start_utc_for_date
    app_class._set_visibility_start_date = _set_visibility_start_date
    app_class._shift_visibility_window = _shift_visibility_window
    app_class._update_visibility_date_label = _update_visibility_date_label
    app_class._open_visibility_calendar = _open_visibility_calendar
    app_class._visibility_window_context = _visibility_window_context
    app_class._visibility_time_label = _visibility_time_label
    app_class._set_visibility_status = _set_visibility_status
    app_class._visibility_state_at_time = _visibility_state_at_time
    app_class._visibility_sample_from_position = _visibility_sample_from_position
    app_class._visibility_sample_at_offset = _visibility_sample_at_offset
    app_class._visibility_samples = _visibility_samples
    app_class._visibility_samples_for_solar_body = _visibility_samples_for_solar_body
    app_class._curve_extreme_sample = _curve_extreme_sample
    app_class._interpolated_visibility_sample = _interpolated_visibility_sample
    app_class._refine_visibility_extreme = _refine_visibility_extreme
    app_class._visibility_samples_with_extrema = _visibility_samples_with_extrema
    app_class._visibility_sun_samples = _visibility_sun_samples
    app_class._twilight_phase_for_sun_altitude = _twilight_phase_for_sun_altitude
    app_class._draw_visibility_twilight_zones = _draw_visibility_twilight_zones
    app_class._visibility_color_for_altitude = _visibility_color_for_altitude
    app_class._draw_visibility_curve = _draw_visibility_curve
    app_class._visibility_sample_at_canvas_x = _visibility_sample_at_canvas_x
    app_class._on_visibility_motion = _on_visibility_motion
    app_class._clear_visibility_hover = _clear_visibility_hover
    app_class._update_visibility_hover = _update_visibility_hover
    app_class._start_visibility_chart_compute = _start_visibility_chart_compute
    app_class._run_visibility_chart_compute = _run_visibility_chart_compute
    app_class._apply_visibility_chart_compute = _apply_visibility_chart_compute
    app_class._draw_visibility_chart_result = _draw_visibility_chart_result
    app_class._update_visibility_chart = _update_visibility_chart

