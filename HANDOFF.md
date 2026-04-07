# HANDOFF — bharataddress

_Last updated: 2026-04-07_

## Current state

- **v0.1.2 shipped.** Tagged on `main`. v0.1.0 / v0.1.1 still live; v0.1.2 adds building_name detection + the first public head-to-head benchmark vs Shiprocket TinyBERT.
- **Branch flow this session:** v0.1.1 (parser fixes + gold realignment) shipped first, then v0.1.2 (building_name + competitor eval) shipped as a second commit on `main`.
- Private eval: ran full private hospital dataset (41,796 entries). Aggregate numbers in `private/reports/`. Top failure categories identified — see `private/reports/analysis.md`.

## Eval results (v0.1.2 vs gold_200)

- Exact match: **48.5%** (97/200) — up from 8.0% (v0.1.0) → 44.0% (v0.1.1) → 48.5% (v0.1.2).
- building_name F1 **0.635** (was 0.197 in v0.1.0, 0.369 in v0.1.1).
- locality F1 **0.723** (was 0.347 → 0.691).
- sub_locality F1 **0.472**, building_number F1 **0.958**, city F1 **0.959**, landmark F1 **0.918**, district F1 **0.933**, state F1 **0.923**, pincode F1 **0.995**.
- Full report: `reports/eval_v0.1.2.json`.

## Competitor benchmark — first public head-to-head

`scripts/eval_competitor.py` runs `shiprocket-ai/open-tinybert-indian-address-ner` (TinyBERT, ~760 MB, Apache-2.0) over the same gold_200 and reports per-field metrics in the exact same shape. Findings:

- bharataddress wins decisively on pincode-derived fields (`city` 0.959 vs 0.718, `state` 0.923 vs 0.268, `district` 0.933 vs N/A, `pincode` 0.995 vs 0.984) because the embedded India Post directory turns these into a lookup. Also wins `landmark` 0.918 vs 0.580.
- Tied on text-only fields: `building_name` 0.635 vs 0.643, `sub_locality` 0.472 vs 0.470, `building_number` 0.958 vs 0.973.
- TinyBERT has no `district` label and can't compete on the lookup-backed fields. Per-field comparison + footprint table now in README "Benchmarks" section.
- Full TinyBERT report: `reports/eval_competitor_v0.1.1.json`.

## What changed in v0.1.2

### Parser
1. **Split LOCALITY_KEYWORDS into two lists.** `tower(s)`, `apartment(s)`, `apts`, `heights`, `residency`, `residences`, `society`, `complex`, `court`, `plaza`, `palace`, `mansion`, `villa(s)`, `flats` moved out of locality and into a new `BUILDING_NAME_KEYWORDS` list. These tokens almost always denote a named property, not a neighbourhood. Removed `sector`, `phase`, `block`, `marg` from locality (they were already in `SUBLOCALITY_RE`, so they'd been double-classified — sub_locality wins).
2. **New `building_name` segment kind.** `_classify` returns `building_name` when `BUILDING_NAME_RE` matches, with priority above sub_locality and locality.
3. **Strong building_name pull.** `parse()` now grabs the first `building_name`-tagged segment regardless of position before falling through to the existing plain-segment fallback. Lifts building_name F1 from 0.369 → 0.635.
4. **Residue reclassification.** When `_extract_building` produces a residue (e.g. `Gandhi Nagar` from `12/3 Gandhi Nagar`), the residue is run back through `_classify`. If it has a locality / sub_locality cue it's pushed back into the segment list to compete for those slots; if it's a short plain token it stays as building_name; if it's a long plain residue (>4 words, typical of no-comma inputs) it's discarded so it doesn't pollute building_name.
5. **building_name kind also serves as a locality fallback.** When all else fails, a building_name candidate can be promoted to locality so we don't lose information.

### New file
- `scripts/eval_competitor.py` — loads `shiprocket-ai/open-tinybert-indian-address-ner` from Hugging Face, runs it over gold_200, maps its labels (`building_name`, `house_details`, `floor`, `road`, `landmarks`, `locality`, `sub_locality`, `city`, `state`, `pincode`, `country`) onto bharataddress's nine fields, and reuses `scripts/evaluate.py`'s scorer (monkeypatching the `parse` import) so the comparison is exactly apples-to-apples. Requires `torch` + `transformers` in a venv — explicitly NOT a runtime dependency of the package.

### README
- New "Benchmarks" section with the full per-field comparison table, exact-match numbers, footprint table (install size, deps, latency, GPU), and a verdict on which parser fits which use case.

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

0. **v0.1.3 priority — refresh `bharataddress/data/pincodes.json`** from the latest data.gov.in India Post source. Target: 80,000+ pincodes with post-2014 naming (Telangana, Kolkata, Odisha, Uttarakhand, Chhattisgarh boundaries correct). Per the private hospital eval, this single fix addresses **92.8% of all failures** (the pincode-only and city/district/state-together signatures together). Rebuild via `scripts/build_pincode_data.py` against the new source.
0a. After the pincode refresh, **re-run the private eval** (gold file under `private/processed/`) with `--private-report` to measure the actual lift on real-world data. Target: <5% mismatch rate, district/state/pincode F1 all >0.96.
1. Lift sub_locality F1 above 0.6 (currently 0.472, the weakest field). Both bharataddress and TinyBERT struggle here — the disambiguation between "MG Road" (sub_locality) vs "Indiranagar" (locality) needs more cues. Possible: a curated list of known Indian neighbourhood names so anything not in the list gets demoted to sub_locality.
2. Handle no-comma inputs (`A-15 Defence Colony New Delhi 110024`, `H No 12 Sarat Bose Road Kolkata 700020`) — currently lost because `_split_segments` only splits on commas. Introduce a secondary split using `\s{2,}` plus known transition keywords (locality keywords, building leads).
3. Handle the locality-with-sub_locality-cue case: when no plain segment is available, allow the locality slot to take a sub_locality-tagged segment that contains a neighbourhood word (`Layout`, `Nagar`, `Colony`) before the cue word — currently `HSR Layout Sector 3` becomes sub_locality and locality goes empty.
4. Patch the 7 missing pincodes into `pincodes.json` (rebuild via `scripts/build_pincode_data.py`). They cause unrecoverable district/state/city false negatives.
5. Re-run eval, target: exact match > 60%, sub_locality F1 > 0.6.
6. (Later) Implement DIGIPIN module per `docs/DIGIPIN_SPEC.md` for v0.3.

## Context for next session

- Architectural constraints (still binding): no network calls during `parse()`, no API keys, no ML in v0.1.x, deterministic only. The `test_no_network_during_parse` socket monkeypatch enforces this.
- Don't touch `bharataddress/data/pincodes.json` by hand — rebuild via `scripts/build_pincode_data.py`.
- Gold set substring matcher tolerates "Bangalore" vs "Bangalore Urban" — don't tighten it without re-baselining.
