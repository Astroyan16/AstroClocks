"""Independent HTTPS reachability checks; no credentials or API queries."""
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.request import Request

from astroclocks.network import urlopen
from astroclocks.secure_store import has_meteofrance_application_id, SecureStoreUnavailable

# Multiple URLs in a row are alternative mirrors, not cumulative requirements.
SERVICES = {
    "aladin": ("Aladin", ("https://aladin.cds.unistra.fr/",)),
    "simbad": ("SIMBAD", ("https://simbad.cds.unistra.fr/",)),
    "sesame": ("CDS Sesame", ("https://cds.unistra.fr/cgi-bin/Sesame",)),
    "vizier": ("VizieR / WDS", ("https://vizier.cds.unistra.fr/",)),
    "orb6": ("ORB6", ("https://crf.usno.navy.mil/", "https://www.astro.gsu.edu/")),
    "imcce": ("IMCCE / Miriade", ("https://ssp.imcce.fr/",)),
    "metar": ("METAR", ("https://aviationweather.gov/",)),
    # The API root closes connections; probe the endpoint used for station lookup.
    "meteofrance": ("Météo-France API", ("https://public-api.meteofrance.fr/public/DPObs/liste-stations?format=csv",)),
    "updates": ("GitHub", ("https://api.github.com/",)),
}
INTERNET_URLS = ("https://www.microsoft.com/", "https://www.cloudflare.com/")
CHECK_INTERVAL_MS = 30_000


def service_configured(name):
    """Only the optional Météo-France API requires local configuration."""
    if name != "meteofrance":
        return True
    try:
        return has_meteofrance_application_id()
    except (OSError, SecureStoreUnavailable):
        return False


def probe_url(url, timeout=4):
    """Verify DNS, TLS and an HTTP response, without downloading a body.

    4xx proves the server can be reached, but does not validate API access.
    5xx means the service cannot currently handle requests.
    """
    try:
        with urlopen(Request(url, method="HEAD"), timeout=timeout) as response:
            status = response.status
        return status < 500, f"HTTP {status}", True
    except HTTPError as exc:
        return exc.code < 500, f"HTTP {exc.code}", True
    except Exception as exc:
        return False, str(exc), False


def probe_service(urls):
    errors = []
    reachable = False
    for url in urls:
        online, detail, responded = probe_url(url)
        reachable = reachable or responded
        if online:
            return True, f"{url} — {detail}", True
        errors.append(f"{url} — {detail}")
    return False, "\n".join(errors), reachable


def check_services():
    with ThreadPoolExecutor(max_workers=len(SERVICES)) as pool:
        pending = {key: pool.submit(probe_service, urls) for key, (_, urls) in SERVICES.items()
                   if service_configured(key)}
        results = {key: future.result() for key, future in pending.items()}
    for key in SERVICES:
        if key not in results:
            results[key] = (None, "", False)
    # A reachable application service already proves Internet access.
    online = any(value[2] for value in results.values())
    if not online:
        _, _, online = probe_service(INTERNET_URLS)
    return online, results


def service_online(app, name):
    """Unknown services remain usable until the first confirmed failure."""
    states = getattr(app, "service_status", None)
    if states is None:
        return getattr(app, "network_online", None)
    return states.get(name)
