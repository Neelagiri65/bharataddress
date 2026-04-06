"""Evaluate bharataddress against tests/data/gold_200.jsonl.

Reports per-field precision / recall / F1, overall exact-match rate, and a
verbose dump of every failing case (input + expected + actual + which fields
disagreed).

Usage:
    python scripts/evaluate.py
    python scripts/evaluate.py --fail-only
    python scripts/evaluate.py --json reports/eval.json
    python scripts/evaluate.py --gold path/to/other.jsonl

Notes
-----
A field "matches" if **both** are None, or **both** are non-None and one is a
case-insensitive substring of the other. Substring matching tolerates minor
differences like "Bangalore" vs "Bangalore Urban" or "Sector 31" vs "Sector
31, Gurgaon", which is the same matcher the unit tests in tests/test_parse.py
use. The evaluator never makes a network call.
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


def evaluate(cases: list[dict]) -> dict:
    counters: dict[str, dict[str, int]] = {
        f: {"tp": 0, "fp": 0, "fn": 0, "tn": 0} for f in FIELDS
    }
    failures: list[dict] = []
    exact_matches = 0

    for case in cases:
        raw_input = case.get("input", "")
        expected = case.get("expected", {}) or {}
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
            if e_present and a_present:
                if ok:
                    c["tp"] += 1
                else:
                    # Wrong value: counts as both a missed gold and a hallucination.
                    c["fn"] += 1
                    c["fp"] += 1
            elif e_present and not a_present:
                c["fn"] += 1
            elif a_present and not e_present:
                c["fp"] += 1
            else:
                c["tn"] += 1

        if case_ok:
            exact_matches += 1
        else:
            failures.append(
                {
                    "input": raw_input,
                    "expected": expected,
                    "actual": actual,
                    "mismatched_fields": [f for f, ok in per_field_ok.items() if not ok],
                }
            )

    per_field: dict[str, dict] = {}
    for f in FIELDS:
        c = counters[f]
        tp, fp, fn, tn = c["tp"], c["fp"], c["fn"], c["tn"]
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        per_field[f] = {
            "precision": round(precision, 3),
            "recall": round(recall, 3),
            "f1": round(f1, 3),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
        }

    total = len(cases)
    return {
        "total": total,
        "exact_match": exact_matches,
        "exact_match_rate": round(exact_matches / total, 4) if total else 0.0,
        "per_field": per_field,
        "failures": failures,
    }


def print_report(report: dict, fail_only: bool) -> None:
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

    failures = report["failures"]
    if failures:
        print()
        print(f"Failures ({len(failures)} of {total}):")
        print("-" * 60)
        for i, fail in enumerate(failures, 1):
            print(f"\n[{i}] input: {fail['input']!r}")
            print(f"    mismatched: {', '.join(fail['mismatched_fields']) or '(none)'}")
            for f in fail["mismatched_fields"]:
                e = fail["expected"].get(f)
                a = fail["actual"].get(f)
                print(f"      {f}: expected {e!r}, got {a!r}")
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
    p.add_argument("--json", type=Path, help="Write the full report as JSON to this path")
    args = p.parse_args(argv)

    if not args.gold.exists():
        print(f"ERROR: gold file not found: {args.gold}", file=sys.stderr)
        return 2

    cases = load_gold(args.gold)
    if not cases:
        print(f"ERROR: no cases loaded from {args.gold}", file=sys.stderr)
        return 2

    report = evaluate(cases)
    print_report(report, fail_only=args.fail_only)

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(f"\nFull report written to {args.json}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
