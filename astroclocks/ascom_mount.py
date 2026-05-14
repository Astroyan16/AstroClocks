from dataclasses import dataclass


EQUATORIAL_SYSTEM_OTHER = 0
EQUATORIAL_SYSTEM_TOPOCENTRIC = 1
EQUATORIAL_SYSTEM_J2000 = 2
EQUATORIAL_SYSTEM_J2050 = 3
EQUATORIAL_SYSTEM_B1950 = 4
TRACKING_RATE_SIDEREAL = 0
TRACKING_RATE_LUNAR = 1
TRACKING_RATE_SOLAR = 2
TRACKING_RATE_KING = 3


class AscomMountError(RuntimeError):
    """Raised when an ASCOM mount operation cannot be completed."""


@dataclass
class MountSnapshot:
    driver_id: str
    driver_name: str
    ra_hours: float
    declination: float
    equatorial_system: int
    slewing: bool | None = None
    tracking: bool | None = None
    tracking_rate: int | None = None
    site_latitude: float | None = None
    site_longitude: float | None = None


@dataclass
class MountCapabilities:
    can_slew: bool = False
    can_slew_async: bool = False
    can_abort_slew: bool = False


def _read_optional_float(value_getter):
    try:
        value = value_getter()
    except Exception:
        return None
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_longitude(longitude):
    normalized = ((longitude + 180.0) % 360.0) - 180.0
    if normalized == -180.0 and longitude > 0:
        return 180.0
    return normalized


def _read_optional_int(value_getter):
    try:
        value = value_getter()
    except Exception:
        return None
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _read_optional_bool(value_getter):
    try:
        value = value_getter()
    except Exception:
        return None
    if value is None:
        return None
    try:
        return bool(value)
    except (TypeError, ValueError):
        return None


def _has_callable_member(target, name):
    try:
        member = getattr(target, name)
    except Exception:
        return False
    return callable(member)


def _require_ascom():
    try:
        import win32com.client  # type: ignore
    except ImportError as exc:  # pragma: no cover - exercised indirectly on Windows
        raise AscomMountError("ASCOM support requires pywin32 on Windows.") from exc

    return win32com.client


def is_available():
    try:
        _require_ascom().Dispatch("ASCOM.Utilities.Chooser")
    except AscomMountError:
        raise
    except Exception as exc:
        raise AscomMountError(
            "The ASCOM Platform chooser is not installed on this computer."
        ) from exc
    return True


def choose_driver(current_driver_id=""):
    win32com_client = _require_ascom()
    try:
        try:
            chooser = win32com_client.Dispatch("ASCOM.Utilities.Chooser")
        except Exception as exc:  # pragma: no cover - depends on local ASCOM install
            raise AscomMountError(
                "The ASCOM Platform chooser is not installed on this computer."
            ) from exc
        chooser.DeviceType = "Telescope"
        driver_id = str(chooser.Choose(current_driver_id or "") or "").strip()
        if not driver_id:
            return "", ""
        driver = win32com_client.Dispatch(driver_id)
        driver_name = str(getattr(driver, "Name", "") or driver_id).strip()
        return driver_id, driver_name
    except AscomMountError:
        raise
    except Exception as exc:  # pragma: no cover - depends on local COM behavior
        raise AscomMountError(f"Unable to open the ASCOM mount chooser: {exc}") from exc


def connect(driver_id):
    if not str(driver_id or "").strip():
        raise AscomMountError("No ASCOM mount driver is selected.")

    win32com_client = _require_ascom()
    try:
        telescope = win32com_client.Dispatch(driver_id)
    except Exception as exc:  # pragma: no cover - depends on local COM behavior
        raise AscomMountError(f"Unable to create the ASCOM mount driver: {exc}") from exc
    try:
        telescope.Connected = True
    except Exception as exc:  # pragma: no cover - depends on driver behavior
        raise AscomMountError(f"Unable to connect to the ASCOM mount: {exc}") from exc
    driver_name = str(getattr(telescope, "Name", "") or driver_id).strip()
    return telescope, driver_name


