"""DIGIPIN encode / decode / validate.

DIGIPIN ("Digital PIN") is the 10-character alphanumeric geocode developed by
the Department of Posts (India Post) in collaboration with IIT Hyderabad and
NRSC. It encodes any point inside India to a ~3.8 m x 3.8 m cell using a
hierarchical 4x4 grid over a fixed bounding box.

Format:    XXX-XXX-XXXX  (10 chars + 2 dashes)
Alphabet:  F C 9 8 J 3 2 7 K 4 5 6 L M P T  (16 symbols)
Bounds:    lat 2.5 to 38.5, lon 63.5 to 99.5 (degrees, EPSG:4326)

This is a verbatim Python port of the official Apache-2.0 reference at
github.com/INDIAPOST-gov/digipin (src/digipin.js). No network, no I/O, no
dependencies — pure deterministic math.
"""
from __future__ import annotations

DIGIPIN_GRID: tuple[tuple[str, ...], ...] = (
    ("F", "C", "9", "8"),
    ("J", "3", "2", "7"),
    ("K", "4", "5", "6"),
    ("L", "M", "P", "T"),
)

MIN_LAT = 2.5
MAX_LAT = 38.5
MIN_LON = 63.5
MAX_LON = 99.5

_VALID_CHARS = frozenset(c for row in DIGIPIN_GRID for c in row)
_CHAR_TO_RC = {c: (r, ci) for r, row in enumerate(DIGIPIN_GRID) for ci, c in enumerate(row)}


def encode(lat: float, lng: float) -> str:
    """Encode latitude / longitude to a 10-character DIGIPIN (formatted XXX-XXX-XXXX).

    Raises ValueError if (lat, lng) is outside the India bounding box.
    """
    if lat < MIN_LAT or lat > MAX_LAT:
        raise ValueError(f"latitude {lat} out of range [{MIN_LAT}, {MAX_LAT}]")
    if lng < MIN_LON or lng > MAX_LON:
        raise ValueError(f"longitude {lng} out of range [{MIN_LON}, {MAX_LON}]")

    min_lat, max_lat = MIN_LAT, MAX_LAT
    min_lon, max_lon = MIN_LON, MAX_LON
    out: list[str] = []

    for level in range(1, 11):
        lat_div = (max_lat - min_lat) / 4
        lon_div = (max_lon - min_lon) / 4

        # Reversed row logic to match the official implementation.
        row = 3 - int((lat - min_lat) // lat_div)
        col = int((lng - min_lon) // lon_div)
        row = max(0, min(row, 3))
        col = max(0, min(col, 3))

        out.append(DIGIPIN_GRID[row][col])
        if level == 3 or level == 6:
            out.append("-")

        # Update bounds (reverse logic for row).
        new_max_lat = min_lat + lat_div * (4 - row)
        new_min_lat = min_lat + lat_div * (3 - row)
        max_lat = new_max_lat
        min_lat = new_min_lat

        new_min_lon = min_lon + lon_div * col
        max_lon = new_min_lon + lon_div
        min_lon = new_min_lon

    return "".join(out)


def decode(digipin: str) -> tuple[float, float]:
    """Decode a DIGIPIN to the centre (lat, lng) of its level-10 cell.

    Accepts the DIGIPIN with or without dashes. Raises ValueError on bad input.
    """
    if not isinstance(digipin, str):
        raise ValueError("digipin must be a string")
    pin = digipin.replace("-", "").upper()
    if len(pin) != 10:
        raise ValueError(f"DIGIPIN must be 10 characters (got {len(pin)})")
    for ch in pin:
        if ch not in _VALID_CHARS:
            raise ValueError(f"invalid character {ch!r} in DIGIPIN")

    min_lat, max_lat = MIN_LAT, MAX_LAT
    min_lon, max_lon = MIN_LON, MAX_LON

    for ch in pin:
        ri, ci = _CHAR_TO_RC[ch]
        lat_div = (max_lat - min_lat) / 4
        lon_div = (max_lon - min_lon) / 4

        lat1 = max_lat - lat_div * (ri + 1)
        lat2 = max_lat - lat_div * ri
        lon1 = min_lon + lon_div * ci
        lon2 = min_lon + lon_div * (ci + 1)

        min_lat, max_lat = lat1, lat2
        min_lon, max_lon = lon1, lon2

    return ((min_lat + max_lat) / 2, (min_lon + max_lon) / 2)


def validate(digipin: str) -> bool:
    """Return True iff `digipin` is a syntactically valid DIGIPIN string."""
    try:
        decode(digipin)
        return True
    except (ValueError, TypeError):
        return False
