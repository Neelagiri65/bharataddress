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
