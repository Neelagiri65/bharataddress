"""Fuzzy similarity score for two Indian addresses.

``similarity(a, b)`` returns a float in [0.0, 1.0]. Inputs may be raw strings
or already-parsed ``ParsedAddress`` instances. The score weights signals by
how reliable they are for India:

- pincode match — strongest signal (0.40)
- city match — 0.20
- state match — 0.10
- locality token overlap (Jaccard, post-normalisation) — 0.20
- building number / building name overlap — 0.10

Normalisation handles the obvious Indian aliases:

- Bengaluru / Bangalore, Mumbai / Bombay, Chennai / Madras, Kolkata / Calcutta,
  Gurgaon / Gurugram, Pune / Poona
- Rd / Road, Ngr / Nagar, Clny / Colony, Apt / Apartment, Bldg / Building
- Mahatma Gandhi Road / MG Road, Subhash Chandra Bose Road / SC Bose Road

This is a heuristic, not a true entity-resolution model. It's good enough for
deduping CRM rows where you have ~10⁴–10⁶ records and want to flag obvious
duplicates without spinning up an ML pipeline.
"""
from __future__ import annotations

import re

from .parser import ParsedAddress, parse
from . import phonetic as _phonetic


# Shared with phonetic.py — single source of truth for canonical aliases.
_CITY_ALIASES = _phonetic.canonical_aliases()

_TOKEN_ALIASES = {
    "rd": "road",
    "st": "street",
    "ln": "lane",
    "ngr": "nagar",
    "clny": "colony",
    "apt": "apartment",
    "apts": "apartment",
    "bldg": "building",
    "blk": "block",
    "sec": "sector",
    "ph": "phase",
    "extn": "extension",
    "extns": "extension",
    "soc": "society",
    "mg": "mahatmagandhi",
    "sc": "subhashchandra",
    "jln": "jawaharlalnehru",
    "jl": "jawaharlalnehru",
}

_MULTIWORD_ALIASES = {
    "mahatma gandhi": "mahatmagandhi",
    "subhash chandra bose": "subhashchandra",
    "subhash chandra": "subhashchandra",
    "jawaharlal nehru": "jawaharlalnehru",
    "indira gandhi": "indiragandhi",
    "rajiv gandhi": "rajivgandhi",
}

_PUNCT_RE = re.compile(r"[^\w\s]+")
_WS_RE = re.compile(r"\s+")


def _normalise_text(s: str | None) -> str:
    if not s:
        return ""
    t = s.lower()
    for k, v in _MULTIWORD_ALIASES.items():
        t = t.replace(k, v)
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


def _tokens(s: str | None) -> set[str]:
    norm = _normalise_text(s)
    if not norm:
        return set()
    out = set()
    for tok in norm.split():
        out.add(_TOKEN_ALIASES.get(tok, tok))
    return out


def _normalise_city(s: str | None) -> str:
    n = _normalise_text(s)
    return _CITY_ALIASES.get(n, n)


def _as_parsed(addr: str | ParsedAddress) -> ParsedAddress:
    if isinstance(addr, ParsedAddress):
        return addr
    return parse(addr)


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def similarity(addr1: str | ParsedAddress, addr2: str | ParsedAddress) -> float:
    """Return a similarity score in [0.0, 1.0] between two addresses."""
    p1 = _as_parsed(addr1)
    p2 = _as_parsed(addr2)

    score = 0.0

    # Pincode — strongest signal.
    if p1.pincode and p2.pincode:
        score += 0.40 if p1.pincode == p2.pincode else 0.0

    # City (with alias normalisation).
    c1, c2 = _normalise_city(p1.city), _normalise_city(p2.city)
    if c1 and c2:
        score += 0.20 if c1 == c2 else 0.0

    # State.
    s1, s2 = _normalise_text(p1.state), _normalise_text(p2.state)
    if s1 and s2:
        score += 0.10 if s1 == s2 else 0.0

    # Locality + sub-locality token overlap.
    loc1 = _tokens(p1.locality) | _tokens(p1.sub_locality)
    loc2 = _tokens(p2.locality) | _tokens(p2.sub_locality)
    score += 0.20 * _jaccard(loc1, loc2)

    # Building number / name.
    b1 = _tokens(p1.building_name) | ({p1.building_number} if p1.building_number else set())
    b2 = _tokens(p2.building_name) | ({p2.building_number} if p2.building_number else set())
    score += 0.10 * _jaccard(b1, b2)

    return round(min(score, 1.0), 3)
