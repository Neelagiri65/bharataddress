# DIGIPIN module spec (bharataddress v0.3)

Status: **draft / research only**. No code yet.

## What DIGIPIN is

DIGIPIN ("Digital PIN") is a 10-character alphanumeric geocode launched by India Post (Department of Posts, Govt of India) in 2025. It encodes any point in India to a ~3.8 m × 3.8 m cell using a hierarchical 4×4 grid over a fixed bounding box. Unlike a PIN code, it identifies a *location*, not a delivery area.

- Format: `XXX-XXX-XXXX` (10 chars + 2 dashes), e.g. `M2J-T3L-747J`
- Alphabet (16 symbols, ambiguous chars excluded): `2 3 4 5 6 7 8 9 C J K L M P F T`
- Bounding box: longitude **63.5° E – 99.5° E**, latitude **2.5° N – 38.5° N** (EPSG:4326)
- Levels: 10 nested 4×4 subdivisions. Each level adds 1 char and divides the cell into 16 children.
- Level-10 cell size: ≈ 3.8 m on a side.
- Reversible: a DIGIPIN decodes to the centre lat/lng of its level-10 cell.

## Sources

| Source | URL | License | Notes |
|---|---|---|---|
| Official India Post repo | github.com/INDIAPOST-gov/digipin | Apache-2.0 | Reference JS implementation + REST API (`/api/digipin/encode`, `/api/digipin/decode`). Authoritative algorithm. |
| PyPI `digipin` (G Kiran) | pypi.org/project/digipin/ (v2.0.1, Jun 2025) | MIT | Pure-Python `encode(lat, lng) -> str` and `decode(code) -> (lat, lng)`. Mirrors the official algorithm. |
| India Post portals | dac.indiapost.gov.in/mydigipin/home, /mypincode/menu | — | User-facing lookup; not an API. |
| Pincode boundary polygons | data.gov.in (India Post pincode GeoJSON) | Govt OGDL | Needed for `pincode_to_digipins`. ~50 MB, v0.3 dataset add. |

There is **no official mapping** between PIN code and DIGIPIN. PIN code → DIGIPIN coverage has to be derived by sampling the pincode polygon and encoding sample points.

## Public API

All functions are pure, offline, and deterministic. New module: `bharataddress/digipin.py`.

```python
def digipin_to_latlng(code: str) -> tuple[float, float]:
    """Decode a DIGIPIN to the centre lat/lng of its level-10 cell.

    Raises ValueError if `code` is not a valid 10-char DIGIPIN.
    """

def latlng_to_digipin(lat: float, lng: float) -> str:
    """Encode lat/lng to a 10-character DIGIPIN (formatted XXX-XXX-XXXX).

    Raises ValueError if (lat, lng) is outside the India bounding box
    (lat 2.5–38.5, lng 63.5–99.5).
    """

def pincode_to_digipins(pincode: str, level: int = 6) -> list[str]:
    """Return DIGIPINs covering the area of a 6-digit PIN code.

    `level` controls the cell granularity (1–10). Default 6 ≈ a few hundred
    metres per cell, which is enough to tile a typical urban PIN code in a few
    dozen codes. Returns [] if the pincode is unknown or its polygon is not
    available in the bundled boundary dataset.
    """
```

### Integration into `parse()`

`ParsedAddress` gains one optional field:

```python
digipin: str | None  # populated only when a lat/lng is known
```

In v0.3 the parser does **not** geocode addresses to lat/lng on its own (no geocoder is bundled). `digipin` is populated in two cases:

1. **User passes a hint**: `parse(addr, latlng=(12.97, 77.59))` → encode and attach.
2. **PIN code centroid fallback** (opt-in via `parse(addr, digipin="centroid")`): if the bundled pincode dataset has a centroid for the resolved PIN code, encode that. The result is marked low-confidence in `components_found` because a centroid is not the address.

Default behaviour stays unchanged (`digipin` is `None`), so v0.1 callers see no difference.

## Implementation approach

Two options, in order of preference:

1. **Vendor the algorithm** (preferred). Port the ~80 lines of encode/decode from the official `INDIAPOST-gov/digipin` JS into `bharataddress/digipin.py`. Keeps the zero-dependency promise from v0.1 intact, keeps the algorithm auditable in-tree, and avoids a new runtime dep that ships its own bounding box constants.
2. **Depend on PyPI `digipin`**. Add `digipin>=2.0.1` as a runtime dep and wrap it. Faster to ship but breaks the "zero runtime deps" property and couples us to a 1-maintainer package.

Decision: **vendor**. The algorithm is ~80 lines, Apache-2.0, and stable since launch. Add a unit test that round-trips 1,000 random points and asserts agreement with a vendored set of golden vectors lifted from the official repo's test suite.

`pincode_to_digipins` is a separate problem and a separate dataset:

- Add `bharataddress/data/pincode_boundaries.geojson` (or a sliced binary format) at build time via a new `scripts/build_pincode_boundaries.py`. Source: data.gov.in pincode GeoJSON.
- At call time: load the polygon for the pincode (lazy, lru_cache like `pincode.py`), tile it at the requested level by walking the DIGIPIN grid, and return cells whose centre falls inside the polygon.
- Bundle size impact: GeoJSON for ~19k pincodes is large (~50 MB). Likely ship as a separate optional package `bharataddress-boundaries` so the core wheel stays small. `pincode_to_digipins` raises a clear `MissingDataError` if the optional package isn't installed.

## Out of scope for v0.3

- Reverse geocoding DIGIPIN → street address.
- Encoding points outside India (the bounding box is hard-coded by India Post).
- Any network call. The official REST API is **not** used at runtime.
- Pincode → single DIGIPIN. A PIN code is an area; collapsing it to one DIGIPIN is misleading. Callers get a list.

## Test plan

- Round-trip: encode → decode → encode is stable for 10k random valid points.
- Golden vectors: 50 (lat, lng, expected_digipin) tuples lifted from the official repo, must match exactly.
- Bounds: points outside the India bbox raise `ValueError`.
- `pincode_to_digipins("560001", level=6)` returns ≥ 1 cell, all of which decode back inside the Bangalore GPO polygon.
- `parse(addr, latlng=(...))` populates `digipin` and serialises through `to_dict()`.
- Architectural constraint: `socket.socket` monkeypatch — no network during any digipin call.