def disconnect(telescope):
    _require_ascom()
    if telescope is None:
        return
    try:
        telescope.Connected = False
    except Exception as exc:  # pragma: no cover - depends on driver behavior
        raise AscomMountError(f"Unable to disconnect the ASCOM mount: {exc}") from exc


def read_capabilities(telescope):
    _require_ascom()
    if telescope is None:
        raise AscomMountError("The ASCOM mount is not connected.")
    can_slew = _read_optional_bool(lambda: getattr(telescope, "CanSlew"))
    can_slew_async = _read_optional_bool(lambda: getattr(telescope, "CanSlewAsync"))
    can_abort_slew = _read_optional_bool(lambda: getattr(telescope, "CanAbortSlew"))
    return MountCapabilities(
        can_slew=bool(can_slew),
        can_slew_async=bool(can_slew_async),
        can_abort_slew=bool(can_abort_slew) or _has_callable_member(telescope, "AbortSlew"),
    )


def slew_to_coordinates(telescope, ra_hours, declination):
    _require_ascom()
    if telescope is None:
        raise AscomMountError("The ASCOM mount is not connected.")
    capabilities = read_capabilities(telescope)
    if capabilities.can_slew_async:
        method_name = "SlewToCoordinatesAsync"
    elif capabilities.can_slew:
        method_name = "SlewToCoordinates"
    else:
        raise AscomMountError("The ASCOM mount does not support GoTo commands.")
    try:
        getattr(telescope, method_name)(
            float(ra_hours) % 24,
            max(-90.0, min(90.0, float(declination))),
        )
    except Exception as exc:  # pragma: no cover - depends on driver behavior
        raise AscomMountError(f"Unable to send the ASCOM mount GoTo command: {exc}") from exc


def abort_slew(telescope):
    _require_ascom()
    if telescope is None:
        raise AscomMountError("The ASCOM mount is not connected.")
    capabilities = read_capabilities(telescope)
    if not capabilities.can_abort_slew:
        raise AscomMountError("The ASCOM mount does not support aborting a GoTo command.")
    try:
        telescope.AbortSlew()
    except Exception as exc:  # pragma: no cover - depends on driver behavior
        raise AscomMountError(f"Unable to stop the ASCOM mount GoTo command: {exc}") from exc


def read_snapshot(telescope, driver_id, driver_name):
    _require_ascom()
    if telescope is None:
        raise AscomMountError("The ASCOM mount is not connected.")
    try:
        connected = bool(getattr(telescope, "Connected"))
    except Exception as exc:  # pragma: no cover - depends on driver behavior
        raise AscomMountError(f"Unable to read the ASCOM mount connection state: {exc}") from exc
    if not connected:
        raise AscomMountError("The ASCOM mount is disconnected.")
    try:
        ra_hours = float(telescope.RightAscension)
        declination = float(telescope.Declination)
    except Exception as exc:  # pragma: no cover - depends on driver behavior
        raise AscomMountError(f"Unable to read the ASCOM mount coordinates: {exc}") from exc
    try:
        equatorial_system = int(getattr(telescope, "EquatorialSystem"))
    except Exception:
        equatorial_system = EQUATORIAL_SYSTEM_TOPOCENTRIC
    try:
        tracking = bool(getattr(telescope, "Tracking"))
    except Exception:
        tracking = None
    slewing = _read_optional_bool(lambda: getattr(telescope, "Slewing"))
    tracking_rate = _read_optional_int(lambda: getattr(telescope, "TrackingRate"))
    site_latitude = _read_optional_float(lambda: getattr(telescope, "SiteLatitude"))
    if site_latitude is not None:
        site_latitude = max(-90.0, min(90.0, site_latitude))
    site_longitude = _read_optional_float(lambda: getattr(telescope, "SiteLongitude"))
    if site_longitude is not None:
        site_longitude = _normalize_longitude(site_longitude)
    return MountSnapshot(
        driver_id=str(driver_id or "").strip(),
        driver_name=str(driver_name or driver_id).strip(),
        ra_hours=ra_hours % 24,
        declination=max(-90.0, min(90.0, declination)),
        equatorial_system=equatorial_system,
        slewing=slewing,
        tracking=tracking,
        tracking_rate=tracking_rate,
        site_latitude=site_latitude,
        site_longitude=site_longitude,
    )
