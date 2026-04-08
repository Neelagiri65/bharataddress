"""Phonetic normalisation + fuzzy matching for Indian place names.

Hand-tuned alias map covering post-independence renames (Bombay/Mumbai,
Madras/Chennai, Calcutta/Kolkata, Bangalore/Bengaluru, Gurgaon/Gurugram,
...) plus common transliteration drift (Gudgaon, Bangalroe, Kolkatta).
``fuzzy_ratio`` uses rapidfuzz when available (optional dep
``pip install bharataddress[fuzzy]``) and falls back to stdlib ``difflib``.
Zero required dependencies, deterministic, no network.
"""
from __future__ import annotations

import difflib
import re

try:
    from rapidfuzz import fuzz as _rf_fuzz  # type: ignore

    _HAS_RAPIDFUZZ = True
except ImportError:  # pragma: no cover — exercised via monkeypatch in tests
    _rf_fuzz = None
    _HAS_RAPIDFUZZ = False


_ALIAS_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("bangalore", ("bengaluru", "bengalooru", "bangalroe", "banglore")),
    ("bombay", ("mumbai",)),
    ("madras", ("chennai", "chenai", "chennay")),
    ("calcutta", ("kolkata", "kolkatta", "calcuta")),
    ("gurgaon", ("gurugram", "gudgaon", "gurgoan", "gurgram")),
    ("pune", ("poona",)),
    ("trivandrum", ("thiruvananthapuram", "thiruvanantapuram")),
    ("cochin", ("kochi",)),
    ("baroda", ("vadodara", "wadodara")),
    ("mysore", ("mysuru",)),
    ("allahabad", ("prayagraj",)),
    ("pondicherry", ("puducherry",)),
    ("varanasi", ("banaras", "benares", "kashi")),
    ("bezawada", ("vijayawada",)),
    ("bhubaneswar", ("bhubaneshwar", "bhuvaneshwar")),
    ("visakhapatnam", ("vizag", "vishakhapatnam")),
    ("mangalore", ("mangaluru",)),
    ("trichy", ("tiruchirappalli", "tiruchirapalli")),
    ("panaji", ("panjim",)),
    ("delhi", ("dilli",)),
)

_CANONICAL: dict[str, str] = {}
for _canon, _aliases in _ALIAS_GROUPS:
    _CANONICAL[_canon] = _canon
    for _a in _aliases:
        _CANONICAL[_a] = _canon


_PUNCT_RE = re.compile(r"[^\w\s]+")
_WS_RE = re.compile(r"\s+")


def _light_normalise(s: str) -> str:
    t = s.lower()
    t = _PUNCT_RE.sub(" ", t)
    t = _WS_RE.sub(" ", t).strip()
    return t


def _try_rewrites(t: str) -> str | None:
    """Probe transliteration rewrites; return canonical on first hit."""
    candidates: list[str] = []
    candidates.append(re.sub(r"aa", "a", t))
    candidates.append(re.sub(r"ee", "i", t))
    candidates.append(re.sub(r"oo", "u", t))
    candidates.append(t.replace("d", "r"))
    candidates.append(t.replace("w", "v"))
    candidates.append(t.replace("ph", "f"))
    candidates.append(t.replace("f", "ph"))
    for suffix in ("puram", "gram", "pur", "ur"):
        if t.endswith(suffix) and len(t) > len(suffix) + 3:
            candidates.append(t[: -len(suffix)])
    candidates.append(t.replace("sh", "s"))
    candidates.append(t.replace("bh", "b"))
    for c in candidates:
        c = _WS_RE.sub(" ", c).strip()
        if c in _CANONICAL:
            return _CANONICAL[c]
    return None


def normalise(s: str | None) -> str:
    """Return a canonical form of a place name (best-effort)."""
    if not s:
        return ""
    t = _light_normalise(s)
    if not t:
        return ""
    if t in _CANONICAL:
        return _CANONICAL[t]
    hit = _try_rewrites(t)
    if hit is not None:
        return hit
    return t


def canonical_aliases() -> dict[str, str]:
    """Flat variant → canonical alias map (copy)."""
    return dict(_CANONICAL)


def fuzzy_ratio(a: str | None, b: str | None) -> float:
    """Similarity in [0.0, 1.0] between two names, post phonetic normalise."""
    if not a or not b:
        return 0.0
    na, nb = normalise(a), normalise(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if _HAS_RAPIDFUZZ:
        return _rf_fuzz.token_set_ratio(na, nb) / 100.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def best_match(
    query: str | None,
    candidates: list[str],
    cutoff: float = 0.6,
) -> tuple[str, float] | None:
    """Best candidate above cutoff, ``None`` if no match."""
    if not query or not candidates:
        return None
    best: tuple[str, float] | None = None
    for c in candidates:
        score = fuzzy_ratio(query, c)
        if score >= cutoff and (best is None or score > best[1]):
            best = (c, round(score, 3))
    return best
