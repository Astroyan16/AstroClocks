"""Offline object-name resolution for bundled AstroClocks catalogs."""

import re
import unicodedata

from astroclocks.local_deep_sky_catalog import DEEP_SKY_OBJECTS, OPENNGC_ATTRIBUTION
from astroclocks.star_catalog import SKY_STARS_J2000


_LOCAL_INDEX = None

STAR_ALIASES = {
    "Betelgeuse": ("Alpha Orionis", "Alpha Ori", "Alf Ori"),
    "Rigel": ("Beta Orionis", "Beta Ori"),
    "Sirius": ("Alpha Canis Majoris", "Alpha CMa"),
    "Vega": ("Alpha Lyrae", "Alpha Lyr"),
    "Arcturus": ("Alpha Bootis", "Alpha Boo"),
    "Capella": ("Alpha Aurigae", "Alpha Aur"),
    "Procyon": ("Alpha Canis Minoris", "Alpha CMi"),
    "Aldebaran": ("Alpha Tauri", "Alpha Tau"),
    "Altair": ("Alpha Aquilae", "Alpha Aql"),
    "Antares": ("Alpha Scorpii", "Alpha Sco"),
    "Spica": ("Alpha Virginis", "Alpha Vir"),
    "Pollux": ("Beta Geminorum", "Beta Gem"),
    "Fomalhaut": ("Alpha Piscis Austrini", "Alpha PsA"),
    "Regulus": ("Alpha Leonis", "Alpha Leo"),
    "Deneb": ("Alpha Cygni", "Alpha Cyg"),
    "Polaris": ("Alpha Ursae Minoris", "Alpha UMi"),
    "Castor": ("Alpha Geminorum", "Alpha Gem"),
}


def normalize_local_object_name(name):
    text = unicodedata.normalize("NFKD", str(name or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def _format_ra(ra_hours):
    total_seconds = int(round((float(ra_hours) % 24) * 3600))
    total_seconds %= 24 * 3600
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}h{minutes:02d}m{seconds:02d}s"


def _format_dec(dec_degrees):
    sign = "-" if float(dec_degrees) < 0 else "+"
    total_seconds = int(round(abs(float(dec_degrees)) * 3600))
    degrees = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{sign}{degrees:02d}d{minutes:02d}m{seconds:02d}s"


def _coordinate_result(name, ra_hours, dec_degrees, source, catalog_note=""):
    ra_text = _format_ra(ra_hours)
    dec_text = _format_dec(dec_degrees)
    total_ra_seconds = int(round((float(ra_hours) % 24) * 3600)) % (24 * 3600)
    alpha_hh = total_ra_seconds // 3600
    alpha_mm = (total_ra_seconds % 3600) // 60
    alpha_ss = total_ra_seconds % 60
    total_dec_seconds = int(round(abs(float(dec_degrees)) * 3600))
    delta_dd = total_dec_seconds // 3600
    delta_mm = (total_dec_seconds % 3600) // 60
    delta_ss = total_dec_seconds % 60
    if float(dec_degrees) < 0:
        delta_dd = "-0" if delta_dd == 0 else -delta_dd
    return {
        "message": (
            f"Coordonnées locales ICRS/J2000 :\n"
            f"Objet : {name}\n"
            f"RA : {ra_text}\n"
            f"Dec : {dec_text}"
        ),
        "source": "local",
        "source_catalog": source,
        "source_note": "",
        "display_name": name,
        "source_ra": ra_text,
        "source_dec": dec_text,
        "alpha_hh": f"{alpha_hh:02d}",
        "alpha_mm": f"{alpha_mm:02d}",
        "alpha_ss": f"{alpha_ss:02d}",
        "delta_dd": str(delta_dd),
        "delta_mm": f"{delta_mm:02d}",
        "delta_ss": f"{delta_ss:02d}",
    }


def _add_alias(index, alias, entry):
    key = normalize_local_object_name(alias)
    if key and key not in index:
        index[key] = entry


def _build_local_index():
    index = {}
    for name, ra_hours, dec_degrees, magnitude in SKY_STARS_J2000:
        entry = {
            "name": name,
            "ra_hours": float(ra_hours),
            "dec_degrees": float(dec_degrees),
            "source": "catalogue local étoiles",
            "note": f"magnitude V {float(magnitude):.2f}",
        }
        _add_alias(index, name, entry)
        if str(name).upper().startswith("HR "):
            _add_alias(index, str(name).replace(" ", ""), entry)
        for alias in STAR_ALIASES.get(name, ()):
            _add_alias(index, alias, entry)

    for name, ra_hours, dec_degrees, aliases, object_type in DEEP_SKY_OBJECTS:
        entry = {
            "name": name,
            "ra_hours": float(ra_hours),
            "dec_degrees": float(dec_degrees),
            "source": "OpenNGC local",
            "note": object_type,
        }
        for alias in aliases:
            _add_alias(index, alias, entry)
    return index


def resolve_local_object_coordinates(object_name):
    global _LOCAL_INDEX
    if _LOCAL_INDEX is None:
        _LOCAL_INDEX = _build_local_index()

    key = normalize_local_object_name(object_name)
    entry = _LOCAL_INDEX.get(key)
    if entry is None:
        return None

    note = entry["note"]
    return _coordinate_result(
        entry["name"],
        entry["ra_hours"],
        entry["dec_degrees"],
        entry["source"],
        note,
    )
