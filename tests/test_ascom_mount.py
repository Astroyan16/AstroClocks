import unittest
from unittest.mock import patch

from astroclocks import ascom_mount


class _FakeTelescope:
    def __init__(
        self,
        connected=True,
        ra_hours=1.5,
        declination=12.0,
        equatorial_system=1,
        slewing=False,
        tracking_rate=0,
        site_latitude=None,
        site_longitude=None,
        can_slew=True,
        can_slew_async=True,
        can_abort_slew=True,
        expose_abort_method=True,
    ):
        self.Connected = connected
        self.RightAscension = ra_hours
        self.Declination = declination
        self.EquatorialSystem = equatorial_system
        self.Slewing = slewing
        self.Tracking = True
        self.TrackingRate = tracking_rate
        self.CanSlew = can_slew
        self.CanSlewAsync = can_slew_async
        self.CanAbortSlew = can_abort_slew
        self.slew_calls = []
        self.abort_calls = 0
        if site_latitude is not None:
            self.SiteLatitude = site_latitude
        if site_longitude is not None:
            self.SiteLongitude = site_longitude
        if expose_abort_method:
            self.AbortSlew = lambda: setattr(self, "abort_calls", self.abort_calls + 1)

    def SlewToCoordinates(self, ra_hours, declination):
        self.slew_calls.append(("sync", ra_hours, declination))

    def SlewToCoordinatesAsync(self, ra_hours, declination):
        self.slew_calls.append(("async", ra_hours, declination))


class AscomMountTests(unittest.TestCase):
    def test_read_snapshot_normalizes_coordinates(self):
        telescope = _FakeTelescope(
            ra_hours=25.25,
            declination=95.0,
            equatorial_system=2,
            tracking_rate=2,
            site_latitude=91.2,
            site_longitude=181.5,
        )

        with patch("astroclocks.ascom_mount._require_ascom", return_value=object()):
            snapshot = ascom_mount.read_snapshot(
                telescope,
                "ASCOM.Test.Driver",
                "Test mount",
            )

        self.assertEqual(snapshot.driver_id, "ASCOM.Test.Driver")
        self.assertEqual(snapshot.driver_name, "Test mount")
        self.assertAlmostEqual(snapshot.ra_hours, 1.25)
        self.assertEqual(snapshot.declination, 90.0)
        self.assertEqual(snapshot.equatorial_system, 2)
        self.assertFalse(snapshot.slewing)
        self.assertTrue(snapshot.tracking)
        self.assertEqual(snapshot.tracking_rate, 2)
        self.assertEqual(snapshot.site_latitude, 90.0)
        self.assertAlmostEqual(snapshot.site_longitude, -178.5)

    def test_read_snapshot_rejects_disconnected_mount(self):
        telescope = _FakeTelescope(connected=False)

        with patch("astroclocks.ascom_mount._require_ascom", return_value=object()):
            with self.assertRaises(ascom_mount.AscomMountError):
                ascom_mount.read_snapshot(telescope, "ASCOM.Test.Driver", "Test mount")

    def test_read_capabilities_reads_supported_actions(self):
        telescope = _FakeTelescope(
            can_slew=False,
            can_slew_async=True,
            can_abort_slew=False,
            expose_abort_method=False,
        )

        with patch("astroclocks.ascom_mount._require_ascom", return_value=object()):
            capabilities = ascom_mount.read_capabilities(telescope)

        self.assertFalse(capabilities.can_slew)
        self.assertTrue(capabilities.can_slew_async)
        self.assertFalse(capabilities.can_abort_slew)

    def test_read_capabilities_falls_back_to_abort_method_when_property_is_missing(self):
        telescope = _FakeTelescope(can_abort_slew=False, expose_abort_method=True)

        with patch("astroclocks.ascom_mount._require_ascom", return_value=object()):
            capabilities = ascom_mount.read_capabilities(telescope)

        self.assertTrue(capabilities.can_abort_slew)

    def test_slew_to_coordinates_prefers_async_when_available(self):
        telescope = _FakeTelescope(can_slew=True, can_slew_async=True)

        with patch("astroclocks.ascom_mount._require_ascom", return_value=object()):
            ascom_mount.slew_to_coordinates(telescope, 25.25, 91.2)

        self.assertEqual(telescope.slew_calls, [("async", 1.25, 90.0)])

    def test_abort_slew_rejects_unsupported_mounts(self):
        telescope = _FakeTelescope(can_abort_slew=False, expose_abort_method=False)

        with patch("astroclocks.ascom_mount._require_ascom", return_value=object()):
            with self.assertRaises(ascom_mount.AscomMountError):
                ascom_mount.abort_slew(telescope)


if __name__ == "__main__":
    unittest.main()
