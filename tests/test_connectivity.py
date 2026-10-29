import ssl
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from astroclocks.connectivity import check_services, probe_service, probe_url, service_online


class ServiceProbeTests(unittest.TestCase):
    def setUp(self):
        configured = patch("astroclocks.connectivity.has_meteofrance_application_id", return_value=True)
        configured.start()
        self.addCleanup(configured.stop)

    def test_unconfigured_optional_api_is_not_probed(self):
        services = {
            "metar": ("METAR", ("metar-url",)),
            "meteofrance": ("Météo-France API", ("mf-url",)),
        }
        with patch("astroclocks.connectivity.SERVICES", services), patch(
            "astroclocks.connectivity.has_meteofrance_application_id", return_value=False
        ), patch("astroclocks.connectivity.probe_service", return_value=(True, "HTTP 200", True)) as probe:
            online, results = check_services()
        self.assertTrue(online)
        self.assertEqual(results["meteofrance"], (None, "", False))
        probe.assert_called_once_with(("metar-url",))

    def test_configured_optional_api_is_probed(self):
        with patch("astroclocks.connectivity.SERVICES", {"meteofrance": ("MF", ("mf-url",))}), patch(
            "astroclocks.connectivity.probe_service", return_value=(False, "HTTP 503", True)
        ) as probe:
            online, results = check_services()
        self.assertTrue(online)
        self.assertFalse(results["meteofrance"][0])
        probe.assert_called_once_with(("mf-url",))

    def test_tls_failure_is_unavailable_without_unverified_retry(self):
        with patch("astroclocks.connectivity.urlopen", side_effect=ssl.SSLCertVerificationError("invalid")) as open_url:
            available, detail, reachable = probe_url("https://example.org/")
        self.assertFalse(available)
        self.assertFalse(reachable)
        self.assertIn("invalid", detail)
        open_url.assert_called_once()
        self.assertEqual(open_url.call_args.args[0].method, "HEAD")
        self.assertEqual(open_url.call_args.kwargs["timeout"], 4)

    def test_authentication_error_still_proves_reachability(self):
        for status in (401, 403, 405):
            with self.subTest(status=status), patch(
                "astroclocks.connectivity.urlopen", side_effect=HTTPError("url", status, "refused", {}, None)
            ):
                self.assertEqual(probe_url("https://example.org/"), (True, f"HTTP {status}", True))

    def test_server_failure_does_not_mean_internet_is_down(self):
        with patch("astroclocks.connectivity.urlopen", side_effect=HTTPError("url", 503, "down", {}, None)):
            self.assertEqual(probe_url("https://example.org/"), (False, "HTTP 503", True))
        with patch("astroclocks.connectivity.SERVICES", {"simbad": ("SIMBAD", ("url",))}), patch(
            "astroclocks.connectivity.probe_service", return_value=(False, "HTTP 503", True)
        ) as probe:
            online, results = check_services()
        self.assertTrue(online)
        self.assertFalse(results["simbad"][0])
        probe.assert_called_once_with(("url",))

    def test_mirror_is_used_when_primary_fails(self):
        with patch("astroclocks.connectivity.probe_url", side_effect=[(False, "timeout", False), (True, "HTTP 200", True)]) as probe:
            available, detail, reachable = probe_service(("primary", "mirror"))
        self.assertTrue(available)
        self.assertTrue(reachable)
        self.assertIn("mirror", detail)
        self.assertEqual(probe.call_count, 2)

    def test_independent_internet_fallback_when_all_services_fail(self):
        with patch("astroclocks.connectivity.SERVICES", {"simbad": ("SIMBAD", ("url",))}), patch(
            "astroclocks.connectivity.probe_service", side_effect=[(False, "timeout", False), (True, "HTTP 200", True)]
        ):
            online, results = check_services()
        self.assertTrue(online)
        self.assertFalse(results["simbad"][0])

    def test_total_disconnection(self):
        with patch("astroclocks.connectivity.probe_service", return_value=(False, "timeout", False)):
            online, results = check_services()
        self.assertFalse(online)
        self.assertTrue(all(not value[0] for value in results.values()))

    def test_service_states_are_independent_of_general_internet(self):
        app = SimpleNamespace(network_online=True, service_status={"simbad": False, "imcce": True})
        self.assertFalse(service_online(app, "simbad"))
        self.assertTrue(service_online(app, "imcce"))
        self.assertIsNone(service_online(app, "aladin"))
