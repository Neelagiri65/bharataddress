"""Lazy-loaded pincode lookup table.

The dataset ships embedded in bharataddress/data/pincodes.json. First call
parses it; subsequent calls reuse the cached dict. No network, no I/O after
first use.
"""
from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import TypedDict


class PincodeRecord(TypedDict):
    pincode: str
    district: str
    city: str
    state: str
    offices: list[str]


@lru_cache(maxsize=1)
def _table() -> dict[str, PincodeRecord]:
    raw = (files("bharataddress.data") / "pincodes.json").read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def _localities_table() -> dict[str, list[str]]:
    raw = (files("bharataddress.data") / "localities.json").read_text(encoding="utf-8")
    return json.loads(raw)


@lru_cache(maxsize=1)
def _city_index() -> dict[str, tuple[str, str]]:
    """city name (lowercased) -> (district, state).

    Derived by inverting the shipped India Post directory. When a city name
    spans several (district, state) pairs (e.g. duplicated town names across
    states), the modal pair wins — the one backing the most pincodes. Built
    once, lazily, from the already-cached pincode table: no new data file, no
    network, no extra dependency.
    """
    from collections import Counter

    counts: dict[str, Counter] = {}
    for rec in _table().values():
        city = (rec.get("city") or "").strip().lower()
        if not city:
            continue
        pair = (rec.get("district") or "", rec.get("state") or "")
        if not pair[1]:
            continue
        counts.setdefault(city, Counter())[pair] += 1
    return {city: c.most_common(1)[0][0] for city, c in counts.items()}


def city_to_admin(name: str | None) -> tuple[str, str] | None:
    """Resolve a city/town name to its modal ``(district, state)``.

    Returns ``None`` if the name is not a known city in the shipped directory.
    Used to recover district/state on addresses that carry no pincode.
    """
    if not name:
        return None
    return _city_index().get(name.strip().lower())


def is_known_city(name: str | None) -> bool:
    """True if ``name`` (case-insensitive) is a city in the shipped directory."""
    if not name:
        return False
    return name.strip().lower() in _city_index()


def lookup(pincode: str | None) -> PincodeRecord | None:
    if not pincode:
        return None
    return _table().get(pincode)


def known_localities(pincode: str | None) -> list[str]:
    """Return the lowercased list of post-office / locality names known for a pincode."""
    if not pincode:
        return []
    return _localities_table().get(pincode, [])


def is_valid(pincode: str | None) -> bool:
    return lookup(pincode) is not None


def size() -> int:
    return len(_table())
