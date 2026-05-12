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
        tracking_rate=0,
        site_latitude=None,
        site_longitude=None,
    ):
        self.Connected = connected
        self.RightAscension = ra_hours
        self.Declination = declination
        self.EquatorialSystem = equatorial_system
        self.Tracking = True
        self.TrackingRate = tracking_rate
        if site_latitude is not None:
            self.SiteLatitude = site_latitude
        if site_longitude is not None:
            self.SiteLongitude = site_longitude


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
        self.assertTrue(snapshot.tracking)
        self.assertEqual(snapshot.tracking_rate, 2)
        self.assertEqual(snapshot.site_latitude, 90.0)
        self.assertAlmostEqual(snapshot.site_longitude, -178.5)

    def test_read_snapshot_rejects_disconnected_mount(self):
        telescope = _FakeTelescope(connected=False)

        with patch("astroclocks.ascom_mount._require_ascom", return_value=object()):
            with self.assertRaises(ascom_mount.AscomMountError):
                ascom_mount.read_snapshot(telescope, "ASCOM.Test.Driver", "Test mount")


if __name__ == "__main__":
    unittest.main()
