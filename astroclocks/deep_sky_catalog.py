"""Deep-sky search catalog helpers."""

import json
import re
import unicodedata
from urllib.parse import urlencode
from urllib.request import urlopen

from astroclocks.deep_sky_photometry import DEEP_SKY_PHOTOMETRY_BY_KEY
from astroclocks.local_deep_sky_catalog import DEEP_SKY_OBJECTS, OPENNGC_ATTRIBUTION
from astroclocks import settings as app_settings


SIMBAD_TAP_URL = "https://simbad.cds.unistra.fr/simbad/sim-tap/sync"
SIMBAD_CACHE_FILENAME = "SIMBAD_deep_sky_cache.json"
SIMBAD_CACHE_VERSION = 1
SIMBAD_ROW_LIMIT = 5000

DEEP_SKY_CATEGORY_ORDER = (
    "planetary_nebula",
    "emission_nebula",
    "reflection_nebula",
    "dark_nebula",
    "supernova_remnant",
    "galaxy",
    "galaxy_cluster",
    "open_cluster",
    "globular_cluster",
    "quasar",
)

DEEP_SKY_CATEGORY_TYPE_CODES = {
    "planetary_nebula": frozenset({"PN"}),
    "emission_nebula": frozenset({"EmN", "HII"}),
    "reflection_nebula": frozenset({"RfN"}),
    "dark_nebula": frozenset({"DrkN"}),
    "supernova_remnant": frozenset({"SNR"}),
    "galaxy": frozenset({"G", "GPair", "GTrpl"}),
    "galaxy_cluster": frozenset({"GGroup"}),
    "open_cluster": frozenset({"OCl", "*Ass", "Cl+N"}),
    "globular_cluster": frozenset({"GCl"}),
    "quasar": frozenset({"QSO"}),
}

DEEP_SKY_TYPE_CATEGORY = {
    type_code: category
    for category, type_codes in DEEP_SKY_CATEGORY_TYPE_CODES.items()
    for type_code in type_codes
}

SIMBAD_CATEGORY_OTYPES = {
    "planetary_nebula": ("PN", "PlanetaryNeb"),
    "emission_nebula": ("HII", "GNe"),
    "reflection_nebula": ("RNe",),
    "dark_nebula": ("DNe", "Cld", "MoC", "CGb"),
    "supernova_remnant": ("SNR",),
    "galaxy": (
        "G",
        "LSB",
        "bCG",
        "SBG",
        "H2G",
        "EmG",
        "AGN",
        "SyG",
        "Sy1",
        "Sy2",
        "rG",
        "LIN",
        "Bla",
        "BLL",
    ),
    "galaxy_cluster": ("GrG", "ClG", "CGG", "SCG"),
    "open_cluster": ("OpC", "As*"),
    "globular_cluster": ("GlC",),
    "quasar": ("QSO",),
}

SUPPLEMENTAL_QUASARS = (
    {
        "name": "3C 273",
        "aliases": ("QSO B1226+023",),
        "ra_hours": 12 + 29 / 60 + 6.7 / 3600,
        "declination": 2 + 3 / 60 + 8.6 / 3600,
        "object_type": "QSO",
        "magnitude": 12.9,
        "magnitude_band": "V",
        "source": "Supplemental quasar list",
    },
    {
        "name": "OJ 287",
        "aliases": ("QSO B0851+202",),
        "ra_hours": 8 + 54 / 60 + 48.9 / 3600,
        "declination": 20 + 6 / 60 + 30.6 / 3600,
        "object_type": "QSO",
        "magnitude": 14.6,
        "magnitude_band": "V",
        "source": "Supplemental quasar list",
    },
    {
        "name": "Markarian 421",
        "aliases": ("Mrk 421",),
        "ra_hours": 11 + 4 / 60 + 27.3 / 3600,
        "declination": 38 + 12 / 60 + 31.8 / 3600,
        "object_type": "QSO",
        "magnitude": 13.3,
        "magnitude_band": "V",
        "source": "Supplemental quasar list",
    },
    {
        "name": "Markarian 501",
        "aliases": ("Mrk 501",),
        "ra_hours": 16 + 53 / 60 + 52.2 / 3600,
        "declination": 39 + 45 / 60 + 36.6 / 3600,
        "object_type": "QSO",
        "magnitude": 13.9,
        "magnitude_band": "V",
        "source": "Supplemental quasar list",
    },
    {
        "name": "3C 279",
        "aliases": ("QSO B1253-055",),
        "ra_hours": 12 + 56 / 60 + 11.2 / 3600,
        "declination": -(5 + 47 / 60 + 21.5 / 3600),
        "object_type": "QSO",
        "magnitude": 17.8,
        "magnitude_band": "V",
        "source": "Supplemental quasar list",
    },
    {
        "name": "CTA 102",
        "aliases": ("QSO B2230+114",),
        "ra_hours": 22 + 32 / 60 + 36.4 / 3600,
        "declination": 11 + 43 / 60 + 50.9 / 3600,
        "object_type": "QSO",
        "magnitude": 17.3,
        "magnitude_band": "V",
        "source": "Supplemental quasar list",
    },
)


