"""SIMBAD-backed and local stellar search helpers."""

import json
from urllib.parse import urlencode
from urllib.request import urlopen

from astroclocks import settings as app_settings


SIMBAD_TAP_URL = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
SIMBAD_STAR_CACHE_FILENAME = "SIMBAD_star_search_cache.json"
SIMBAD_STAR_CACHE_VERSION = 1
SIMBAD_STAR_ROW_LIMIT = 5000
_LOCAL_STAR_SEARCH_OBJECTS = None


def star_spectral_class(spectral_type, default=""):
    normalized = str(spectral_type or "").strip().upper()
    if normalized in app_settings.STAR_SEARCH_SPECTRAL_TYPES:
        return normalized
    if normalized.startswith("SD") and len(normalized) > 2:
        normalized = normalized[2:]
    elif (
        normalized.startswith("G")
        and len(normalized) > 1
        and normalized[1] in app_settings.STAR_SEARCH_SPECTRAL_TYPES
    ):
        normalized = normalized[1:]
    elif normalized.startswith("D") and len(normalized) > 1:
        return default
    for character in normalized:
        if character in app_settings.STAR_SEARCH_SPECTRAL_TYPES:
            return character
    return default


def normalize_star_spectral_type(spectral_type):
    normalized = star_spectral_class(
        spectral_type,
        default=app_settings.DEFAULT_STAR_SEARCH_SPECTRAL_TYPE,
    )
    if normalized not in app_settings.STAR_SEARCH_SPECTRAL_TYPES:
        return app_settings.DEFAULT_STAR_SEARCH_SPECTRAL_TYPE
    return normalized


def normalize_star_magnitude_band(band):
    normalized = str(band or app_settings.DEFAULT_STAR_SEARCH_MAGNITUDE_BAND).upper()
    if normalized not in app_settings.STAR_SEARCH_MAGNITUDE_BAND_CODES:
        return app_settings.DEFAULT_STAR_SEARCH_MAGNITUDE_BAND
    return normalized


def _star_cache_file():
    return app_settings.SETTINGS_FILE.with_name(SIMBAD_STAR_CACHE_FILENAME)


def _star_key(star):
    source_id = str(star.get("source_id", "")).strip()
    if source_id:
        return ("simbad", source_id)
    return (
        "coordinates",
        str(star.get("name", "")).strip().casefold(),
        round(float(star["ra_hours"]), 6),
        round(float(star["declination"]), 5),
    )


def _normalize_star_record(star, default_source="SIMBAD/CDS"):
    normalized = dict(star)
    normalized["name"] = str(normalized.get("name", "")).strip()
    normalized["ra_hours"] = float(normalized["ra_hours"])
    normalized["declination"] = float(normalized["declination"])
    normalized["magnitude"] = float(normalized["magnitude"])
    normalized["magnitude_band"] = normalize_star_magnitude_band(
        normalized.get("magnitude_band")
    )
    normalized["spectral_type"] = str(normalized.get("spectral_type", "")).strip()
    normalized["spectral_class"] = star_spectral_class(
        normalized.get("spectral_class")
        or normalized["spectral_type"],
    )
    normalized["source"] = str(normalized.get("source") or default_source)
    normalized["source_id"] = str(normalized.get("source_id") or normalized["name"])
    return normalized


def _normalize_cached_star(star):
    return _normalize_star_record(star, default_source="SIMBAD/CDS")


def _merged_star_key(star):
    return (
        "coordinates",
        round(float(star["ra_hours"]), 5),
        round(float(star["declination"]), 4),
        star.get("magnitude_band", ""),
    )


def merge_star_search_objects(*catalogs):
    merged = {}
    for catalog in catalogs:
        for star in catalog or []:
            try:
                default_source = star.get("source", "") if isinstance(star, dict) else ""
                normalized = _normalize_star_record(star, default_source=default_source)
            except (KeyError, TypeError, ValueError):
                continue
            merged[_merged_star_key(normalized)] = normalized
    return list(merged.values())


