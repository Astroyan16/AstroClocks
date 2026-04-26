import datetime
import json
from time import strftime
from urllib.parse import urlencode
from urllib.request import urlopen

import zeep
from astropy import units as u
from astropy.coordinates import FK5, SkyCoord
from astropy.time import Time

from astroclocks.utils import separate_dms_coordinates


def format_timezone_label():
    tz_value = strftime("%z")
    if float(tz_value[3:5]) > 0:
        return (
            "UTC"
            + tz_value[0]
            + str(
                float(f"{float(tz_value[0:3]):.2f}")
                + float(f"{float(tz_value[3:5]) / 60:.2f}")
            )
        )

    return "UTC" + tz_value[0] + str(int(f"{float(tz_value[0:3]):.0f}"))


def convert_j2000_to_now(coords):
    """Convert J2000 coordinates to the current FK5 equinox."""
    date_time = Time(Time(datetime.datetime.utcnow(), scale="utc").jd, format="jd", scale="utc")
    j2000_coords = [coords, coords.replace(":", " ")]
    fk5 = FK5(equinox=date_time)
    jnow = SkyCoord(j2000_coords, frame=None, unit=(u.hourangle, u.deg)).transform_to(fk5)
    return jnow[0].to_string("hmsdms")


def convert_star_catalog_j2000_to_jnow(stars):
    """Convert a J2000/ICRS star catalog to the current FK5 equinox."""
    if not stars:
        return []

    date_time = Time(Time(datetime.datetime.utcnow(), scale="utc").jd, format="jd", scale="utc")
    fk5_now = FK5(equinox=date_time)
    catalog = SkyCoord(
        ra=[star[1] for star in stars] * u.hourangle,
        dec=[star[2] for star in stars] * u.deg,
        frame="icrs",
    ).transform_to(fk5_now)

    return [
        (star[0], catalog[index].ra.hour, catalog[index].dec.deg, star[3])
        for index, star in enumerate(stars)
    ]


def get_planet_coord(object_type, planet_name):
    """Retrieve ICRS coordinates from IMCCE Miriade."""
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


def resolve_solar_system_coordinates(selected_type, object_name):
    prefix_mapping = {
        "Asteroid": "a",
        "Comet": "c",
        "Dwarf Planet": "dp",
        "Planet": "p",
        "Natural Satellite": "s",
    }

    coordinates = get_planet_coord(prefix_mapping[selected_type], object_name)
    alpha_hh, alpha_mm, alpha_ss = coordinates[0][1:].split(":")
    delta_dd, delta_mm, delta_ss = coordinates[1].split(":")

    return {
        "message": (
            "ICRS Coordinates from IMCCE:\n"
            f"Alpha : {coordinates[0]}\n"
            f"Delta : {coordinates[1]}"
        ),
        "alpha_hh": int(alpha_hh),
        "alpha_mm": int(alpha_mm),
        "alpha_ss": str(round(float(alpha_ss))).zfill(2),
        "delta_dd": int(delta_dd),
        "delta_mm": int(delta_mm),
        "delta_ss": str(round(float(delta_ss))).zfill(2),
    }


def resolve_deep_sky_coordinates(object_name):
    coordinates = SkyCoord.from_name(object_name)
    j2000 = coordinates.to_string("hmsdms")
    coord = convert_j2000_to_now(j2000)
    alpha2000, delta2000 = j2000.split(" ")
    alpha, delta = coord.split(" ")

    alpha_digits = "".join(char for char in alpha if char == "." or char.isdigit())
    delta_dd, delta_mm, delta_ss = separate_dms_coordinates(delta)
    alpha_value = alpha_digits[0:9]

    return {
        "message": (
            "ICRS Coordinates from Sesame :\n"
            f"RA (Alpha) : {alpha2000}\n"
            f"Dec (Delta) : {delta2000}"
        ),
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


def compute_clock_state(longitude, alpha_hh, alpha_mm, alpha_ss):
    date_time = strftime("%m%d%Y %H%M%S")
    date_time_utc = datetime.datetime.utcnow().strftime("%m%d%Y %H%M%S")

    hour = float(date_time[9:11])
    minute = float(date_time[11:13])
    second = float(date_time[13:15])

    month_utc = float(date_time_utc[0:2])
    day_utc = float(date_time_utc[2:4])
    year_utc = float(date_time_utc[4:8])
    hour_utc = float(date_time_utc[9:11])
    minute_utc = float(date_time_utc[11:13])
    second_utc = float(date_time_utc[13:15])

    local_string = f"{int(hour):02d}:{int(minute):02d}:{int(second):02d}"
    utc_string = f"{int(hour_utc):02d}:{int(minute_utc):02d}:{int(second_utc):02d}"

    ut = hour_utc + (minute_utc / 60) + (second_utc / 3600)
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
    gmst_mm = (gmst - int(gmst)) * 60
    gmst_ss = (gmst_mm - int(gmst_mm)) * 60
    gmst_string = f"{int(gmst):02d}:{int(gmst_mm):02d}:{int(gmst_ss):02d}"

    longitude_hours = longitude / 15
    lst = (gmst + longitude_hours) % 24
    lst_mm = (lst - int(lst)) * 60
    lst_ss = (lst_mm - int(lst_mm)) * 60
    lst_string = f"{int(lst):02d}:{int(lst_mm):02d}:{int(lst_ss):02d}"

    alpha_seconds = float(alpha_hh) * 3600 + float(alpha_mm) * 60 + float(alpha_ss)
    hour_angle = (3600 * (lst + 6) - alpha_seconds)
    ha_hh = int((hour_angle / 3600) % 24)
    ha_mm = int(((hour_angle / 60 - ha_hh * 60) % 60))
    ha_ss = int((hour_angle - ha_mm * 60 - ha_hh * 3600) % 60)
    ha_string = f"{ha_hh:02d}h {ha_mm:02d}m {ha_ss:02d}s"

    return {
        "local": local_string,
        "utc": utc_string,
        "gmst": gmst_string,
        "lst": lst_string,
        "hour_angle": ha_string,
    }


def compute_declination_display(delta_dd, delta_mm, delta_ss):
    dec_sign = -1 if str(delta_dd).strip().startswith("-") else 1
    dec_degrees = dec_sign * (
        abs(float(delta_dd)) + (float(delta_mm) / 60) + (float(delta_ss) / 3600)
    )
    total_seconds = int(round((dec_degrees + 90) * 3600))
    total_seconds = max(0, min(180 * 3600, total_seconds))

    dec_dd = str(total_seconds // 3600).zfill(2)
    dec_mm = str((total_seconds % 3600) // 60).zfill(2)
    dec_ss = str(total_seconds % 60).zfill(2)
    return f"{dec_dd}\N{DEGREE SIGN} {dec_mm}' {dec_ss}\""
