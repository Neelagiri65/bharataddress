# PRD — bharataddress v0.4 (multilingual / vernacular)

## Problem Statement
A large fraction of real Indian addresses are written in native scripts (Devanagari, Tamil, Telugu, Kannada, Bengali, Malayalam) or use Romanised vernacular terms ("Salai", "Veedhi", "Theru", "Para", "Mukku") that v0.3 doesn't recognise. Today `bharataddress` silently fails on these — it returns low-confidence garbage rather than a structured result. No open-source Indian address parser handles native scripts; community Q&A on the topic is effectively non-existent. v0.4 closes this gap and makes `bharataddress` the only `pip install`-able parser that reads Indian addresses in the language they're actually written in.

## User Story
As a Python developer ingesting addresses from Indian e-commerce, logistics, or government data sources, I want `parse("मुंबई, महाराष्ट्र 400001", transliterate=True)` and `parse("123, Anna Salai, T Nagar, Chennai 600017")` to both return a structured, validated `ParsedAddress` so that I can handle real-world Indian address data without dropping every non-English row on the floor.

## Acceptance Criteria
1. **Core stays zero-dep.** `pip install bharataddress` (no extras) succeeds, all v0.3 tests pass, and a new test imports `bharataddress` in an environment where `indic-transliteration` is *not* installed and parses a Latin address successfully.
2. **Extras work.** `pip install bharataddress[indic]` installs `indic-transliteration` (162 kB, pure Python, zero deps). `parse("मुंबई, महाराष्ट्र 400001", transliterate=True)` returns `city="Mumbai"`, `state="Maharashtra"`, `pincode="400001"`, `confidence > 0.7`.
3. **Six scripts supported via opt-in transliteration:** Devanagari (Hindi/Marathi), Tamil, Telugu, Kannada, Bengali, Malayalam. A representative test address in each script parses to the correct state and pincode.
4. **Vernacular mappings expanded from ~70 to 400+ terms**, organised as **per-language files** under `bharataddress/data/mappings/`:
   - `common.json` — shared/pan-Indian terms (Nagar, Colony, Road, Marg, Sector, Phase, Block, Tower, Apartments, …) — always loaded.
   - `hi.json`, `ta.json`, `te.json`, `kn.json`, `bn.json`, `ml.json` — language-specific terms, loaded conditionally based on pincode → state → primary language(s) of state.
   - Each file ≥40 entries (excluding common); common ≥80 entries. Total ≥400.
