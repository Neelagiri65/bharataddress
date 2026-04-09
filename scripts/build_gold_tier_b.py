"""v0.4 issue #6: build Tier B candidates for gold_500.

Two sources, both producing rows of the shape::

    {"input": str, "expected": {...}, "language": str, "source": str}

1. **OSMNames** (Latin-script regional rows). Accepts a path to the India
   TSV dump from https://osmnames.org/ (CC-BY). The dump is ~100 MB so we
   never auto-download it — pass ``--osmnames PATH``. Each row becomes a
   simple ``"<name>, <city>, <state> <postcode>"``-style input string with
   the structured fields as the expected dict.

2. **Overpass API** (native-script rows for hi/ta/te/kn/bn/ml). One query
   per target city, rate-limited at 1 req/sec to be polite to the public
   instance. Pulls nodes/ways with ``name:<lang>`` and ``addr:*`` tags so
   we get a real native-script name string and a structured expected dict
   from the same OSM object.

Both sources write to the same output file
(``tests/data/gold_500_candidates.jsonl`` by default), which is gitignored
via the ``tests/data/gold_5*.jsonl`` rule. The user hand-promotes rows
into ``gold_500.jsonl`` after review.

This script is **not** part of the package. It makes network calls and
must never be imported from ``bharataddress``. The zero-network contract
on ``parse()`` is unaffected.

Usage::

    # Native-script via Overpass only (no download needed)
    python scripts/build_gold_tier_b.py --overpass

    # Latin regional rows from a downloaded OSMNames dump
    python scripts/build_gold_tier_b.py --osmnames ~/Downloads/in.tsv.gz

    # Both, custom output, cap each source at N rows
    python scripts/build_gold_tier_b.py --overpass --osmnames in.tsv.gz \\
        --out tests/data/gold_500_candidates.jsonl --limit 150
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Iterable, Iterator

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO_ROOT / "tests" / "data" / "gold_500_candidates.jsonl"

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# (city display, state, language code, OSM area name, name:<lang> tag suffix)
OVERPASS_CITIES: tuple[tuple[str, str, str, str, str], ...] = (
    ("New Delhi",  "Delhi",         "hi", "Delhi",       "hi"),
    ("Chennai",    "Tamil Nadu",    "ta", "Chennai",     "ta"),
    ("Hyderabad",  "Telangana",     "te", "Hyderabad",   "te"),
    ("Bengaluru",  "Karnataka",     "kn", "Bengaluru",   "kn"),
    ("Kolkata",    "West Bengal",   "bn", "Kolkata",     "bn"),
    ("Kochi",      "Kerala",        "ml", "Kochi",       "ml"),
)


# --- OSMNames -----------------------------------------------------------------

def _open_maybe_gz(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def iter_osmnames(path: Path, limit: int | None) -> Iterator[dict]:
    """Yield candidate rows from an OSMNames India TSV dump.

    The OSMNames TSV header includes columns like ``name``, ``city``,
    ``county``, ``state``, ``country_code``, ``lon``, ``lat``. We keep
    rows where country_code == 'in', city is non-empty, and state is
    non-empty — those become Latin-script regional rows tagged ``en``.
    """
    yielded = 0
    with _open_maybe_gz(path) as fh:
        header = fh.readline().rstrip("\n").split("\t")
        col = {name: i for i, name in enumerate(header)}
        required = ("name", "city", "state", "country_code")
        for r in required:
            if r not in col:
                print(
                    f"ERROR: OSMNames TSV missing required column '{r}'. "
                    f"Header was: {header[:8]}...",
                    file=sys.stderr,
                )
                return

        for raw in fh:
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < len(header):
                continue
            if parts[col["country_code"]].lower() != "in":
                continue
            name = parts[col["name"]].strip()
            city = parts[col["city"]].strip()
            state = parts[col["state"]].strip()
            if not name or not city or not state:
                continue
            # Pincode column is optional in some dumps; keep flexible.
            pincode = ""
            if "postcode" in col:
                pincode = parts[col["postcode"]].strip()

            input_parts = [name, city, state]
            if pincode:
                input_parts.append(pincode)
            input_str = ", ".join(input_parts[:-1]) + (
                f" {input_parts[-1]}" if pincode else ""
            )

            expected: dict[str, str] = {"city": city, "state": state}
            if pincode:
                expected["pincode"] = pincode

            yield {
                "input": input_str,
                "expected": expected,
                "language": "en",
                "source": "osmnames",
            }
            yielded += 1
            if limit is not None and yielded >= limit:
                return


# --- Overpass -----------------------------------------------------------------

def _overpass_query(area_name: str, lang: str) -> str:
    # Pull nodes+ways inside the named area that carry both name:<lang>
    # and addr:postcode (so we get something we can score against).
    return f"""
