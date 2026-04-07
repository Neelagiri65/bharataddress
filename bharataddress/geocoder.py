"""Pincode-centroid geocoding + reverse geocoding.

Pincode → (lat, lng) and (lat, lng) → nearest pincode + DIGIPIN.

The shipped ``pincodes.json`` does not currently carry centroids; the parser's
DIGIPIN auto-fill branch is dormant for the same reason. ``geocode`` therefore
returns ``None`` for any pincode whose record lacks a ``latitude`` /
``longitude`` field. As soon as a future dataset refresh adds centroids, this
module starts returning real coordinates with no API change.

``reverse_geocode`` always returns a DIGIPIN (DIGIPIN is pure math), and
returns the nearest pincode only if centroids are available in the dataset.

No network calls. No external services. All deterministic.
"""
from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from . import digipin as _digipin
from . import pincode as _pincode
from .parser import ParsedAddress


def _record_latlng(rec: dict | None) -> tuple[float, float] | None:
    if not rec:
        return None
    lat = rec.get("latitude")
    lng = rec.get("longitude")
    if lat is None or lng is None:
        return None
    try:
        return float(lat), float(lng)
    except (TypeError, ValueError):
        return None


def geocode(parsed: ParsedAddress) -> tuple[float, float] | None:
    """Return ``(lat, lng)`` from the pincode centroid, or ``None``.

    Resolution is the centre of the pincode's service area — typically several
    km, occasionally tens of km. This is *not* a building-level geocode.
    """
    if not parsed.pincode:
        return None
    return _record_latlng(_pincode.lookup(parsed.pincode))


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371.0
    p1, p2 = radians(lat1), radians(lat2)
    dp = radians(lat2 - lat1)
    dl = radians(lng2 - lng1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * r * asin(sqrt(a))


def reverse_geocode(lat: float, lng: float) -> dict:
    """Return ``{"digipin": ..., "pincode": ..., "distance_km": ...}``.

    ``digipin`` is always populated (it's pure math). ``pincode`` is populated
    only if the shipped dataset has centroids; otherwise ``None``.
    """
    out: dict = {"digipin": None, "pincode": None, "distance_km": None}
    try:
        out["digipin"] = _digipin.encode(lat, lng)
    except ValueError:
        out["digipin"] = None

    table = _pincode._table()  # noqa: SLF001 — internal access is fine in-package
    nearest_pin: str | None = None
    nearest_d = float("inf")
    for pin, rec in table.items():
        ll = _record_latlng(rec)
        if ll is None:
            continue
        d = _haversine_km(lat, lng, ll[0], ll[1])
        if d < nearest_d:
            nearest_d = d
            nearest_pin = pin
    if nearest_pin is not None:
        out["pincode"] = nearest_pin
        out["distance_km"] = round(nearest_d, 3)
    return out
