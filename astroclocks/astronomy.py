import datetime
import json
import unicodedata
from urllib.parse import urlencode
from urllib.request import urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import zeep
from astropy import units as u
from astropy.coordinates import AltAz, EarthLocation, FK5, SkyCoord, TETE, get_body, get_sun
from astropy.coordinates import solar_system_ephemeris
from astropy.time import Time

from astroclocks.utils import separate_dms_coordinates


def _format_timezone_offset(offset):
    if offset is None:
        return "UTC"
    total_minutes = int(offset.total_seconds() // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours = total_minutes // 60
    minutes = total_minutes % 60
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def resolve_timezone(timezone_name=None):
    timezone_name = str(timezone_name or "").strip()
    if not timezone_name:
        return None

    upper_name = timezone_name.upper()
    if upper_name in {"UTC", "GMT", "Z"}:
        return datetime.timezone.utc

    for prefix in ("UTC", "GMT"):
        if upper_name.startswith(prefix) and len(timezone_name) > len(prefix):
            offset_text = timezone_name[len(prefix) :].strip()
            if offset_text[0] not in "+-":
                break
            sign = 1 if offset_text[0] == "+" else -1
            offset_body = offset_text[1:]
            if ":" in offset_body:
                hour_text, minute_text = offset_body.split(":", 1)
            else:
                hour_text = offset_body[:2]
                minute_text = offset_body[2:] or "0"
            try:
                hours = int(hour_text)
                minutes = int(minute_text)
            except ValueError as exc:
                raise ValueError(f"Invalid time zone: {timezone_name}") from exc
            if hours > 23 or minutes > 59:
                raise ValueError(f"Invalid time zone: {timezone_name}")
            return datetime.timezone(sign * datetime.timedelta(hours=hours, minutes=minutes))

    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise ValueError(f"Invalid time zone: {timezone_name}") from exc


def _manual_timezone_offset(utc_now, tzinfo, daylight_saving_enabled):
    local_now = utc_now.astimezone(tzinfo)
    offset = local_now.utcoffset() or datetime.timedelta()
    dst = local_now.dst() or datetime.timedelta()
    offset -= dst
    if daylight_saving_enabled:
        offset += datetime.timedelta(hours=1)
    return offset


def format_timezone_label(timezone_name=None, daylight_saving_enabled=False, now_utc=None):
    utc_now = _coerce_utc_datetime(now_utc)
    tzinfo = resolve_timezone(timezone_name)
    timezone_name = str(timezone_name or "").strip()
    if timezone_name:
        offset = _manual_timezone_offset(utc_now, tzinfo, daylight_saving_enabled)
        offset_label = _format_timezone_offset(offset)
        return f"{offset_label} ({timezone_name})"
    local_now = utc_now.astimezone()
    offset = local_now.utcoffset()
    return _format_timezone_offset(offset)


def convert_j2000_to_now(coords):
    """Convert J2000 coordinates to the current FK5 equinox."""
    date_time = Time(Time(datetime.datetime.utcnow(), scale="utc").jd, format="jd", scale="utc")
    j2000_coords = [coords, coords.replace(":", " ")]
    fk5 = FK5(equinox=date_time)
    jnow = SkyCoord(j2000_coords, frame=None, unit=(u.hourangle, u.deg)).transform_to(fk5)
    return jnow[0].to_string("hmsdms")


def convert_star_catalog_j2000_to_jnow(stars):
    """Convert an FK5 J2000 star catalog to the current FK5 equinox."""
    if not stars:
        return []

    date_time = Time(Time(datetime.datetime.utcnow(), scale="utc").jd, format="jd", scale="utc")
    fk5_j2000 = FK5(equinox=Time("J2000"))
    fk5_now = FK5(equinox=date_time)
    catalog = SkyCoord(
        ra=[star[1] for star in stars] * u.hourangle,
        dec=[star[2] for star in stars] * u.deg,
        frame=fk5_j2000,
    ).transform_to(fk5_now)

    return [
        (star[0], catalog[index].ra.hour, catalog[index].dec.deg, star[3])
        for index, star in enumerate(stars)
    ]


def j2000_to_jnow_coordinates(ra_hours, dec_degrees, now_utc=None):
    """Convert FK5 J2000/ICRS-like coordinates to the current FK5 equinox."""
    current_equinox = Time(_coerce_utc_datetime(now_utc), scale="utc")
    j2000 = SkyCoord(
        ra=float(ra_hours) * u.hourangle,
        dec=float(dec_degrees) * u.deg,
        frame=FK5(equinox=Time("J2000")),
    )
    jnow = j2000.transform_to(FK5(equinox=current_equinox))
    return jnow.ra.hour, jnow.dec.deg


def jnow_to_j2000_coordinates(ra_hours, dec_degrees, now_utc=None):
    """Convert current FK5 equinox coordinates to FK5 J2000 input coordinates."""
    current_equinox = Time(_coerce_utc_datetime(now_utc), scale="utc")
    jnow = SkyCoord(
        ra=float(ra_hours) * u.hourangle,
        dec=float(dec_degrees) * u.deg,
        frame=FK5(equinox=current_equinox),
    )
    j2000 = jnow.transform_to(FK5(equinox=Time("J2000")))
    return j2000.ra.hour, j2000.dec.deg


def get_planet_coord(object_type, planet_name):
    """Retrieve apparent coordinates of date from IMCCE Miriade."""
    wsdl_url = "https://ssp.imcce.fr/webservices/miriade/miriade.php?wsdl"
    client = zeep.Client(wsdl=wsdl_url)

    header = {
        "clientID": {
            "from": "YourName",
            "hostip": "",
            "lang": "en",
        }
    }

    input_params = {
        "name": f"{object_type}:{planet_name}",
        "nbd": 1,
        "epoch": "now",
        "mime": "json",
        "observer": "005",
        "tcoor": 1,
        "teph": 2,
        "rplane": 1,
    }

    result = client.service.ephemcc(input_params, _soapheaders=header)
    if result.flag != 1:
        raise RuntimeError("An error occurred while retrieving the ephemerides.")

    data = json.loads(result.result)
    ra = data["data"][0]["RA"]
    dec = data["data"][0]["DEC"]
    return ra, dec


def normalize_miriade_object_name(object_name):
    """Normalize common French/English Solar System names for IMCCE Miriade."""
    normalized = unicodedata.normalize("NFKD", str(object_name).strip())
    ascii_name = "".join(char for char in normalized if not unicodedata.combining(char))
    compact = ascii_name.casefold()
    aliases = {
        "soleil": "Sun",
        "sun": "Sun",
        "mercure": "Mercury",
        "mercury": "Mercury",
        "venus": "Venus",
        "terre": "Earth",
        "earth": "Earth",
        "lune": "Moon",
        "moon": "Moon",
        "mars": "Mars",
        "jupiter": "Jupiter",
        "saturne": "Saturn",
        "saturn": "Saturn",
        "uranus": "Uranus",
        "neptune": "Neptune",
        "pluton": "Pluto",
        "pluto": "Pluto",
    }
    return aliases.get(compact, str(object_name).strip())


def normalize_sesame_object_name(object_name):
    """Normalize object names before asking CDS Sesame."""
    normalized = unicodedata.normalize("NFKD", str(object_name).strip())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def resolve_solar_system_coordinates(selected_type, object_name):
    prefix_mapping = {
        "Asteroid": "a",
        "Comet": "c",
        "Dwarf Planet": "dp",
        "Planet": "p",
        "Natural Satellite": "s",
    }

    object_name = normalize_miriade_object_name(object_name)
    coordinates = get_planet_coord(prefix_mapping[selected_type], object_name)
    alpha_hh, alpha_mm, alpha_ss = coordinates[0][1:].split(":")
    delta_dd, delta_mm, delta_ss = coordinates[1].split(":")
    local_solar_names = {
        "Sun",
        "Moon",
        "Mercury",
        "Venus",
        "Mars",
        "Jupiter",
        "Saturn",
        "Uranus",
        "Neptune",
    }

    return {
        "message": (
            "Apparent JNow coordinates from IMCCE:\n"
            f"Alpha JNow : {coordinates[0]}\n"
            f"Delta JNow : {coordinates[1]}"
        ),
        "source": "imcce",
        "display_name": object_name,
        "solar_system_name": object_name if object_name in local_solar_names else None,
        "source_ra": coordinates[0],
        "source_dec": coordinates[1],
        "alpha_hh": int(alpha_hh),
        "alpha_mm": int(alpha_mm),
        "alpha_ss": str(round(float(alpha_ss))).zfill(2),
        "delta_dd": int(delta_dd),
        "delta_mm": int(delta_mm),
        "delta_ss": str(round(float(delta_ss))).zfill(2),
    }


def resolve_local_solar_system_coordinates(object_name, now_utc=None, latitude=None, longitude=None):
    """Resolve major Solar System objects with Astropy's built-in ephemerides."""
    label = normalize_miriade_object_name(object_name)
    body_names = {
        "Sun": "sun",
        "Moon": "moon",
        "Mercury": "mercury",
        "Venus": "venus",
        "Mars": "mars",
        "Jupiter": "jupiter",
        "Saturn": "saturn",
        "Uranus": "uranus",
        "Neptune": "neptune",
    }
    body_name = body_names.get(label)
    if body_name is None:
        return None

    observation_time = Time(_coerce_utc_datetime(now_utc), scale="utc")
    location = None
    if latitude is not None and longitude is not None:
        location = EarthLocation.from_geodetic(
            lon=float(longitude) * u.deg,
            lat=float(latitude) * u.deg,
        )
    apparent_frame = TETE(obstime=observation_time, location=location)
    with solar_system_ephemeris.set("builtin"):
        coordinates = get_sun(observation_time) if body_name == "sun" else get_body(
            body_name,
            observation_time,
            location,
        )
        apparent = coordinates.transform_to(apparent_frame)

    ra_text = str(apparent.ra.to_string(unit=u.hour, sep=":", precision=2, pad=True))
    dec_text = str(apparent.dec.to_string(unit=u.deg, sep=":", precision=1, alwayssign=True, pad=True))
    total_ra_seconds = int(round(apparent.ra.hour * 3600)) % (24 * 3600)
    alpha_hh = total_ra_seconds // 3600
    alpha_mm = (total_ra_seconds % 3600) // 60
    alpha_ss = total_ra_seconds % 60
    total_dec_seconds = int(round(abs(apparent.dec.deg) * 3600))
    delta_dd = total_dec_seconds // 3600
    delta_mm = (total_dec_seconds % 3600) // 60
    delta_ss = total_dec_seconds % 60
    if apparent.dec.deg < 0:
        delta_dd = "-0" if delta_dd == 0 else -delta_dd

    return {
        "message": (
            "Apparent JNow coordinates from local ephemerides:\n"
            f"Alpha JNow : {ra_text}\n"
            f"Delta JNow : {dec_text}"
        ),
        "source": "local_solar",
        "display_name": label,
        "solar_system_name": label,
        "source_ra": ra_text,
        "source_dec": dec_text,
        "alpha_hh": alpha_hh,
        "alpha_mm": alpha_mm,
        "alpha_ss": f"{alpha_ss:02d}",
        "delta_dd": delta_dd,
        "delta_mm": delta_mm,
        "delta_ss": f"{delta_ss:02d}",
    }


def resolve_deep_sky_coordinates(object_name):
    coordinates = SkyCoord.from_name(normalize_sesame_object_name(object_name))
    j2000 = coordinates.to_string("hmsdms")
    alpha2000, delta2000 = j2000.split(" ")

    alpha_digits = "".join(char for char in alpha2000 if char == "." or char.isdigit())
    delta_dd, delta_mm, delta_ss = separate_dms_coordinates(delta2000)
    alpha_value = alpha_digits[0:9]

    return {
        "message": (
            "ICRS Coordinates from Sesame :\n"
            f"RA (Alpha) : {alpha2000}\n"
            f"Dec (Delta) : {delta2000}"
        ),
        "source": "sesame",
        "source_ra": alpha2000,
        "source_dec": delta2000,
        "alpha_hh": alpha_value[0:2],
        "alpha_mm": alpha_value[2:4],
        "alpha_ss": str(round(float(alpha_value[4:9]))).zfill(2),
        "delta_dd": delta_dd,
        "delta_mm": delta_mm,
        "delta_ss": str(round(float(delta_ss))).zfill(2),
    }


def jnow_to_icrs_degrees(alpha_hh, alpha_mm, alpha_ss, delta_dd, delta_mm, delta_ss):
    ra_hours = float(alpha_hh) + (float(alpha_mm) / 60) + (float(alpha_ss) / 3600)
    dec_sign = -1 if str(delta_dd).strip().startswith("-") else 1
    dec_degrees = dec_sign * (
        abs(float(delta_dd)) + (float(delta_mm) / 60) + (float(delta_ss) / 3600)
    )

    current_equinox = Time(datetime.datetime.utcnow(), scale="utc")
    jnow_center = SkyCoord(
        ra=ra_hours * u.hourangle,
        dec=dec_degrees * u.deg,
        frame=FK5(equinox=current_equinox),
    )
    center = jnow_center.transform_to("icrs")
    return center.ra.deg, center.dec.deg


def compute_solar_system_positions(latitude, longitude, now_utc=None):
    """Return apparent local Alt/Az and true-equator/equinox coordinates."""
    utc_now = _coerce_utc_datetime(now_utc)
    observation_time = Time(utc_now, scale="utc")
    location = EarthLocation.from_geodetic(
        lon=float(longitude) * u.deg,
        lat=float(latitude) * u.deg,
    )
    altaz_frame = AltAz(obstime=observation_time, location=location)
    apparent_frame = TETE(obstime=observation_time, location=location)

    bodies = (
        ("Sun", "sun"),
        ("Moon", "moon"),
        ("Mercury", "mercury"),
        ("Venus", "venus"),
        ("Mars", "mars"),
        ("Jupiter", "jupiter"),
        ("Saturn", "saturn"),
        ("Uranus", "uranus"),
        ("Neptune", "neptune"),
    )
    positions = []
    with solar_system_ephemeris.set("builtin"):
        for label, body_name in bodies:
            coordinates = get_sun(observation_time) if body_name == "sun" else get_body(
                body_name,
                observation_time,
                location,
            )
            altaz = coordinates.transform_to(altaz_frame)
            apparent = coordinates.transform_to(apparent_frame)
            positions.append(
                {
                    "name": label,
                    "ra_hours": apparent.ra.hour,
                    "declination": apparent.dec.deg,
                    "altitude": altaz.alt.deg,
                    "azimuth": altaz.az.deg,
                }
            )

    return positions


def compute_solar_system_body_positions(body_label, latitude, longitude, utc_datetimes):
    """Return apparent local Alt/Az and true-equator/equinox coordinates for one body."""
    body_names = {
        "Sun": "sun",
        "Moon": "moon",
        "Mercury": "mercury",
        "Venus": "venus",
        "Mars": "mars",
        "Jupiter": "jupiter",
        "Saturn": "saturn",
        "Uranus": "uranus",
        "Neptune": "neptune",
    }
    body_name = body_names.get(body_label)
    if body_name is None:
        return []

    utc_times = [_coerce_utc_datetime(utc_datetime) for utc_datetime in utc_datetimes]
    observation_times = Time(utc_times, scale="utc")
    location = EarthLocation.from_geodetic(
        lon=float(longitude) * u.deg,
        lat=float(latitude) * u.deg,
    )
    altaz_frame = AltAz(obstime=observation_times, location=location)
    apparent_frame = TETE(obstime=observation_times, location=location)

    with solar_system_ephemeris.set("builtin"):
        coordinates = (
            get_sun(observation_times)
            if body_name == "sun"
            else get_body(body_name, observation_times, location)
        )
        altaz = coordinates.transform_to(altaz_frame)
        apparent = coordinates.transform_to(apparent_frame)

    return [
        {
            "name": body_label,
            "ra_hours": apparent[index].ra.hour,
            "declination": apparent[index].dec.deg,
            "altitude": altaz[index].alt.deg,
            "azimuth": altaz[index].az.deg,
        }
        for index in range(len(utc_times))
    ]


def compute_sun_altitudes(latitude, longitude, utc_datetimes):
    """Return apparent solar altitude in degrees for one or more UTC datetimes."""
    utc_times = [_coerce_utc_datetime(utc_datetime) for utc_datetime in utc_datetimes]
    observation_times = Time(utc_times, scale="utc")
    location = EarthLocation.from_geodetic(
        lon=float(longitude) * u.deg,
        lat=float(latitude) * u.deg,
    )
    altaz_frame = AltAz(obstime=observation_times, location=location)
    altaz = get_sun(observation_times).transform_to(altaz_frame)
    return [float(altitude) for altitude in altaz.alt.deg]


def fetch_sky_area_png(
    alpha_hh,
    alpha_mm,
    alpha_ss,
    delta_dd,
    delta_mm,
    delta_ss,
    field_of_view_deg=0.5,
    image_pixels=720,
):
    ra_deg, dec_deg = jnow_to_icrs_degrees(
        alpha_hh,
        alpha_mm,
        alpha_ss,
        delta_dd,
        delta_mm,
        delta_ss,
    )
    query = urlencode(
        {
            "hips": "CDS/P/DSS2/color",
            "ra": f"{ra_deg:.8f}",
            "dec": f"{dec_deg:.8f}",
            "fov": f"{field_of_view_deg:.6f}",
            "width": str(image_pixels),
            "height": str(image_pixels),
            "projection": "TAN",
            "coordsys": "icrs",
            "format": "png",
        }
    )
    url = f"https://alasky.cds.unistra.fr/hips-image-services/hips2fits?{query}"

    with urlopen(url, timeout=20) as response:
        return response.read()


def _format_hms_from_hours(hours):
    total_seconds = int(hours * 3600) % 86400
    hour = total_seconds // 3600
    minute = (total_seconds % 3600) // 60
    second = total_seconds % 60
    return f"{hour:02d}:{minute:02d}:{second:02d}"


def _coerce_utc_datetime(now_utc):
    if now_utc is None:
        return datetime.datetime.now(datetime.timezone.utc)
    if now_utc.tzinfo is None:
        return now_utc.replace(tzinfo=datetime.timezone.utc)
    return now_utc.astimezone(datetime.timezone.utc)


def compute_clock_state(
    longitude,
    alpha_hh,
    alpha_mm,
    alpha_ss,
    hour_angle_offset_hours=6,
    timezone_name=None,
    daylight_saving_enabled=False,
    now_utc=None,
):
    utc_now = _coerce_utc_datetime(now_utc)
    tzinfo = resolve_timezone(timezone_name)
    if tzinfo is not None:
        offset = _manual_timezone_offset(utc_now, tzinfo, daylight_saving_enabled)
        local_now = (utc_now + offset).replace(tzinfo=datetime.timezone(offset))
    else:
        local_now = utc_now.astimezone()

    local_string = local_now.strftime("%H:%M:%S")
    utc_string = utc_now.strftime("%H:%M:%S")

    month_utc = utc_now.month
    day_utc = utc_now.day
    year_utc = utc_now.year
    second_utc = utc_now.second + (utc_now.microsecond / 1_000_000)
    ut = utc_now.hour + (utc_now.minute / 60) + (second_utc / 3600)
    julian_date = (
        (367 * year_utc)
        - int((7 * (year_utc + int((month_utc + 9) / 12))) / 4)
        + int((275 * month_utc) / 9)
        + day_utc
        + 1721013.5
        + (ut / 24)
    )

    gmst = 18.697374558 + 24.06570982441908 * (julian_date - 2451545)
    gmst = gmst % 24
    gmst_string = _format_hms_from_hours(gmst)

    longitude_hours = longitude / 15
    lst = (gmst + longitude_hours) % 24
    lst_string = _format_hms_from_hours(lst)

    alpha_seconds = float(alpha_hh) * 3600 + float(alpha_mm) * 60 + float(alpha_ss)
    hour_angle = (3600 * (lst + hour_angle_offset_hours) - alpha_seconds) % 86400
    ha_hh = int(hour_angle // 3600)
    ha_mm = int((hour_angle % 3600) // 60)
    ha_ss = int(hour_angle % 60)
    ha_string = f"{ha_hh:02d}h {ha_mm:02d}m {ha_ss:02d}s"

    return {
        "local": local_string,
        "utc": utc_string,
        "gmst": gmst_string,
        "lst": lst_string,
        "hour_angle": ha_string,
    }


def compute_declination_display(delta_dd, delta_mm, delta_ss, apply_offset=True):
    dec_sign = -1 if str(delta_dd).strip().startswith("-") else 1
    dec_degrees = dec_sign * (
        abs(float(delta_dd)) + (float(delta_mm) / 60) + (float(delta_ss) / 3600)
    )
    display_degrees = dec_degrees + 90 if apply_offset else dec_degrees
    lower_bound = 0 if apply_offset else -90
    upper_bound = 180 if apply_offset else 90
    total_seconds = int(round(display_degrees * 3600))
    total_seconds = max(lower_bound * 3600, min(upper_bound * 3600, total_seconds))

    sign = "-" if total_seconds < 0 else ""
    total_seconds = abs(total_seconds)

    dec_dd = sign + str(total_seconds // 3600).zfill(2)
    dec_mm = str((total_seconds % 3600) // 60).zfill(2)
    dec_ss = str(total_seconds % 60).zfill(2)
    return f"{dec_dd}\N{DEGREE SIGN} {dec_mm}' {dec_ss}\""
