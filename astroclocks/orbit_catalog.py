"""ORB6 visual-binary ephemeris helpers."""

import datetime
import json
import re
from urllib.request import urlopen

from astroclocks import settings as app_settings


ORB6_EPHEMERIS_URLS = (
    "https://crf.usno.navy.mil/data_products/WDS/orb6/orb6ephem.txt",
    "https://www.astro.gsu.edu/wds/orb6/orb6ephem.txt",
)
ORB6_ORBIT_URLS = (
    "https://crf.usno.navy.mil/data_products/WDS/orb6/orb6orbits.txt",
    "https://www.astro.gsu.edu/wds/orb6/orb6orbits.txt",
)
ORB6_CACHE_FILENAME = "ORB6_ephemerides_cache.json"
ORB6_ORBIT_CACHE_FILENAME = "ORB6_orbits_cache.json"
ORB6_CACHE_VERSION = 4

_YEAR_PATTERN = re.compile(r"\b\d{4}\.\d\b")
_DESIGNATION_CLEANUP_PATTERN = re.compile(r"[^A-Z0-9]")
_ORB6_MEMORY_INDEX = None
_ORB6_ORBIT_MEMORY_INDEX = None


def _orb6_cache_file():
    return app_settings.SETTINGS_FILE.with_name(ORB6_CACHE_FILENAME)


def _orb6_orbit_cache_file():
    return app_settings.SETTINGS_FILE.with_name(ORB6_ORBIT_CACHE_FILENAME)


def _field(line, start, end):
    return line[start - 1 : end]


def _parse_float(value):
    text = str(value).strip()
    if not text or text == ".":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_int(value):
    text = str(value).strip()
    if not text or text == ".":
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _parse_float_token(token):
    text = str(token).strip()
    if not text or text == ".":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _decimal_count(token):
    text = str(token).strip()
    if "." not in text or text == ".":
        return 0
    return len(text.rsplit(".", 1)[1])


def _designation_key(value):
    return _DESIGNATION_CLEANUP_PATTERN.sub("", str(value or "").upper())


def _decimal_year(when=None):
    if when is None:
        when = datetime.datetime.now(datetime.timezone.utc)
    elif isinstance(when, datetime.date) and not isinstance(when, datetime.datetime):
        when = datetime.datetime(when.year, when.month, when.day, tzinfo=datetime.timezone.utc)
    elif when.tzinfo is None:
        when = when.replace(tzinfo=datetime.timezone.utc)
    else:
        when = when.astimezone(datetime.timezone.utc)

    start = datetime.datetime(when.year, 1, 1, tzinfo=datetime.timezone.utc)
    end = datetime.datetime(when.year + 1, 1, 1, tzinfo=datetime.timezone.utc)
    return when.year + (when - start).total_seconds() / (end - start).total_seconds()


def _interpolate_angle_degrees(start_angle, end_angle, fraction):
    delta = ((end_angle - start_angle + 180.0) % 360.0) - 180.0
    return (start_angle + delta * fraction) % 360.0


def _julian_day_to_decimal_year(julian_day):
    try:
        z = int(julian_day + 0.5)
        fraction = julian_day + 0.5 - z
        if z < 2299161:
            a_value = z
        else:
            alpha = int((z - 1867216.25) / 36524.25)
            a_value = z + 1 + alpha - int(alpha / 4)
        b_value = a_value + 1524
        c_value = int((b_value - 122.1) / 365.25)
        d_value = int(365.25 * c_value)
        e_value = int((b_value - d_value) / 30.6001)
        day = b_value - d_value - int(30.6001 * e_value) + fraction
        month = e_value - 1 if e_value < 14 else e_value - 13
        year = c_value - 4716 if month > 2 else c_value - 4715
        whole_day = int(day)
        day_fraction = day - whole_day
        start = datetime.datetime(year, 1, 1, tzinfo=datetime.timezone.utc)
        current = datetime.datetime(year, month, whole_day, tzinfo=datetime.timezone.utc)
        current += datetime.timedelta(days=day_fraction)
        end = datetime.datetime(year + 1, 1, 1, tzinfo=datetime.timezone.utc)
        return year + (current - start).total_seconds() / (end - start).total_seconds()
    except (OverflowError, ValueError):
        return 2000.0 + (julian_day - 2451545.0) / 365.25


