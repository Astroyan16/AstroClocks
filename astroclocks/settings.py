import json
from dataclasses import asdict, dataclass

from astroclocks.utils import resource_path


DEFAULT_SITE_NAME = "Telescope T1m - Observatoire de Meudon"
DEFAULT_LATITUDE = 48.805
DEFAULT_LONGITUDE = 2.23006
DEFAULT_ALADIN_FOV_DEG = 0.5
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = {"en", "fr"}

LONGITUDE_FILE = resource_path("Longitude.ini")
SETTINGS_FILE = resource_path("AstroClocks.ini")


@dataclass
class AppSettings:
    site_name: str = DEFAULT_SITE_NAME
    latitude: float = DEFAULT_LATITUDE
    longitude: float = DEFAULT_LONGITUDE
    aladin_fov_deg: float = DEFAULT_ALADIN_FOV_DEG
    language: str = DEFAULT_LANGUAGE


def _clamp(value, minimum, maximum):
    return max(minimum, min(maximum, value))


def _read_legacy_longitude():
    try:
        with open(LONGITUDE_FILE, "r", encoding="utf-8") as file:
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

    return AppSettings(
        site_name=str(settings.site_name or DEFAULT_SITE_NAME),
        latitude=_clamp(float(settings.latitude), -90, 90),
        longitude=_clamp(float(settings.longitude), -180, 180),
        aladin_fov_deg=_clamp(float(settings.aladin_fov_deg), 0.01, 180),
        language=language,
    )


def load_app_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
    except (FileNotFoundError, json.JSONDecodeError):
        return normalize_settings(
            AppSettings(
                latitude=DEFAULT_LATITUDE,
                longitude=_read_legacy_longitude(),
            )
        )

    return normalize_settings(
        AppSettings(
            site_name=data.get("site_name", DEFAULT_SITE_NAME),
            latitude=data.get("latitude", DEFAULT_LATITUDE),
            longitude=data.get("longitude", DEFAULT_LONGITUDE),
            aladin_fov_deg=data.get("aladin_fov_deg", DEFAULT_ALADIN_FOV_DEG),
            language=data.get("language", DEFAULT_LANGUAGE),
        )
    )


def save_app_settings(settings):
    settings = normalize_settings(settings)
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


def format_longitude_display(longitude):
    return _format_signed_angle(longitude, "E", "W")


def format_latitude_display(latitude):
    return _format_signed_angle(latitude, "N", "S")
