"""Rule-based extractor for Indian address components.

This is the deterministic core of bharataddress v0.1. It walks comma-separated
segments left-to-right and classifies each by pattern.

Component priority (highest to lowest confidence):
    pincode  -> regex, validated against shipped India Post directory
    state    -> from pincode lookup (overrides any text guess)
    district -> from pincode lookup
    city     -> from pincode lookup; falls back to last non-pincode segment
    locality -> sector/phase/block/<x> nagar / <x> colony / <x> layout
    landmark -> segment beginning with near/opp/behind/beside/next to/in front of
    building_number, building_name -> first segment with a leading number or
        flat/house keyword

No LLM. No network. Pure regex + the embedded pincode table.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from . import pincode as _pincode
from .preprocessor import PINCODE_RE, preprocess

LANDMARK_PREFIX_RE = re.compile(
    r"^(?:near|opposite|opp|behind|beside|next to|in front of|adjacent to|adj|adjoining)\b[\s,.-]*",
    re.IGNORECASE,
)

BUILDING_LEAD_RE = re.compile(
    r"^(?:flat|flat\s*number|house\s*number|house|h\s*number|plot|plot\s*number|door\s*number|apt|apartment|shop|shop\s*number|#)\s*[:.-]?\s*",
    re.IGNORECASE,
)

# Letter-prefixed building tokens like "B-302", "A-101", "BD-12", "E2017".
BUILDING_ALPHANUM_RE = re.compile(r"^[A-Za-z]{1,3}[-]?\d+[A-Za-z]?(?:[/-]\d+[A-Za-z]?)*$")

# Addressee prefixes that the abbreviation expander has already unfolded.
ADDRESSEE_RE = re.compile(r"^(?:son of|daughter of|wife of|care of)\b", re.IGNORECASE)

# Things that strongly look like a sub-locality (street, block, tower, floor)
# rather than a neighbourhood proper.
SUBLOCALITY_RE = re.compile(
    r"\b(?:block|sector|phase|tower|floor|cross|avenue|salai|marg|main\s+road|road\s*(?:no|number|num)?\b)|\d+(?:st|nd|rd|th)?\s*(?:cross|block|main|avenue)",
    re.IGNORECASE,
)
SUBLOC_END_RE = re.compile(r"\b(?:road|rd|street|st|lane|path)\s*$", re.IGNORECASE)

# A "locality token" — a segment containing one of these strongly suggests a
# named locality / sub-locality rather than a city or building.
LOCALITY_KEYWORDS = (
    "nagar", "colony", "layout", "vihar",
    "puram", "puri", "ganj", "bagh", "enclave", "extension", "township",
    "chowk", "gali", "mohalla", "wadi", "halli", "pally",
    "pet", "kunj",
    "park", "gardens", "estate",
)
LOCALITY_RE = re.compile(
    r"\b(?:" + "|".join(LOCALITY_KEYWORDS) + r")\b", re.IGNORECASE
)

# A "building name token" — a segment containing one of these strongly
# suggests a named building / complex / society rather than a neighbourhood.
BUILDING_NAME_KEYWORDS = (
    "tower", "towers", "apartment", "apartments", "apts",
    "heights", "residency", "residences", "society",
    "complex", "court", "plaza", "palace", "mansion",
    "villa", "villas", "flats",
)
BUILDING_NAME_RE = re.compile(
    r"\b(?:" + "|".join(BUILDING_NAME_KEYWORDS) + r")\b", re.IGNORECASE
)

SECTOR_RE = re.compile(r"\bsector\s*[-#]?\s*\d+[A-Za-z]?\b", re.IGNORECASE)
PHASE_RE = re.compile(r"\bphase\s*[-#]?\s*[IVX0-9]+\b", re.IGNORECASE)
BLOCK_RE = re.compile(r"\bblock\s*[-#]?\s*[A-Za-z0-9]+\b", re.IGNORECASE)


@dataclass(slots=True)
class ParsedAddress:
    raw: str
    cleaned: str
    building_number: str | None = None
    building_name: str | None = None
    landmark: str | None = None
    locality: str | None = None
    sub_locality: str | None = None
    city: str | None = None
    district: str | None = None
    state: str | None = None
    pincode: str | None = None
    confidence: float = 0.0
    components_found: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d.pop("components_found", None)
        return d


def _split_segments(cleaned: str) -> list[str]:
    parts = [p.strip(" ,.-") for p in cleaned.split(",")]
    return [p for p in parts if p]


def _strip_pincode(segment: str) -> str:
    return PINCODE_RE.sub("", segment).strip(" ,.-")


def _classify(segment: str) -> str | None:
    """Return one of: 'addressee', 'landmark', 'building', 'sub_locality', 'locality', or None."""
    if ADDRESSEE_RE.match(segment):
        return "addressee"
    if LANDMARK_PREFIX_RE.match(segment):
        return "landmark"
    if BUILDING_LEAD_RE.match(segment):
        return "building"
    if re.match(r"^[#]?\d+[A-Za-z]?(?:[/-]\d+[A-Za-z]?)*\b", segment):
        return "building"
    if BUILDING_ALPHANUM_RE.match(segment):
        return "building"
    # Building-name cues (towers / apartments / heights / villas / complex)
    # take precedence — they almost always denote a named property.
    if BUILDING_NAME_RE.search(segment):
        return "building_name"
    # Sub-locality cues take precedence over generic locality keywords because
    # tokens like "block" / "sector" appear in both lists.
    if SUBLOCALITY_RE.search(segment) or SUBLOC_END_RE.search(segment):
        return "sub_locality"
    if LOCALITY_RE.search(segment):
        return "locality"
    return None


def _extract_building(segment: str) -> tuple[str | None, str | None]:
    """Pull a building number (numeric or alphanumeric) off the front."""
    s = BUILDING_LEAD_RE.sub("", segment)
    s = re.sub(r"^(?:no|number|num)[.\s:-]*", "", s, flags=re.IGNORECASE)
    m = re.match(
        r"^([#]?[A-Za-z]{0,3}[-]?\d+[A-Za-z]?(?:[/-]\d+[A-Za-z]?)*)[\s,.-]*(.*)$",
        s,
    )
    if m:
        num = m.group(1).lstrip("#")
        name = m.group(2).strip(" ,.-") or None
        return num, name
    return None, segment.strip(" ,.-") or None


def _extract_landmark(segment: str) -> str:
    return LANDMARK_PREFIX_RE.sub("", segment).strip(" ,.-")


def _confidence(found: list[str], city_matches_pincode: bool) -> float:
    weights = {
        "pincode": 0.40,
        "city": 0.20 if city_matches_pincode else 0.10,
        "locality": 0.20,
        "building": 0.10,
        "landmark": 0.10,
    }
    score = sum(weights.get(c, 0.0) for c in set(found))
    return round(min(score, 1.0), 3)


def parse(raw: str) -> ParsedAddress:
    """Parse a messy Indian address string into structured components."""
    if not isinstance(raw, str) or not raw.strip():
        return ParsedAddress(raw=raw or "", cleaned="")

    cleaned, pin = preprocess(raw)
    out = ParsedAddress(raw=raw, cleaned=cleaned, pincode=pin)
    found: list[str] = []

    # Pincode → district/state/city from shipped directory.
    rec = _pincode.lookup(pin)
    if rec:
        out.district = rec["district"] or None
        out.state = rec["state"] or None
        out.city = rec["city"] or None
        found.append("pincode")
        if out.city:
            found.append("city")

    segments = _split_segments(cleaned)
    # Each entry: dict(kind=..., text=...). Order is preserved so we can do
    # position-aware assignment (e.g. building_name immediately follows the
    # building number).
    tagged: list[dict[str, str]] = []
    for seg in segments:
        seg_no_pin = _strip_pincode(seg)
        if not seg_no_pin:
            continue
        kind = _classify(seg_no_pin) or "plain"
        if kind == "addressee":
            continue  # Drop "son of Suresh" etc.
        tagged.append({"kind": kind, "text": seg_no_pin})

    # Pull landmarks out first; they have a clear prefix and are unambiguous.
    landmark_parts = [_extract_landmark(t["text"]) for t in tagged if t["kind"] == "landmark"]
    tagged = [t for t in tagged if t["kind"] != "landmark"]
    if landmark_parts:
        out.landmark = "; ".join(p for p in landmark_parts if p) or None
        if out.landmark:
            found.append("landmark")

    # Pull the first building segment.
    building_idx = next((i for i, t in enumerate(tagged) if t["kind"] == "building"), None)
    if building_idx is not None:
        seg = tagged[building_idx]["text"]
        num, name = _extract_building(seg)
        if num:
            out.building_number = num
        if num or name:
            found.append("building")
        del tagged[building_idx]
        # If extraction left behind a residue, reclassify it. A residue with
        # locality / sub-locality cues should compete for those slots, not be
        # silently planted in building_name. Only keep it as building_name if
        # it actually looks like a building name.
        if name:
            residue_kind = _classify(name) or "plain"
            if residue_kind == "building_name":
                out.building_name = name
            elif residue_kind in ("locality", "sub_locality"):
                tagged.insert(building_idx, {"kind": residue_kind, "text": name})
            elif residue_kind == "plain" and len(name.split()) <= 4:
                # Short plain residue: tentatively a building_name. Long
                # residues from no-comma inputs are usually a whole address
                # tail and should not pollute building_name.
                out.building_name = name

    # If pincode didn't give us a city, take the last "plain" segment as city.
    if not out.city:
        for i in range(len(tagged) - 1, -1, -1):
            if tagged[i]["kind"] == "plain":
                out.city = tagged[i]["text"]
                del tagged[i]
                found.append("city")
                break

    # Drop tagged entries that just repeat the city, district, or state names
    # already pulled from the pincode lookup — they're trailing noise, not new
    # locality information.
    def _is_dup(text: str) -> bool:
        t = text.lower().strip()
        for ref in (out.city, out.district, out.state):
            if ref and (t == ref.lower() or t in ref.lower() or ref.lower() in t):
                return True
        return False

    tagged = [t for t in tagged if not _is_dup(t["text"])]

    # Strong building_name cue (towers / apartments / heights / villas /
    # complex / society) — pull the first such segment regardless of position.
    if not out.building_name:
        for i, t in enumerate(tagged):
            if t["kind"] == "building_name":
                out.building_name = t["text"]
                del tagged[i]
                if "building" not in found:
                    found.append("building")
                break

    # Building name fallback: only when the next remaining segment is a plain
    # named token (e.g. "Lodha Altamount") AND there's still something left
    # behind it for locality. Sub_locality / locality cues stay where they are.
    if (
        out.building_number
        and not out.building_name
        and len(tagged) >= 2
        and tagged[0]["kind"] == "plain"
    ):
        out.building_name = tagged[0]["text"]
        del tagged[0]
        if "building" not in found:
            found.append("building")

    # Locality: prefer a "plain" or generic-locality segment over a
    # sub_locality cue (block/sector/road).
    def _take(predicate):
        for i, t in enumerate(tagged):
            if predicate(t):
                return tagged.pop(i)["text"]
        return None

    out.locality = (
        _take(lambda t: t["kind"] == "plain")
        or _take(lambda t: t["kind"] == "locality")
        or _take(lambda t: t["kind"] == "sub_locality")
        or _take(lambda t: t["kind"] == "building_name")
    )
    if out.locality:
        found.append("locality")

    # Sub-locality: prefer an explicit sub_locality cue, else fall through.
    out.sub_locality = (
        _take(lambda t: t["kind"] == "sub_locality")
        or _take(lambda t: t["kind"] == "locality")
        or _take(lambda t: t["kind"] == "plain")
    )
    if out.sub_locality:
        found.append("sub_locality")

    city_matches = bool(rec and out.city and rec["city"] and out.city.lower() == rec["city"].lower())
    out.confidence = _confidence(found, city_matches_pincode=city_matches or bool(rec))
    out.components_found = sorted(set(found))
    return out
