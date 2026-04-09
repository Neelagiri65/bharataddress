"""v0.4 architectural constraint: no English/Latin regression vs the v0.3 baseline.

Locks the per-component F1 floor for the existing 200-row Latin gold set. Every
component must stay within ±0.02 of the v0.3.0 numbers recorded in
``tests/data/v03_baseline.json``. If this gate fires during v0.4 work, the offending
change is the problem — fix the change, do not move the baseline.

Run with: ``PYTHONPATH=. python3 -m pytest tests/test_en_regression_gate.py -q``
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BASELINE_PATH = REPO_ROOT / "tests" / "data" / "v03_baseline.json"

# v0.4 issue #6 will rename gold_200.jsonl -> gold_200_v03.jsonl and freeze it.
# Until that lands, the regression gate reads whichever exists.
_FROZEN = REPO_ROOT / "tests" / "data" / "gold_200_v03.jsonl"
_CURRENT = REPO_ROOT / "tests" / "data" / "gold_200.jsonl"
GOLD_PATH = _FROZEN if _FROZEN.exists() else _CURRENT


def _load_baseline() -> dict:
    return json.loads(BASELINE_PATH.read_text())


def _run_evaluator() -> dict:
    """Invoke scripts/evaluate.evaluate() programmatically against the frozen gold."""
    sys.path.insert(0, str(REPO_ROOT))
    from scripts import evaluate as ev  # noqa: PLC0415

    cases = ev.load_gold(GOLD_PATH)
    return ev.evaluate(cases)


def test_en_regression_gate_within_tolerance() -> None:
    baseline = _load_baseline()
    tolerance = baseline["tolerance"]
    expected = baseline["per_field_f1"]

    report = _run_evaluator()
    actual = {f: round(m["f1"], 3) for f, m in report["per_field"].items()}

    regressions: list[str] = []
    for field, baseline_f1 in expected.items():
        current_f1 = actual.get(field)
        assert current_f1 is not None, f"evaluator did not report F1 for {field}"
        delta = current_f1 - baseline_f1
        if delta < -tolerance:
            regressions.append(
                f"{field}: baseline={baseline_f1:.3f} current={current_f1:.3f} "
                f"delta={delta:+.3f} (tolerance={tolerance})"
            )

    assert not regressions, (
        "v0.4 has regressed v0.3 English/Latin F1 beyond tolerance:\n  "
        + "\n  ".join(regressions)
    )
