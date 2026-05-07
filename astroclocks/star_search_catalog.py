"""SIMBAD-backed and local stellar search helpers."""

import json
import math
import re
from urllib.parse import urlencode
from urllib.request import urlopen

from astroclocks import settings as app_settings


SIMBAD_TAP_URL = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
SIMBAD_STAR_CACHE_FILENAME = "SIMBAD_star_search_cache.json"
SIMBAD_STAR_CACHE_VERSION = 2
SIMBAD_STAR_ROW_LIMIT = 5000
SIMBAD_STAR_PHOTOMETRY_BATCH_SIZE = 200
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


def _star_photometry_band_map(photometry):
    if photometry is None:
        return {}
    if isinstance(photometry, dict):
        return {
            str(band).upper(): float(magnitude)
            for band, magnitude in photometry.items()
            if magnitude is not None
        }
    magnitude, band = photometry
    if magnitude is None or not band:
        return {}
    return {str(band).upper(): float(magnitude)}


def _star_photometry_flag_map(photometry_flags):
    if photometry_flags is None or not isinstance(photometry_flags, dict):
        return {}
    return {
        str(band).upper(): str(flag).strip().upper()
        for band, flag in photometry_flags.items()
        if str(flag or "").strip()
    }


def _star_photometry(star):
    photometry = _star_photometry_band_map(star.get("photometry"))
    if photometry:
        return photometry
    return _star_photometry_band_map((star.get("magnitude"), star.get("magnitude_band")))


def _star_photometry_flags(star):
    flags = _star_photometry_flag_map(star.get("photometry_flags"))
    band = str(star.get("magnitude_band") or "").upper()
    flag = str(star.get("magnitude_flag") or "").strip().upper()
    if band and flag:
        flags.setdefault(band, flag)
    return flags


def _preferred_star_band_order(preferred_band):
    preferred_band = normalize_star_magnitude_band(preferred_band)
    return (preferred_band,) + tuple(
        band
        for band in app_settings.STAR_SEARCH_MAGNITUDE_BANDS
        if band != preferred_band
    )


def _resolved_star_photometry(photometry, preferred_band):
    for band in _preferred_star_band_order(preferred_band):
        if band in photometry:
            return photometry[band], band
    for band, magnitude in photometry.items():
        return magnitude, band
    return None, ""


def resolve_star_photometry(
    star,
    preferred_band=app_settings.DEFAULT_STAR_SEARCH_MAGNITUDE_BAND,
):
    resolved = dict(star)
    photometry = _star_photometry(star)
    photometry_flags = _star_photometry_flags(star)
    resolved["photometry"] = photometry
    resolved["photometry_flags"] = photometry_flags
    magnitude, band = _resolved_star_photometry(photometry, preferred_band)
    resolved["magnitude"] = magnitude
    resolved["magnitude_band"] = band
    resolved["magnitude_flag"] = photometry_flags.get(band, "")
    return resolved


def _normalize_star_record(star, default_source="SIMBAD/CDS"):
    normalized = dict(star)
    normalized["name"] = str(normalized.get("name", "")).strip()
    normalized["ra_hours"] = float(normalized["ra_hours"])
    normalized["declination"] = float(normalized["declination"])
    normalized["aliases"] = tuple(
        str(alias).strip()
        for alias in normalized.get("aliases", ())
        if str(alias).strip()
    )
    preferred_band = normalize_star_magnitude_band(
        normalized.get("magnitude_band")
    )
    photometry = _star_photometry_band_map(normalized.get("photometry"))
    photometry_flags = _star_photometry_flag_map(normalized.get("photometry_flags"))
    if normalized.get("magnitude") is not None:
        photometry.setdefault(preferred_band, float(normalized["magnitude"]))
        if str(normalized.get("magnitude_flag") or "").strip():
            photometry_flags.setdefault(
                preferred_band,
                str(normalized["magnitude_flag"]).strip().upper(),
            )
    normalized["photometry"] = photometry
    normalized["photometry_flags"] = photometry_flags
    normalized["spectral_type"] = str(normalized.get("spectral_type", "")).strip()
    normalized["spectral_class"] = star_spectral_class(
        normalized.get("spectral_class")
        or normalized["spectral_type"],
    )
    normalized["source"] = str(normalized.get("source") or default_source)
    normalized["source_id"] = str(normalized.get("source_id") or normalized["name"])
    return resolve_star_photometry(normalized, preferred_band=preferred_band)


