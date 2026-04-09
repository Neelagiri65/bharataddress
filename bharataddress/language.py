"""Language resolution and per-language vernacular mapping loader.

v0.4 introduces per-language vernacular term files under
``bharataddress/data/mappings/``. This module is the single resolver:

* ``from_pincode(pin)`` — pincode -> state -> primary language(s) for that state.
* ``load_mappings(lang_codes)`` — merges ``common.json`` (always) with the
  requested language files into a single ``{token: normalised}`` dict.

The merge is "first writer wins": ``common.json`` entries are loaded first; a
language file may add new tokens but does not override common ones. Cross-file
duplicates inside the language tier are deterministic in language-code order.

Pure data, zero dependencies, fully offline.
"""
from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files

from . import pincode as _pin

# The six v0.4 language codes. Order matters only for determinism in merges.
SUPPORTED_LANGUAGES: tuple[str, ...] = ("hi", "ta", "te", "kn", "bn", "ml")


@lru_cache(maxsize=1)
def _state_languages() -> dict[str, list[str]]:
    raw = (files("bharataddress.data") / "state_languages.json").read_text(encoding="utf-8")
    table = json.loads(raw)
    return {k: v for k, v in table.items() if not k.startswith("_")}


@lru_cache(maxsize=8)
def _load_one(name: str) -> dict[str, str]:
    """Load a single mapping file by basename (e.g. 'common', 'ta')."""
    raw = (
        (files("bharataddress.data") / "mappings" / f"{name}.json")
        .read_text(encoding="utf-8")
    )
    table = json.loads(raw)
    return {k.lower(): v for k, v in table.items() if not k.startswith("_")}


def from_pincode(pin: str | None) -> list[str]:
    """Return the language code(s) associated with the state for ``pin``.

    Returns an empty list if the pincode is unknown or the state has no
    v0.4-supported language. Callers should always layer ``common.json`` on top
    via ``load_mappings``.
    """
    rec = _pin.lookup(pin)
    if rec is None:
        return []
    return list(_state_languages().get(rec["state"], []))


def load_mappings(lang_codes: list[str] | tuple[str, ...] | None) -> dict[str, str]:
    """Return the merged ``{token: normalised}`` dict for the requested languages.

    ``common.json`` is always included. Unknown / unsupported language codes are
    silently ignored (so ``from_pincode`` for an unknown state still produces a
    valid common-only mapping). Common entries take precedence over per-language
    entries with the same key, so a language file cannot accidentally redefine a
    pan-Indian term.
    """
    merged: dict[str, str] = {}
    # Per-language tier first, then common overlays it.
    for code in lang_codes or ():
        if code in SUPPORTED_LANGUAGES:
            for k, v in _load_one(code).items():
                merged.setdefault(k, v)
    for k, v in _load_one("common").items():
        merged[k] = v
    return merged
