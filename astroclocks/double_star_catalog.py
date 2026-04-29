"""Double star catalog helpers.

The bundled values are approximate and intended for planning and lookup, not
orbit fitting. RA is expressed in decimal hours, declination in decimal degrees,
separation in arcseconds, and position angle in degrees.
"""

import datetime
import json
import re
from urllib.parse import urlencode
from urllib.request import urlopen

from astroclocks import settings as app_settings
from astroclocks.wds_binary_catalog import WDS_PHYSICAL_BINARIES


WDS_VIZIER_URL = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"
WDS_COLUMNS = "RAJ2000,DEJ2000,WDS,Disc,Comp,Obs2,Nobs,sep2,pa2,mag1,mag2,Notes"
WDS_PHYSICAL_NOTE_FILTERS = ("O", "C", "Z", "T", "V")
WDS_NOTED_NOTE_FILTERS = ("N",)
WDS_APPARENT_NOTE_FILTERS = ("Y", "S", "U")
WDS_UNCERTAIN_NOTE_FILTERS = ("I", "X")
WDS_ROW_LIMIT = 5000
WDS_CACHE_FILENAME = "WDS_double_star_cache.json"
WDS_CACHE_VERSION = 1
_DESIGNATION_CLEANUP_PATTERN = re.compile(r"[^A-Z0-9]")

KNOWN_WDS_PAIR_ALIASES = {
    ("00491+5749", "STF60AB"): {
        "proper_name": "Achird",
        "common_name": "Eta Cassiopeiae",
    },
    ("05387-0236", "BU1032AB"): {
        "common_name": "Sigma Orionis / Sigma Ori AB",
    },
    ("07346+3153", "STF1110AB"): {
        "proper_name": "Castor",
        "common_name": "Alpha Geminorum",
    },
    ("08122+1739", "STF1196ABC"): {
        "proper_name": "Tegmine",
        "common_name": "Zeta Cancri",
    },
    ("10200+1950", "STF1424AB"): {
        "proper_name": "Algieba",
        "common_name": "Gamma Leonis",
    },
    ("12417-0127", "STF1670AB"): {
        "proper_name": "Porrima",
        "common_name": "Gamma Virginis",
    },
    ("14450+2704", "STF1877AB"): {
        "proper_name": "Izar",
        "common_name": "Epsilon Bootis",
        "hd": 129989,
        "hip": 72105,
        "hr": 5506,
    },
    ("17146+1423", "STF2140AB"): {
        "proper_name": "Rasalgethi",
        "common_name": "Alpha Herculis",
    },
    ("18443+3940", "STFA37ABCD"): {
        "proper_name": "Double Double",
        "common_name": "Epsilon Lyrae",
    },
    ("19450+4508", "STF2579AB"): {
        "proper_name": "Fawaris",
        "common_name": "Delta Cygni",
        "hd": 186882,
        "hip": 97165,
        "hr": 7528,
    },
    ("21069+3845", "STF2758AB"): {
        "common_name": "61 Cygni",
    },
}

FEATURED_WDS_DUPLICATE_NAMES = {
    "Achird",
    "Castor",
    "Epsilon Lyrae",
    "Gamma Leonis",
    "Izar",
    "Porrima",
    "Rasalgethi",
    "Sigma Orionis",
    "61 Cygni",
    "Zeta Cancri",
}

SUPPLEMENTAL_WDS_BINARIES = [
    {
        "name": "WDS J14450+2704",
        "designation": "STF1877 AB",
        "ra_hours": 14 + 44 / 60 + 59.14 / 3600,
        "declination": 27 + 4 / 60 + 29.9 / 3600,
        "mag_primary": 2.58,
        "mag_secondary": 4.81,
        "separation": 2.90,
        "separation_precision": 2,
        "position_angle": 347,
        "last_observation_year": 2024,
        "observation_count": 479,
        "constellation": "",
        "source": "WDS",
        "wds": "14450+2704",
        "notes": "N",
        "physical_status": "binary",
    },
]


def _parse_float(value):
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(value):
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _designation_key(value):
    return _DESIGNATION_CLEANUP_PATTERN.sub("", str(value or "").upper())


def _wds_cache_file():
    return app_settings.SETTINGS_FILE.with_name(WDS_CACHE_FILENAME)


def _apply_known_pair_aliases(star):
    wds = str(star.get("wds", "")).strip()
    designation_key = _designation_key(star.get("designation", ""))
    aliases = KNOWN_WDS_PAIR_ALIASES.get((wds, designation_key))
    if aliases:
        star.update(aliases)
    return star


