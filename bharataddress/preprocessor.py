"""Preprocessing for Indian address strings.

Steps:
    1. NFKC unicode normalisation
    2. Whitespace + punctuation tidy
    3. Abbreviation expansion (H.No., Opp., Nr., S/O, ...)
    4. Vernacular token normalisation (Ngr -> Nagar, Gully -> Gali, ...)
    5. Pincode extraction via regex

The preprocessor is deterministic and offline.
"""
from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from importlib.resources import files

# Indian PIN: 6 digits, first digit 1-8 (0 and 9 are unallocated by India Post).
PINCODE_RE = re.compile(r"\b([1-8]\d{5})\b")

# Token splitter that preserves word boundaries while keeping punctuation.
_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z./]*|\d+|,|-")


@lru_cache(maxsize=1)
def _abbreviations() -> dict[str, str]:
    raw = (files("bharataddress.data") / "abbreviations.json").read_text(encoding="utf-8")
    return {k.lower(): v for k, v in json.loads(raw).items()}


@lru_cache(maxsize=1)
def _vernacular() -> dict[str, str]:
    raw = (files("bharataddress.data") / "vernacular_mappings.json").read_text(encoding="utf-8")
    table = json.loads(raw)
    return {k.lower(): v for k, v in table.items() if not k.startswith("_")}


def normalise_unicode(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def tidy_whitespace(text: str) -> str:
    text = text.replace("\n", ", ").replace("\t", " ")
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"(,\s*)+", ", ", text)
    return text.strip(", ").strip()


def expand_abbreviations(text: str) -> str:
    """Expand multi-word abbreviations first, then single tokens."""
    abbr = _abbreviations()
    # Multi-word keys (contain a space) — replace as substrings, case-insensitive.
    multi = {k: v for k, v in abbr.items() if " " in k}
    for k in sorted(multi, key=len, reverse=True):
        text = re.sub(rf"(?i)(?<![A-Za-z]){re.escape(k)}(?![A-Za-z])", multi[k], text)
    # Single-token keys: walk tokens and replace.
    single = {k: v for k, v in abbr.items() if " " not in k}

    def repl(match: re.Match[str]) -> str:
        tok = match.group(0)
        return single.get(tok.lower(), tok)

    text = re.sub(r"[A-Za-z][A-Za-z./]*", repl, text)
    return text


def normalise_vernacular(text: str) -> str:
    vern = _vernacular()

    def repl(match: re.Match[str]) -> str:
        tok = match.group(0)
        return vern.get(tok.lower(), tok)

    return re.sub(r"[A-Za-z]+", repl, text)


def extract_pincode(text: str) -> str | None:
    matches = PINCODE_RE.findall(text)
    return matches[-1] if matches else None


def preprocess(text: str) -> tuple[str, str | None]:
    """Return (cleaned_text, pincode_or_None)."""
    text = normalise_unicode(text)
    text = tidy_whitespace(text)
    text = expand_abbreviations(text)
    text = normalise_vernacular(text)
    text = tidy_whitespace(text)
    pin = extract_pincode(text)
    return text, pin