def _normalize_cached_star(star):
    return _normalize_star_record(star, default_source="SIMBAD/CDS")


def _merged_star_key(star):
    return (
        "coordinates",
        round(float(star["ra_hours"]), 5),
        round(float(star["declination"]), 4),
    )


def _star_identifier_variants(value):
    text = " ".join(str(value or "").strip().split())
    if not text:
        return set()
    variants = {text.casefold(), text.replace(" ", "").casefold()}
    match = re.match(r"^(BSC|HR|HD|HIP)\s*(\d+)$", text, re.IGNORECASE)
    if match:
        prefix = match.group(1).upper()
        number = match.group(2)
        canonical = "HR" if prefix == "BSC" else prefix
        variants.add(f"{canonical.casefold()} {number}")
        variants.add(f"{canonical.casefold()}{number}")
    return variants


def _star_identifier_keys(star):
    keys = set()
    for value in (
        star.get("name", ""),
        star.get("source_id", ""),
        *star.get("aliases", ()),
    ):
        keys.update(_star_identifier_variants(value))
    return keys


def _star_coordinate_distance_arcsec(first, second):
    delta_ra_hours = float(first["ra_hours"]) - float(second["ra_hours"])
    delta_ra_degrees = delta_ra_hours * 15
    average_declination = math.radians(
        (float(first["declination"]) + float(second["declination"])) / 2
    )
    delta_ra_arcsec = delta_ra_degrees * 3600 * math.cos(average_declination)
    delta_dec_arcsec = (
        float(first["declination"]) - float(second["declination"])
    ) * 3600
    return math.hypot(delta_ra_arcsec, delta_dec_arcsec)


def _star_coordinate_match(first, second, max_distance_arcsec=2.0):
    return _star_coordinate_distance_arcsec(first, second) <= max_distance_arcsec


def _star_coordinate_bucket(star, bucket_arcsec=4.0):
    ra_bucket = math.floor(float(star["ra_hours"]) * 15 * 3600 / bucket_arcsec)
    dec_bucket = math.floor(float(star["declination"]) * 3600 / bucket_arcsec)
    return (ra_bucket, dec_bucket)


def _star_coordinate_bucket_candidates(star, bucket_arcsec=4.0):
    ra_bucket, dec_bucket = _star_coordinate_bucket(star, bucket_arcsec=bucket_arcsec)
    for ra_offset in (-1, 0, 1):
        for dec_offset in (-1, 0, 1):
            yield (ra_bucket + ra_offset, dec_bucket + dec_offset)


def _merge_star_entries(existing, new_star):
    merged = dict(existing)
    alias_candidates = []
    for value in (
        existing.get("name", ""),
        *existing.get("aliases", ()),
        existing.get("source_id", ""),
        new_star.get("name", ""),
        *new_star.get("aliases", ()),
        new_star.get("source_id", ""),
    ):
        text = str(value or "").strip()
        if text and text not in alias_candidates:
            alias_candidates.append(text)

    photometry = _star_photometry(existing)
    photometry.update(_star_photometry(new_star))
    if photometry:
        merged["photometry"] = photometry
    photometry_flags = _star_photometry_flags(existing)
    photometry_flags.update(_star_photometry_flags(new_star))
    if photometry_flags:
        merged["photometry_flags"] = photometry_flags

    if new_star.get("source") == "SIMBAD/CDS":
        for key in (
            "name",
            "ra_hours",
            "declination",
            "object_type",
            "spectral_type",
            "spectral_class",
            "source_id",
        ):
            merged[key] = new_star.get(key, merged.get(key))

    merged["aliases"] = tuple(
        alias for alias in alias_candidates if alias != merged.get("name")
    )

    sources = []
    for value in (existing.get("source"), new_star.get("source")):
        for chunk in str(value or "").split("+"):
            text = chunk.strip()
            if text and text not in sources:
                sources.append(text)
    merged["source"] = " + ".join(sources)
    return merged