def normalize_deep_sky_key(value):
    text = unicodedata.normalize("NFKD", str(value or "").strip())
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.casefold()
    return re.sub(r"[^a-z0-9]+", "", text)


def _simbad_cache_file():
    return app_settings.SETTINGS_FILE.with_name(SIMBAD_CACHE_FILENAME)


def deep_sky_category_for_type(object_type):
    return DEEP_SKY_TYPE_CATEGORY.get(object_type)


def _photometry_for_aliases(name, aliases):
    for alias in (name, *aliases):
        photometry = DEEP_SKY_PHOTOMETRY_BY_KEY.get(normalize_deep_sky_key(alias))
        if photometry is not None:
            magnitude, band = photometry
            return magnitude, band
    return None, ""


def _simbad_object_key(sky_object):
    source_id = normalize_deep_sky_key(sky_object.get("source_id", ""))
    if source_id:
        return ("simbad", source_id)
    return (
        "coordinates",
        normalize_deep_sky_key(sky_object.get("name", "")),
        round(float(sky_object["ra_hours"]), 6),
        round(float(sky_object["declination"]), 5),
    )


def _deep_sky_identifier_keys(sky_object):
    keys = set()
    for value in (
        sky_object.get("name", ""),
        sky_object.get("source_id", ""),
        *sky_object.get("aliases", ()),
    ):
        normalized = normalize_deep_sky_key(value)
        if normalized:
            keys.add(normalized)
    return keys


def _deep_sky_sources(existing, new_object):
    sources = []
    for value in (existing.get("source"), new_object.get("source")):
        if value and value not in sources:
            sources.append(value)
    return " + ".join(sources)


def _merge_deep_sky_entry(existing, new_object):
    merged = dict(existing)

    merged_aliases = []
    for value in (
        existing.get("name", ""),
        *existing.get("aliases", ()),
        new_object.get("name", ""),
        *new_object.get("aliases", ()),
        new_object.get("source_id", ""),
    ):
        text = str(value or "").strip()
        if text and text != merged.get("name") and text not in merged_aliases:
            merged_aliases.append(text)
    merged["aliases"] = tuple(merged_aliases)

    if new_object.get("source") == "SIMBAD/CDS":
        merged["magnitude"] = new_object.get("magnitude", merged.get("magnitude"))
        merged["magnitude_band"] = new_object.get("magnitude_band", merged.get("magnitude_band", ""))
        merged["source_id"] = new_object.get("source_id", merged.get("source_id"))
        merged["object_type"] = new_object.get("object_type", merged.get("object_type"))
        merged["morphology"] = new_object.get("morphology", merged.get("morphology"))
        merged["ra_hours"] = new_object.get("ra_hours", merged.get("ra_hours"))
        merged["declination"] = new_object.get("declination", merged.get("declination"))
    elif merged.get("magnitude") is None and new_object.get("magnitude") is not None:
        merged["magnitude"] = new_object.get("magnitude")
        merged["magnitude_band"] = new_object.get("magnitude_band", merged.get("magnitude_band", ""))

    merged["source"] = _deep_sky_sources(existing, new_object)
    return merged


