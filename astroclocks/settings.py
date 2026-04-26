from astroclocks.utils import resource_path


DEFAULT_LONGITUDE = 2.23006
LONGITUDE_FILE = resource_path("Longitude.ini")


def init_default_longitude():
    with open(LONGITUDE_FILE, "w+", encoding="utf-8") as file:
        file.write(str(DEFAULT_LONGITUDE))


def load_longitude():
    """Load longitude from file and recreate the default value when needed."""
    try:
        with open(LONGITUDE_FILE, "r", encoding="utf-8") as file:
            content = file.readline().strip()
    except FileNotFoundError:
        init_default_longitude()
        return DEFAULT_LONGITUDE

    if not content:
        init_default_longitude()
        return DEFAULT_LONGITUDE

    try:
        longitude = float(content)
    except ValueError:
        init_default_longitude()
        return DEFAULT_LONGITUDE

    if longitude < -180 or longitude > 180:
        init_default_longitude()
        return DEFAULT_LONGITUDE

    return longitude


def save_longitude(longitude):
    with open(LONGITUDE_FILE, "w+", encoding="utf-8") as file:
        file.write(str(longitude))


def get_hemisphere(longitude):
    return "E" if longitude > 0 else "W"


def format_longitude_display(longitude):
    hemisphere = get_hemisphere(longitude)
    long_deg = int(longitude)
    long_min_float = (longitude - int(longitude)) * 60
    long_sec = int((long_min_float - int(long_min_float)) * 60)
    long_min = int(long_min_float)
    return (
        f"{longitude}\N{DEGREE SIGN} "
        f"({long_deg}\N{DEGREE SIGN} {long_min}' {long_sec}\" {hemisphere})"
    )