def merge_star_search_objects(
    *catalogs,
    preferred_band=app_settings.DEFAULT_STAR_SEARCH_MAGNITUDE_BAND,
):
    merged = {}
    identifier_to_key = {}
    coordinate_buckets = {}
    key_to_bucket = {}
    for catalog in catalogs:
        for star in catalog or []:
            try:
                default_source = star.get("source", "") if isinstance(star, dict) else ""
                normalized = _normalize_star_record(star, default_source=default_source)
            except (KeyError, TypeError, ValueError):
                continue
            key = _merged_star_key(normalized)
            identifiers = _star_identifier_keys(normalized)
            existing_key = next(
                (
                    identifier_to_key[identifier]
                    for identifier in identifiers
                    if identifier in identifier_to_key
                ),
                None,
            )
            if existing_key is None:
                for bucket_key in _star_coordinate_bucket_candidates(normalized):
                    for candidate_key in coordinate_buckets.get(bucket_key, ()):
                        candidate = merged.get(candidate_key)
                        if candidate is None:
                            continue
                        if _star_coordinate_match(candidate, normalized):
                            existing_key = candidate_key
                            break
                    if existing_key is not None:
                        break
            if existing_key is not None and existing_key in merged:
                merged[existing_key] = _merge_star_entries(merged[existing_key], normalized)
                for identifier in _star_identifier_keys(merged[existing_key]):
                    identifier_to_key[identifier] = existing_key
                previous_bucket = key_to_bucket.get(existing_key)
                current_bucket = _star_coordinate_bucket(merged[existing_key])
                if previous_bucket != current_bucket:
                    if previous_bucket in coordinate_buckets:
                        coordinate_buckets[previous_bucket] = [
                            candidate
                            for candidate in coordinate_buckets[previous_bucket]
                            if candidate != existing_key
                        ]
                        if not coordinate_buckets[previous_bucket]:
                            del coordinate_buckets[previous_bucket]
                    coordinate_buckets.setdefault(current_bucket, []).append(existing_key)
                    key_to_bucket[existing_key] = current_bucket
                continue
            merged[key] = normalized
            for identifier in identifiers:
                identifier_to_key[identifier] = key
            bucket_key = _star_coordinate_bucket(normalized)
            coordinate_buckets.setdefault(bucket_key, []).append(key)
            key_to_bucket[key] = bucket_key
    return [
        resolve_star_photometry(star, preferred_band=preferred_band)
        for star in merged.values()
    ]


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
        if star.get("spectral_class") != spectral_type
    ]
    merged = merge_star_search_objects(
        existing,
        new_stars,
        preferred_band=magnitude_band,
    )
    return save_cached_simbad_stars(merged)


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
                    "aliases": (),
                    "spectral_type": spectral_type,
                    "spectral_class": spectral_class,
                    "magnitude": magnitude,
                    "magnitude_band": "V",
                    "photometry": {"V": magnitude},
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
        "basic.main_id, basic.ra, basic.dec, basic.otype, basic.sp_type, flux.flux AS mag, flux.qual AS mag_qual\n"
        "FROM basic\n"
        "JOIN flux ON basic.oid = flux.oidref\n"
        f"WHERE flux.filter = '{band}'\n"
        f"  AND flux.flux BETWEEN {float(min_magnitude):g} AND {float(max_magnitude):g}\n"
        f"  AND basic.sp_type LIKE '{spectral_type}%'\n"
        "  AND basic.ra IS NOT NULL\n"
        "  AND basic.dec IS NOT NULL\n"
        "ORDER BY mag ASC, main_id ASC"
    )


def _simbad_escape_literal(value):
    return str(value).replace("'", "''")


def _simbad_star_flux_columns_and_joins(bands):
    columns = []
    joins = []
    for index, band in enumerate(bands):
        alias = f"flux_{index}"
        columns.append(f"{alias}.flux AS flux_{band}")
        columns.append(f"{alias}.qual AS qual_{band}")
        joins.append(
            f"LEFT JOIN flux AS {alias} ON basic.oid = {alias}.oidref AND {alias}.filter = '{band}'"
        )
    return ", ".join(columns), "\n".join(joins)


