"""Evaluate bharataddress against tests/data/gold_200.jsonl.

Reports per-field precision / recall / F1, overall exact-match rate, and a
dump of every failing case (row number + which fields disagreed). Pass
``--verbose`` to also print the full input string and expected/actual values
for each failure — off by default so private gold sets cannot leak addresses
into terminal scrollback or CI logs.

Usage:
    python scripts/evaluate.py
    python scripts/evaluate.py --fail-only
    python scripts/evaluate.py --verbose                # show full addresses
    python scripts/evaluate.py --json reports/eval.json
    python scripts/evaluate.py --gold path/to/other.jsonl
    python scripts/evaluate.py --gold private/processed/gold_500.jsonl \\
        --private-report --json private/reports/eval_gold_500.json

Notes
-----
A field "matches" if **both** are None, or **both** are non-None and one is a
case-insensitive substring of the other. Substring matching tolerates minor
differences like "Bangalore" vs "Bangalore Urban" or "Sector 31" vs "Sector
31, Gurgaon", which is the same matcher the unit tests in tests/test_parse.py
use. The evaluator never makes a network call.

Privacy
-------
- Default failure output is row number + mismatched field names only. No
  addresses, no expected/actual values. Use ``--verbose`` to override (only
  for the public gold set).
- ``--private-report`` requires the ``--json`` target path to live under
  ``private/reports/``. It refuses to write report JSON anywhere else, so
  results from a private gold set cannot land in the public ``reports/``
  directory by accident.
- The full report JSON contains failure details (input + expected + actual).
  When evaluating private data, always pair ``--json`` with
  ``--private-report`` so that JSON lands inside ``private/reports/``.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from bharataddress import parse

GOLD_PATH = Path(__file__).resolve().parents[1] / "tests" / "data" / "gold_200.jsonl"

FIELDS: tuple[str, ...] = (
    "building_number",
    "building_name",
    "landmark",
    "locality",
    "sub_locality",
    "city",
    "district",
    "state",
    "pincode",
)


def _norm(value: object) -> str | None:
    if value is None:
        return None
    s = str(value).strip().lower()
    return s or None


def _field_match(expected: object, actual: object) -> bool:
    e = _norm(expected)
    a = _norm(actual)
    if e is None and a is None:
        return True
    if e is None or a is None:
        return False
    return e in a or a in e


def load_gold(path: Path) -> list[dict]:
    cases: list[dict] = []
    with path.open(encoding="utf-8") as f:
        for line_no, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                cases.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"WARN: line {line_no} not valid JSON: {e}", file=sys.stderr)
    return cases


def _empty_counters() -> dict[str, dict[str, int]]:
    return {f: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for f in FIELDS}


def _is_native_script(text: str) -> bool:
    """True if any character is in a v0.4 supported Indic Unicode block.

    The eval auto-detects native-script gold rows so they get
    ``parse(..., transliterate=True)`` without requiring an explicit field on
    every row. Mirrors the block list in ``preprocessor._SCRIPT_BLOCKS``.
    """
    for ch in text:
        cp = ord(ch)
        if cp < 0x80:
            continue
        if (
            0x0900 <= cp <= 0x097F
            or 0x0980 <= cp <= 0x09FF
            or 0x0B80 <= cp <= 0x0BFF
            or 0x0C00 <= cp <= 0x0C7F
            or 0x0C80 <= cp <= 0x0CFF
            or 0x0D00 <= cp <= 0x0D7F
        ):
            return True
    return False


def _finalise(
    counters: dict[str, dict[str, int]], total: int, exact_matches: int
) -> dict:
    per_field: dict[str, dict] = {}
    for f in FIELDS:
        c = counters[f]
        tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (
            (2 * precision * recall / (precision + recall))
            if (precision + recall)
            else 0.0
        )
        per_field[f] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }
    return {
        "total": total,
        "exact_match": exact_matches,
        "exact_match_rate": round(exact_matches / total, 4) if total else 0.0,
        "per_field": per_field,
    }


def evaluate(cases: list[dict]) -> dict:
    counters = _empty_counters()
    # Per-language buckets. Each bucket carries its own counters and totals.
    lang_counters: dict[str, dict[str, dict[str, int]]] = defaultdict(_empty_counters)
    lang_totals: dict[str, int] = defaultdict(int)
    lang_exact: dict[str, int] = defaultdict(int)

    failures: list[dict] = []
    exact_matches = 0

    for case in cases:
        raw_input = case.get("input", "")
        expected = case.get("expected", {}) or {}
        # Language tag: explicit field wins, otherwise default "en". v0.4 gold
        # rows carry a language field; pre-v0.4 rows inherit "en".
        lang = case.get("language") or "en"
        lang_totals[lang] += 1

        # Auto-route native-script input through the transliteration shim so
        # eval doesn't need a separate flag per row. ASCII rows go through the
        # default path unchanged.
        if _is_native_script(raw_input):
            actual = parse(raw_input, transliterate=True).to_dict()
        else:
            actual = parse(raw_input).to_dict()

        case_ok = True
        per_field_ok: dict[str, bool] = {}
        for f in FIELDS:
            e = expected.get(f)
            a = actual.get(f)
            ok = _field_match(e, a)
            per_field_ok[f] = ok
            if not ok:
                case_ok = False

            e_present = _norm(e) is not None
            a_present = _norm(a) is not None
            c = counters[f]
            lc = lang_counters[lang][f]
            if e_present and a_present:
                if ok:
                    c["tp"] += 1
                    lc["tp"] += 1
                else:
                    # Wrong value: counts as both a missed gold and a hallucination.
                    c["fn"] += 1
                    c["fp"] += 1
                    lc["fn"] += 1
                    lc["fp"] += 1
            elif e_present and not a_present:
                c["fn"] += 1
                lc["fn"] += 1
            elif a_present and not e_present:
                c["fp"] += 1
                lc["fp"] += 1
            else:
                c["tn"] += 1
                lc["tn"] += 1

        if case_ok:
            exact_matches += 1
            lang_exact[lang] += 1
        else:
            failures.append(
                {
                    "input": raw_input,
                    "expected": expected,
                    "actual": actual,
                    "mismatched_fields": [f for f, ok in per_field_ok.items() if not ok],
                    "language": lang,
                }
            )

    total = len(cases)
    report = _finalise(counters, total, exact_matches)
    # Per-language block: stable alphabetical order so report diffs are clean.
    per_language: dict[str, dict] = {}
    for lang in sorted(lang_totals):
        per_language[lang] = _finalise(
            lang_counters[lang], lang_totals[lang], lang_exact[lang]
        )
    report["per_language"] = per_language
    report["failures"] = failures
    return report


def print_report(report: dict, fail_only: bool, verbose: bool = False) -> None:
    total = report["total"]
    em = report["exact_match"]
    rate = report["exact_match_rate"]

    if not fail_only:
        print()
        print("bharataddress evaluation against gold_200")
        print("=" * 60)
        print(f"Total cases:       {total}")
        print(f"Exact-match cases: {em} ({rate * 100:.1f}%)")
        print()
        print("Per-field metrics:")
        header = f"  {'field':<18} {'P':>7} {'R':>7} {'F1':>7}    {'TP':>4} {'FP':>4} {'FN':>4} {'TN':>4}"
        print(header)
        print("  " + "-" * (len(header) - 2))
        for f, m in report["per_field"].items():
            print(
                f"  {f:<18} {m['precision']:>7.3f} {m['recall']:>7.3f} {m['f1']:>7.3f}    "
                f"{m['tp']:>4} {m['fp']:>4} {m['fn']:>4} {m['tn']:>4}"
            )

        per_language = report.get("per_language") or {}
        if len(per_language) > 1:
            print()
            print("Per-language F1 (component breakdown):")
            field_short = {
                "building_number": "bldg#",
                "building_name": "bldgN",
                "landmark": "lmk",
                "locality": "loc",
                "sub_locality": "subloc",
                "city": "city",
                "district": "dist",
                "state": "state",
                "pincode": "pin",
            }
            header_cols = " ".join(f"{field_short[f]:>6}" for f in FIELDS)
            print(f"  {'lang':<6} {'rows':>5} {'em%':>6}  {header_cols}")
            print("  " + "-" * (6 + 1 + 5 + 1 + 6 + 2 + len(header_cols)))
            for lang, block in per_language.items():
                rows = block["total"]
                em_pct = block["exact_match_rate"] * 100
                f1s = " ".join(
                    f"{block['per_field'][f]['f1']:>6.3f}" for f in FIELDS
                )
                print(f"  {lang:<6} {rows:>5} {em_pct:>5.1f}%  {f1s}")

    failures = report["failures"]
    if failures:
        print()
        print(f"Failures ({len(failures)} of {total}):")
        print("-" * 60)
        if not verbose:
            print("(addresses suppressed; pass --verbose to show them)")
        for i, fail in enumerate(failures, 1):
            mismatched = ", ".join(fail["mismatched_fields"]) or "(none)"
            if verbose:
                print(f"\n[{i}] input: {fail['input']!r}")
                print(f"    mismatched: {mismatched}")
                for f in fail["mismatched_fields"]:
                    e = fail["expected"].get(f)
                    a = fail["actual"].get(f)
                    print(f"      {f}: expected {e!r}, got {a!r}")
            else:
                print(f"  [{i}] mismatched: {mismatched}")
    elif not fail_only:
        print("\nNo failures.")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Evaluate bharataddress against the gold_200 test set."
    )
    p.add_argument("--gold", type=Path, default=GOLD_PATH, help="Path to gold JSONL")
    p.add_argument(
        "--fail-only",
        action="store_true",
        help="Skip the per-field summary and only print failing cases",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help=(
            "Print full input addresses and expected/actual values for "
            "every failing case. OFF by default so private gold sets cannot "
            "leak addresses into terminal scrollback or CI logs."
        ),
    )
    p.add_argument("--json", type=Path, help="Write the full report as JSON to this path")
    p.add_argument(
        "--private-report",
        action="store_true",
        help=(
            "Require the --json target to live under private/reports/. "
            "Use this whenever --gold points at a private gold set, so the "
            "report cannot land in the public reports/ directory by accident."
        ),
    )
    args = p.parse_args(argv)

    if not args.gold.exists():
        print(f"ERROR: gold file not found: {args.gold}", file=sys.stderr)
        return 2

    if args.private_report:
        if args.json is None:
            print(
                "ERROR: --private-report requires --json to be set",
                file=sys.stderr,
            )
            return 2
        try:
            json_resolved = args.json.resolve()
            private_root = (Path(__file__).resolve().parents[1] / "private" / "reports").resolve()
            json_resolved.relative_to(private_root)
        except ValueError:
            print(
                f"ERROR: --private-report requires --json under private/reports/, "
                f"got: {args.json}",
                file=sys.stderr,
            )
            return 2

    cases = load_gold(args.gold)
    if not cases:
        print(f"ERROR: no cases loaded from {args.gold}", file=sys.stderr)
        return 2

    report = evaluate(cases)
    print_report(report, fail_only=args.fail_only, verbose=args.verbose)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nFull report written to {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
