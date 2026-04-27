import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

from astroclocks.utils import resource_path


DEFAULT_SITE_NAME = "Observatoire de Meudon - T1m"
DEFAULT_COUNTRY = "France"
LEGACY_DEFAULT_SITE_NAMES = {
    "Telescope T1m - Observatoire de Meudon",
    "Télescope T1m - Observatoire de Meudon",
}
DEFAULT_LATITUDE = 48.805
DEFAULT_LONGITUDE = 2.23006
DEFAULT_ALADIN_FOV_DEG = 0.5
DEFAULT_SKY_MAGNITUDE_LIMIT = 4.0
DEFAULT_SKY_SHOW_ALTAZ_GRID = True
DEFAULT_SKY_SHOW_EQUATORIAL_GRID = True
DEFAULT_SKY_SHOW_SOLAR_SYSTEM = False
MAX_SKY_MAGNITUDE_LIMIT = 15.0
DEFAULT_TIMEZONE_NAME = ""
DEFAULT_DAYLIGHT_SAVING_ENABLED = False
DEFAULT_LANGUAGE = "en"
DEFAULT_HOUR_ANGLE_OFFSET_ENABLED = True
DEFAULT_DECLINATION_OFFSET_ENABLED = True
SUPPORTED_LANGUAGES = {"en", "fr"}

LEGACY_LONGITUDE_FILE = resource_path("Longitude.ini")
LEGACY_SETTINGS_FILE = resource_path("AstroClocks.ini")


def _user_config_dir():
    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "AstroClocks"
    return Path.home() / ".astroclocks"


SETTINGS_FILE = _user_config_dir() / "AstroClocks.ini"


@dataclass
class AppSettings:
    site_name: str = DEFAULT_SITE_NAME
    country: str = DEFAULT_COUNTRY
    latitude: float = DEFAULT_LATITUDE
    longitude: float = DEFAULT_LONGITUDE
    aladin_fov_deg: float = DEFAULT_ALADIN_FOV_DEG
    sky_magnitude_limit: float = DEFAULT_SKY_MAGNITUDE_LIMIT
    sky_show_altaz_grid: bool = DEFAULT_SKY_SHOW_ALTAZ_GRID
    sky_show_equatorial_grid: bool = DEFAULT_SKY_SHOW_EQUATORIAL_GRID
    sky_show_solar_system: bool = DEFAULT_SKY_SHOW_SOLAR_SYSTEM
    timezone_name: str = DEFAULT_TIMEZONE_NAME
    daylight_saving_enabled: bool = DEFAULT_DAYLIGHT_SAVING_ENABLED
    language: str = DEFAULT_LANGUAGE
    hour_angle_offset_enabled: bool = DEFAULT_HOUR_ANGLE_OFFSET_ENABLED
    declination_offset_enabled: bool = DEFAULT_DECLINATION_OFFSET_ENABLED


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _coerce_bool(value, default):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    if value is None:
        return default
    return bool(value)


def _read_legacy_longitude():
    try:
        with open(LEGACY_LONGITUDE_FILE, "r", encoding="utf-8") as file:
            content = file.readline().strip()
    except FileNotFoundError:
        return DEFAULT_LONGITUDE

    try:
        longitude = float(content)
    except ValueError:
        return DEFAULT_LONGITUDE

    return _clamp(longitude, -180, 180)


def normalize_settings(settings):
    language = str(getattr(settings, "language", DEFAULT_LANGUAGE) or DEFAULT_LANGUAGE).lower()
    if language not in SUPPORTED_LANGUAGES:
        language = DEFAULT_LANGUAGE
    site_name = str(settings.site_name or DEFAULT_SITE_NAME)
    if site_name in LEGACY_DEFAULT_SITE_NAMES:
        site_name = DEFAULT_SITE_NAME
    country = str(getattr(settings, "country", DEFAULT_COUNTRY) or DEFAULT_COUNTRY).strip()
    timezone_name = str(
        getattr(settings, "timezone_name", DEFAULT_TIMEZONE_NAME) or DEFAULT_TIMEZONE_NAME
    ).strip()

    return AppSettings(
        site_name=site_name,
        country=country or DEFAULT_COUNTRY,
        latitude=_clamp(float(settings.latitude), -90, 90),
        longitude=_clamp(float(settings.longitude), -180, 180),
        aladin_fov_deg=_clamp(float(settings.aladin_fov_deg), 0.01, 180),
        sky_magnitude_limit=_clamp(
            float(getattr(settings, "sky_magnitude_limit", DEFAULT_SKY_MAGNITUDE_LIMIT)),
            -2,
            MAX_SKY_MAGNITUDE_LIMIT,
        ),
        sky_show_altaz_grid=_coerce_bool(
            getattr(settings, "sky_show_altaz_grid", DEFAULT_SKY_SHOW_ALTAZ_GRID),
            DEFAULT_SKY_SHOW_ALTAZ_GRID,
        ),
        sky_show_equatorial_grid=_coerce_bool(
            getattr(settings, "sky_show_equatorial_grid", DEFAULT_SKY_SHOW_EQUATORIAL_GRID),
            DEFAULT_SKY_SHOW_EQUATORIAL_GRID,
        ),
        sky_show_solar_system=_coerce_bool(
            getattr(settings, "sky_show_solar_system", DEFAULT_SKY_SHOW_SOLAR_SYSTEM),
            DEFAULT_SKY_SHOW_SOLAR_SYSTEM,
        ),
        timezone_name=timezone_name,
        daylight_saving_enabled=_coerce_bool(
            getattr(settings, "daylight_saving_enabled", DEFAULT_DAYLIGHT_SAVING_ENABLED),
            DEFAULT_DAYLIGHT_SAVING_ENABLED,
        ),
        language=language,
        hour_angle_offset_enabled=_coerce_bool(
            getattr(settings, "hour_angle_offset_enabled", DEFAULT_HOUR_ANGLE_OFFSET_ENABLED),
            DEFAULT_HOUR_ANGLE_OFFSET_ENABLED,
        ),
        declination_offset_enabled=_coerce_bool(
            getattr(settings, "declination_offset_enabled", DEFAULT_DECLINATION_OFFSET_ENABLED),
            DEFAULT_DECLINATION_OFFSET_ENABLED,
        ),
    )


