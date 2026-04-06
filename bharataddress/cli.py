"""Command-line interface for bharataddress.

    bharataddress parse "Flat 302, Raheja Atlantis, Sector 31, Gurgaon 122001"
    bharataddress lookup 122001
"""
from __future__ import annotations

import argparse
import json
import sys

from . import __version__, parse
from . import pincode as _pincode


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="bharataddress",
        description="Parse messy Indian addresses into structured JSON. Offline. Deterministic.",
    )
    p.add_argument("--version", action="version", version=f"bharataddress {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("parse", help="Parse an address string")
    sp.add_argument("address", help="Address string in quotes")
    sp.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")

    sl = sub.add_parser("lookup", help="Look up a pincode")
    sl.add_argument("pincode", help="6-digit pincode")

    args = p.parse_args(argv)

    if args.cmd == "parse":
        result = parse(args.address)
        indent = 2 if args.pretty else None
        print(json.dumps(result.to_dict(), indent=indent, ensure_ascii=False))
        return 0

    if args.cmd == "lookup":
        rec = _pincode.lookup(args.pincode)
        if not rec:
            print(json.dumps({"error": "pincode not found", "pincode": args.pincode}))
            return 1
        # offices list can be huge — trim for CLI display.
        trimmed = dict(rec)
        trimmed["offices"] = trimmed["offices"][:10]
        print(json.dumps(trimmed, indent=2, ensure_ascii=False))
        return 0

    return 2


if __name__ == "__main__":
    sys.exit(main())