def _wds_star_key(star):
    if star.get("wds"):
        return (
            "wds",
            str(star.get("wds", "")).strip(),
            _designation_key(star.get("designation", "")),
        )
    return (
        "local",
        str(star.get("designation", star.get("name", ""))).strip(),
        round(float(star["ra_hours"]), 5),
        round(float(star["declination"]), 5),
    )


def _normalize_cached_wds_star(star):
    normalized = dict(star)
    normalized.setdefault("name", f"WDS J{normalized.get('wds', '')}".strip())
    normalized.setdefault("designation", normalized.get("wds", ""))
    normalized.setdefault("constellation", "")
    normalized.setdefault("source", "WDS Cache")
    normalized.setdefault("notes", "")
    normalized.setdefault(
        "physical_status",
        _physical_status_from_notes(normalized.get("notes", "")),
    )
    if normalized.get("separation_precision") is None:
        normalized["separation_precision"] = 1
    for key in (
        "ra_hours",
        "declination",
        "mag_primary",
        "mag_secondary",
        "separation",
    ):
        normalized[key] = float(normalized[key])
    normalized["position_angle"] = int(float(normalized.get("position_angle", 0)))
    for key in ("last_observation_year", "observation_count"):
        value = normalized.get(key)
        normalized[key] = int(value) if value is not None and str(value) else None
    return _apply_known_pair_aliases(normalized)


def _parse_ra_hours(value):
    parts = str(value).strip().replace(":", " ").split()
    if len(parts) != 3:
        return None
    hours, minutes, seconds = (float(part) for part in parts)
    return hours + minutes / 60 + seconds / 3600


def _parse_dec_degrees(value):
    parts = str(value).strip().replace(":", " ").split()
    if len(parts) != 3:
        return None
    sign = -1 if parts[0].startswith("-") else 1
    degrees = abs(float(parts[0]))
    minutes = float(parts[1])
    seconds = float(parts[2])
    return sign * (degrees + minutes / 60 + seconds / 3600)


def _physical_status_from_notes(notes):
    notes_text = str(notes or "").strip().upper()
    if any(flag in notes_text for flag in WDS_UNCERTAIN_NOTE_FILTERS):
        return "unknown"
    if any(flag in notes_text for flag in WDS_APPARENT_NOTE_FILTERS):
        return "apparent"
    if any(flag in notes_text for flag in WDS_PHYSICAL_NOTE_FILTERS):
        return "binary"
    return "unknown"


def _query_wds_rows(params, timeout=12):
    query = urlencode(params)
    with urlopen(f"{WDS_VIZIER_URL}?{query}", timeout=timeout) as response:
        content = response.read().decode("utf-8", errors="replace")

    if "VOTable Error" in content or "no connection" in content.lower():
        raise RuntimeError("VizieR WDS database is not reachable")

    rows = []
    header = None
    for line in content.splitlines():
        if not line or line.startswith("#"):
            continue
        values = line.split("\t")
        if values[0] == "RAJ2000":
            header = values
            continue
        if header is None or values[0].startswith('"') or values[0].startswith("-"):
            continue
        if len(values) != len(header):
            continue
        rows.append(dict(zip(header, values)))
    if header is None:
        raise RuntimeError("VizieR WDS response did not contain a data table")
    return rows


def _query_wds_note_rows(params, timeout=12):
    query = urlencode(params)
    with urlopen(f"{WDS_VIZIER_URL}?{query}", timeout=timeout) as response:
        content = response.read().decode("utf-8", errors="replace")

    if "VOTable Error" in content or "no connection" in content.lower():
        raise RuntimeError("VizieR WDS notes database is not reachable")

    rows = []
    header = None
    for line in content.splitlines():
        if not line or line.startswith("#"):
            continue
        values = line.split("\t")
        if "WDS" in values and "Text" in values:
            header = values
            continue
        if header is None or values[0].startswith('"') or values[0].startswith("-"):
            continue
        if len(values) != len(header):
            continue
        if not any(value.strip() for value in values):
            continue
        rows.append(dict(zip(header, values)))
    if header is None:
        raise RuntimeError("VizieR WDS notes response did not contain a data table")
    return rows