def load_cached_simbad_stars():
    try:
        with open(_star_cache_file(), "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []

    if data.get("version") != SIMBAD_STAR_CACHE_VERSION:
        return []

    stars = []
    for star in data.get("stars", []):
        try:
            stars.append(_normalize_cached_star(star))
        except (KeyError, TypeError, ValueError):
            continue
    return stars


def save_cached_simbad_stars(stars):
    cache_file = _star_cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    serializable = [_normalize_cached_star(star) for star in stars]
    with open(cache_file, "w", encoding="utf-8") as file:
        json.dump(
            {
                "version": SIMBAD_STAR_CACHE_VERSION,
                "stars": serializable,
            },
            file,
            indent=2,
        )
    return serializable


def merge_cached_simbad_stars(new_stars, spectral_type, magnitude_band):
    spectral_type = normalize_star_spectral_type(spectral_type)
    magnitude_band = normalize_star_magnitude_band(magnitude_band)
    existing = [
        star
        for star in load_cached_simbad_stars()
        if (
            star.get("spectral_class") != spectral_type
            or star.get("magnitude_band") != magnitude_band
        )
    ]
    merged = {}
    for star in (*existing, *new_stars):
        normalized = _normalize_cached_star(star)
        merged[_star_key(normalized)] = normalized
    return save_cached_simbad_stars(merged.values())


def clear_cached_simbad_stars():
    try:
        _star_cache_file().unlink()
        return True
    except FileNotFoundError:
        return False


def local_star_search_objects():
    global _LOCAL_STAR_SEARCH_OBJECTS
    if _LOCAL_STAR_SEARCH_OBJECTS is not None:
        return list(_LOCAL_STAR_SEARCH_OBJECTS)

    from astroclocks.star_catalog import SKY_STARS_J2000
    from astroclocks.star_spectral_catalog import SKY_STAR_SPECTRAL_METADATA

    if len(SKY_STARS_J2000) != len(SKY_STAR_SPECTRAL_METADATA):
        raise RuntimeError("Le catalogue spectral local n'est pas aligné avec la carte du ciel.")

    stars = []
    for (name, ra_hours, declination, magnitude), (hr_number, spectral_type) in zip(
        SKY_STARS_J2000,
        SKY_STAR_SPECTRAL_METADATA,
    ):
        spectral_type = str(spectral_type).strip()
        spectral_class = star_spectral_class(spectral_type)
        if not spectral_class:
            continue
        stars.append(
            _normalize_star_record(
                {
                    "name": name,
                    "ra_hours": ra_hours,
                    "declination": declination,
                    "spectral_type": spectral_type,
                    "spectral_class": spectral_class,
                    "magnitude": magnitude,
                    "magnitude_band": "V",
                    "source": "BSC local",
                    "source_id": f"BSC {int(hr_number)}",
                },
                default_source="BSC local",
            )
        )
    _LOCAL_STAR_SEARCH_OBJECTS = tuple(stars)
    return list(_LOCAL_STAR_SEARCH_OBJECTS)


def _simbad_star_query(spectral_type, min_magnitude, max_magnitude, band, row_limit):
    spectral_type = normalize_star_spectral_type(spectral_type)
    band = normalize_star_magnitude_band(band)
    return (
        f"SELECT TOP {int(row_limit)} "
        "basic.main_id, basic.ra, basic.dec, basic.otype, basic.sp_type, flux.flux\n"
        "FROM basic\n"
        "JOIN flux ON basic.oid = flux.oidref\n"
        f"WHERE flux.filter = '{band}'\n"
        f"  AND flux.flux BETWEEN {float(min_magnitude):g} AND {float(max_magnitude):g}\n"
        f"  AND UPPER(basic.sp_type) LIKE '{spectral_type}%'\n"
        "  AND basic.ra IS NOT NULL\n"
        "  AND basic.dec IS NOT NULL\n"
        "ORDER BY flux.flux ASC"
    )


def _fetch_simbad_json(query, timeout):
    request_url = f"{SIMBAD_TAP_URL}?{urlencode({'request': 'doQuery', 'lang': 'adql', 'format': 'json', 'query': query})}"
    with urlopen(request_url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def fetch_simbad_stars(
    spectral_type,
    min_magnitude,
    max_magnitude,
    magnitude_band=app_settings.DEFAULT_STAR_SEARCH_MAGNITUDE_BAND,
    row_limit=SIMBAD_STAR_ROW_LIMIT,
    timeout=20,
):
    spectral_type = normalize_star_spectral_type(spectral_type)
    magnitude_band = normalize_star_magnitude_band(magnitude_band)
    query = _simbad_star_query(
        spectral_type,
        min_magnitude,
        max_magnitude,
        magnitude_band,
        row_limit,
    )
    payload = _fetch_simbad_json(query, timeout)
    stars = []
    for row in payload.get("data", []):
        name, ra_degrees, dec_degrees, object_type, spectral, magnitude = row
        if magnitude is None:
            continue
        stars.append(
            {
                "name": str(name),
                "ra_hours": float(ra_degrees) / 15,
                "declination": float(dec_degrees),
                "object_type": str(object_type),
                "spectral_type": str(spectral or "").strip(),
                "spectral_class": spectral_type,
                "magnitude": float(magnitude),
                "magnitude_band": magnitude_band,
                "source": "SIMBAD/CDS",
                "source_id": str(name),
            }
        )
    return stars
