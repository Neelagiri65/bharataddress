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

import json
import time
import urllib.parse
import urllib.request
from math import asin, cos, radians, sin, sqrt

from . import _geocode_cache
from . import digipin as _digipin
from . import pincode as _pincode
from .parser import ParsedAddress

_NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
_USER_AGENT = "bharataddress/0.3.0 (+https://github.com/Neelagiri65/bharataddress)"
_MIN_INTERVAL_S = 1.0  # Nominatim ToS: <= 1 req/sec
_last_call_ts: float = 0.0


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


def _build_query(parsed: ParsedAddress) -> str:
    parts = [
        parsed.locality,
        parsed.sub_locality,
        parsed.city,
        parsed.district,
        parsed.state,
        parsed.pincode,
        "India",
    ]
    return ", ".join(p for p in parts if p)


def _nominatim_lookup(query: str, timeout: float) -> tuple[float, float] | None:
    """Hit Nominatim once. Returns ``(lat, lng)`` or ``None``. Never raises."""
    global _last_call_ts
    elapsed = time.monotonic() - _last_call_ts
    if elapsed < _MIN_INTERVAL_S:
        time.sleep(_MIN_INTERVAL_S - elapsed)
    _last_call_ts = time.monotonic()

    params = urllib.parse.urlencode({"q": query, "format": "json", "limit": "1"})
    url = f"{_NOMINATIM_URL}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return None
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None
    if not data:
        return None
    try:
        return float(data[0]["lat"]), float(data[0]["lon"])
    except (KeyError, ValueError, TypeError):
        return None


def geocode(
    parsed: ParsedAddress,
    *,
    online: bool = False,
    timeout: float = 5.0,
) -> tuple[float, float] | None:
    """Return ``(lat, lng)``, or ``None``.

    Default (``online=False``) uses the embedded pincode centroid only — no
    network. ``online=True`` falls back to Nominatim with SQLite caching for
    pincodes whose centroid is unknown. Centroid hits never trigger a network
    call regardless of the flag (saves rate-limit budget).

    TODO: ``force_online=True`` kwarg for v0.4 — override centroid when caller
    knows it's wrong.
    """
    if parsed.pincode:
        ll = _record_latlng(_pincode.lookup(parsed.pincode))
        if ll is not None:
            return ll
    if not online:
        return None

    query = _build_query(parsed)
    if not query.strip(", "):
        return None

    cached = _geocode_cache.get(query)
    if cached != "miss":
        return cached  # tuple, or None for negative cache

    result = _nominatim_lookup(query, timeout)
    if result is None:
        _geocode_cache.put(query, None, None, "nominatim")
    else:
        _geocode_cache.put(query, result[0], result[1], "nominatim")
    return result


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
