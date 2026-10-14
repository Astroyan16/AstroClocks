"""Lightweight, approximate V magnitudes from existing GCRS vectors in AU.

Planets: Mallama & Hilton (2018), https://arxiv.org/abs/1808.01973
Moon: Krisciunas & Schaefer (1991), eq. 9, with distance scaling:
https://articles.adsabs.harvard.edu/pdf/1991PASP..103.1033K
Sun: NASA V(1,0)=-26.74, https://nssdc.gsfc.nasa.gov/planetary/factsheet/sunfact.html
Pole directions: Archinal et al. (2011), J2000 equatorial axes:
https://aa.usno.navy.mil/downloads/reports/Archinaletal2011a.pdf

No atmosphere, eclipses, occultations, Mars albedo/seasonal corrections, or
short-term weather variability. GCRS apparent vectors are adequate for these
estimates; this is not a replacement for full physical ephemerides.
"""

import math
from astropy import units as u

AU_KM = 149597870.7


def _norm(vector):
    return math.sqrt(sum(x*x for x in vector))


def _latitude(vector, pole):
    ra, dec = map(math.radians, pole)
    axis = math.cos(dec)*math.cos(ra), math.cos(dec)*math.sin(ra), math.sin(dec)
    sine = sum(a*b for a, b in zip(vector, axis)) / _norm(vector)
    return math.degrees(math.asin(max(-1, min(1, sine))))


def estimate_visual_magnitude(name, body_vector, sun_vector, year=2026.0):
    """Return an above-atmosphere estimate or None outside supported ranges."""
    delta = _norm(body_vector)
    if not math.isfinite(delta) or delta <= 0:
        return None
    if name == "Sun":
        return -26.74 + 5*math.log10(delta)
    heliocentric = tuple(b-s for b, s in zip(body_vector, sun_vector))
    radius = _norm(heliocentric)
    if radius <= 0 or not math.isfinite(radius):
        return None
    cosine = sum(b*h for b, h in zip(body_vector, heliocentric)) / (delta*radius)
    alpha = math.degrees(math.acos(max(-1, min(1, cosine))))
    distance_term = 5*math.log10(radius*delta)
    if name == "Moon":
        # Reference full Moon at mean Earth-Moon distance; no eclipse model.
        if alpha > 170:
            return None
        return -12.73 + .026*alpha + 4e-9*alpha**4 + 5*math.log10(radius*delta*AU_KM/384400)
    if name == "Mercury":
        if alpha > 170:
            return None
        coefficients = (-.613, .063280, -.0016336, .000033644, -3.4265e-7, 1.6893e-9, -3.0334e-12)
        correction = sum(c*alpha**i for i, c in enumerate(coefficients))
    elif name == "Venus":
        if alpha >= 179:
            return None
        correction = (-4.384 - .001044*alpha + .0003687*alpha**2 - .000002814*alpha**3
                      + 8.938e-9*alpha**4) if alpha <= 163.7 else (236.05828-2.81914*alpha+.00839034*alpha**2)
    elif name == "Mars":
        if alpha > 50:
            return None
        correction = -1.601 + .02267*alpha - .0001302*alpha**2
    elif name == "Jupiter":
        if alpha > 12:
            return None
        correction = -9.395 - .00037*alpha + .000616*alpha**2
    elif name == "Saturn":
        if alpha > 6.5:
            return None
        centuries = (year-2000)/100
        pole = (40.589-.036*centuries, 83.537-.004*centuries)
        beta_e = _latitude(tuple(-b for b in body_vector), pole)
        beta_s = _latitude(tuple(-h for h in heliocentric), pole)
        beta = math.sqrt(beta_e*beta_s) if beta_e*beta_s > 0 else 0
        if beta > 27:
            return None
        inclination = math.sin(math.radians(beta))
        correction = -8.914 - 1.825*inclination + .026*alpha - .378*inclination*math.exp(-2.25*alpha)
    elif name == "Uranus":
        if alpha > 3.2:
            return None
        pole = (257.311, -15.175)
        latitudes = (_latitude(tuple(-b for b in body_vector), pole),
                     _latitude(tuple(-h for h in heliocentric), pole))
        phi = sum(abs(math.degrees(math.atan(math.tan(math.radians(lat))/(1-.0022927)**2)))
                  for lat in latitudes)/2
        correction = -7.110 - .00084*phi
    elif name == "Neptune":
        if alpha > 1.9:
            return None
        correction = -6.89 if year < 1980 else (-6.89-.0055*(year-1980) if year < 2000 else -7.0)
    else:
        return None
    return distance_term + correction


def local_solar_information(name, coordinates, sun_coordinates, year):
    """Extract Astropy's existing distance; add only scalar geometry/math."""
    body_vector = tuple(float(x) for x in coordinates.cartesian.xyz.to_value(u.au))
    sun_vector = tuple(float(x) for x in sun_coordinates.cartesian.xyz.to_value(u.au))
    distance = _norm(body_vector)
    return {
        "magnitude": estimate_visual_magnitude(name, body_vector, sun_vector, year),
        "magnitude_band": "V", "magnitude_estimated": True,
        "distance_au": distance,
        "distance_km": distance*AU_KM if name == "Moon" else None,
        "distance_estimated": True,
    }
