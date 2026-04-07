"""Add latitude / longitude centroids to bharataddress/data/pincodes.json.

Source: OpenStreetMap India extract at private/raw/india-latest.osm.pbf.

The build walks every OSM node carrying an `addr:postcode` tag matching the
Indian pincode pattern, accumulates the lat/lng, and writes the per-pincode
mean back into `pincodes.json` as `latitude` / `longitude` floats. Only
pincodes that already exist in the directory are updated; OSM is treated as
a centroid source, never as a source of new pincodes (the existing build
script is authoritative for membership).

Note on `private/raw/indiapost.csv`: the India Post directory CSV does *not*
carry lat/lng columns despite the spec asking for it. OSM is therefore the
sole source. If a future India Post dataset gains coordinates, add a first
phase here that prefers it.

This is a build-time script. `pyosmium` is required to run it but is not a
runtime dependency of the package. The output `pincodes.json` is shipped with
the package; the build is reproducible from this script + the OSM PBF.

Usage:
    python3 scripts/build_pincode_centroids.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OSM_PBF = ROOT / "private" / "raw" / "india-latest.osm.pbf"
PINCODES = ROOT / "bharataddress" / "data" / "pincodes.json"

PIN_RE = re.compile(r"^[1-8]\d{5}$")


def main() -> None:
    try:
        import osmium
    except ImportError:
        sys.exit("pyosmium is required: pip install osmium")

    if not OSM_PBF.exists():
        sys.exit(f"OSM PBF not found: {OSM_PBF}")
    if not PINCODES.exists():
        sys.exit(f"pincodes.json not found: {PINCODES}")

    table: dict[str, dict] = json.loads(PINCODES.read_text(encoding="utf-8"))
    print(f"loaded {len(table):,} pincodes from {PINCODES.name}", file=sys.stderr)

    sums: dict[str, list[float]] = {}  # pin -> [sum_lat, sum_lon, n]

    class _Handler(osmium.SimpleHandler):  # type: ignore[misc]
        def __init__(self) -> None:
            super().__init__()
            self.seen = 0

        def node(self, n) -> None:  # noqa: ANN001 - osmium type
            tags = n.tags
            pin = tags.get("addr:postcode")
            if not pin or not PIN_RE.match(pin):
                return
            if pin not in table:
                return
            try:
                lat = float(n.location.lat)
                lon = float(n.location.lon)
            except (osmium.InvalidLocationError, ValueError):
                return
            entry = sums.get(pin)
            if entry is None:
                sums[pin] = [lat, lon, 1.0]
            else:
                entry[0] += lat
                entry[1] += lon
                entry[2] += 1
            self.seen += 1
            if self.seen % 50_000 == 0:
                print(f"  processed {self.seen:,} tagged nodes", file=sys.stderr)

    h = _Handler()
    print("walking OSM PBF (this takes a few minutes) ...", file=sys.stderr)
    h.apply_file(str(OSM_PBF))
    print(
        f"matched {h.seen:,} OSM nodes across {len(sums):,} pincodes",
        file=sys.stderr,
    )

    n_updated = 0
    for pin, (slat, slon, n) in sums.items():
        rec = table.get(pin)
        if rec is None:
            continue
        rec["latitude"] = round(slat / n, 5)
        rec["longitude"] = round(slon / n, 5)
        n_updated += 1

    PINCODES.write_text(
        json.dumps(table, separators=(",", ":"), ensure_ascii=False),
        encoding="utf-8",
    )
    size_mb = PINCODES.stat().st_size / 1_000_000
    pct = 100.0 * n_updated / len(table) if table else 0.0
    print(
        f"wrote {n_updated:,} centroids ({pct:.1f}% coverage) -> {PINCODES.name} "
        f"({size_mb:.2f} MB)",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
