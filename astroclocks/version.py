"""Version and release metadata for AstroClocks."""

from datetime import date

APP_NAME = "AstroClocks"
APP_VERSION = "3.4.0"
APP_RELEASE_DATE = date(2026, 7, 10)
UPDATE_REPOSITORY = "Astroyan16/AstroClocks"
INSTALLER_NAME_PREFIX = "Install_AstroClocks"
APP_EXECUTABLE_STEM = "AstroClockV3"
APP_EXECUTABLE_NAME = f"{APP_EXECUTABLE_STEM}.exe"

__version__ = APP_VERSION


def installer_name(version=None):
    """Return the expected Windows installer filename for ``version``."""
    return f"{INSTALLER_NAME_PREFIX}{version or APP_VERSION}.exe"