def _period_to_years(value, unit):
    if value is None or value <= 0:
        return None
    unit = (unit or "y").strip()
    if unit == "c":
        return value * 100.0
    if unit == "d":
        return value / 365.25
    if unit == "h":
        return value / (24.0 * 365.25)
    if unit == "m":
        return value / (60.0 * 24.0 * 365.25)
    return value


def _semimajor_to_arcseconds(value, unit):
    if value is None or value <= 0:
        return None
    unit = (unit or "a").strip()
    if unit == "m":
        return value / 1000.0
    if unit == "M":
        return value * 60.0
    if unit == "u":
        return value / 1000000.0
    return value


def _t0_to_decimal_year(value, unit):
    if value is None:
        return None
    unit = (unit or "y").strip()
    if unit == "c":
        return value * 100.0
    if unit == "d":
        return _julian_day_to_decimal_year(value + 2400000.0)
    if unit == "m":
        return _julian_day_to_decimal_year(value + 2400000.5)
    return value


def _parse_orb6_ephemerides(content):
    years = []
    entries = []

    for line in content.splitlines():
        matches = _YEAR_PATTERN.findall(line)
        if len(matches) >= 2:
            years = [float(match) for match in matches]
            break

    if not years:
        raise RuntimeError("ORB6 ephemeris years were not found")

    for line in content.splitlines():
        if len(line) < 47 or not line[:5].isdigit():
            continue

        wds = _field(line, 1, 10).strip()
        designation = _field(line, 12, 25).strip()
        grade_value = _parse_int(_field(line, 30, 30))
        reference = _field(line, 35, 42).strip()
        tokens = line[46:].split()
        predictions = []
        for index, year in enumerate(years):
            theta_index = index * 2
            rho_index = theta_index + 1
            if rho_index >= len(tokens):
                break
            theta_token = tokens[theta_index]
            rho_token = tokens[rho_index]
            theta = _parse_float_token(theta_token)
            rho = _parse_float_token(rho_token)
            if theta is None or rho is None:
                continue
            predictions.append(
                {
                    "year": year,
                    "theta": theta,
                    "rho": rho,
                    "rho_precision": _decimal_count(rho_token),
                }
            )

        notes = " ".join(tokens[len(years) * 2 :]).strip()
        if not wds or not designation or grade_value is None or not predictions:
            continue
        if grade_value == 9 or "astrometric" in notes.lower():
            continue

        entries.append(
            {
                "wds": wds,
                "designation": designation.strip(),
                "designation_key": _designation_key(designation),
                "grade": grade_value,
                "reference": reference.strip(),
                "predictions": predictions,
                "notes": notes,
            }
        )

    return entries


def _parse_orbit_line(line):
    if len(line) < 245 or not line[:6].strip().isdigit():
        return None

    wds = _field(line, 20, 29).strip()
    designation = _field(line, 31, 44).strip()
    ads = _parse_int(_field(line, 46, 50))
    hd = _parse_int(_field(line, 52, 57))
    hip = _parse_int(_field(line, 59, 64))
    grade = _parse_int(_field(line, 234, 234))
    if not wds or not designation or grade is None or grade not in {1, 2, 3, 4, 5}:
        return None

    period_value = _parse_float(_field(line, 81, 92))
    period_unit = _field(line, 93, 93).strip() or "y"
    semimajor_value = _parse_float(_field(line, 106, 114))
    semimajor_unit = _field(line, 115, 115).strip() or "a"
    inclination = _parse_float(_field(line, 126, 133))
    node = _parse_float(_field(line, 144, 151))
    periastron_value = _parse_float(_field(line, 163, 174))
    periastron_unit = _field(line, 175, 175).strip() or "y"
    eccentricity = _parse_float(_field(line, 188, 195))
    periastron_longitude = _parse_float(_field(line, 206, 213))
    reference = _field(line, 238, 245).strip()

    period_years = _period_to_years(period_value, period_unit)
    semimajor_arcsec = _semimajor_to_arcseconds(semimajor_value, semimajor_unit)
    periastron_year = _t0_to_decimal_year(periastron_value, periastron_unit)
    required = (
        period_years,
        semimajor_arcsec,
        inclination,
        node,
        periastron_year,
        eccentricity,
        periastron_longitude,
    )
    if any(value is None for value in required):
        return None
    if not 0 <= eccentricity < 1:
        return None

    return {
        "wds": wds,
        "designation": designation,
        "designation_key": _designation_key(designation),
        "ads": ads,
        "hd": hd,
        "hip": hip,
        "period_years": period_years,
        "period_value": period_value,
        "period_unit": period_unit,
        "semimajor_arcsec": semimajor_arcsec,
        "semimajor_value": semimajor_value,
        "semimajor_unit": semimajor_unit,
        "inclination_deg": inclination,
        "node_deg": node,
        "periastron_year": periastron_year,
        "periastron_value": periastron_value,
        "periastron_unit": periastron_unit,
        "eccentricity": eccentricity,
        "periastron_longitude_deg": periastron_longitude,
        "grade": grade,
        "reference": reference,
    }


