"""Version and release metadata for AstroClocks."""

from datetime import date

APP_NAME = "AstroClocks"
APP_VERSION = "3.3.3"
APP_RELEASE_DATE = date(2026, 5, 10)
UPDATE_REPOSITORY = "Astroyan16/AstroClocks"
INSTALLER_NAME_PREFIX = "Install_AstroClocks"

__version__ = APP_VERSION


def installer_name(version=None):
    """Return the expected Windows installer filename for ``version``."""
    return f"{INSTALLER_NAME_PREFIX}{version or APP_VERSION}.exe"
