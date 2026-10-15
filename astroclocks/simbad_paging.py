"""Stable SIMBAD page cursors and resumable search metadata."""

import json
import math
import os

from astroclocks import settings


class SimbadPage(list):
    def __init__(self, objects, rows, limit, magnitude_index=None):
        super().__init__(objects)
        self.has_more = len(rows) > limit
        selected = rows[:limit]
        self.loaded = len(selected)
        self.cursor = None
        if selected:
            last = selected[-1]
            self.cursor = [float(last[magnitude_index]) if magnitude_index is not None else None,
                           str(last[0])]


def cursor_joins(band, cursor, grouped=False):
    if not cursor:
        return ""
    identifier = str(cursor[1]).replace("'", "''")
    table = "allfluxes" if grouped else "flux"
    band_filter = "" if grouped else f" AND page_flux.filter = '{band}'"
    return (f"JOIN basic AS page_anchor ON page_anchor.main_id = '{identifier}'\n"
            f"JOIN {table} AS page_flux ON page_flux.oidref = page_anchor.oid{band_filter}\n")


def after_condition(expression, cursor, reference=None):
    if not cursor:
        return ""
    magnitude, identifier = cursor
    identifier = str(identifier).replace("'", "''")
    tie = f"basic.main_id > '{identifier}'"
    if expression is None:
        return f"\n  AND {tie}"
    magnitude = float(magnitude)
    if not math.isfinite(magnitude):
        raise ValueError("Invalid SIMBAD magnitude cursor")
    boundary = reference if reference is not None else repr(magnitude)
    return (f"\n  AND ({expression} > {boundary} OR "
            f"({expression} = {boundary} AND {tie}))")


def search_key(kind, filters):
    keys = (("spectral_type", "min_magnitude", "max_magnitude", "magnitude_band")
            if kind == "stars" else
            ("category", "use_magnitude", "min_magnitude", "max_magnitude", "magnitude_band"))
    return {key: filters.get(key) for key in keys}


def _state_file(kind):
    return settings.SETTINGS_FILE.with_name(f"SIMBAD_{kind}_page.json")


def load_page_state(kind):
    try:
        state = json.loads(_state_file(kind).read_text(encoding="utf-8"))
        if (state.get("version") == 1 and isinstance(state.get("key"), dict)
                and isinstance(state.get("has_more"), bool)
                and isinstance(state.get("count"), int)
                and state["count"] >= 0
                and (state.get("cursor") is None or
                     isinstance(state["cursor"], list) and len(state["cursor"]) == 2)):
            return state
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return None


def clear_page_state(kind):
    _state_file(kind).unlink(missing_ok=True)


def continuation(kind, filters, requested):
    state = load_page_state(kind) if requested else None
    return state if state and state["key"] == search_key(kind, filters) and state["has_more"] else None


def save_page_state(kind, filters, page, previous=None):
    if not isinstance(page, SimbadPage):
        return None
    state = dict(version=1, key=search_key(kind, filters), cursor=page.cursor,
                 has_more=page.has_more, count=(previous["count"] if previous else 0) + page.loaded)
    path = _state_file(kind)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(f".{os.getpid()}.tmp")
    try:
        temporary.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return state


def page_note(app, kind, filters):
    state = load_page_state(kind)
    if not state or state["key"] != search_key(kind, filters):
        return None
    key = "search.page_partial" if state["has_more"] else "search.page_complete"
    return app._tr(key, count=state["count"])