def _parse_orb6_orbits(content):
    entries = []
    for line in content.splitlines():
        entry = _parse_orbit_line(line)
        if entry is not None:
            entries.append(entry)
    return entries


def _entry_rank(entry):
    return (
        entry.get("grade", 9),
        entry.get("reference", ""),
        entry.get("designation", ""),
    )


def _build_orb6_index(entries, *, from_cache=False, downloaded_at="", source_url=""):
    by_pair = {}

    for entry in entries:
        pair_key = (entry["wds"], entry["designation_key"])
        existing = by_pair.get(pair_key)
        if existing is None or _entry_rank(entry) < _entry_rank(existing):
            by_pair[pair_key] = entry

    return {
        "by_pair": by_pair,
        "count": len(entries),
        "from_cache": from_cache,
        "downloaded_at": downloaded_at,
        "source_url": source_url,
    }


def _build_orbit_index(entries, *, from_cache=False, downloaded_at="", source_url=""):
    by_pair = {}

    for entry in entries:
        pair_key = (entry["wds"], entry["designation_key"])
        existing = by_pair.get(pair_key)
        if existing is None or _entry_rank(entry) < _entry_rank(existing):
            by_pair[pair_key] = entry

    return {
        "by_pair": by_pair,
        "count": len(entries),
        "from_cache": from_cache,
        "downloaded_at": downloaded_at,
        "source_url": source_url,
    }


def _write_orb6_cache(entries, source_url):
    cache_file = _orb6_cache_file()
    downloaded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "version": ORB6_CACHE_VERSION,
        "downloaded_at": downloaded_at,
        "source_url": source_url,
        "entries": entries,
    }
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
    except OSError:
        pass
    return downloaded_at


def _write_orb6_orbit_cache(entries, source_url):
    cache_file = _orb6_orbit_cache_file()
    downloaded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {
        "version": ORB6_CACHE_VERSION,
        "downloaded_at": downloaded_at,
        "source_url": source_url,
        "entries": entries,
    }
    try:
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_file, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=2)
    except OSError:
        pass
    return downloaded_at


def load_cached_orb6_ephemerides():
    """Load the persisted ORB6 ephemeris index, if one exists."""
    global _ORB6_MEMORY_INDEX

    cache_file = _orb6_cache_file()
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("version") != ORB6_CACHE_VERSION:
        return None

    entries = payload.get("entries")
    if not isinstance(entries, list):
        return None

    index = _build_orb6_index(
        entries,
        from_cache=True,
        downloaded_at=str(payload.get("downloaded_at", "")),
        source_url=str(payload.get("source_url", "")),
    )
    _ORB6_MEMORY_INDEX = index
    return index


def load_cached_orb6_orbits():
    """Load the persisted ORB6 orbital-element index, if one exists."""
    global _ORB6_ORBIT_MEMORY_INDEX

    cache_file = _orb6_orbit_cache_file()
    if not cache_file.exists():
        return None

    try:
        with open(cache_file, "r", encoding="utf-8") as file:
            payload = json.load(file)
    except (OSError, json.JSONDecodeError):
        return None

    if payload.get("version") != ORB6_CACHE_VERSION:
        return None

    entries = payload.get("entries")
    if not isinstance(entries, list):
        return None

    index = _build_orbit_index(
        entries,
        from_cache=True,
        downloaded_at=str(payload.get("downloaded_at", "")),
        source_url=str(payload.get("source_url", "")),
    )
    _ORB6_ORBIT_MEMORY_INDEX = index
    return index


