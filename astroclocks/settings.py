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
DEFAULT_MOUNT_SHOW_RETICLE = True
MAX_SKY_MAGNITUDE_LIMIT = 6.2
DEFAULT_TIMEZONE_NAME = ""
DEFAULT_DAYLIGHT_SAVING_ENABLED = False
DEFAULT_LANGUAGE = "en"
DEFAULT_HOUR_ANGLE_OFFSET_ENABLED = True
DEFAULT_DECLINATION_OFFSET_ENABLED = True
DEFAULT_DOUBLE_MAX_PRIMARY_MAGNITUDE = 10.0
DEFAULT_DOUBLE_MAX_SECONDARY_MAGNITUDE = 12.0
DEFAULT_DOUBLE_MIN_SEPARATION = 0.14
DEFAULT_DOUBLE_MAX_SEPARATION = 5.0
DEFAULT_DOUBLE_MIN_MAX_ALTITUDE = 10.0
DEFAULT_DOUBLE_VISIBLE_NIGHT = True
DEFAULT_DOUBLE_TRANSIT_NIGHT = False
DEFAULT_DOUBLE_INCLUDE_PHYSICAL = True
DEFAULT_DOUBLE_INCLUDE_NOTED = True
DEFAULT_DOUBLE_INCLUDE_APPARENT = False
DEFAULT_DOUBLE_INCLUDE_UNCERTAIN = False
DEFAULT_DOUBLE_EXCLUDE_POLAR_CIRCLE = False
DEFAULT_DOUBLE_USE_ONLINE = True
DEFAULT_DEEP_SKY_CATEGORY = "galaxy"
DEFAULT_DEEP_SKY_MIN_MAGNITUDE = -2.0
DEFAULT_DEEP_SKY_MAX_MAGNITUDE = 13.0
DEFAULT_DEEP_SKY_MIN_MAX_ALTITUDE = 10.0
DEFAULT_DEEP_SKY_VISIBLE_NIGHT = True
DEFAULT_DEEP_SKY_TRANSIT_NIGHT = False
DEFAULT_DEEP_SKY_EXCLUDE_POLAR_CIRCLE = False
DEFAULT_DEEP_SKY_EXCLUDE_SUSPECT_MAGNITUDES = False
DEEP_SKY_MAGNITUDE_BANDS = ("V", "U", "B", "R", "I", "J", "H", "K")
DEFAULT_DEEP_SKY_MAGNITUDE_BAND = "V"
DEEP_SKY_MAGNITUDE_BAND_CODES = set(DEEP_SKY_MAGNITUDE_BANDS)
STAR_SEARCH_SPECTRAL_TYPES = ("O", "B", "A", "F", "G", "K", "M")
DEFAULT_STAR_SEARCH_SPECTRAL_TYPE = "G"
STAR_SEARCH_MAGNITUDE_BANDS = DEEP_SKY_MAGNITUDE_BANDS
DEFAULT_STAR_SEARCH_MAGNITUDE_BAND = "V"
STAR_SEARCH_MAGNITUDE_BAND_CODES = set(STAR_SEARCH_MAGNITUDE_BANDS)
DEFAULT_STAR_SEARCH_MIN_MAGNITUDE = -2.0
DEFAULT_STAR_SEARCH_MAX_MAGNITUDE = 8.5
DEFAULT_STAR_SEARCH_MIN_MAX_ALTITUDE = 10.0
DEFAULT_STAR_SEARCH_VISIBLE_NIGHT = True
DEFAULT_STAR_SEARCH_TRANSIT_NIGHT = False
DEFAULT_STAR_SEARCH_EXCLUDE_POLAR_CIRCLE = False
DEFAULT_STAR_SEARCH_EXCLUDE_SUSPECT_MAGNITUDES = False
DEEP_SKY_CATEGORY_CODES = {
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
}
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
    mount_ascom_driver_id: str = ""
    mount_ascom_driver_name: str = ""
    mount_show_reticle: bool = DEFAULT_MOUNT_SHOW_RETICLE
    timezone_name: str = DEFAULT_TIMEZONE_NAME
    daylight_saving_enabled: bool = DEFAULT_DAYLIGHT_SAVING_ENABLED
    language: str = DEFAULT_LANGUAGE
    hour_angle_offset_enabled: bool = DEFAULT_HOUR_ANGLE_OFFSET_ENABLED
    declination_offset_enabled: bool = DEFAULT_DECLINATION_OFFSET_ENABLED
    double_max_primary_magnitude: float = DEFAULT_DOUBLE_MAX_PRIMARY_MAGNITUDE
    double_max_secondary_magnitude: float = DEFAULT_DOUBLE_MAX_SECONDARY_MAGNITUDE
    double_min_separation: float = DEFAULT_DOUBLE_MIN_SEPARATION
    double_max_separation: float = DEFAULT_DOUBLE_MAX_SEPARATION
    double_min_max_altitude: float = DEFAULT_DOUBLE_MIN_MAX_ALTITUDE
    double_visible_night: bool = DEFAULT_DOUBLE_VISIBLE_NIGHT
    double_transit_night: bool = DEFAULT_DOUBLE_TRANSIT_NIGHT
    double_include_physical: bool = DEFAULT_DOUBLE_INCLUDE_PHYSICAL
    double_include_noted: bool = DEFAULT_DOUBLE_INCLUDE_NOTED
    double_include_apparent: bool = DEFAULT_DOUBLE_INCLUDE_APPARENT
    double_include_uncertain: bool = DEFAULT_DOUBLE_INCLUDE_UNCERTAIN
    double_exclude_polar_circle: bool = DEFAULT_DOUBLE_EXCLUDE_POLAR_CIRCLE
    double_use_online: bool = DEFAULT_DOUBLE_USE_ONLINE
    deep_sky_category: str = DEFAULT_DEEP_SKY_CATEGORY
    deep_sky_min_magnitude: float = DEFAULT_DEEP_SKY_MIN_MAGNITUDE
    deep_sky_max_magnitude: float = DEFAULT_DEEP_SKY_MAX_MAGNITUDE
    deep_sky_min_max_altitude: float = DEFAULT_DEEP_SKY_MIN_MAX_ALTITUDE
    deep_sky_visible_night: bool = DEFAULT_DEEP_SKY_VISIBLE_NIGHT
    deep_sky_transit_night: bool = DEFAULT_DEEP_SKY_TRANSIT_NIGHT
    deep_sky_exclude_polar_circle: bool = DEFAULT_DEEP_SKY_EXCLUDE_POLAR_CIRCLE
    deep_sky_exclude_suspect_magnitudes: bool = DEFAULT_DEEP_SKY_EXCLUDE_SUSPECT_MAGNITUDES
    deep_sky_magnitude_band: str = DEFAULT_DEEP_SKY_MAGNITUDE_BAND
    star_search_spectral_type: str = DEFAULT_STAR_SEARCH_SPECTRAL_TYPE
    star_search_magnitude_band: str = DEFAULT_STAR_SEARCH_MAGNITUDE_BAND
    star_search_min_magnitude: float = DEFAULT_STAR_SEARCH_MIN_MAGNITUDE
    star_search_max_magnitude: float = DEFAULT_STAR_SEARCH_MAX_MAGNITUDE
    star_search_min_max_altitude: float = DEFAULT_STAR_SEARCH_MIN_MAX_ALTITUDE
    star_search_visible_night: bool = DEFAULT_STAR_SEARCH_VISIBLE_NIGHT
    star_search_transit_night: bool = DEFAULT_STAR_SEARCH_TRANSIT_NIGHT
    star_search_exclude_polar_circle: bool = DEFAULT_STAR_SEARCH_EXCLUDE_POLAR_CIRCLE
    star_search_exclude_suspect_magnitudes: bool = DEFAULT_STAR_SEARCH_EXCLUDE_SUSPECT_MAGNITUDES


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
    mount_ascom_driver_id = str(
        getattr(settings, "mount_ascom_driver_id", "") or ""
    ).strip()
    mount_ascom_driver_name = str(
        getattr(settings, "mount_ascom_driver_name", "") or ""
    ).strip()
    timezone_name = str(
        getattr(settings, "timezone_name", DEFAULT_TIMEZONE_NAME) or DEFAULT_TIMEZONE_NAME
    ).strip()
    deep_sky_category = str(
        getattr(settings, "deep_sky_category", DEFAULT_DEEP_SKY_CATEGORY)
        or DEFAULT_DEEP_SKY_CATEGORY
    )
    if deep_sky_category not in DEEP_SKY_CATEGORY_CODES:
        deep_sky_category = DEFAULT_DEEP_SKY_CATEGORY
    deep_sky_magnitude_band = str(
        getattr(settings, "deep_sky_magnitude_band", DEFAULT_DEEP_SKY_MAGNITUDE_BAND)
        or DEFAULT_DEEP_SKY_MAGNITUDE_BAND
    ).upper()
    if deep_sky_magnitude_band not in DEEP_SKY_MAGNITUDE_BAND_CODES:
        deep_sky_magnitude_band = DEFAULT_DEEP_SKY_MAGNITUDE_BAND
    star_search_spectral_type = str(
        getattr(settings, "star_search_spectral_type", DEFAULT_STAR_SEARCH_SPECTRAL_TYPE)
        or DEFAULT_STAR_SEARCH_SPECTRAL_TYPE
    ).upper()
    if star_search_spectral_type not in STAR_SEARCH_SPECTRAL_TYPES:
        star_search_spectral_type = DEFAULT_STAR_SEARCH_SPECTRAL_TYPE
    star_search_magnitude_band = str(
        getattr(settings, "star_search_magnitude_band", DEFAULT_STAR_SEARCH_MAGNITUDE_BAND)
        or DEFAULT_STAR_SEARCH_MAGNITUDE_BAND
    ).upper()
    if star_search_magnitude_band not in STAR_SEARCH_MAGNITUDE_BAND_CODES:
        star_search_magnitude_band = DEFAULT_STAR_SEARCH_MAGNITUDE_BAND

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
        mount_ascom_driver_id=mount_ascom_driver_id,
        mount_ascom_driver_name=mount_ascom_driver_name or mount_ascom_driver_id,
        mount_show_reticle=_coerce_bool(
            getattr(settings, "mount_show_reticle", DEFAULT_MOUNT_SHOW_RETICLE),
            DEFAULT_MOUNT_SHOW_RETICLE,
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
        double_max_primary_magnitude=_clamp(
            float(
                getattr(
                    settings,
                    "double_max_primary_magnitude",
                    DEFAULT_DOUBLE_MAX_PRIMARY_MAGNITUDE,
                )
            ),
            -2,
            20,
        ),
        double_max_secondary_magnitude=_clamp(
            float(
                getattr(
                    settings,
                    "double_max_secondary_magnitude",
                    DEFAULT_DOUBLE_MAX_SECONDARY_MAGNITUDE,
                )
            ),
            -2,
            20,
        ),
        double_min_separation=_clamp(
            float(getattr(settings, "double_min_separation", DEFAULT_DOUBLE_MIN_SEPARATION)),
            0,
            10000,
        ),
        double_max_separation=_clamp(
            float(getattr(settings, "double_max_separation", DEFAULT_DOUBLE_MAX_SEPARATION)),
            0,
            10000,
        ),
        double_min_max_altitude=_clamp(
            float(getattr(settings, "double_min_max_altitude", DEFAULT_DOUBLE_MIN_MAX_ALTITUDE)),
            -90,
            90,
        ),
        double_visible_night=_coerce_bool(
            getattr(settings, "double_visible_night", DEFAULT_DOUBLE_VISIBLE_NIGHT),
            DEFAULT_DOUBLE_VISIBLE_NIGHT,
        ),
        double_transit_night=_coerce_bool(
            getattr(settings, "double_transit_night", DEFAULT_DOUBLE_TRANSIT_NIGHT),
            DEFAULT_DOUBLE_TRANSIT_NIGHT,
        ),
        double_include_physical=_coerce_bool(
            getattr(settings, "double_include_physical", DEFAULT_DOUBLE_INCLUDE_PHYSICAL),
            DEFAULT_DOUBLE_INCLUDE_PHYSICAL,
        ),
        double_include_noted=_coerce_bool(
            getattr(settings, "double_include_noted", DEFAULT_DOUBLE_INCLUDE_NOTED),
            DEFAULT_DOUBLE_INCLUDE_NOTED,
        ),
        double_include_apparent=_coerce_bool(
            getattr(settings, "double_include_apparent", DEFAULT_DOUBLE_INCLUDE_APPARENT),
            DEFAULT_DOUBLE_INCLUDE_APPARENT,
        ),
        double_include_uncertain=_coerce_bool(
            getattr(settings, "double_include_uncertain", DEFAULT_DOUBLE_INCLUDE_UNCERTAIN),
            DEFAULT_DOUBLE_INCLUDE_UNCERTAIN,
        ),
        double_exclude_polar_circle=_coerce_bool(
            getattr(settings, "double_exclude_polar_circle", DEFAULT_DOUBLE_EXCLUDE_POLAR_CIRCLE),
            DEFAULT_DOUBLE_EXCLUDE_POLAR_CIRCLE,
        ),
        double_use_online=_coerce_bool(
            getattr(settings, "double_use_online", DEFAULT_DOUBLE_USE_ONLINE),
            DEFAULT_DOUBLE_USE_ONLINE,
        ),
        deep_sky_category=deep_sky_category,
        deep_sky_min_magnitude=_clamp(
            float(getattr(settings, "deep_sky_min_magnitude", DEFAULT_DEEP_SKY_MIN_MAGNITUDE)),
            -30,
            30,
        ),
        deep_sky_max_magnitude=_clamp(
            float(getattr(settings, "deep_sky_max_magnitude", DEFAULT_DEEP_SKY_MAX_MAGNITUDE)),
            -30,
            30,
        ),
        deep_sky_min_max_altitude=_clamp(
            float(getattr(settings, "deep_sky_min_max_altitude", DEFAULT_DEEP_SKY_MIN_MAX_ALTITUDE)),
            -90,
            90,
        ),
        deep_sky_visible_night=_coerce_bool(
            getattr(settings, "deep_sky_visible_night", DEFAULT_DEEP_SKY_VISIBLE_NIGHT),
            DEFAULT_DEEP_SKY_VISIBLE_NIGHT,
        ),
        deep_sky_transit_night=_coerce_bool(
            getattr(settings, "deep_sky_transit_night", DEFAULT_DEEP_SKY_TRANSIT_NIGHT),
            DEFAULT_DEEP_SKY_TRANSIT_NIGHT,
        ),
        deep_sky_exclude_polar_circle=_coerce_bool(
            getattr(
                settings,
                "deep_sky_exclude_polar_circle",
                DEFAULT_DEEP_SKY_EXCLUDE_POLAR_CIRCLE,
            ),
            DEFAULT_DEEP_SKY_EXCLUDE_POLAR_CIRCLE,
        ),
        deep_sky_exclude_suspect_magnitudes=_coerce_bool(
            getattr(
                settings,
                "deep_sky_exclude_suspect_magnitudes",
                DEFAULT_DEEP_SKY_EXCLUDE_SUSPECT_MAGNITUDES,
            ),
            DEFAULT_DEEP_SKY_EXCLUDE_SUSPECT_MAGNITUDES,
        ),
        deep_sky_magnitude_band=deep_sky_magnitude_band,
        star_search_spectral_type=star_search_spectral_type,
        star_search_magnitude_band=star_search_magnitude_band,
        star_search_min_magnitude=_clamp(
            float(getattr(settings, "star_search_min_magnitude", DEFAULT_STAR_SEARCH_MIN_MAGNITUDE)),
            -30,
            30,
        ),
        star_search_max_magnitude=_clamp(
            float(getattr(settings, "star_search_max_magnitude", DEFAULT_STAR_SEARCH_MAX_MAGNITUDE)),
            -30,
            30,
        ),
        star_search_min_max_altitude=_clamp(
            float(getattr(settings, "star_search_min_max_altitude", DEFAULT_STAR_SEARCH_MIN_MAX_ALTITUDE)),
            -90,
            90,
        ),
        star_search_visible_night=_coerce_bool(
            getattr(settings, "star_search_visible_night", DEFAULT_STAR_SEARCH_VISIBLE_NIGHT),
            DEFAULT_STAR_SEARCH_VISIBLE_NIGHT,
        ),
        star_search_transit_night=_coerce_bool(
            getattr(
                settings,
                "star_search_transit_night",
                DEFAULT_STAR_SEARCH_TRANSIT_NIGHT,
            ),
            DEFAULT_STAR_SEARCH_TRANSIT_NIGHT,
        ),
        star_search_exclude_polar_circle=_coerce_bool(
            getattr(
                settings,
                "star_search_exclude_polar_circle",
                DEFAULT_STAR_SEARCH_EXCLUDE_POLAR_CIRCLE,
            ),
            DEFAULT_STAR_SEARCH_EXCLUDE_POLAR_CIRCLE,
        ),
        star_search_exclude_suspect_magnitudes=_coerce_bool(
            getattr(
                settings,
                "star_search_exclude_suspect_magnitudes",
                DEFAULT_STAR_SEARCH_EXCLUDE_SUSPECT_MAGNITUDES,
            ),
            DEFAULT_STAR_SEARCH_EXCLUDE_SUSPECT_MAGNITUDES,
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
            mount_ascom_driver_id=data.get("mount_ascom_driver_id", ""),
            mount_ascom_driver_name=data.get("mount_ascom_driver_name", ""),
            mount_show_reticle=data.get(
                "mount_show_reticle",
                DEFAULT_MOUNT_SHOW_RETICLE,
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
            double_max_primary_magnitude=data.get(
                "double_max_primary_magnitude",
                DEFAULT_DOUBLE_MAX_PRIMARY_MAGNITUDE,
            ),
            double_max_secondary_magnitude=data.get(
                "double_max_secondary_magnitude",
                DEFAULT_DOUBLE_MAX_SECONDARY_MAGNITUDE,
            ),
            double_min_separation=data.get(
                "double_min_separation",
                DEFAULT_DOUBLE_MIN_SEPARATION,
            ),
            double_max_separation=data.get(
                "double_max_separation",
                DEFAULT_DOUBLE_MAX_SEPARATION,
            ),
            double_min_max_altitude=data.get(
                "double_min_max_altitude",
                DEFAULT_DOUBLE_MIN_MAX_ALTITUDE,
            ),
            double_visible_night=data.get(
                "double_visible_night",
                DEFAULT_DOUBLE_VISIBLE_NIGHT,
            ),
            double_transit_night=data.get(
                "double_transit_night",
                DEFAULT_DOUBLE_TRANSIT_NIGHT,
            ),
            double_include_physical=data.get(
                "double_include_physical",
                DEFAULT_DOUBLE_INCLUDE_PHYSICAL,
            ),
            double_include_noted=data.get(
                "double_include_noted",
                DEFAULT_DOUBLE_INCLUDE_NOTED,
            ),
            double_include_apparent=data.get(
                "double_include_apparent",
                DEFAULT_DOUBLE_INCLUDE_APPARENT,
            ),
            double_include_uncertain=data.get(
                "double_include_uncertain",
                DEFAULT_DOUBLE_INCLUDE_UNCERTAIN,
            ),
            double_exclude_polar_circle=data.get(
                "double_exclude_polar_circle",
                DEFAULT_DOUBLE_EXCLUDE_POLAR_CIRCLE,
            ),
            double_use_online=data.get(
                "double_use_online",
                DEFAULT_DOUBLE_USE_ONLINE,
            ),
            deep_sky_category=data.get(
                "deep_sky_category",
                DEFAULT_DEEP_SKY_CATEGORY,
            ),
            deep_sky_min_magnitude=data.get(
                "deep_sky_min_magnitude",
                DEFAULT_DEEP_SKY_MIN_MAGNITUDE,
            ),
            deep_sky_max_magnitude=data.get(
                "deep_sky_max_magnitude",
                DEFAULT_DEEP_SKY_MAX_MAGNITUDE,
            ),
            deep_sky_min_max_altitude=data.get(
                "deep_sky_min_max_altitude",
                DEFAULT_DEEP_SKY_MIN_MAX_ALTITUDE,
            ),
            deep_sky_visible_night=data.get(
                "deep_sky_visible_night",
                DEFAULT_DEEP_SKY_VISIBLE_NIGHT,
            ),
            deep_sky_transit_night=data.get(
                "deep_sky_transit_night",
                DEFAULT_DEEP_SKY_TRANSIT_NIGHT,
            ),
            deep_sky_exclude_polar_circle=data.get(
                "deep_sky_exclude_polar_circle",
                DEFAULT_DEEP_SKY_EXCLUDE_POLAR_CIRCLE,
            ),
            deep_sky_exclude_suspect_magnitudes=data.get(
                "deep_sky_exclude_suspect_magnitudes",
                DEFAULT_DEEP_SKY_EXCLUDE_SUSPECT_MAGNITUDES,
            ),
            deep_sky_magnitude_band=data.get(
                "deep_sky_magnitude_band",
                DEFAULT_DEEP_SKY_MAGNITUDE_BAND,
            ),
            star_search_spectral_type=data.get(
                "star_search_spectral_type",
                DEFAULT_STAR_SEARCH_SPECTRAL_TYPE,
            ),
            star_search_magnitude_band=data.get(
                "star_search_magnitude_band",
                DEFAULT_STAR_SEARCH_MAGNITUDE_BAND,
            ),
            star_search_min_magnitude=data.get(
                "star_search_min_magnitude",
                DEFAULT_STAR_SEARCH_MIN_MAGNITUDE,
            ),
            star_search_max_magnitude=data.get(
                "star_search_max_magnitude",
                DEFAULT_STAR_SEARCH_MAX_MAGNITUDE,
            ),
            star_search_min_max_altitude=data.get(
                "star_search_min_max_altitude",
                DEFAULT_STAR_SEARCH_MIN_MAX_ALTITUDE,
            ),
            star_search_visible_night=data.get(
                "star_search_visible_night",
                DEFAULT_STAR_SEARCH_VISIBLE_NIGHT,
            ),
            star_search_transit_night=data.get(
                "star_search_transit_night",
                DEFAULT_STAR_SEARCH_TRANSIT_NIGHT,
            ),
            star_search_exclude_polar_circle=data.get(
                "star_search_exclude_polar_circle",
                DEFAULT_STAR_SEARCH_EXCLUDE_POLAR_CIRCLE,
            ),
            star_search_exclude_suspect_magnitudes=data.get(
                "star_search_exclude_suspect_magnitudes",
                DEFAULT_STAR_SEARCH_EXCLUDE_SUSPECT_MAGNITUDES,
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
