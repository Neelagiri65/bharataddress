"""Per-field confidence + consistency checks for a ``ParsedAddress``.

The parser is deterministic but the *input* may be wrong. ``validator`` answers
two different questions:

- ``validate(parsed)`` — for each populated field, give a 0.0–1.0 confidence
  plus a list of consistency issues (e.g. parsed state disagrees with the
  state India Post records for that pincode).
- ``is_deliverable(parsed)`` — quick boolean for the minimum field set a
  postal worker needs to actually deliver: pincode + city + state.

No network. The pincode lookup is the embedded India Post directory.
"""
from __future__ import annotations

from typing import Any

from . import pincode as _pincode
from .parser import ParsedAddress


_REQUIRED_FOR_DELIVERY = ("pincode", "city", "state")


def is_deliverable(parsed: ParsedAddress) -> bool:
    """True if the address has the minimum fields needed for postal delivery."""
    return all(getattr(parsed, f) for f in _REQUIRED_FOR_DELIVERY)


def _norm(s: str | None) -> str:
    return (s or "").strip().lower()


def validate(parsed: ParsedAddress) -> dict[str, Any]:
    """Return per-field confidence + a list of consistency issues.

    Shape::

        {
          "fields": {"pincode": 1.0, "city": 0.9, ...},
          "issues": ["state mismatch: parsed='Karnataka' expected='Tamil Nadu'"],
          "is_deliverable": True,
          "overall": 0.87,
        }
    """
    fields: dict[str, float] = {}
    issues: list[str] = []

    rec = _pincode.lookup(parsed.pincode) if parsed.pincode else None

    if parsed.pincode:
        fields["pincode"] = 1.0 if rec else 0.3
        if not rec:
            issues.append(f"pincode {parsed.pincode} not in India Post directory")

    if parsed.state:
        if rec and rec.get("state"):
            ok = _norm(parsed.state) == _norm(rec["state"])
            fields["state"] = 1.0 if ok else 0.4
            if not ok:
                issues.append(
                    f"state mismatch: parsed={parsed.state!r} expected={rec['state']!r}"
                )
        else:
            fields["state"] = 0.5

    if parsed.district:
        if rec and rec.get("district"):
            ok = _norm(parsed.district) == _norm(rec["district"])
            fields["district"] = 1.0 if ok else 0.4
            if not ok:
                issues.append(
                    f"district mismatch: parsed={parsed.district!r} expected={rec['district']!r}"
                )
        else:
            fields["district"] = 0.5

    if parsed.city:
        if rec and rec.get("city"):
            pc, rc = _norm(parsed.city), _norm(rec["city"])
            if pc == rc:
                fields["city"] = 1.0
            elif pc in rc or rc in pc:
                fields["city"] = 0.8
            else:
                fields["city"] = 0.4
                issues.append(
                    f"city mismatch: parsed={parsed.city!r} expected={rec['city']!r}"
                )
        else:
            fields["city"] = 0.5

    for soft in ("locality", "sub_locality", "building_name", "building_number", "landmark"):
        v = getattr(parsed, soft)
        if v:
            fields[soft] = 0.7

    overall = round(sum(fields.values()) / len(fields), 3) if fields else 0.0
    return {
        "fields": fields,
        "issues": issues,
        "is_deliverable": is_deliverable(parsed),
        "overall": overall,
    }
