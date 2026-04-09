"""v0.4 issue #3: vernacular mapping coverage and cross-file dedup contract.

Locks two facts:
1. Each mapping file meets its v0.4 minimum entry count.
2. No surface key appears in more than one *language* file. (Common is exempt;
   common always loads, so a language file repeating a common key would be
   redundant but not incorrect — we still ban it to keep maintenance honest.)

Total target across all files: >=400 entries.
"""

from __future__ import annotations

import json
from importlib.resources import files

LANG_FILES = ("hi", "ta", "te", "kn", "bn", "ml")

# v0.4 minimums per the PRD acceptance criteria.
MIN_ENTRIES = {
    "common": 80,
    "hi": 40,
    "ta": 40,
    "te": 40,
    "kn": 40,
    "bn": 40,
    "ml": 40,
}
MIN_TOTAL = 400


def _load(name: str) -> dict[str, str]:
    raw = (
        (files("bharataddress.data") / "mappings" / f"{name}.json")
        .read_text(encoding="utf-8")
    )
    table = json.loads(raw)
    return {k: v for k, v in table.items() if not k.startswith("_")}


def test_per_file_minimum_entry_counts() -> None:
    shortfalls = []
    for name, minimum in MIN_ENTRIES.items():
        n = len(_load(name))
        if n < minimum:
            shortfalls.append(f"{name}: {n} < {minimum}")
    assert not shortfalls, "v0.4 vernacular minimums not met:\n  " + "\n  ".join(shortfalls)


def test_total_entries_at_least_400() -> None:
    total = sum(len(_load(n)) for n in ("common", *LANG_FILES))
    assert total >= MIN_TOTAL, f"v0.4 total vernacular entries {total} < {MIN_TOTAL}"


def test_no_cross_language_duplicates() -> None:
    """A surface key may appear in common + at most one language file, never in
    two language files. Cross-language collisions are real (e.g. 'para' is both
    Bengali neighbourhood and Malayalam landmark) — when they happen, the term
    must be promoted to common.json or one language wins via documented choice."""
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for lang in LANG_FILES:
        for key in _load(lang):
            if key in seen:
                collisions.append(f"{key!r}: in both {seen[key]}.json and {lang}.json")
            else:
                seen[key] = lang
    assert not collisions, "cross-language duplicates found:\n  " + "\n  ".join(collisions)


def test_common_does_not_redundantly_define_language_keys() -> None:
    """If a key is in common.json, it should not also live in a language file —
    common always loads, so the language entry is dead code. Catches drift
    introduced by future expansions."""
    common_keys = set(_load("common"))
    redundant: list[str] = []
    for lang in LANG_FILES:
        for key in _load(lang):
            if key in common_keys:
                redundant.append(f"{key!r} in both common.json and {lang}.json")
    assert not redundant, "redundant keys (already in common):\n  " + "\n  ".join(redundant)
