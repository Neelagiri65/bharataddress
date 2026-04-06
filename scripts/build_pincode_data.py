"""Build bharataddress/data/pincodes.json from kishorek/India-Codes CSV.

One-shot dataset builder. Run once at package build time, not at runtime.

Usage:
    python scripts/build_pincode_data.py

Source: https://raw.githubusercontent.com/kishorek/India-Codes/master/csv/pincodes.csv
"""
from __future__ import annotations

import csv
import json
import sys
import urllib.request
from pathlib import Path

SOURCE_URL = "https://raw.githubusercontent.com/kishorek/India-Codes/master/csv/pincodes.csv"
OUT_PATH = Path(__file__).resolve().parents[1] / "bharataddress" / "data" / "pincodes.json"


def fetch_csv() -> str:
    print(f"Fetching {SOURCE_URL} ...", file=sys.stderr)
    with urllib.request.urlopen(SOURCE_URL, timeout=60) as resp:
        return resp.read().decode("utf-8")


def build(text: str) -> dict[str, dict]:
    """Collapse rows by pincode. First row wins for district/city/state.

    Multiple post offices share a pincode; we keep the canonical district/state
    and a deduped list of office names.
    """
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


def main() -> None:
    text = fetch_csv()
    table = build(text)
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8") as f:
        json.dump(table, f, separators=(",", ":"), ensure_ascii=False)
    size_mb = OUT_PATH.stat().st_size / 1_000_000
    print(f"Wrote {len(table):,} pincodes to {OUT_PATH} ({size_mb:.2f} MB)", file=sys.stderr)


if __name__ == "__main__":
    main()
