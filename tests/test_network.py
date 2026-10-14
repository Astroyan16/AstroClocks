import ssl
import sys
import unittest
from urllib.error import URLError
from urllib.request import Request
from unittest.mock import patch

from astroclocks import network


class NetworkTests(unittest.TestCase):
    def test_context_requires_chain_and_hostname_verification(self):
        context = network.create_https_context()
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)
        if sys.platform == "win32":
            import truststore
            self.assertIsInstance(context, truststore.SSLContext)

    def test_request_preserves_headers_body_timeout_and_verified_context(self):
        request = Request("https://simbad.cds.unistra.fr/", headers={"User-Agent": "AstroClocks"})
        with patch("astroclocks.network.urllib.request.urlopen") as opener:
            result = network.urlopen(request, data=b"query=test", timeout=12)
        self.assertIs(result, opener.return_value)
        args, kwargs = opener.call_args
        self.assertIs(args[0], request)
        self.assertEqual(kwargs["data"], b"query=test")
        self.assertEqual(kwargs["timeout"], 12)
        self.assertEqual(kwargs["context"].verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(kwargs["context"].check_hostname)

    def test_certificate_error_propagates_without_unverified_retry(self):
        error = URLError(ssl.SSLCertVerificationError(1, "untrusted issuer"))
        with patch("astroclocks.network.urllib.request.urlopen", side_effect=error) as opener:
            with self.assertRaises(URLError) as caught:
                network.urlopen("https://example.invalid/", timeout=1)
        self.assertIs(caught.exception, error)
        opener.assert_called_once()

    def test_other_platforms_keep_standard_verified_tls(self):
        with patch("astroclocks.network.sys.platform", "linux"):
            context = network.create_https_context()
        self.assertIsInstance(context, ssl.SSLContext)
        self.assertEqual(context.verify_mode, ssl.CERT_REQUIRED)
        self.assertTrue(context.check_hostname)


if __name__ == "__main__":
    unittest.main()