def fetch_orb6_ephemerides(timeout=8):
    """Fetch and index ORB6 ephemerides, falling back to the persisted cache."""
    global _ORB6_MEMORY_INDEX

    if _ORB6_MEMORY_INDEX is not None and not _ORB6_MEMORY_INDEX.get("from_cache"):
        return _ORB6_MEMORY_INDEX

    errors = []
    for url in ORB6_EPHEMERIS_URLS:
        try:
            with urlopen(url, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
            entries = _parse_orb6_ephemerides(content)
            downloaded_at = _write_orb6_cache(entries, url)
            index = _build_orb6_index(
                entries,
                from_cache=False,
                downloaded_at=downloaded_at,
                source_url=url,
            )
            _ORB6_MEMORY_INDEX = index
            return index
        except Exception as exc:
            errors.append(f"{url}: {exc}")

    cached_index = _ORB6_MEMORY_INDEX if _ORB6_MEMORY_INDEX is not None else None
    if cached_index is None:
        cached_index = load_cached_orb6_ephemerides()
    if cached_index is not None:
        cached_index["fetch_error"] = "; ".join(errors)
        return cached_index

    raise RuntimeError("; ".join(errors) or "ORB6 ephemerides are unavailable")


def fetch_orb6_orbits(timeout=8):
    """Fetch and index ORB6 orbital elements, falling back to the persisted cache."""
    global _ORB6_ORBIT_MEMORY_INDEX

    if _ORB6_ORBIT_MEMORY_INDEX is not None and not _ORB6_ORBIT_MEMORY_INDEX.get("from_cache"):
        return _ORB6_ORBIT_MEMORY_INDEX

    errors = []
    for url in ORB6_ORBIT_URLS:
        try:
            with urlopen(url, timeout=timeout) as response:
                content = response.read().decode("utf-8", errors="replace")
            entries = _parse_orb6_orbits(content)
            downloaded_at = _write_orb6_orbit_cache(entries, url)
            index = _build_orbit_index(
                entries,
                from_cache=False,
                downloaded_at=downloaded_at,
                source_url=url,
            )
            _ORB6_ORBIT_MEMORY_INDEX = index
            return index
        except Exception as exc:
            errors.append(f"{url}: {exc}")

    cached_index = (
        _ORB6_ORBIT_MEMORY_INDEX if _ORB6_ORBIT_MEMORY_INDEX is not None else None
    )
    if cached_index is None:
        cached_index = load_cached_orb6_orbits()
    if cached_index is not None:
        cached_index["fetch_error"] = "; ".join(errors)
        return cached_index

    raise RuntimeError("; ".join(errors) or "ORB6 orbital elements are unavailable")


def _find_orb6_entry(star, orb6_index):
    wds = str(star.get("wds", "")).strip()
    if not wds or not orb6_index:
        return None

    designation_key = _designation_key(star.get("designation", ""))
    if designation_key:
        entry = orb6_index.get("by_pair", {}).get((wds, designation_key))
        if entry is not None:
            return entry

    return None


def _scaled_rho_precision(precision, separation_scale):
    if separation_scale == 60.0:
        return max(0, precision - 1)
    return precision


def _ephemeris_separation_scale(orbit_entry):
    if orbit_entry is not None and orbit_entry.get("semimajor_unit") == "M":
        return 60.0
    return 1.0


def _interpolate_entry(entry, when=None, separation_scale=1.0):
    predictions = sorted(entry["predictions"], key=lambda item: item["year"])
    if not predictions:
        return None

    target_year = _decimal_year(when)
    if target_year <= predictions[0]["year"]:
        left = right = predictions[0]
    elif target_year >= predictions[-1]["year"]:
        left = right = predictions[-1]
    else:
        left = predictions[0]
        right = predictions[-1]
        for current, following in zip(predictions, predictions[1:]):
            if current["year"] <= target_year <= following["year"]:
                left = current
                right = following
                break

    if left["year"] == right["year"]:
        theta = left["theta"]
        rho = left["rho"] * separation_scale
        precision = left["rho_precision"]
    else:
        fraction = (target_year - left["year"]) / (right["year"] - left["year"])
        theta = _interpolate_angle_degrees(left["theta"], right["theta"], fraction)
        rho = (
            left["rho"] + (right["rho"] - left["rho"]) * fraction
        ) * separation_scale
        precision = max(left["rho_precision"], right["rho_precision"])

    return {
        "orb6_current_pa": theta,
        "orb6_current_separation": rho,
        "orb6_separation_precision": _scaled_rho_precision(
            precision,
            separation_scale,
        ),
        "orb6_epoch": target_year,
        "orb6_reference": entry["reference"],
        "orb6_grade": entry["grade"],
        "orb6_note": entry["notes"],
    }


def _solve_eccentric_anomaly(mean_anomaly, eccentricity):
    import math

    two_pi = 2.0 * math.pi
    mean_anomaly = mean_anomaly % two_pi
    eccentric_anomaly = mean_anomaly if eccentricity < 0.8 else math.pi
    for _iteration in range(60):
        denominator = 1.0 - eccentricity * math.cos(eccentric_anomaly)
        if abs(denominator) < 1e-14:
            break
        delta = (
            eccentric_anomaly
            - eccentricity * math.sin(eccentric_anomaly)
            - mean_anomaly
        ) / denominator
        eccentric_anomaly -= delta
        if abs(delta) < 1e-12:
            return eccentric_anomaly % two_pi
        if not math.isfinite(eccentric_anomaly):
            break

    low = 0.0
    high = two_pi
    for _iteration in range(80):
        midpoint = (low + high) / 2.0
        value = midpoint - eccentricity * math.sin(midpoint) - mean_anomaly
        if value < 0:
            low = midpoint
        else:
            high = midpoint
    return ((low + high) / 2.0) % two_pi


def orbit_position_at_year(orbit, year):
    """Compute apparent position for a visual-binary orbit at a decimal year."""
    import math

    period = orbit["period_years"]
    eccentricity = orbit["eccentricity"]
    mean_anomaly = (2.0 * math.pi * ((year - orbit["periastron_year"]) / period)) % (
        2.0 * math.pi
    )
    eccentric_anomaly = _solve_eccentric_anomaly(mean_anomaly, eccentricity)

    semimajor = orbit["semimajor_arcsec"]
    x_orbit = semimajor * (math.cos(eccentric_anomaly) - eccentricity)
    y_orbit = semimajor * math.sqrt(1.0 - eccentricity * eccentricity) * math.sin(
        eccentric_anomaly
    )
    node = math.radians(orbit["node_deg"])
    periastron_longitude = math.radians(orbit["periastron_longitude_deg"])
    inclination = math.radians(orbit["inclination_deg"])

    north = x_orbit * (
        math.cos(node) * math.cos(periastron_longitude)
        - math.sin(node) * math.sin(periastron_longitude) * math.cos(inclination)
    ) - y_orbit * (
        math.cos(node) * math.sin(periastron_longitude)
        + math.sin(node) * math.cos(periastron_longitude) * math.cos(inclination)
    )
    east = x_orbit * (
        math.sin(node) * math.cos(periastron_longitude)
        + math.cos(node) * math.sin(periastron_longitude) * math.cos(inclination)
    ) - y_orbit * (
        math.sin(node) * math.sin(periastron_longitude)
        - math.cos(node) * math.cos(periastron_longitude) * math.cos(inclination)
    )
    rho = math.hypot(east, north)
    theta = math.degrees(math.atan2(east, north)) % 360.0
    return {
        "year": year,
        "east": east,
        "north": north,
        "rho": rho,
        "theta": theta,
    }


def sample_orbit_points(orbit, start_year=None, count=720):
    """Sample one apparent revolution of an ORB6 visual-binary orbit."""
    import math

    period = orbit["period_years"]
    if start_year is None:
        current_year = _decimal_year()
        cycles = math.floor((current_year - orbit["periastron_year"]) / period)
        start_year = orbit["periastron_year"] + cycles * period
    count = max(24, int(count))
    if count == 1:
        return [orbit_position_at_year(orbit, start_year)]
    return [
        orbit_position_at_year(orbit, start_year + period * index / (count - 1))
        for index in range(count)
    ]


def enrich_double_stars_with_orb6(stars, orb6_index, when=None, orbit_index=None):
    """Return copies of stars enriched with current ORB6 theta/rho when available."""
    enriched = []
    matched = 0
    for star in stars:
        enriched_star = dict(star)
        entry = _find_orb6_entry(enriched_star, orb6_index)
        orbit_entry = _find_orb6_entry(enriched_star, orbit_index)
        separation_scale = _ephemeris_separation_scale(orbit_entry)
        ephemeris = (
            _interpolate_entry(entry, when, separation_scale)
            if entry is not None
            else None
        )
        if ephemeris is not None:
            enriched_star.update(ephemeris)
            matched += 1
        if orbit_entry is not None:
            enriched_star["orb6_orbit"] = orbit_entry
            enriched_star["orb6_has_orbit"] = True
            for catalog_key in ("ads", "hd", "hip"):
                catalog_value = orbit_entry.get(catalog_key)
                if catalog_value is not None and not enriched_star.get(catalog_key):
                    enriched_star[catalog_key] = catalog_value
        enriched.append(enriched_star)
    return enriched, matched