def _wds_row_to_star(row):
    ra_hours = _parse_ra_hours(row.get("RAJ2000"))
    declination = _parse_dec_degrees(row.get("DEJ2000"))
    separation = _parse_float(row.get("sep2"))
    mag_primary = _parse_float(row.get("mag1"))
    mag_secondary = _parse_float(row.get("mag2"))
    if (
        ra_hours is None
        or declination is None
        or separation is None
        or mag_primary is None
        or mag_secondary is None
    ):
        return None

    position_angle = _parse_int(row.get("pa2"))
    last_observation_year = _parse_int(row.get("Obs2"))
    observation_count = _parse_int(row.get("Nobs"))
    wds = str(row.get("WDS", "")).strip()
    discoverer = str(row.get("Disc", "")).strip()
    component = str(row.get("Comp", "")).strip()
    designation = " ".join(part for part in (discoverer, component) if part).strip()
    notes = str(row.get("Notes", "")).strip()

    return _apply_known_pair_aliases({
        "name": f"WDS J{wds}" if wds else designation or "WDS",
        "designation": designation or wds,
        "ra_hours": ra_hours,
        "declination": declination,
        "mag_primary": mag_primary,
        "mag_secondary": mag_secondary,
        "separation": separation,
        "separation_precision": 1,
        "position_angle": position_angle if position_angle is not None else 0,
        "last_observation_year": last_observation_year,
        "observation_count": observation_count,
        "constellation": "",
        "source": "WDS",
        "wds": wds,
        "notes": notes,
        "physical_status": _physical_status_from_notes(notes),
    })


def fetch_wds_double_stars(
    max_primary,
    max_secondary,
    min_separation,
    max_separation,
    include_physical=True,
    include_noted=True,
    include_apparent=False,
    include_uncertain=False,
    timeout=12,
    row_limit=WDS_ROW_LIMIT,
):
    """Fetch matching WDS entries from VizieR.

    By default this keeps only likely physical binaries: WDS note ``O`` means
    the pair has an orbit entry, and ``Z`` marks common-parallax physical pairs.
    When ``include_apparent`` is true, the broader WDS result is returned too.
    """
    base_params = {
        "-source": "B/wds/wds",
        "-out.max": str(row_limit),
        "-sort": "mag1",
        "-out": WDS_COLUMNS,
        "mag1": f"..{max_primary:g}",
        "mag2": f"..{max_secondary:g}",
        "sep2": f"{min_separation:g}..{max_separation:g}",
    }

    parameter_sets = []
    if include_physical and include_noted and include_apparent and include_uncertain:
        parameter_sets.append(base_params)
    else:
        note_filters = []
        if include_physical:
            note_filters.extend(WDS_PHYSICAL_NOTE_FILTERS)
        if include_noted:
            note_filters.extend(WDS_NOTED_NOTE_FILTERS)
        if include_apparent:
            note_filters.extend(WDS_APPARENT_NOTE_FILTERS)
        if include_uncertain:
            note_filters.extend(WDS_UNCERTAIN_NOTE_FILTERS)

        for note_filter in dict.fromkeys(note_filters):
            params = dict(base_params)
            params["Notes"] = f"*{note_filter}*"
            parameter_sets.append(params)

    stars_by_key = {}
    for params in parameter_sets:
        for row in _query_wds_rows(params, timeout=timeout):
            star = _wds_row_to_star(row)
            if star is None:
                continue
            key = (
                star.get("wds", ""),
                star.get("designation", ""),
                round(star["separation"], 2),
            )
            stars_by_key[key] = star

    return list(stars_by_key.values())


