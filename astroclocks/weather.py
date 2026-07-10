"""Weather data helpers used by optional refraction settings."""

import gzip
import json
import math
import csv
import datetime
import io
import urllib.parse
from json import JSONDecodeError
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from astroclocks.secure_store import load_meteofrance_application_id


METAR_STATIONS_CACHE_URL = "https://aviationweather.gov/data/cache/stations.cache.json.gz"
METAR_DATA_URL = "https://aviationweather.gov/api/data/metar"
METEOFRANCE_TOKEN_URL = "https://portail-api.meteofrance.fr/token"
METEOFRANCE_DPOBS_BASE_URL = "https://public-api.meteofrance.fr/public/DPObs"
METEOFRANCE_DPOBS_API_URL = f"{METEOFRANCE_DPOBS_BASE_URL}/station/infrahoraire-6m"
METEOFRANCE_STATIONS_URL = f"{METEOFRANCE_DPOBS_BASE_URL}/liste-stations"
METEOFRANCE_DPCLIM_BASE_URL = "https://public-api.meteofrance.fr/public/DPClim/v1"
METEOFRANCE_DPCLIM_STATIONS_URL = (
    f"{METEOFRANCE_DPCLIM_BASE_URL}/liste-stations/infrahoraire-6m"
)
SYNOP_STATIONS_URL = "https://meteofrance.s3.sbg.io.cloud.ovh.net/data/synchro_ftp/OBS/SYNOP/postes_synop.geojson"
SYNOP_YEAR_URL_TEMPLATE = (
    "https://meteofrance.s3.sbg.io.cloud.ovh.net/data/synchro_ftp/OBS/SYNOP/synop_{year}.csv.gz"
)
WEATHER_USER_AGENT = "AstroClocks weather lookup"
MAX_WEATHER_OBSERVATION_AGE_HOURS = 6
METEOFRANCE_STATIONS_CACHE_SECONDS = 3600
METEOFRANCE_OBSERVATION_CACHE_SECONDS = 300
METEOFRANCE_MAX_OBSERVATION_LOOKUPS_PER_SEARCH = 20
_METEOFRANCE_ACCESS_TOKEN = {"value": None, "expires_at": None}
_METEOFRANCE_STATIONS_CACHE = {"value": None, "expires_at": None, "credential": None}
_METEOFRANCE_OBSERVATION_CACHE = {}


def _haversine_km(latitude_a, longitude_a, latitude_b, longitude_b):
    radius_km = 6371.0088
    lat_a = math.radians(float(latitude_a))
    lat_b = math.radians(float(latitude_b))
    delta_lat = lat_b - lat_a
    delta_lon = math.radians(float(longitude_b) - float(longitude_a))
    chord = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2) ** 2
    )
    return 2 * radius_km * math.asin(min(1.0, math.sqrt(chord)))


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc)


def _cache_is_valid(cache_entry, now=None):
    if not cache_entry:
        return False
    now = now or _utc_now()
    expires_at = cache_entry.get("expires_at")
    return expires_at is not None and now < expires_at


