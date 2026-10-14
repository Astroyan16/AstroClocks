"""Verified HTTPS using the native Windows certificate chain validator.

Use explicit contexts so catalog workers get the same verification as the
main process, without globally patching ssl or installing certificates.
"""

import socket
import ssl
import sys
import urllib.request

if sys.platform == "win32":
    import truststore


def create_https_context():
    """Require a trusted certificate chain and a matching server hostname."""
    if sys.platform == "win32":
        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    return ssl.create_default_context()


def urlopen(url, data=None, timeout=socket._GLOBAL_DEFAULT_TIMEOUT):
    """Open a URL with verified TLS, including HTTPS redirects/downloads."""
    return urllib.request.urlopen(
        url, data=data, timeout=timeout, context=create_https_context()
    )
