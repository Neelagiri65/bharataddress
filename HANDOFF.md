# HANDOFF — bharataddress

_Last updated: 2026-04-07_

## Current state

- **v0.1.0 shipped.** Live on GitHub: https://github.com/Neelagiri65/bharataddress, tagged `v0.1.0`. MIT, zero runtime deps, 23,915 pincodes bundled.
- **Active branch:** `feature/gold-200-eval` (pushed, **not merged**).
  - `tests/data/gold_200.jsonl` — 200 hand-labelled addresses across 8 categories
  - `scripts/evaluate.py` — per-field P/R/F1 + exact-match + failure dump
  - `reports/eval_v0.1.0.json` — first baseline run
- **Research docs landed today:**
  - `docs/DIGIPIN_SPEC.md` — 4-function API spec, vendor-the-algorithm decision, optional `bharataddress-boundaries` package for pincode→digipin GeoJSON
  - `docs/COMPETITOR_BENCHMARK.md` — 7 projects surveyed; **shiprocket-ai/open-tinybert-indian-address-ner** is the main ML competitor (Apache-2.0, claimed Micro F1 0.94 on private set, ~760 MB, no public test set)

## Eval baseline (v0.1.0 vs gold_200)

- Exact match: **8%** (16/200)
- Tier A (working): pincode F1 **0.995**, landmark 0.918, building_number 0.912, state 0.862
- Tier B (broken): locality F1 **0.347**, building_name 0.197, sub_locality **0.000**

## Known bugs (v0.1)

1. **building_name swallows locality.** The `expect_building_name` fallback in `bharataddress/parser.py` overfires: when the first segment is a number-only building token, the next unclassified segment is grabbed as building_name even when it's actually the locality.
2. **S/O abbreviation expansion pollutes locality.** `s/o` → `son of` runs before segment classification, so the addressee's name leaks into the locality field.
3. **sub_locality is never populated.** No rule ever assigns it. F1 = 0.000.

## Known gold-set errors

Caught on review, **not yet fixed in `gold_200.jsonl`**:
- Row 163 — district should be South Delhi for 110016
- Row 164 — 700089 is South 24 Parganas, not North
- Row 166 — 802301 is Arrah, not Bhojpur
- Estimate ~10 more wrong-district entries to audit before re-running eval.

## NEXT (in order)

1. Fix the ~10 wrong-district entries in `gold_200.jsonl` (start with rows 163, 164, 166).
2. Fix Bugs 1–3 in `bharataddress/parser.py`.
3. Re-run `scripts/evaluate.py --json reports/eval_v0.1.1.json`. Target: locality F1 > 0.6, sub_locality F1 > 0.3, exact match > 25%.
4. Merge `feature/gold-200-eval` to main.
5. Tag and ship **v0.1.1**.
6. (Optional) Wrap shiprocket TinyBERT in `scripts/eval_competitor.py`, run head-to-head on `gold_200.jsonl`, publish per-field comparison in README.
7. (Later) Implement DIGIPIN module per `docs/DIGIPIN_SPEC.md` for v0.3.

## Context for next session

- Architectural constraints (still binding): no network calls during `parse()`, no API keys, no ML in v0.1.x, deterministic only. The `test_no_network_during_parse` socket monkeypatch enforces this.
- Don't touch `bharataddress/data/pincodes.json` by hand — rebuild via `scripts/build_pincode_data.py`.
- Gold set substring matcher tolerates "Bangalore" vs "Bangalore Urban" — don't tighten it without re-baselining.