5. **Language-aware mapping application.** A test asserts that `Salai` (Tamil-only) fires on a Chennai address and does *not* fire on a Kolkata address; that `Veedhi` (Telugu-only) fires on a Hyderabad address; and that `Nagar` (common) fires everywhere. No flat global mapping table.
6. **Public gold expanded** from `gold_200.jsonl` to `gold_500.jsonl` with +300 new rows tagged by a new `language` field (`en`, `hi`, `ta`, `te`, `kn`, `bn`, `ml`). Per-language minimum: ≥40 rows for each of the 6 vernacular buckets. Sourcing: Tier A (≥50 hand-curated by user, real addresses) + Tier B (≤250 from OSM `name:xx` tags and Wikipedia infoboxes for Indian places, with attribution in `tests/data/SOURCES.md`).
7. **Per-language F1 reporting.** `scripts/evaluate.py` outputs a per-language breakdown: rows, exact-match %, and per-component F1 (building_name, locality, sub_locality, city, district, state, pincode), in addition to the existing global numbers. Output goes to both stdout and the JSON report.
8. **No regression on Latin/English.** The pre-v0.4 `en` subset (the existing 200 rows, retagged with `language="en"`) must hold v0.3 F1 within ±0.02 on every component. Enforced by a CI check that fails the build on regression.
9. **Architectural constraint preserved.** New socket-monkeypatch test confirms `parse()` makes zero network calls even when called with `transliterate=True` and `indic-transliteration` installed. The Nominatim geocoder remains the only network-touching code path and remains opt-in via its existing flag.
10. **Pincode dataset cross-check (sanity, not blocker).** A test compares our pincode set against [`captn3m0/india-pincode-regex`](https://github.com/captn3m0/india-pincode-regex)'s 19,584 valid prefixes. Divergences are reported, not failed — this is a sanity log, not a gate.
11. **CLI exposes the new flag.** `bharataddress parse "मुंबई 400001" --transliterate` works and prints the same JSON as the Python API.
12. **All 37 existing tests still pass.** Total test count after v0.4: ≥60.

## Technical Approach

**Package layout (additions only):**
```
bharataddress/
├── parser.py                 # +transliterate kwarg, +language-aware mapping selection
├── preprocessor.py           # +transliterate_to_latin() (lazy import of indic_transliteration)
├── language.py               # NEW: pincode → state → primary language(s) resolver
├── data/
│   ├── mappings/             # NEW: replaces vernacular_mappings.json
│   │   ├── common.json
│   │   ├── hi.json
│   │   ├── ta.json
│   │   ├── te.json
│   │   ├── kn.json
│   │   ├── bn.json
│   │   └── ml.json
│   └── state_languages.json  # NEW: state code → [primary language codes]
├── cli.py                    # +--transliterate flag
tests/
├── data/
│   ├── gold_500.jsonl        # NEW (replaces gold_200.jsonl; old file kept as gold_200_v03.jsonl for diff reference)
│   └── SOURCES.md            # NEW: attribution for OSM/Wikipedia sourced rows
├── test_transliteration.py   # NEW
├── test_language_mapping.py  # NEW
├── test_no_indic_dep.py      # NEW: confirms parse() works without indic-transliteration installed
└── test_no_network_v04.py    # NEW: socket monkeypatch with transliterate=True
scripts/
├── evaluate.py               # +per-language breakdown
├── source_osm_gold.py        # NEW: one-shot scraper for Tier B rows (not run in CI)
└── verify_pincode_set.py     # NEW: cross-check vs captn3m0/india-pincode-regex
pyproject.toml                # +[project.optional-dependencies] indic = ["indic-transliteration>=2.3"]
```

**Data flow for vernacular input:**
1. Caller invokes `parse(addr, transliterate=True)`.
2. `preprocessor.transliterate_to_latin(addr)` detects script via Unicode block, lazy-imports `indic_transliteration`, transliterates to Latin (HK or ITRANS scheme), returns `(latin_text, detected_lang_code)`.
3. If `indic_transliteration` is not installed, raises `ImportError` with a clear message: `pip install bharataddress[indic]`.
4. `parser.parse()` proceeds with the Latin string, but now also uses `detected_lang_code` (or `language.from_pincode(pin)`) to decide which `mappings/{lang}.json` files to load on top of `common.json`.
5. Output is unchanged — same `ParsedAddress` shape.

**Language resolution order:**
1. Explicit `language=` kwarg on `parse()` (new, optional).
2. Script-detected language from `transliterate_to_latin()`.
3. Pincode → state → `state_languages.json` lookup.
4. Fallback: `common.json` only.

## Architectural Constraint Test
**Non-negotiables:**
- `parse()` makes zero network calls. (existing socket monkeypatch test, extended to cover `transliterate=True`)
- Core install (`pip install bharataddress`) has zero runtime dependencies.
- `indic-transliteration` is an *optional extra*, not a core dep, and the package must import and parse Latin addresses without it installed.
- No regression on the existing English/Latin gold rows.
- No language-specific term may fire outside its declared language(s) without an explicit override.

**Verification before any code:** the new tests `test_no_indic_dep.py`, `test_no_network_v04.py`, and the `language="en"` regression check must be written *first* and must fail in the right way before any feature code is added. This is the lesson from the ContextKey cloud-API flaw — write the constraint test before the feature, not after.

## Out of Scope
- Marathi, Punjabi, Gujarati, Odia, Assamese, Urdu — deferred to a later release. v0.4 ships 6 scripts and stops.
- Full neural transliteration (AI4Bharat IndicXlit, IndicTrans2). Way too heavy for a deterministic parser; deterministic ITRANS/HK round-tripping is sufficient for address tokens.
- Mixed-script addresses where the same row contains both Latin and native script in non-trivial ways (e.g. "Plot 12, अंधेरी West, Mumbai"). v0.4 handles either-or; mixed-script is a v0.5 problem.
- Sub-locality F1 improvement from the pincode → known-localities dataset (separate v0.5 workstream).
- LLM opt-in parser (`mode="llm"`).
- `force_online=True` for the geocoder (separate small ticket).
- Morphological analysis of vernacular terms (declension, plurals). We match surface forms only.
- Real-time language detection on Latin-only Romanised input (we use pincode → state as a heuristic, not actual NLP language ID).

## Dependencies
- `indic-transliteration>=2.3` available on PyPI (verified: 162 kB pure-Python wheel, zero declared deps, supports all 6 target scripts via HK/ITRANS schemes).
- OSM Nominatim public API (one-shot, offline-cached, for Tier B gold sourcing only — not in runtime path). ODbL attribution required.
- Wikipedia infoboxes (one-shot, for Tier B gold sourcing only). CC-BY-SA attribution required.
- User availability for ~50 hand-curated Tier A gold rows (the bottleneck — without these, the gold set is purely scraped and lower trust).

**Locked decisions (do not re-open):**
- Tier B sourcing is **OSM `name:xx` tags + Wikipedia infoboxes**. AI4Bharat indicnlp_catalog is a metadata index, not structured address data — already evaluated and rejected.
- Transliteration target scheme is **ITRANS** (ASCII-clean, no diacritics, readable to Indian devs reviewing gold).
- Gold file is **single `gold_500.jsonl` with a `language` field**. One file, one evaluation loop.

## Estimated Complexity
**M (medium).** Roughly:
- Mapping expansion (data work): low risk, mechanical, ~1 day if user provides Tier A and contributes term review per language. Bottleneck = user time, not code.
- Transliteration shim + extras packaging: low-medium risk, ~half day. Pattern is identical to the existing Nominatim opt-in.
- Language-aware mapping selection: medium risk. The parser doesn't currently thread a language hint through its rules; this is the only real refactor in v0.4.
- Gold expansion + per-language F1: medium risk. Tier B sourcing script is the unknown — could find rich data fast (AI4Bharat catalog) or be painful (OSM rate limits, Wikipedia parsing). Time-box to one day, fall back to a smaller gold set if blocked.
- Per-language F1 reporting: low risk, ~2 hours of additions to `evaluate.py`.

**Risk register:**
1. **Tier B gold sourcing slips.** Mitigation: scope a smaller v0.4 (≥25 rows/language instead of 40) rather than slip the release.
2. **Language-aware mapping breaks an existing English row.** Mitigation: the regression CI check is the gate. If it fires, the offending mapping is moved to a more specific language file or marked English-incompatible.
3. **`indic-transliteration` produces Latin output our existing rules don't recognise** (e.g. odd diacritics from IAST). Mitigation: choose HK or ITRANS scheme (ASCII-only output), not IAST. Test in the constraint phase.
4. **User unavailable for Tier A curation.** Mitigation: ship v0.4 as "Tier B only, marked experimental in release notes" rather than block.

## Status
PRD locked 2026-04-09. Ready for issue decomposition (Phase 1 Step 3).
