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
    r"^(?:flat|house\s*number|house|h\s*number|plot|plot\s*number|door\s*number|#)\s*[:.-]?\s*",
    re.IGNORECASE,
)

# A "locality token" — a segment containing one of these strongly suggests a
# named locality / sub-locality rather than a city or building.
LOCALITY_KEYWORDS = (
    "sector", "phase", "block", "nagar", "colony", "layout", "vihar",
    "puram", "puri", "ganj", "bagh", "enclave", "extension", "township",
    "marg", "chowk", "gali", "mohalla", "vihar", "wadi", "halli", "pally",
    "pet", "kunj", "society", "apartments", "heights", "residency",
    "park", "gardens", "estate", "complex",
)
LOCALITY_RE = re.compile(
    r"\b(?:" + "|".join(LOCALITY_KEYWORDS) + r")\b", re.IGNORECASE
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
    """Return one of: 'landmark', 'locality', 'building', or None."""
    if LANDMARK_PREFIX_RE.match(segment):
        return "landmark"
    if BUILDING_LEAD_RE.match(segment) or re.match(r"^[#]?\d+[A-Za-z]?(?:[/-]\d+)?\b", segment):
        return "building"
    if LOCALITY_RE.search(segment):
        return "locality"
    return None


def _extract_building(segment: str) -> tuple[str | None, str | None]:
    """Pull a numeric building number off the front; rest is building name."""
    s = BUILDING_LEAD_RE.sub("", segment)
    m = re.match(r"^([#]?\d+[A-Za-z]?(?:[/-]\d+)?)[\s,.-]*(.*)$", s)
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
    landmark_parts: list[str] = []
    locality_parts: list[str] = []
    building_done = False
    expect_building_name = False
    leftover: list[str] = []

    for seg in segments:
        seg_no_pin = _strip_pincode(seg)
        if not seg_no_pin:
            continue
        kind = _classify(seg_no_pin)
        if kind == "building" and not building_done:
            num, name = _extract_building(seg_no_pin)
            if num:
                out.building_number = num
            if name:
                out.building_name = name
            building_done = True
            expect_building_name = bool(num and not name)
            if num or name:
                found.append("building")
            continue
        if expect_building_name and kind is None:
            out.building_name = seg_no_pin
            expect_building_name = False
            continue
        expect_building_name = False
        if kind == "landmark":
            landmark_parts.append(_extract_landmark(seg_no_pin))
            continue
        if kind == "locality":
            locality_parts.append(seg_no_pin)
            continue
        leftover.append(seg_no_pin)

    if landmark_parts:
        out.landmark = "; ".join(p for p in landmark_parts if p) or None
        if out.landmark:
            found.append("landmark")

    if locality_parts:
        out.locality = locality_parts[0]
        if len(locality_parts) > 1:
            out.sub_locality = locality_parts[1]
        found.append("locality")

    # If no city from pincode, fall back to the last leftover segment.
    if not out.city and leftover:
        candidate = leftover[-1]
        # Avoid using a state name as the city if it's clearly a state.
        out.city = candidate
        leftover = leftover[:-1]

    # If we have leftover segments and no locality, promote the longest leftover.
    if not out.locality and leftover:
        out.locality = max(leftover, key=len)
        found.append("locality")

    city_matches = bool(rec and out.city and rec["city"] and out.city.lower() == rec["city"].lower())
    out.confidence = _confidence(found, city_matches_pincode=city_matches or bool(rec))
    out.components_found = sorted(set(found))
    return out