def merge_deep_sky_objects(*object_lists):
    merged = {}
    identifier_to_key = {}
    for object_list in object_lists:
        for sky_object in object_list:
            key = (
                normalize_deep_sky_key(sky_object.get("name", "")),
                round(float(sky_object["ra_hours"]), 6),
                round(float(sky_object["declination"]), 5),
            )
            if sky_object.get("source_id"):
                key = _simbad_object_key(sky_object)
            identifiers = _deep_sky_identifier_keys(sky_object)
            existing_key = next(
                (identifier_to_key[identifier] for identifier in identifiers if identifier in identifier_to_key),
                None,
            )
            if existing_key is not None and existing_key in merged:
                merged[existing_key] = _merge_deep_sky_entry(merged[existing_key], sky_object)
                for identifier in _deep_sky_identifier_keys(merged[existing_key]):
                    identifier_to_key[identifier] = existing_key
                continue

            merged[key] = dict(sky_object)
            for identifier in identifiers:
                identifier_to_key[identifier] = key
    return list(merged.values())


def load_cached_simbad_deep_sky_objects():
    try:
        with open(_simbad_cache_file(), "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return []

    if data.get("version") != SIMBAD_CACHE_VERSION:
        return []

    objects = []
    for sky_object in data.get("objects", []):
        try:
            normalized = dict(sky_object)
            normalized["ra_hours"] = float(normalized["ra_hours"])
            normalized["declination"] = float(normalized["declination"])
            if normalized.get("magnitude") is not None:
                normalized["magnitude"] = float(normalized["magnitude"])
            normalized["aliases"] = tuple(normalized.get("aliases", ()))
            objects.append(normalized)
        except (KeyError, TypeError, ValueError):
            continue
    return objects


def save_cached_simbad_deep_sky_objects(objects):
    cache_file = _simbad_cache_file()
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    serializable = []
    for sky_object in objects:
        item = dict(sky_object)
        item["aliases"] = list(item.get("aliases", ()))
        serializable.append(item)
    with open(cache_file, "w", encoding="utf-8") as file:
        json.dump(
            {
                "version": SIMBAD_CACHE_VERSION,
                "objects": serializable,
            },
            file,
            indent=2,
        )


def merge_cached_simbad_deep_sky_objects(new_objects, category):
    existing = [
        sky_object
        for sky_object in load_cached_simbad_deep_sky_objects()
        if sky_object.get("category") != category
    ]
    merged = merge_deep_sky_objects(existing, new_objects)
    save_cached_simbad_deep_sky_objects(merged)
    return merged


def _simbad_type_condition(category):
    type_codes = SIMBAD_CATEGORY_OTYPES.get(category)
    if not type_codes:
        raise ValueError(f"Unsupported SIMBAD deep-sky category: {category}")
    values = ", ".join(f"'{type_code}'" for type_code in type_codes)
    return f"basic.otype IN ({values})"


def _simbad_query(category, row_limit):
    columns = (
        "basic.main_id, basic.ra, basic.dec, basic.otype, basic.morph_type, "
        "v.flux AS v_mag, b.flux AS b_mag"
    )
    joins = (
        "LEFT OUTER JOIN flux v ON basic.oid = v.oidref AND v.filter = 'V'\n"
        "LEFT OUTER JOIN flux b ON basic.oid = b.oidref AND b.filter = 'B'"
    )
    return (
        f"SELECT TOP {int(row_limit)} {columns}\n"
        "FROM basic\n"
        f"{joins}\n"
        f"WHERE {_simbad_type_condition(category)}\n"
        "ORDER BY main_id ASC"
    )


def _simbad_band_query(category, min_magnitude, max_magnitude, band, row_limit):
    band = str(band).upper()
    return (
        f"SELECT TOP {int(row_limit)} "
        "basic.main_id, basic.ra, basic.dec, basic.otype, basic.morph_type, flux.flux\n"
        "FROM flux\n"
        "JOIN basic ON basic.oid = flux.oidref\n"
        f"WHERE flux.filter = '{band}'\n"
        f"  AND flux.flux BETWEEN {float(min_magnitude):g} AND {float(max_magnitude):g}\n"
        f"  AND {_simbad_type_condition(category)}"
    )


def _fetch_simbad_json(query, timeout):
    request_url = f"{SIMBAD_TAP_URL}?{urlencode({'request': 'doQuery', 'lang': 'adql', 'format': 'json', 'query': query})}"
    with urlopen(request_url, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _append_simbad_band_rows(objects_by_id, rows, band):
    for row in rows:
        name, ra_degrees, dec_degrees, object_type, morphology, magnitude = row
        source_id = str(name)
        band = str(band).upper()
        existing = objects_by_id.get(source_id)
        if existing is not None and existing.get("magnitude_band") == "V" and band != "V":
            continue
        objects_by_id[source_id] = {
            "name": source_id,
            "aliases": (),
            "ra_hours": float(ra_degrees) / 15,
            "declination": float(dec_degrees),
            "object_type": str(object_type),
            "category": None,
            "morphology": str(morphology).strip() if morphology else "",
            "magnitude": float(magnitude) if magnitude is not None else None,
            "magnitude_band": band,
            "source": "SIMBAD/CDS",
            "source_id": source_id,
        }


def fetch_simbad_deep_sky_objects(
    category,
    min_magnitude=None,
    max_magnitude=None,
    use_magnitude=True,
    row_limit=SIMBAD_ROW_LIMIT,
    timeout=20,
):
    if use_magnitude:
        objects_by_id = {}
        for band in ("V", "B"):
            query = _simbad_band_query(
                category,
                min_magnitude,
                max_magnitude,
                band,
                row_limit,
            )
            payload = _fetch_simbad_json(query, timeout)
            _append_simbad_band_rows(objects_by_id, payload.get("data", []), band)

        objects = list(objects_by_id.values())
        for sky_object in objects:
            sky_object["category"] = category
        objects.sort(
            key=lambda sky_object: (
                sky_object.get("magnitude") is None,
                sky_object.get("magnitude") if sky_object.get("magnitude") is not None else 0,
                str(sky_object.get("name", "")).casefold(),
            )
        )
        return objects[:row_limit]

    payload = _fetch_simbad_json(_simbad_query(category, row_limit), timeout)
    objects = []
    for row in payload.get("data", []):
        name, ra_degrees, dec_degrees, object_type, morphology, v_mag, b_mag = row
        magnitude = v_mag if v_mag is not None else b_mag
        band = "V" if v_mag is not None else ("B" if b_mag is not None else "")
        objects.append(
            {
                "name": str(name),
                "aliases": (),
                "ra_hours": float(ra_degrees) / 15,
                "declination": float(dec_degrees),
                "object_type": str(object_type),
                "category": category,
                "morphology": str(morphology).strip() if morphology else "",
                "magnitude": float(magnitude) if magnitude is not None else None,
                "magnitude_band": band,
                "source": "SIMBAD/CDS",
                "source_id": str(name),
            }
        )
    return objects


def deep_sky_search_objects():
    for name, ra_hours, dec_degrees, aliases, object_type in DEEP_SKY_OBJECTS:
        category = deep_sky_category_for_type(object_type)
        if category is None:
            continue
        magnitude, magnitude_band = _photometry_for_aliases(name, aliases)
        yield {
            "name": name,
            "aliases": tuple(alias for alias in aliases if alias != name),
            "ra_hours": float(ra_hours),
            "declination": float(dec_degrees),
            "object_type": object_type,
            "category": category,
            "magnitude": magnitude,
            "magnitude_band": magnitude_band,
            "source": OPENNGC_ATTRIBUTION,
        }

    for quasar in SUPPLEMENTAL_QUASARS:
        item = dict(quasar)
        item["category"] = "quasar"
        item["aliases"] = tuple(item.get("aliases", ()))
        yield item
