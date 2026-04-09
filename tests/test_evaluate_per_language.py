"""v0.4 issue #5: per-language F1 breakdown in scripts/evaluate.py.

Locks the additive contract:
* The existing top-level ``per_field`` block is unchanged.
* A new ``per_language`` block is present, keyed by language code, each
  carrying its own ``total``, ``exact_match``, ``exact_match_rate``, and
  ``per_field`` (same shape as the top-level block).
* Cases without an explicit ``language`` field bucket into ``"en"``.
* The global numbers equal the sum of all per-language buckets.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from scripts import evaluate as ev  # noqa: E402


def _case(input_str: str, language: str | None, expected: dict) -> dict:
    case = {"input": input_str, "expected": expected}
    if language is not None:
        case["language"] = language
    return case


def test_per_language_block_exists_and_buckets_by_language() -> None:
    cases = [
        # Two clean Latin English rows (default to "en").
        _case(
            "Flat 302, MG Road, Bangalore 560001",
            None,
            {"city": "Bangalore", "state": "Karnataka", "pincode": "560001"},
        ),
        _case(
            "12, Park Street, Kolkata 700016",
            None,
            {"city": "Kolkata", "state": "West Bengal", "pincode": "700016"},
        ),
        # Explicitly tagged Hindi-belt row (still Latin script).
        _case(
            "5, Connaught Place, New Delhi 110001",
            "hi",
            {"city": "New Delhi", "state": "Delhi", "pincode": "110001"},
        ),
    ]
    report = ev.evaluate(cases)

    # Top-level shape unchanged.
    assert report["total"] == 3
    assert "per_field" in report
    assert "pincode" in report["per_field"]

    # Per-language block present and bucketed correctly.
    assert "per_language" in report
    pl = report["per_language"]
    assert set(pl.keys()) == {"en", "hi"}
    assert pl["en"]["total"] == 2
    assert pl["hi"]["total"] == 1
    # Each bucket carries its own per-field block of the same shape.
    for lang, block in pl.items():
        for field in ev.FIELDS:
            assert field in block["per_field"], f"{lang}: missing {field}"
            assert "f1" in block["per_field"][field]


def test_per_language_totals_sum_to_global_total() -> None:
    cases = [
        _case(
            "Flat 1, MG Road, Bangalore 560001",
            "en",
            {"city": "Bangalore", "pincode": "560001"},
        ),
        _case(
            "Flat 2, MG Road, Bangalore 560002",
            "en",
            {"city": "Bangalore", "pincode": "560002"},
        ),
        _case(
            "Door 3, Anna Salai, Chennai 600001",
            "ta",
            {"city": "Chennai", "pincode": "600001"},
        ),
    ]
    report = ev.evaluate(cases)
    pl_total = sum(b["total"] for b in report["per_language"].values())
    assert pl_total == report["total"]


def test_missing_language_field_defaults_to_en() -> None:
    cases = [
        _case(
            "12, MG Road, Bangalore 560001",
            None,  # no language field
            {"city": "Bangalore", "pincode": "560001"},
        ),
    ]
    report = ev.evaluate(cases)
    assert "en" in report["per_language"]
    assert report["per_language"]["en"]["total"] == 1


def test_failures_carry_language_tag() -> None:
    # An impossible-to-satisfy expected so we get a failure deterministically.
    cases = [
        _case(
            "12, MG Road, Bangalore 560001",
            "ta",
            {"city": "ZZ-NotARealCity", "pincode": "560001"},
        ),
    ]
    report = ev.evaluate(cases)
    assert report["failures"], "expected at least one failure"
    assert report["failures"][0]["language"] == "ta"


def test_native_script_input_auto_routes_through_transliterate() -> None:
    """An evaluation row with native-script input should be parsed via
    parse(transliterate=True) automatically — no explicit flag in the gold.
    Skipped if the optional extras package isn't installed."""
    import pytest

    pytest.importorskip("indic_transliteration")

    cases = [
        _case(
            "मुंबई, महाराष्ट्र 400001",
            "hi",
            {
                "city": "Mumbai",
                "district": "Mumbai",
                "state": "Maharashtra",
                "pincode": "400001",
            },
        ),
    ]
    report = ev.evaluate(cases)
    # If the auto-route works, this row is an exact match (Mumbai, Maharashtra,
    # 400001 all resolve from the pincode after transliteration).
    assert report["exact_match"] == 1, (
        f"native-script row didn't exact-match — auto-route failed. "
        f"Failures: {report['failures']}"
    )