def _read_json_url(url, timeout=15):
    request = Request(url, headers={"User-Agent": WEATHER_USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read()
    if not payload:
        return None
    if url.endswith(".gz"):
        payload = gzip.decompress(payload)
    return json.loads(payload.decode("utf-8"))


def _read_text_url(url, timeout=15):
    request = Request(url, headers={"User-Agent": WEATHER_USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        payload = response.read()
    if not payload:
        return ""
    if url.endswith(".gz"):
        payload = gzip.decompress(payload)
    return payload.decode("utf-8")


def _read_json_request(request, timeout=15):
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        snippet = " ".join(body.strip().split())[:180] or exc.reason
        raise ValueError(f"Météo-France HTTP {exc.code}: {snippet}") from exc
    if not payload:
        return None
    text = payload.decode("utf-8", errors="replace")
    try:
        return json.loads(text)
    except JSONDecodeError as exc:
        snippet = " ".join(text.strip().split())[:180] or "empty response"
        raise ValueError(
            f"Expected a JSON response from Météo-France, got: {snippet}"
        ) from exc


def _read_text_request(request, timeout=15):
    try:
        with urlopen(request, timeout=timeout) as response:
            payload = response.read()
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        snippet = " ".join(body.strip().split())[:180] or exc.reason
        raise ValueError(f"Météo-France HTTP {exc.code}: {snippet}") from exc
    if not payload:
        return ""
    return payload.decode("utf-8-sig")


def load_metar_stations(timeout=20):
    """Return stations that can report METAR observations."""
    stations = _read_json_url(METAR_STATIONS_CACHE_URL, timeout=timeout)
    return [
        station
        for station in stations
        if station.get("icaoId")
        and "METAR" in (station.get("siteType") or ())
        and station.get("lat") is not None
        and station.get("lon") is not None
    ]


def load_synop_stations(timeout=20):
    """Return Météo-France SYNOP stations."""
    payload = _read_json_url(SYNOP_STATIONS_URL, timeout=timeout)
    stations = []
    for feature in payload.get("features", []):
        properties = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        if len(coordinates) < 2 or not properties.get("Id"):
            continue
        stations.append(
            {
                "station_id": str(properties["Id"]),
                "station_name": properties.get("Nom") or str(properties["Id"]),
                "latitude": float(coordinates[1]),
                "longitude": float(coordinates[0]),
                "elevation_m": properties.get("Altitude"),
                "source": "SYNOP",
            }
        )
    return stations


def nearest_metar_stations(latitude, longitude, limit=12, max_distance_km=150, timeout=20):
    """Return the nearest METAR stations around a site."""
    candidates = []
    for station in load_metar_stations(timeout=timeout):
        distance_km = _haversine_km(
            latitude,
            longitude,
            station["lat"],
            station["lon"],
        )
        if distance_km <= max_distance_km:
            candidates.append((distance_km, station))
    candidates.sort(key=lambda item: item[0])
    return candidates[:limit]


def nearest_synop_stations(latitude, longitude, limit=12, max_distance_km=150, timeout=20):
    """Return the nearest Météo-France SYNOP stations around a site."""
    candidates = []
    for station in load_synop_stations(timeout=timeout):
        distance_km = _haversine_km(
            latitude,
            longitude,
            station["latitude"],
            station["longitude"],
        )
        if distance_km <= max_distance_km:
            candidates.append((distance_km, station))
    candidates.sort(key=lambda item: item[0])
    return candidates[:limit]


def nearest_metar_station_options(latitude, longitude, limit=3, max_distance_km=150):
    """Return nearest METAR stations formatted for UI selection."""
    return [
        {
            "station_id": station["icaoId"],
            "station_name": station.get("site") or station["icaoId"],
            "distance_km": distance_km,
            "latitude": station["lat"],
            "longitude": station["lon"],
            "elevation_m": station.get("elev"),
            "source": "METAR",
        }
        for distance_km, station in nearest_metar_stations(
            latitude,
            longitude,
            limit=limit,
            max_distance_km=max_distance_km,
        )
    ]


def _csv_dialect_for_text(text):
    sample = text[:4096]
    try:
        return csv.Sniffer().sniff(sample, delimiters=";,")
    except csv.Error:
        dialect = csv.excel()
        dialect.delimiter = ";" if sample.count(";") >= sample.count(",") else ","
        return dialect


def _case_insensitive_row_get(row, *names):
    lookup = {str(key).strip().lower(): value for key, value in row.items()}
    for name in names:
        value = lookup.get(name.lower())
        if value not in (None, ""):
            return value
    return None


def _float_or_none(value):
    if value in (None, ""):
        return None
    return float(str(value).replace(",", "."))


def _meteofrance_station_from_row(row):
    station_id = _case_insensitive_row_get(
        row,
        "id_station",
        "idstation",
        "id",
        "Id",
        "geo_id_insee",
        "geo_id_wmo",
        "numer_sta",
    )
    latitude = _float_or_none(
        _case_insensitive_row_get(row, "lat", "latitude", "Latitude")
    )
    longitude = _float_or_none(
        _case_insensitive_row_get(row, "lon", "longitude", "Longitude")
    )
    if not station_id or latitude is None or longitude is None:
        return None
    name = _case_insensitive_row_get(
        row,
        "nom",
        "name",
        "libelle",
        "nom_usuel",
        "station_name",
        "Nom",
    )
    elevation = _float_or_none(
        _case_insensitive_row_get(row, "altitude", "alt", "z", "elevation")
    )
    return {
        "source": "METEOFRANCE",
        "station_id": str(station_id).strip(),
        "station_name": (str(name).strip() if name else str(station_id).strip()),
        "latitude": latitude,
        "longitude": longitude,
        "elevation_m": elevation,
    }


def _parse_meteofrance_stations_text(text):
    if not text.strip():
        return []
    stations = []
    dialect = _csv_dialect_for_text(text)
    for row in csv.DictReader(io.StringIO(text), dialect=dialect):
        station = _meteofrance_station_from_row(row)
        if station is not None:
            stations.append(station)
    return stations


def load_meteofrance_stations(timeout=20, application_id=None):
    """Return live Météo-France DPObs stations from the station list endpoint."""
    headers = _meteofrance_authorization_headers(api_key=application_id)
    if not headers:
        return []
    credential = headers["apikey"]
    now = _utc_now()
    if (
        _METEOFRANCE_STATIONS_CACHE.get("credential") == credential
        and _cache_is_valid(_METEOFRANCE_STATIONS_CACHE, now=now)
    ):
        return list(_METEOFRANCE_STATIONS_CACHE.get("value") or [])
    query = urlencode({"format": "csv"})
    request = Request(
        f"{METEOFRANCE_STATIONS_URL}?{query}",
        headers=headers,
    )
    stations = _parse_meteofrance_stations_text(
        _read_text_request(request, timeout=timeout)
    )
    _METEOFRANCE_STATIONS_CACHE["value"] = list(stations)
    _METEOFRANCE_STATIONS_CACHE["expires_at"] = now + datetime.timedelta(
        seconds=METEOFRANCE_STATIONS_CACHE_SECONDS
    )
    _METEOFRANCE_STATIONS_CACHE["credential"] = credential
    return stations


def nearest_meteofrance_stations(
    latitude,
    longitude,
    limit=12,
    max_distance_km=150,
    timeout=20,
):
    """Return nearest Météo-France DPObs stations around a site."""
    candidates = []
    for station in load_meteofrance_stations(timeout=timeout):
        distance_km = _haversine_km(
            latitude,
            longitude,
            station["latitude"],
            station["longitude"],
        )
        if distance_km <= max_distance_km:
            candidates.append((distance_km, station))
    candidates.sort(key=lambda item: item[0])
    return candidates[:limit]


def fetch_metar_observation(station_id, timeout=8):
    query = urlencode(
        {
            "ids": station_id,
            "format": "json",
            "hours": 3,
        }
    )
    observations = _read_json_url(f"{METAR_DATA_URL}?{query}", timeout=timeout)
    if not observations:
        return None
    return observations[0]


def fetch_metar_observations(station_ids, timeout=8):
    station_ids = [station_id for station_id in station_ids if station_id]
    if not station_ids:
        return {}
    query = urlencode(
        {
            "ids": ",".join(station_ids),
            "format": "json",
            "hours": 3,
        }
    )
    observations = _read_json_url(f"{METAR_DATA_URL}?{query}", timeout=timeout)
    if not observations:
        return {}
    return {observation.get("icaoId"): observation for observation in observations}


def fetch_metar_pressure_for_station(station, timeout=8):
    """Return recent METAR pressure for one station option."""
    station_id = station["station_id"]
    observation = fetch_metar_observation(station_id, timeout=timeout)
    if observation is None:
        return None
    pressure_hpa = observation.get("altim")
    if pressure_hpa is None:
        return None
    return {
        "station_id": station_id,
        "station_name": observation.get("name") or station.get("station_name") or station_id,
        "distance_km": station["distance_km"],
        "pressure_hpa": float(pressure_hpa),
        "temperature_c": observation.get("temp"),
        "humidity_percent": _observation_humidity_percent(observation),
        "report_time": observation.get("reportTime"),
    }


def metar_pressures_for_stations(stations, timeout=8):
    observations = fetch_metar_observations(
        [station["station_id"] for station in stations],
        timeout=timeout,
    )
    results = {}
    for station in stations:
        observation = observations.get(station["station_id"])
        if observation is None:
            continue
        pressure_hpa = observation.get("altim")
        if pressure_hpa is None:
            continue
        results[station["station_id"]] = {
            "source": "METAR",
            "station_id": station["station_id"],
            "station_name": observation.get("name") or station.get("station_name") or station["station_id"],
            "distance_km": station["distance_km"],
            "pressure_hpa": float(pressure_hpa),
            "temperature_c": observation.get("temp"),
            "humidity_percent": _observation_humidity_percent(observation),
            "report_time": observation.get("reportTime"),
        }
    return results


def _parse_iso_datetime(value):
    if not value:
        return datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _is_recent_observation(report_time, now_utc=None, max_age_hours=MAX_WEATHER_OBSERVATION_AGE_HOURS):
    observation_time = _parse_iso_datetime(report_time)
    if observation_time == datetime.datetime.min.replace(tzinfo=datetime.timezone.utc):
        return False
    now_utc = now_utc or datetime.datetime.now(datetime.timezone.utc)
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=datetime.timezone.utc)
    else:
        now_utc = now_utc.astimezone(datetime.timezone.utc)
    age = now_utc - observation_time.astimezone(datetime.timezone.utc)
    return datetime.timedelta() <= age <= datetime.timedelta(hours=max_age_hours)


def _normalize_pressure_hpa(value):
    if value in (None, ""):
        return None
    pressure = float(value)
    if pressure > 2000:
        pressure /= 100.0
    return pressure


def _normalize_temperature_c(value):
    if value in (None, ""):
        return None
    temperature = float(value)
    if temperature > 150:
        temperature -= 273.15
    return temperature


def _normalize_humidity_percent(value):
    if value in (None, ""):
        return None
    humidity = float(value)
    if 0 <= humidity <= 1:
        humidity *= 100.0
    return max(0.0, min(100.0, humidity))


def _observation_humidity_percent(observation):
    for key in ("relh", "rh", "humidity", "humidite", "u"):
        if observation.get(key) not in (None, ""):
            return _normalize_humidity_percent(observation[key])
    return None


def _extract_observation_rows(payload):
    if payload is None:
        return []
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("data", "features", "observations", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                if key == "features":
                    return [
                        feature.get("properties", feature)
                        for feature in value
                        if isinstance(feature, dict)
                    ]
                return value
        return [payload]
    return []


def _row_time_value(row):
    for key in ("validity_time", "date", "datetime", "reference_time", "time"):
        value = row.get(key)
        if value:
            return value
    return ""


def _exchange_meteofrance_application_id(application_id, timeout=12):
    """Return an OAuth access token for legacy Météo-France Application IDs."""
    credential = str(application_id or "").strip()
    if not credential:
        return ""
    now = datetime.datetime.now(datetime.timezone.utc)
    cached_value = _METEOFRANCE_ACCESS_TOKEN.get("value")
    expires_at = _METEOFRANCE_ACCESS_TOKEN.get("expires_at")
    if cached_value and expires_at and now < expires_at:
        return cached_value
    body = urlencode({"grant_type": "client_credentials"}).encode("ascii")
    request = Request(
        METEOFRANCE_TOKEN_URL,
        data=body,
        headers={
            "Authorization": f"Basic {credential}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": WEATHER_USER_AGENT,
        },
        method="POST",
    )
    payload = _read_json_request(request, timeout=timeout)
    token = (payload or {}).get("access_token", "")
    if token:
        expires_in = int((payload or {}).get("expires_in", 3600))
        _METEOFRANCE_ACCESS_TOKEN["value"] = token
        _METEOFRANCE_ACCESS_TOKEN["expires_at"] = now + datetime.timedelta(
            seconds=max(60, expires_in - 60)
        )
    return token


def _get_meteofrance_api_key(api_key=None):
    return str(api_key or load_meteofrance_application_id() or "").strip()


def _meteofrance_authorization_headers(api_key=None):
    credential = _get_meteofrance_api_key(api_key=api_key)
    if not credential:
        return None
    return {
        "apikey": credential,
        "accept": "application/json",
        "User-Agent": WEATHER_USER_AGENT,
    }


def test_meteofrance_api_key(timeout=12, api_key=None):
    """Return available Météo-France capabilities for the configured API key."""
    headers = _meteofrance_authorization_headers(api_key=api_key)
    if not headers:
        return {
            "observations_available": False,
            "climatology_available": False,
            "station_count": 0,
            "observation_error": "No API key is configured.",
            "climatology_error": "",
        }

    result = {
        "observations_available": False,
        "climatology_available": False,
        "station_count": 0,
        "observation_error": "",
        "climatology_error": "",
    }

    try:
        stations = load_meteofrance_stations(timeout=timeout, application_id=api_key)
    except (HTTPError, JSONDecodeError, OSError, TimeoutError, ValueError) as exc:
        result["observation_error"] = str(exc)
    else:
        result["observations_available"] = bool(stations)
        result["station_count"] = len(stations)

    if result["observations_available"]:
        return result

    query = urlencode({"id-departement": "75"})
    request = Request(
        f"{METEOFRANCE_DPCLIM_STATIONS_URL}?{query}",
        headers=headers,
    )
    try:
        stations = _read_json_request(request, timeout=timeout)
    except (HTTPError, JSONDecodeError, OSError, TimeoutError, ValueError) as exc:
        result["climatology_error"] = str(exc)
    else:
        if isinstance(stations, list):
            result["climatology_available"] = True
            result["station_count"] = len(stations)
        else:
            result["climatology_error"] = "Unexpected DPClim station list response."
    return result


def _meteofrance_observation_cache_key(station_id, api_key=None):
    credential = _get_meteofrance_api_key(api_key=api_key)
    return credential, str(station_id)


def _meteofrance_cached_observation(station_id, api_key=None, now=None):
    cache_key = _meteofrance_observation_cache_key(station_id, api_key=api_key)
    cache_entry = _METEOFRANCE_OBSERVATION_CACHE.get(cache_key)
    if _cache_is_valid(cache_entry, now=now):
        return cache_entry.get("value")
    _METEOFRANCE_OBSERVATION_CACHE.pop(cache_key, None)
    return None


def _cache_meteofrance_observation(station_id, value, api_key=None, now=None):
    now = now or _utc_now()
    cache_key = _meteofrance_observation_cache_key(station_id, api_key=api_key)
    _METEOFRANCE_OBSERVATION_CACHE[cache_key] = {
        "value": value,
        "expires_at": now + datetime.timedelta(
            seconds=METEOFRANCE_OBSERVATION_CACHE_SECONDS
        ),
    }


def _format_meteofrance_station_result(station, observation):
    if observation is None:
        return None
    return {
        "source": "METEOFRANCE",
        "station_id": station["station_id"],
        "station_name": station.get("station_name") or station["station_id"],
        "distance_km": station["distance_km"],
        "pressure_hpa": observation["pressure_hpa"],
        "temperature_c": observation.get("temperature_c"),
        "humidity_percent": observation.get("humidity_percent"),
        "report_time": observation.get("report_time"),
    }


def fetch_meteofrance_pressure_for_station(station, timeout=12, application_id=None):
    """Return recent Météo-France DPObs pressure for one station option."""
    now = _utc_now()
    cached = _meteofrance_cached_observation(
        station["station_id"],
        api_key=application_id,
        now=now,
    )
    if cached is not None:
        return _format_meteofrance_station_result(station, cached)
    headers = _meteofrance_authorization_headers(api_key=application_id)
    if not headers:
        return None
    query = urlencode(
        {
            "id_station": station["station_id"],
            "format": "json",
        }
    )
    request = Request(
        f"{METEOFRANCE_DPOBS_API_URL}?{query}",
        headers=headers,
    )
    payload = _read_json_request(request, timeout=timeout)
    latest = None
    latest_time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    for row in _extract_observation_rows(payload):
        if not isinstance(row, dict):
            continue
        pressure = _normalize_pressure_hpa(row.get("pmer") or row.get("pres"))
        if pressure is None:
            continue
        row_time_text = _row_time_value(row)
        row_time = _parse_iso_datetime(row_time_text)
        if row_time >= latest_time:
            latest = row
            latest_time = row_time
    if latest is None:
        _cache_meteofrance_observation(
            station["station_id"],
            None,
            api_key=application_id,
            now=now,
        )
        return None
    pressure_hpa = _normalize_pressure_hpa(latest.get("pmer") or latest.get("pres"))
    temperature_c = _normalize_temperature_c(latest.get("t"))
    humidity_percent = _observation_humidity_percent(latest)
    observation = {
        "pressure_hpa": pressure_hpa,
        "temperature_c": temperature_c,
        "humidity_percent": humidity_percent,
        "report_time": _row_time_value(latest),
    }
    _cache_meteofrance_observation(
        station["station_id"],
        observation,
        api_key=application_id,
        now=now,
    )
    return _format_meteofrance_station_result(station, observation)


def fetch_synop_pressure_for_station(station, timeout=60, year=None):
    """Return recent Météo-France SYNOP sea-level pressure for one station option."""
    year = year or datetime.datetime.now(datetime.timezone.utc).year
    url = SYNOP_YEAR_URL_TEMPLATE.format(year=year)
    text = _read_text_url(url, timeout=timeout)
    return _synop_pressure_for_station_from_text(station, text)


def _synop_pressure_for_station_from_text(station, text):
    latest = None
    latest_time = datetime.datetime.min.replace(tzinfo=datetime.timezone.utc)
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        if row.get("geo_id_wmo") != station["station_id"]:
            continue
        if not row.get("pmer"):
            continue
        validity_time = _parse_iso_datetime(row.get("validity_time"))
        if validity_time >= latest_time:
            latest = row
            latest_time = validity_time
    if latest is None:
        return None
    pressure_hpa = float(latest["pmer"]) / 100.0
    temperature_c = None
    if latest.get("t"):
        temperature_c = float(latest["t"]) - 273.15
    return {
        "source": "SYNOP",
        "station_id": station["station_id"],
        "station_name": station.get("station_name") or latest.get("name") or station["station_id"],
        "distance_km": station["distance_km"],
        "pressure_hpa": pressure_hpa,
        "temperature_c": temperature_c,
        "humidity_percent": _observation_humidity_percent(latest),
        "report_time": latest.get("validity_time"),
    }


def synop_pressures_for_stations(stations, timeout=60, year=None):
    """Return recent SYNOP pressures for several station options with one CSV download."""
    year = year or datetime.datetime.now(datetime.timezone.utc).year
    url = SYNOP_YEAR_URL_TEMPLATE.format(year=year)
    text = _read_text_url(url, timeout=timeout)
    station_lookup = {station["station_id"]: station for station in stations}
    latest_rows = {}
    latest_times = {}
    for row in csv.DictReader(io.StringIO(text), delimiter=";"):
        station_id = row.get("geo_id_wmo")
        if station_id not in station_lookup or not row.get("pmer"):
            continue
        validity_time = _parse_iso_datetime(row.get("validity_time"))
        if validity_time >= latest_times.get(
            station_id,
            datetime.datetime.min.replace(tzinfo=datetime.timezone.utc),
        ):
            latest_rows[station_id] = row
            latest_times[station_id] = validity_time

    results = {}
    for station_id, row in latest_rows.items():
        station = station_lookup[station_id]
        pressure_hpa = float(row["pmer"]) / 100.0
        temperature_c = None
        if row.get("t"):
            temperature_c = float(row["t"]) - 273.15
        results[station_id] = {
            "source": "SYNOP",
            "station_id": station_id,
            "station_name": station.get("station_name") or row.get("name") or station_id,
            "distance_km": station["distance_km"],
            "pressure_hpa": pressure_hpa,
            "temperature_c": temperature_c,
            "humidity_percent": _observation_humidity_percent(row),
            "report_time": row.get("validity_time"),
        }
    return results


def fetch_pressure_for_station(station):
    if station.get("source") == "METEOFRANCE":
        return fetch_meteofrance_pressure_for_station(station)
    if station.get("source") == "SYNOP":
        return fetch_synop_pressure_for_station(station)
    return fetch_metar_pressure_for_station(station)


def nearest_metar_pressure_station_options(
    latitude,
    longitude,
    limit=3,
    max_distance_km=150,
    scan_limit=10,
    now_utc=None,
):
    """Return nearest METAR stations that currently expose a QNH/altimeter value."""
    stations_with_pressure = []
    for distance_km, station in nearest_metar_stations(
        latitude,
        longitude,
        limit=scan_limit,
        max_distance_km=max_distance_km,
    ):
        station_option = {
            "source": "METAR",
            "station_id": station["icaoId"],
            "station_name": station.get("site") or station["icaoId"],
            "distance_km": distance_km,
            "latitude": station["lat"],
            "longitude": station["lon"],
            "elevation_m": station.get("elev"),
        }
        try:
            pressure = fetch_metar_pressure_for_station(station_option)
        except (HTTPError, JSONDecodeError, OSError, TimeoutError):
            continue
        if pressure is None:
            continue
        if not _is_recent_observation(pressure.get("report_time"), now_utc=now_utc):
            continue
        stations_with_pressure.append({**station_option, **pressure})
        if len(stations_with_pressure) >= limit:
            break
    return stations_with_pressure


def nearest_pressure_station_options(
    latitude,
    longitude,
    limit=3,
    max_distance_km=150,
    scan_limit=20,
    now_utc=None,
):
    """Return nearest weather stations that currently expose recent pressure."""
    stations_with_pressure = []
    meteofrance_scan_limit = min(
        max(scan_limit, limit),
        METEOFRANCE_MAX_OBSERVATION_LOOKUPS_PER_SEARCH,
    )
    metar_candidates = nearest_metar_stations(
        latitude,
        longitude,
        limit=scan_limit,
        max_distance_km=max_distance_km,
    )
    metar_options = [
        {
            "source": "METAR",
            "station_id": station["icaoId"],
            "station_name": station.get("site") or station["icaoId"],
            "distance_km": distance_km,
            "latitude": station["lat"],
            "longitude": station["lon"],
            "elevation_m": station.get("elev"),
        }
        for distance_km, station in metar_candidates
    ]
    try:
        metar_pressures = metar_pressures_for_stations(metar_options)
    except (HTTPError, JSONDecodeError, OSError, TimeoutError):
        metar_pressures = {}
    for station_option in metar_options:
        pressure = metar_pressures.get(station_option["station_id"])
        if pressure is not None and _is_recent_observation(
            pressure.get("report_time"),
            now_utc=now_utc,
        ):
            stations_with_pressure.append({**station_option, **pressure})

    try:
        meteofrance_candidates = nearest_meteofrance_stations(
            latitude,
            longitude,
            limit=meteofrance_scan_limit,
            max_distance_km=max_distance_km,
        )
    except (HTTPError, JSONDecodeError, OSError, TimeoutError, ValueError):
        meteofrance_candidates = []

    for distance_km, station in meteofrance_candidates[:meteofrance_scan_limit]:
        stations_with_pressure.sort(key=lambda item: item["distance_km"])
        if len(stations_with_pressure) >= limit and distance_km > stations_with_pressure[
            limit - 1
        ]["distance_km"]:
            # Subsequent candidates are farther away: they cannot enter the
            # globally nearest `limit` stations, whatever their observation.
            break
        station_option = {**station, "distance_km": distance_km}
        try:
            pressure = fetch_meteofrance_pressure_for_station(station_option)
        except (HTTPError, JSONDecodeError, OSError, TimeoutError, ValueError):
            continue
        if pressure is not None and _is_recent_observation(
            pressure.get("report_time"),
            now_utc=now_utc,
        ):
            stations_with_pressure.append({**station_option, **pressure})

    stations_with_pressure.sort(key=lambda item: item["distance_km"])
    return stations_with_pressure[:limit]


def fetch_nearest_metar_pressure(latitude, longitude, max_distance_km=150):
    """Return the nearest recent METAR pressure observation around a site.

    The returned pressure is the METAR altimeter/QNH value in hPa, i.e. a
    sea-level pressure suitable for the refraction settings' sea-level pressure
    field.
    """
    for distance_km, station in nearest_metar_stations(
        latitude,
        longitude,
        max_distance_km=max_distance_km,
    ):
        try:
            result = fetch_metar_pressure_for_station(
                {
                    "station_id": station["icaoId"],
                    "station_name": station.get("site") or station["icaoId"],
                    "distance_km": distance_km,
                }
            )
        except (HTTPError, JSONDecodeError, OSError, TimeoutError):
            continue
        if result is None:
            continue
        return result
    return None