def load_cached_wds_double_stars():
    cache_file = _wds_cache_file()
    if not cache_file.exists():
        return []

    try:
        with open(cache_file, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return []

    if payload.get("version") != WDS_CACHE_VERSION:
        return []

    stars = []
    for item in payload.get("stars", []):
        if not isinstance(item, dict):
            continue
        try:
            stars.append(_normalize_cached_wds_star(item))
        except (KeyError, TypeError, ValueError):
            continue
    return stars


def save_cached_wds_double_stars(stars):
    cache_file = _wds_cache_file()
    unique = {}
    for star in stars:
        try:
            normalized = _normalize_cached_wds_star(star)
        except (KeyError, TypeError, ValueError):
            continue
        unique[_wds_star_key(normalized)] = normalized

    payload = {
        "version": WDS_CACHE_VERSION,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "stars": list(unique.values()),
    }
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
    except OSError:
        pass
    return list(unique.values())


def merge_cached_wds_double_stars(new_stars):
    merged = {}
    for star in load_cached_wds_double_stars():
        merged[_wds_star_key(star)] = star
    for star in new_stars:
        try:
            normalized = _normalize_cached_wds_star(star)
        except (KeyError, TypeError, ValueError):
            continue
        normalized["source"] = "WDS Cache"
        merged[_wds_star_key(normalized)] = normalized
    return save_cached_wds_double_stars(merged.values())


def build_wds_notes_url(wds):
    params = {
        "-source": "B/wds/notes",
        "-out.max": "100",
        "-out.all": "1",
        "WDS": str(wds or "").strip(),
    }
    return f"{WDS_VIZIER_URL}?{urlencode(params)}"


def fetch_wds_notes(wds, timeout=12):
    wds = str(wds or "").strip()
    if not wds:
        return []
    rows = _query_wds_note_rows(
        {
            "-source": "B/wds/notes",
            "-out.max": "100",
            "-out.all": "1",
            "WDS": wds,
        },
        timeout=timeout,
    )
    return [
        {
            "wds": str(row.get("WDS", "")).strip(),
            "designation": str(row.get("Disc", "")).strip(),
            "text": str(row.get("Text", "")).strip(),
            "reference": str(row.get("RefCode", "")).strip(),
        }
        for row in rows
    ]


FEATURED_DOUBLE_STARS = [
    {
        "name": "Albireo",
        "designation": "Beta Cygni",
        "ra_hours": 19.5120,
        "declination": 27.9597,
        "mag_primary": 3.1,
        "mag_secondary": 5.1,
        "separation": 34.3,
        "position_angle": 54,
        "constellation": "Cyg",
    },
    {
        "name": "Mizar",
        "designation": "Zeta Ursae Majoris",
        "ra_hours": 13.3988,
        "declination": 54.9254,
        "mag_primary": 2.2,
        "mag_secondary": 3.9,
        "separation": 14.4,
        "position_angle": 153,
        "constellation": "UMa",
    },
    {
        "name": "Alcor-Mizar",
        "designation": "80/79 Ursae Majoris",
        "ra_hours": 13.4204,
        "declination": 54.9880,
        "mag_primary": 2.2,
        "mag_secondary": 4.0,
        "separation": 708,
        "position_angle": 71,
        "constellation": "UMa",
    },
    {
        "name": "Castor",
        "designation": "Alpha Geminorum",
        "ra_hours": 7.5766,
        "declination": 31.8883,
        "mag_primary": 1.9,
        "mag_secondary": 2.9,
        "separation": 5.2,
        "position_angle": 52,
        "constellation": "Gem",
    },
    {
        "name": "Gamma Leonis",
        "designation": "Algieba",
        "ra_hours": 10.3329,
        "declination": 19.8415,
        "mag_primary": 2.3,
        "mag_secondary": 3.5,
        "separation": 4.7,
        "position_angle": 126,
        "constellation": "Leo",
    },
    {
        "name": "Gamma Andromedae",
        "designation": "Almach",
        "ra_hours": 2.0650,
        "declination": 42.3297,
        "mag_primary": 2.3,
        "mag_secondary": 5.0,
        "separation": 9.8,
        "position_angle": 63,
        "constellation": "And",
    },
    {
        "name": "Epsilon Lyrae",
        "designation": "Double Double",
        "ra_hours": 18.7380,
        "declination": 39.6700,
        "mag_primary": 4.7,
        "mag_secondary": 5.1,
        "separation": 208,
        "position_angle": 172,
        "constellation": "Lyr",
    },
    {
        "name": "Izar",
        "designation": "Epsilon Bootis",
        "ra_hours": 14.7498,
        "declination": 27.0742,
        "mag_primary": 2.6,
        "mag_secondary": 4.8,
        "separation": 2.9,
        "position_angle": 343,
        "constellation": "Boo",
    },
    {
        "name": "Cor Caroli",
        "designation": "Alpha Canum Venaticorum",
        "ra_hours": 12.9338,
        "declination": 38.3184,
        "mag_primary": 2.9,
        "mag_secondary": 5.6,
        "separation": 19.6,
        "position_angle": 229,
        "constellation": "CVn",
    },
    {
        "name": "Porrima",
        "designation": "Gamma Virginis",
        "ra_hours": 12.6943,
        "declination": -1.4494,
        "mag_primary": 3.5,
        "mag_secondary": 3.5,
        "separation": 3.1,
        "position_angle": 353,
        "constellation": "Vir",
    },
    {
        "name": "Acrab",
        "designation": "Beta Scorpii",
        "ra_hours": 16.0906,
        "declination": -19.8055,
        "mag_primary": 2.6,
        "mag_secondary": 4.9,
        "separation": 13.6,
        "position_angle": 20,
        "constellation": "Sco",
    },
    {
        "name": "Rasalgethi",
        "designation": "Alpha Herculis",
        "ra_hours": 17.2441,
        "declination": 14.3903,
        "mag_primary": 3.4,
        "mag_secondary": 5.4,
        "separation": 4.6,
        "position_angle": 104,
        "constellation": "Her",
    },
    {
        "name": "Polaris",
        "designation": "Alpha Ursae Minoris",
        "ra_hours": 2.5303,
        "declination": 89.2641,
        "mag_primary": 2.0,
        "mag_secondary": 9.1,
        "separation": 18.4,
        "position_angle": 236,
        "constellation": "UMi",
    },
    {
        "name": "Achird",
        "designation": "Eta Cassiopeiae",
        "ra_hours": 0.8184,
        "declination": 57.8152,
        "mag_primary": 3.4,
        "mag_secondary": 7.5,
        "separation": 13.4,
        "position_angle": 326,
        "constellation": "Cas",
    },
    {
        "name": "Sigma Orionis",
        "designation": "Sigma Ori AB",
        "ra_hours": 5.6458,
        "declination": -2.6000,
        "mag_primary": 3.8,
        "mag_secondary": 6.6,
        "separation": 0.25,
        "position_angle": 84,
        "constellation": "Ori",
    },
    {
        "name": "Theta Orionis",
        "designation": "Trapezium",
        "ra_hours": 5.5881,
        "declination": -5.3897,
        "mag_primary": 5.1,
        "mag_secondary": 6.7,
        "separation": 13.0,
        "position_angle": 32,
        "constellation": "Ori",
    },
    {
        "name": "Sirius",
        "designation": "Alpha Canis Majoris",
        "ra_hours": 6.7525,
        "declination": -16.7161,
        "mag_primary": -1.5,
        "mag_secondary": 8.4,
        "separation": 11.0,
        "position_angle": 70,
        "constellation": "CMa",
    },
    {
        "name": "Rigel",
        "designation": "Beta Orionis",
        "ra_hours": 5.2423,
        "declination": -8.2016,
        "mag_primary": 0.2,
        "mag_secondary": 6.8,
        "separation": 9.5,
        "position_angle": 202,
        "constellation": "Ori",
    },
    {
        "name": "Zeta Cancri",
        "designation": "Tegmine",
        "ra_hours": 8.2035,
        "declination": 17.6478,
        "mag_primary": 5.3,
        "mag_secondary": 6.3,
        "separation": 5.9,
        "position_angle": 67,
        "constellation": "Cnc",
    },
    {
        "name": "Iota Cancri",
        "designation": "Iota Cnc",
        "ra_hours": 8.7783,
        "declination": 28.7600,
        "mag_primary": 4.0,
        "mag_secondary": 6.6,
        "separation": 30.6,
        "position_angle": 307,
        "constellation": "Cnc",
    },
    {
        "name": "24 Comae Berenices",
        "designation": "24 Com",
        "ra_hours": 12.5851,
        "declination": 18.3770,
        "mag_primary": 5.1,
        "mag_secondary": 6.3,
        "separation": 20.3,
        "position_angle": 271,
        "constellation": "Com",
    },
    {
        "name": "95 Herculis",
        "designation": "95 Her",
        "ra_hours": 18.0249,
        "declination": 21.5957,
        "mag_primary": 4.9,
        "mag_secondary": 5.2,
        "separation": 6.3,
        "position_angle": 258,
        "constellation": "Her",
    },
    {
        "name": "61 Cygni",
        "designation": "61 Cyg",
        "ra_hours": 21.1152,
        "declination": 38.7459,
        "mag_primary": 5.2,
        "mag_secondary": 6.0,
        "separation": 31.0,
        "position_angle": 150,
        "constellation": "Cyg",
    },
]

FEATURED_DOUBLE_STARS = [
    star for star in FEATURED_DOUBLE_STARS if star["name"] not in FEATURED_WDS_DUPLICATE_NAMES
]

FEATURED_STATUS_OVERRIDES = {
    "Albireo": "apparent",
    "24 Comae Berenices": "apparent",
}

for featured_star in FEATURED_DOUBLE_STARS:
    featured_star.setdefault("source", "Featured")
    featured_star.setdefault(
        "physical_status",
        FEATURED_STATUS_OVERRIDES.get(featured_star["name"], "binary"),
    )


for wds_star in WDS_PHYSICAL_BINARIES:
    _apply_known_pair_aliases(wds_star)

for wds_star in SUPPLEMENTAL_WDS_BINARIES:
    _apply_known_pair_aliases(wds_star)

DOUBLE_STARS = WDS_PHYSICAL_BINARIES + SUPPLEMENTAL_WDS_BINARIES + FEATURED_DOUBLE_STARS
