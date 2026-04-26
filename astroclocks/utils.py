import re
import sys
from os import path


def resource_path(relative_path):
    """Get absolute path to a bundled resource."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = path.abspath(".")

    return path.join(base_path, relative_path)


def separate_dms_coordinates(dms_coordinate):
    """Extract degrees, minutes and seconds from a DMS string."""
    pattern = r"([+-]?\d+)d(\d+)m([\d.]+)s"
    match = re.match(pattern, dms_coordinate)

    if not match:
        raise ValueError("Invalid DMS coordinate format")

    degrees = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return degrees, minutes, seconds


def is_float(value):
    """Return True when value can be converted to float."""
    try:
        float(value)
        return True
    except ValueError:
        return False