def load_app_settings():
    for settings_file in (SETTINGS_FILE, LEGACY_SETTINGS_FILE):
        try:
            with open(settings_file, "r", encoding="utf-8") as file:
                data = json.load(file)
            break
        except FileNotFoundError:
            data = None
        except json.JSONDecodeError:
            data = None
            break

    if data is None:
        return normalize_settings(
            AppSettings(
                latitude=DEFAULT_LATITUDE,
                longitude=_read_legacy_longitude(),
            )
        )

    return normalize_settings(
        AppSettings(
            site_name=data.get("site_name", DEFAULT_SITE_NAME),
            country=data.get("country", DEFAULT_COUNTRY),
            latitude=data.get("latitude", DEFAULT_LATITUDE),
            longitude=data.get("longitude", DEFAULT_LONGITUDE),
            aladin_fov_deg=data.get("aladin_fov_deg", DEFAULT_ALADIN_FOV_DEG),
            sky_magnitude_limit=data.get(
                "sky_magnitude_limit",
                DEFAULT_SKY_MAGNITUDE_LIMIT,
            ),
            sky_show_altaz_grid=data.get(
                "sky_show_altaz_grid",
                DEFAULT_SKY_SHOW_ALTAZ_GRID,
            ),
            sky_show_equatorial_grid=data.get(
                "sky_show_equatorial_grid",
                DEFAULT_SKY_SHOW_EQUATORIAL_GRID,
            ),
            sky_show_solar_system=data.get(
                "sky_show_solar_system",
                DEFAULT_SKY_SHOW_SOLAR_SYSTEM,
            ),
            timezone_name=data.get("timezone_name", DEFAULT_TIMEZONE_NAME),
            daylight_saving_enabled=data.get(
                "daylight_saving_enabled", DEFAULT_DAYLIGHT_SAVING_ENABLED
            ),
            language=data.get("language", DEFAULT_LANGUAGE),
            hour_angle_offset_enabled=data.get(
                "hour_angle_offset_enabled", DEFAULT_HOUR_ANGLE_OFFSET_ENABLED
            ),
            declination_offset_enabled=data.get(
                "declination_offset_enabled", DEFAULT_DECLINATION_OFFSET_ENABLED
            ),
        )
    )


def save_app_settings(settings):
    settings = normalize_settings(settings)
    SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w+", encoding="utf-8") as file:
        json.dump(asdict(settings), file, indent=2)


def init_default_longitude():
    save_app_settings(AppSettings())


def load_longitude():
    """Backward-compatible helper for older code paths."""
    return load_app_settings().longitude


def save_longitude(longitude):
    settings = load_app_settings()
    settings.longitude = longitude
    save_app_settings(settings)


def _format_signed_angle(value, positive_suffix, negative_suffix):
    suffix = positive_suffix if value >= 0 else negative_suffix
    abs_value = abs(value)
    degrees = int(abs_value)
    minutes_float = (abs_value - degrees) * 60
    minutes = int(minutes_float)
    seconds = int(round((minutes_float - minutes) * 60))
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        degrees += 1

    return f"{value:.5f}\N{DEGREE SIGN} ({degrees}\N{DEGREE SIGN} {minutes}' {seconds}\" {suffix})"


def get_hemisphere(longitude):
    return "E" if longitude >= 0 else "W"


def format_longitude_display(longitude, east_suffix="E", west_suffix="W"):
    return _format_signed_angle(longitude, east_suffix, west_suffix)


def format_latitude_display(latitude, north_suffix="N", south_suffix="S"):
    return _format_signed_angle(latitude, north_suffix, south_suffix)