def _simbad_star_photometry_query(source_ids):
    flux_columns, joins = _simbad_star_flux_columns_and_joins(
        app_settings.STAR_SEARCH_MAGNITUDE_BANDS
    )
    identifiers = ", ".join(
        f"'{_simbad_escape_literal(source_id)}'" for source_id in source_ids
    )
    return (
        "SELECT "
        f"basic.main_id, basic.ra, basic.dec, basic.otype, basic.sp_type, {flux_columns}\n"
        "FROM basic\n"
        f"{joins}\n"
        f"WHERE basic.main_id IN ({identifiers})\n"
        "ORDER BY main_id ASC"
    )


def _fetch_simbad_json(query, timeout):
    request_url = f"{SIMBAD_TAP_URL}?{urlencode({'request': 'doQuery', 'lang': 'adql', 'format': 'json', 'query': query})}"
    with urlopen(request_url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _simbad_star_photometry_from_row(row, band_order):
    photometry = {}
    photometry_flags = {}
    values = row[5:]
    for index, band in enumerate(band_order):
        magnitude_index = index * 2
        quality_index = magnitude_index + 1
        magnitude = values[magnitude_index] if magnitude_index < len(values) else None
        quality = values[quality_index] if quality_index < len(values) else None
        if magnitude is not None:
            photometry[band] = float(magnitude)
        if str(quality or "").strip():
            photometry_flags[band] = str(quality).strip().upper()
    return photometry, photometry_flags


def _fetch_simbad_star_photometry_by_id(source_ids, timeout):
    band_order = app_settings.STAR_SEARCH_MAGNITUDE_BANDS
    photometry_by_id = {}
    for start in range(0, len(source_ids), SIMBAD_STAR_PHOTOMETRY_BATCH_SIZE):
        batch_ids = source_ids[start : start + SIMBAD_STAR_PHOTOMETRY_BATCH_SIZE]
        payload = _fetch_simbad_json(_simbad_star_photometry_query(batch_ids), timeout)
        for row in payload.get("data", []):
            source_id = str(row[0])
            photometry, photometry_flags = _simbad_star_photometry_from_row(row, band_order)
            photometry_by_id[source_id] = {
                "ra_hours": float(row[1]) / 15,
                "declination": float(row[2]),
                "object_type": str(row[3]),
                "spectral_type": str(row[4] or "").strip(),
                "photometry": photometry,
                "photometry_flags": photometry_flags,
            }
    return photometry_by_id


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
    initial_rows = payload.get("data", [])
    photometry_by_id = _fetch_simbad_star_photometry_by_id(
        [str(row[0]) for row in initial_rows],
        timeout,
    )
    stars = []
    for row in initial_rows:
        name, ra_degrees, dec_degrees, object_type, spectral, magnitude = row[:6]
        magnitude_flag = row[6] if len(row) > 6 else ""
        stars.append(
            {
                "name": str(name),
                "ra_hours": photometry_by_id.get(str(name), {}).get(
                    "ra_hours",
                    float(ra_degrees) / 15,
                ),
                "declination": photometry_by_id.get(str(name), {}).get(
                    "declination",
                    float(dec_degrees),
                ),
                "aliases": (),
                "object_type": photometry_by_id.get(str(name), {}).get(
                    "object_type",
                    str(object_type),
                ),
                "spectral_type": photometry_by_id.get(str(name), {}).get(
                    "spectral_type",
                    str(spectral or "").strip(),
                ),
                "spectral_class": spectral_type,
                "magnitude": float(magnitude) if magnitude is not None else None,
                "magnitude_band": magnitude_band,
                "photometry": photometry_by_id.get(str(name), {}).get(
                    "photometry",
                    {magnitude_band: float(magnitude)} if magnitude is not None else {},
                ),
                "photometry_flags": photometry_by_id.get(str(name), {}).get(
                    "photometry_flags",
                    (
                        {magnitude_band: str(magnitude_flag).strip().upper()}
                        if magnitude is not None and str(magnitude_flag or "").strip()
                        else {}
                    ),
                ),
                "magnitude_flag": (
                    photometry_by_id.get(str(name), {})
                    .get("photometry_flags", {})
                    .get(
                        magnitude_band,
                        str(magnitude_flag).strip().upper(),
                    )
                ),
                "source": "SIMBAD/CDS",
                "source_id": str(name),
            }
        )
    return merge_star_search_objects(stars, preferred_band=magnitude_band)
