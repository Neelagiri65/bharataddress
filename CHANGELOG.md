# Changelog

All notable changes to `bharataddress` are recorded here.

## v0.4.0 — 2026-04-09

The multilingual / vernacular release.

### Added
- **Opt-in transliteration shim** for 6 Indic scripts: Devanagari (hi),
  Bengali (bn), Tamil (ta), Telugu (te), Kannada (kn), Malayalam (ml).
  Install via `pip install bharataddress[indic]` and pass
  `parse(addr, transliterate=True)` (Python API) or
  `bharataddress parse --transliterate "<addr>"` (CLI). The optional
  extras pull in `indic-transliteration` (~162 kB, pure Python). Core
  install remains zero-dependency.
- **Per-language vernacular mappings** under `bharataddress/data/mappings/`.
  409 total entries across 7 files: `common.json` (161 pan-Indian terms)
  plus per-language overlays for hi/ta/te/kn/bn/ml. The matcher resolves
  pincode → state → language code at preprocess time and only loads the
  relevant overlay. Common.json always wins.
- **Per-language F1 in `scripts/evaluate.py`**. The report grows a new
  additive `per_language` block keyed by language code, each carrying its
  own `total`, `exact_match`, `exact_match_rate`, and `per_field` (same
  shape as the top-level block). Failures gain a `language` tag. The
  evaluator auto-routes native-script gold rows through
  `parse(transliterate=True)` based on Unicode block detection — no
  per-row flag needed. Single-language eval is byte-identical to v0.3
  output.
- **Tier B candidate scraper** at `scripts/build_gold_tier_b.py`. Pulls
  open data from OSMNames (CC-BY, Latin regional rows) and the Overpass
  API (native-script rows for the 6 supported scripts). Output is
  gitignored and hand-promoted. Includes exponential backoff on HTTP
  429/504 and a `--langs`/`--append` workflow for partial retries.
- **Pincode dataset sanity check** at `scripts/crosscheck_pincodes.py`.
  Fully offline internal consistency report — buckets pincodes by 3-digit
  prefix and flags any prefix that maps to 3+ states. Sanity log, not a
  gate. Output: `reports/pincode_crosscheck.md`.
- **`tests/data/SOURCES.md`** documenting provenance, licences, and the
  AI4Bharat / BSTD rejection rationale for v0.4 gold sources.

### Changed
- `preprocess()` now extracts the pincode **before** vernacular
  normalisation, so the language-aware matcher can pick the correct
  per-language overlay from the start.
- `bharataddress.data` package data now includes `mappings/*.json`.
- `parse()` accepts a new `transliterate: bool = False` keyword argument.
  When `True`, native-script input is transliterated to ITRANS Latin
  before parsing; the original string is preserved on `ParsedAddress.raw`,
  the Latin form on `ParsedAddress.cleaned`. Default behaviour is
  unchanged.

### Architectural constraints (still binding)
- `parse()` makes **zero** network calls. Enforced by an extended socket
  monkeypatch test that now also covers `parse(transliterate=True)`.
- Core import works without `indic-transliteration` installed; the
  optional extras only load on demand. Locked by `tests/test_no_indic_dep.py`.
- v0.3 English regression gate: every per-field F1 on `gold_200.jsonl`
  must stay within ±0.02 of the v0.3.0 baseline. Locked by
  `tests/test_en_regression_gate.py` against `tests/data/v03_baseline.json`.

### Tests
162 tests passing (up from 137 in v0.3). New tests:
`test_no_indic_dep.py`, `test_no_network_v04.py`, `test_en_regression_gate.py`,
`test_language_mapping.py`, `test_vernacular_coverage.py`,
`test_transliteration.py`, `test_evaluate_per_language.py`,
`test_cli_transliterate.py`.

## v0.3.0 — 2026-04
- Phonetic alias matching + Nominatim online geocoding (opt-in).

## v0.2.2 — 2026-03
- Pincode directory rebuild, README PyPI badge.
