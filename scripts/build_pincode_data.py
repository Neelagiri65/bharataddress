"""Build bharataddress/data/pincodes.json.

Merge strategy (v0.1.3):
    1. Coverage base = kishorek/India-Codes pincode CSV (~24k unique pincodes).
    2. Overlay post-2014 naming fixes from the India Post directory mirror at
       saravanakumargn/All-India-Pincode-Directory (which has correct modern
       state names but lower unique-pincode coverage). The overlay is name-only
       and never adds or drops pincodes from the base — it only rewrites the
       `state` and `district` fields where the modern name differs.

Renames applied unconditionally to the base:
    state    Orissa       -> Odisha
    state    Uttaranchal  -> Uttarakhand
    district Calcutta     -> Kolkata

Telangana split:
    For every pincode the India Post mirror marks as TELANGANA, the merged
    table's `state` is set to "Telangana" (the kishorek base predates the 2014
    bifurcation and labels these as Andhra Pradesh).

Usage:
    # Default: fetch the kishorek base over the network and overlay from
    # private/raw/indiapost.csv (must already be downloaded).
    python scripts/build_pincode_data.py

    # Or pass a local kishorek CSV:
    python scripts/build_pincode_data.py path/to/pincodes.csv
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KISHOREK_URL = "https://raw.githubusercontent.com/kishorek/India-Codes/master/csv/pincodes.csv"
INDIAPOST_CSV = ROOT / "private" / "raw" / "indiapost.csv"
OUT_PATH = ROOT / "bharataddress" / "data" / "pincodes.json"

STATE_RENAMES = {
    "Orissa": "Odisha",
    "Uttaranchal": "Uttarakhand",
}
DISTRICT_RENAMES = {
    "Calcutta": "Kolkata",
}


def fetch_kishorek() -> str:
    print(f"Fetching {KISHOREK_URL} ...", file=sys.stderr)
    with urllib.request.urlopen(KISHOREK_URL, timeout=60) as resp:
        return resp.read().decode("utf-8")


def build_base(text: str) -> dict[str, dict]:
    table: dict[str, dict] = {}
    reader = csv.DictReader(text.splitlines())
    for row in reader:
        pin = (row.get("Pincode") or "").strip()
        if not pin or len(pin) != 6 or not pin.isdigit():
            continue
        entry = table.get(pin)
        office = (row.get("PostOfficeName") or "").strip()
        if entry is None:
            table[pin] = {
                "pincode": pin,
                "district": (row.get("DistrictsName") or "").strip(),
                "city": (row.get("City") or "").strip(),
                "state": (row.get("State") or "").strip(),
                "offices": [office] if office else [],
            }
        else:
            if office and office not in entry["offices"]:
                entry["offices"].append(office)
    return table


def load_telangana_pincodes(path: Path) -> set[str]:
    if not path.exists():
        print(
            f"WARNING: India Post overlay not found at {path}; "
            "Telangana split will be skipped.",
            file=sys.stderr,
        )
        return set()
    tg: set[str] = set()
    with path.open(encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            state = (row.get("statename") or "").strip().upper()
            pin = (row.get("pincode") or "").strip()
            if state == "TELANGANA" and pin and pin.isdigit() and len(pin) == 6:
                tg.add(pin)
    return tg


def overlay(table: dict[str, dict], telangana: set[str]) -> tuple[int, int, int]:
    """Apply renames + Telangana split. Returns (n_state, n_district, n_tg)."""
    n_state = n_district = n_tg = 0
    for pin, entry in table.items():
        st = entry["state"]
        if st in STATE_RENAMES:
            entry["state"] = STATE_RENAMES[st]
            n_state += 1
        if entry["district"] in DISTRICT_RENAMES:
            entry["district"] = DISTRICT_RENAMES[entry["district"]]
            n_district += 1
        if pin in telangana and entry["state"] != "Telangana":
            entry["state"] = "Telangana"
            n_tg += 1
    return n_state, n_district, n_tg


def main() -> None:
    if len(sys.argv) > 1:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    else:
        text = fetch_kishorek()
    table = build_base(text)
    print(f"Base coverage: {len(table):,} pincodes", file=sys.stderr)
    tg = load_telangana_pincodes(INDIAPOST_CSV)
    print(f"Telangana pincodes from overlay: {len(tg):,}", file=sys.stderr)
    n_s, n_d, n_t = overlay(table, tg)
    print(
        f"Renames applied — state: {n_s}, district: {n_d}, Telangana split: {n_t}",
        file=sys.stderr,
    )
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(table, f, separators=(",", ":"), ensure_ascii=False)
    size_mb = OUT_PATH.stat().st_size / 1_000_000
    print(f"Wrote {len(table):,} pincodes to {OUT_PATH} ({size_mb:.2f} MB)", file=sys.stderr)


if __name__ == "__main__":
    main()
