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


from . import language as _language


@lru_cache(maxsize=1)
def _vernacular_legacy() -> dict[str, str]:
    """Deprecated v0.3 flat mapping. Kept only as a safety net for callers that
    invoke ``normalise_vernacular`` without a pincode hint and want the full v0.3
    behaviour. v0.4 routes through ``language.load_mappings`` instead.
    """
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


def normalise_vernacular(text: str, pincode: str | None = None) -> str:
    """Normalise vernacular tokens, language-aware via pincode -> state.

    When ``pincode`` is provided and resolves to a v0.4-supported state, the
    matching language file(s) are layered on top of ``common.json``. When the
    pincode is missing or resolves to no supported language, only ``common.json``
    is applied — preserving the v0.3 default for unknown / English addresses.
    """
    lang_codes = _language.from_pincode(pincode) if pincode else []
    vern = _language.load_mappings(lang_codes)

    def repl(match: re.Match[str]) -> str:
        tok = match.group(0)
        return vern.get(tok.lower(), tok)

    return re.sub(r"[A-Za-z]+", repl, text)


def extract_pincode(text: str) -> str | None:
    matches = PINCODE_RE.findall(text)
    return matches[-1] if matches else None


# Strip phone-number annotations ("Ph: 98765...", "Phone: 022-1234..."). These
# are never address components and the bare "Ph" token previously expanded to
# "phase", which then leaked into sub_locality.
_PHONE_RE = re.compile(
    r"\b(?:ph|phone|tel|telephone|mob|mobile|contact)\b[\s.:#-]*\+?\d[\d\s./-]*",
    re.IGNORECASE,
)
# Strip leftover "Pincode -" / "Pin Code:" labels — the pincode itself is
# already extracted by regex, the label only confuses the segmenter.
_PIN_LABEL_RE = re.compile(r"\bpin\s*code\b\s*[:#-]*\s*", re.IGNORECASE)


# --- v0.4: opt-in script transliteration --------------------------------------

# Unicode block ranges for the six v0.4 scripts. The first non-ASCII char in the
# input picks the script. ITRANS is the chosen Latin target scheme — ASCII-only,
# no diacritics, readable to Indian developers reviewing gold rows.
_SCRIPT_BLOCKS: tuple[tuple[int, int, str, str], ...] = (
    (0x0900, 0x097F, "DEVANAGARI", "hi"),
    (0x0980, 0x09FF, "BENGALI", "bn"),
    (0x0B80, 0x0BFF, "TAMIL", "ta"),
    (0x0C00, 0x0C7F, "TELUGU", "te"),
    (0x0C80, 0x0CFF, "KANNADA", "kn"),
    (0x0D00, 0x0D7F, "MALAYALAM", "ml"),
)

_INDIC_INSTALL_HINT = (
    "indic-transliteration is required for transliterate=True. "
    "Install with: pip install bharataddress[indic]"
)


def _detect_script(text: str) -> tuple[str, str] | None:
    """Return (sanscript_scheme_name, language_code) for the first non-ASCII
    char that lands in a supported Indic block, or None if the text is ASCII /
    unsupported.
    """
    for ch in text:
        cp = ord(ch)
        if cp < 0x80:
            continue
        for lo, hi, scheme, lang in _SCRIPT_BLOCKS:
            if lo <= cp <= hi:
                return scheme, lang
        # First non-ASCII char isn't in a supported block — give up rather than
        # scanning further. Mixed-script handling is out of scope for v0.4.
        return None
    return None


def transliterate_to_latin(text: str) -> tuple[str, str | None]:
    """Transliterate native-script Indic text to Latin (ITRANS scheme).

    Returns ``(latin_text, detected_lang_code)``. If the input is already ASCII
    or its first non-ASCII char isn't in one of the six v0.4 supported blocks,
    returns ``(text, None)`` *without* importing ``indic_transliteration`` — the
    extras dependency is only loaded when actually needed.

    Raises ``ImportError`` with the install hint if the extras package is not
    installed and the input requires transliteration.
    """
    detected = _detect_script(text)
    if detected is None:
        return text, None
    scheme_name, lang = detected
    try:
        from indic_transliteration import sanscript  # type: ignore[import-not-found]
    except ImportError as exc:
        raise ImportError(_INDIC_INSTALL_HINT) from exc
    source_scheme = getattr(sanscript, scheme_name)
    latin = sanscript.transliterate(text, source_scheme, sanscript.ITRANS)
    return latin, lang


def preprocess(text: str) -> tuple[str, str | None]:
    """Return (cleaned_text, pincode_or_None).

    v0.4: pincode is extracted *before* vernacular normalisation so that
    ``normalise_vernacular`` can pick the right per-language mapping file via
    pincode -> state -> language. The pincode regex is robust enough to fire on
    raw input — it does not need abbreviations or vernacular normalisation first.
    """
    text = normalise_unicode(text)
    text = _PHONE_RE.sub(" ", text)
    text = _PIN_LABEL_RE.sub(" ", text)
    text = tidy_whitespace(text)
    pin = extract_pincode(text)
    text = expand_abbreviations(text)
    text = normalise_vernacular(text, pincode=pin)
    text = tidy_whitespace(text)
    return text, pin
