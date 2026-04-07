"""Format a ParsedAddress back into a clean human-readable string.

Three styles:

- ``india_post`` — multiline, India Post envelope convention. Building / name on
  line 1, locality + sub-locality on line 2, landmark on line 3, city + district
  on line 4, state + pincode on line 5. Empty lines are dropped.
- ``single_line`` — comma-separated single line, suitable for CRM fields.
- ``label`` — multiline like ``india_post`` but with field labels prefixed,
  useful for debugging or CSR tooling.

Pure string assembly. No network, no I/O.
"""
from __future__ import annotations

from .parser import ParsedAddress

_STYLES = ("india_post", "single_line", "label")


def _join(parts: list[str | None], sep: str = ", ") -> str:
    return sep.join(p.strip() for p in parts if p and p.strip())


def format(parsed: ParsedAddress, style: str = "india_post") -> str:
    """Reconstruct a clean address string from a ``ParsedAddress``.

    ``style`` must be one of ``"india_post"``, ``"single_line"``, ``"label"``.
    """
    if style not in _STYLES:
        raise ValueError(f"unknown style {style!r}; expected one of {_STYLES}")

    p = parsed
    building_line = _join([p.building_number, p.building_name])

    if style == "single_line":
        return _join(
            [
                building_line or None,
                p.sub_locality,
                p.locality,
                p.landmark,
                p.city,
                p.district if p.district and p.district != p.city else None,
                p.state,
                p.pincode,
            ]
        )

    if style == "india_post":
        lines = [
            building_line,
            _join([p.sub_locality, p.locality]),
            p.landmark,
            _join([p.city, p.district]) if p.district and p.district != p.city else (p.city or ""),
            _join([p.state, p.pincode]),
        ]
        return "\n".join(line for line in lines if line)

    # label
    rows = [
        ("Building", building_line),
        ("Sub-locality", p.sub_locality),
        ("Locality", p.locality),
        ("Landmark", p.landmark),
        ("City", p.city),
        ("District", p.district),
        ("State", p.state),
        ("Pincode", p.pincode),
    ]
    return "\n".join(f"{label}: {value}" for label, value in rows if value)
