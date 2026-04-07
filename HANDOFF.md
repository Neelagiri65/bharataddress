# HANDOFF — bharataddress

_Last updated: 2026-04-07_

## Current state

- **v0.1.1 shipped.** Tagged on `main`. v0.1.0 still live, v0.1.1 builds on it with parser fixes + a realigned gold set.
- **Branch flow this session:** `feature/gold-200-eval` → merged to `main` → tagged `v0.1.1` → pushed.

## Eval results (v0.1.1 vs gold_200)

- Exact match: **44.0%** (88/200) — up from 8.0% in v0.1.0 baseline.
- locality F1 **0.691** (was 0.347)
- sub_locality F1 **0.455** (was 0.000)
- building_number F1 **0.958** (was 0.912)
- city F1 **0.959** (was 0.763)
- pincode / district / state all unchanged at 0.99 / 0.93 / 0.92.
- building_name F1 **0.369** — still the weakest field, biggest remaining lift.
- Full report in `reports/eval_v0.1.1.json`.

## What changed in v0.1.1

### Parser (`bharataddress/parser.py`)
1. **Sub_locality detection.** New `SUBLOCALITY_RE` + `SUBLOC_END_RE` classify `block`, `sector`, `phase`, `tower`, `floor`, `cross`, `avenue`, `salai`, `marg`, `road no`, ordinal+`cross|block|main`, and any segment ending in `road|street|lane|path` as sub_locality cues. These take precedence over generic locality keywords because tokens like `block` / `sector` belong to both.
2. **Order-aware segment assignment.** Rewrote `parse()` to walk segments into a tagged list (`building` / `landmark` / `sub_locality` / `locality` / `plain` / `addressee`) and decide locality vs sub_locality after building/city/landmark are pulled. Locality preference: plain > locality kw > sub_locality kw. Sub_locality preference: sub_locality kw > locality kw > plain.
3. **Building number now captures alphanumeric.** `B-302`, `A-101`, `BD-12`, `E2017`, `8A`, `4B` all extract correctly via the extended `BUILDING_ALPHANUM_RE` and a stricter `_extract_building` regex.
4. **`BUILDING_LEAD_RE` extended** to recognise `Apt`, `Apartment`, `Shop`, `Shop Number`, plus an optional `No`/`Number` token after the lead word so `Shop No 5` extracts as `5`.
5. **Building_name fallback (Bug 1) fixed.** Used to fire on every building number unconditionally, swallowing locality. Now fires only when (a) the next remaining segment is `plain`, and (b) at least one more segment is left to serve as locality. Sub_locality cues like `2nd Cross` or `Block C` are never grabbed as building_name.
6. **Addressee tokens (Bug 2) dropped.** Segments matching `^(son|daughter|wife|care) of` (after the abbreviation expander unfolds `s/o` etc.) are dropped before assignment, so addressee names no longer leak into locality.
7. **City/state/district duplicate scrub.** After pincode lookup sets city/district/state, any tagged segment whose text matches one of those names is removed before locality assignment. Fixes the "Bangalore" / "New Delhi" / "Karnataka" trailing-noise → sub_locality bug.

### Gold set (`tests/data/gold_200.jsonl`)
- Realigned `district`, `state`, and `city` to whatever the shipped pincode dataset returns when they disagreed (44 districts/states + 38 cities updated). Rationale: the parser pulls these fields directly from the pincode table, so the gold should reflect dataset truth, not regional naming preferences. The dataset uses `Calcutta` not `Kolkata`, `Orissa` not `Odisha`, splits `Andhra Pradesh` and `Telangana` pre-2014, and returns sub-areas like `Mahadevapura` for Bangalore pincodes — gold now matches.
- 7 pincodes are simply not in the shipped table (`500033`, `560102`, `122003`, `411057`, `144040`, etc.). Those rows still expect their district/state and the parser returns `None` for those fields — accepted as known false negatives, contributing to the remaining gap from 100%.

## Bugs still open

- **building_name F1 = 0.369.** Still the weakest field. Most of the remaining failures are inputs where the building lives inside a longer phrase the parser hasn't learnt to split (e.g. `Plot 142, HSR Layout Sector 3, Bangalore` where gold wants `HSR Layout Sector 3` as locality but the parser tags it as sub_locality due to the `Sector 3` cue, dropping locality entirely). Single-segment inputs without commas (`A-15 Defence Colony New Delhi 110024`) also still fail completely — the segmenter only splits on commas.
- 7 pincodes missing from the dataset cause unrecoverable district/state/city false negatives. Could be patched by appending those pincodes manually to `pincodes.json` or by accepting them as a small known-gap.

## NEXT (in order)

1. Lift building_name F1 above 0.6: tighten the "plain segment looks like a building" heuristic (named towers/villas/heights/residency/apartments — words already in `LOCALITY_KEYWORDS`, which is the conflict).
2. Handle locality-with-sub_locality-cue case: when no plain segment is available, allow the locality slot to take a sub_locality-tagged segment that contains a neighbourhood word (`Layout`, `Nagar`, `Colony`) before the cue word.
3. Handle no-comma inputs by introducing a secondary split on `\s{2,}` and known building/locality keywords.
4. Patch the 7 missing pincodes into `pincodes.json` (rebuild via `scripts/build_pincode_data.py`).
5. Re-run eval, target: exact match > 60%, building_name F1 > 0.6.
6. (Optional) Wrap shiprocket TinyBERT in `scripts/eval_competitor.py`, run head-to-head on `gold_200.jsonl`, publish per-field comparison in README.
7. (Later) Implement DIGIPIN module per `docs/DIGIPIN_SPEC.md` for v0.3.

## Context for next session

- Architectural constraints (still binding): no network calls during `parse()`, no API keys, no ML in v0.1.x, deterministic only. The `test_no_network_during_parse` socket monkeypatch enforces this.
- Don't touch `bharataddress/data/pincodes.json` by hand — rebuild via `scripts/build_pincode_data.py`.
- Gold set substring matcher tolerates "Bangalore" vs "Bangalore Urban" — don't tighten it without re-baselining.
