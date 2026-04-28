"""Double star catalog helpers.

The bundled values are approximate and intended for planning and lookup, not
orbit fitting. RA is expressed in decimal hours, declination in decimal degrees,
separation in arcseconds, and position angle in degrees.
"""

from urllib.parse import urlencode
from urllib.request import urlopen

from astroclocks.wds_binary_catalog import WDS_PHYSICAL_BINARIES


WDS_VIZIER_URL = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"
WDS_COLUMNS = "RAJ2000,DEJ2000,WDS,Disc,Comp,sep2,pa2,mag1,mag2,Notes"
WDS_PHYSICAL_NOTE_FILTERS = ("O", "Z")
WDS_ROW_LIMIT = 5000


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
    if "O" in notes_text or "Z" in notes_text:
        return "binary"
    if "Y" in notes_text:
        return "apparent"
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
    wds = str(row.get("WDS", "")).strip()
    discoverer = str(row.get("Disc", "")).strip()
    component = str(row.get("Comp", "")).strip()
    designation = " ".join(part for part in (discoverer, component) if part).strip()
    notes = str(row.get("Notes", "")).strip()

    return {
        "name": f"WDS {wds}" if wds else designation or "WDS",
        "designation": designation or wds,
        "ra_hours": ra_hours,
        "declination": declination,
        "mag_primary": mag_primary,
        "mag_secondary": mag_secondary,
        "separation": separation,
        "position_angle": position_angle if position_angle is not None else 0,
        "constellation": "",
        "source": "WDS",
        "wds": wds,
        "notes": notes,
        "physical_status": _physical_status_from_notes(notes),
    }


def fetch_wds_double_stars(
    max_primary,
    max_secondary,
    min_separation,
    max_separation,
    include_apparent=False,
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
    if include_apparent:
        parameter_sets.append(base_params)
    else:
        for note_filter in WDS_PHYSICAL_NOTE_FILTERS:
            params = dict(base_params)
            params["Notes"] = f"*{note_filter}*"
            parameter_sets.append(params)

    stars_by_key = {}
    for params in parameter_sets:
        for row in _query_wds_rows(params, timeout=timeout):
            star = _wds_row_to_star(row)
            if star is None:
                continue
            if not include_apparent and star["physical_status"] != "binary":
                continue
            key = (
                star.get("wds", ""),
                star.get("designation", ""),
                round(star["separation"], 2),
            )
            stars_by_key[key] = star

    return list(stars_by_key.values())


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
        "name": "Delta Cygni",
        "designation": "Rukh",
        "ra_hours": 19.7496,
        "declination": 45.1308,
        "mag_primary": 2.9,
        "mag_secondary": 6.3,
        "separation": 2.8,
        "position_angle": 220,
        "constellation": "Cyg",
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


DOUBLE_STARS = WDS_PHYSICAL_BINARIES + FEATURED_DOUBLE_STARS
