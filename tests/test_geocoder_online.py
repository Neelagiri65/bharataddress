"""Tests for the online Nominatim path of geocoder.geocode.

Real network is never hit. urllib.request.urlopen is monkeypatched and the
SQLite cache is redirected to a tmp_path file.
"""
from __future__ import annotations

import io
import json
from pathlib import Path

from bharataddress import _geocode_cache, geocoder, parser


def _stub_urlopen(payload):
    class _Resp:
        status = 200
        def __init__(self, body):
            self._body = body
        def read(self):
            return json.dumps(self._body).encode("utf-8")
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    calls = {"n": 0, "ua": None}

    def _fake(req, timeout=None):
        calls["n"] += 1
        try:
            calls["ua"] = req.get_header("User-agent")
        except Exception:
            calls["ua"] = None
        return _Resp(payload)

    return _fake, calls


def _redirect_cache(monkeypatch, tmp_path):
    p = tmp_path / "geocode.sqlite"
    monkeypatch.setattr(_geocode_cache, "default_path", lambda: p)
    return p


def test_geocode_offline_default_no_network(monkeypatch, tmp_path):
    _redirect_cache(monkeypatch, tmp_path)
    def _boom(*a, **k):
        raise AssertionError("network call should not happen with online=False")
    monkeypatch.setattr(geocoder.urllib.request, "urlopen", _boom)

    p = parser.parse("M G Road, Bangalore 560001")
    # offline path may or may not return centroid depending on dataset; but it
    # must NOT raise.
    geocoder.geocode(p, online=False)


def test_geocode_online_hits_nominatim_and_caches(monkeypatch, tmp_path):
    cache_path = _redirect_cache(monkeypatch, tmp_path)
    fake, calls = _stub_urlopen([{"lat": "12.97", "lon": "77.59"}])
    monkeypatch.setattr(geocoder.urllib.request, "urlopen", fake)
    # zero rate limit so test is fast
    monkeypatch.setattr(geocoder, "_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(geocoder, "_last_call_ts", 0.0)

    # Use a parsed address with a pincode whose centroid is missing — force
    # the online path. We fabricate a ParsedAddress directly to skip the
    # offline centroid lookup entirely.
    p = parser.ParsedAddress(raw="x", cleaned="x", city="Bangalore", state="Karnataka", pincode="999999")

    result = geocoder.geocode(p, online=True)
    assert result == (12.97, 77.59)
    assert calls["n"] == 1
    assert calls["ua"] and "bharataddress" in calls["ua"].lower()
    assert cache_path.exists()

    # Second call: cache hit, no extra network call.
    result2 = geocoder.geocode(p, online=True)
    assert result2 == (12.97, 77.59)
    assert calls["n"] == 1


def test_geocode_online_negative_cache(monkeypatch, tmp_path):
    _redirect_cache(monkeypatch, tmp_path)
    fake, calls = _stub_urlopen([])  # empty result
    monkeypatch.setattr(geocoder.urllib.request, "urlopen", fake)
    monkeypatch.setattr(geocoder, "_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(geocoder, "_last_call_ts", 0.0)

    p = parser.ParsedAddress(raw="x", cleaned="x", city="Nowhere", pincode="888888")
    assert geocoder.geocode(p, online=True) is None
    assert calls["n"] == 1
    # Second call: negative-cached, no network.
    assert geocoder.geocode(p, online=True) is None
    assert calls["n"] == 1


def test_geocode_online_network_error_returns_none(monkeypatch, tmp_path):
    _redirect_cache(monkeypatch, tmp_path)
    def _err(*a, **k):
        raise OSError("no network")
    monkeypatch.setattr(geocoder.urllib.request, "urlopen", _err)
    monkeypatch.setattr(geocoder, "_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(geocoder, "_last_call_ts", 0.0)

    p = parser.ParsedAddress(raw="x", cleaned="x", city="Anywhere", pincode="777777")
    assert geocoder.geocode(p, online=True) is None


def test_parse_geocode_kwarg_populates_latlng(monkeypatch, tmp_path):
    _redirect_cache(monkeypatch, tmp_path)
    fake, calls = _stub_urlopen([{"lat": "28.61", "lon": "77.23"}])
    monkeypatch.setattr(geocoder.urllib.request, "urlopen", fake)
    monkeypatch.setattr(geocoder, "_MIN_INTERVAL_S", 0.0)
    monkeypatch.setattr(geocoder, "_last_call_ts", 0.0)

    # Use an address with a pincode missing from the centroid table to force
    # the online path. 999999 is not a real pincode so the lookup returns None.
    p = parser.parse("Connaught Place, New Delhi 999999", geocode=True)
    assert p.latitude == 28.61
    assert p.longitude == 77.23