[out:json][timeout:60];
area["name"="{area_name}"]["boundary"="administrative"]->.a;
(
  node(area.a)["name:{lang}"]["addr:postcode"];
  way(area.a)["name:{lang}"]["addr:postcode"];
);
out tags 200;
""".strip()


def _overpass_fetch(query: str, max_attempts: int = 5) -> dict:
    """POST to Overpass with exponential backoff on HTTP 429/504.

    The public instance returns 429 when its slot pool is empty. Wait
    longer each retry (8s, 16s, 32s, 64s) before giving up.
    """
    data = ("data=" + query).encode("utf-8")
    delay = 8.0
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            OVERPASS_URL,
            data=data,
            headers={"User-Agent": "bharataddress-gold-builder/0.4 (open source)"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_exc = e
            if e.code in (429, 504) and attempt < max_attempts:
                print(
                    f"    HTTP {e.code}, backing off {delay:.0f}s "
                    f"(attempt {attempt}/{max_attempts})",
                    file=sys.stderr,
                )
                time.sleep(delay)
                delay *= 2
                continue
            raise
        except Exception as e:
            last_exc = e
            raise
    assert last_exc is not None
    raise last_exc


def iter_overpass(
    limit_per_city: int | None,
    langs: tuple[str, ...] | None = None,
) -> Iterator[dict]:
    for city, state, lang, area, lang_tag in OVERPASS_CITIES:
        if langs and lang not in langs:
            continue
        print(f"  overpass: {city} ({lang})...", file=sys.stderr)
        try:
            payload = _overpass_fetch(_overpass_query(area, lang_tag))
        except Exception as e:  # network/timeout/HTTP — log and skip
            print(f"    skipped ({e})", file=sys.stderr)
            time.sleep(1.0)
            continue

        seen_in_city = 0
        for el in payload.get("elements", []):
            tags = el.get("tags") or {}
            native_name = tags.get(f"name:{lang_tag}")
            postcode = tags.get("addr:postcode")
            if not native_name or not postcode:
                continue
            # Optional structural fields — keep what's there.
            addr_city = tags.get("addr:city") or city
            street = tags.get("addr:street")
            housenumber = tags.get("addr:housenumber")

            input_parts: list[str] = []
            if housenumber:
                input_parts.append(str(housenumber))
            if street:
                input_parts.append(str(street))
            input_parts.append(native_name)
            input_parts.append(addr_city)
            input_str = ", ".join(input_parts) + f" {postcode}"

            expected: dict[str, str] = {
                "city": addr_city,
                "state": state,
                "pincode": str(postcode),
            }
            if street:
                expected["locality"] = str(street)
            if housenumber:
                expected["building_number"] = str(housenumber)

            yield {
                "input": input_str,
                "expected": expected,
                "language": lang,
                "source": f"overpass:{lang_tag}",
            }
            seen_in_city += 1
            if limit_per_city is not None and seen_in_city >= limit_per_city:
                break

        # Be polite to the public Overpass instance.
        time.sleep(1.0)


# --- driver -------------------------------------------------------------------

def write_jsonl(rows: Iterable[dict], out_path: Path, append: bool = False) -> int:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    mode = "a" if append else "w"
    with out_path.open(mode, encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            n += 1
    return n


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Build Tier B candidate rows for gold_500."
    )
    p.add_argument(
        "--osmnames",
        type=Path,
        help="Path to OSMNames India TSV dump (.tsv or .tsv.gz). "
             "Get it from https://osmnames.org/ (CC-BY).",
    )
    p.add_argument(
        "--overpass",
        action="store_true",
        help="Fetch native-script rows from the Overpass API "
             "(6 cities, ~6 requests, rate-limited).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help=f"Output JSONL path (default: {DEFAULT_OUT.relative_to(REPO_ROOT)})",
    )
    p.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Cap rows per source (per-city for Overpass).",
    )
    p.add_argument(
        "--langs",
        type=str,
        default=None,
        help="Comma-separated language codes to restrict Overpass to "
             "(e.g. 'bn,ml'). Defaults to all 6 supported scripts.",
    )
    p.add_argument(
        "--append",
        action="store_true",
        help="Append to --out instead of overwriting. Use this when "
             "topping up after a partial 429 failure.",
    )
    args = p.parse_args(argv)

    if not args.osmnames and not args.overpass:
        print(
            "ERROR: pass at least one of --osmnames PATH or --overpass",
            file=sys.stderr,
        )
        return 2

    rows: list[dict] = []

    if args.overpass:
        print("Fetching Overpass native-script rows...", file=sys.stderr)
        langs = tuple(s.strip() for s in args.langs.split(",")) if args.langs else None
        rows.extend(iter_overpass(limit_per_city=args.limit, langs=langs))

    if args.osmnames:
        if not args.osmnames.exists():
            print(f"ERROR: OSMNames file not found: {args.osmnames}", file=sys.stderr)
            return 2
        print(f"Reading OSMNames dump: {args.osmnames}", file=sys.stderr)
        rows.extend(iter_osmnames(args.osmnames, limit=args.limit))

    n = write_jsonl(rows, args.out, append=args.append)
    print(
        f"\nWrote {n} candidate rows to {args.out}\n"
        f"  (gitignored — review and hand-promote into gold_500.jsonl)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
