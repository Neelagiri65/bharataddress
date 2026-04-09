# Issues — bharataddress v0.4 (multilingual / vernacular)

All issues below ship as open source under the existing MIT licence as part of the v0.4.0 release. Fully public, no commercial gating. Source: `docs/prd-v0.4-multilingual.md`.

Order is dependency-first. Each issue is independently implementable on a feature branch, has a clear pass/fail test, and touches ≤5 files unless noted.

---

## #1 — Architectural constraint tests (write first, must fail correctly)

**Branch:** `feature/v04-constraint-tests`
**Depends on:** none
**Files touched:** `tests/test_no_indic_dep.py` (new), `tests/test_no_network_v04.py` (new), `tests/test_en_regression_gate.py` (new), `scripts/evaluate.py` (minor: emit per-row language tag if present)

**What to build**
Three failing tests that lock the v0.4 non-negotiables before any feature code is written:
1. `test_no_indic_dep.py` — in a subprocess with `indic_transliteration` uninstalled (or monkeypatched to raise on import), `from bharataddress import parse; parse("Flat 302, MG Road, Bangalore 560001")` returns a valid `ParsedAddress`. Calling `parse(..., transliterate=True)` raises `ImportError` with the message `pip install bharataddress[indic]`.
2. `test_no_network_v04.py` — extends the existing socket monkeypatch test to cover `parse(addr, transliterate=True)` with `indic_transliteration` installed. Asserts zero socket calls.
3. `test_en_regression_gate.py` — runs `evaluate.py` against the existing `gold_200.jsonl` (treated as the `language="en"` baseline) and asserts every per-component F1 is within ±0.02 of the v0.3 baseline numbers. Baseline numbers loaded from `tests/data/v03_baseline.json` (committed in this issue from the v0.3 final eval report).

**Pass/fail**
- Tests 1 and 2: must fail in this issue (no `transliterate` kwarg exists yet) and pass after issue #4.
- Test 3: must pass immediately (it's the regression gate; we're locking v0.3 numbers as the floor).
- CI must run all three on every PR for the rest of v0.4.

**Why first:** lesson from ContextKey cloud-API flaw — write the constraint test before the feature, not after.

---

## #2 — Per-language mapping file restructure

**Branch:** `feature/v04-mapping-restructure`
**Depends on:** #1
**Files touched:** `bharataddress/data/mappings/common.json` (new), `bharataddress/data/mappings/{hi,ta,te,kn,bn,ml}.json` (new, each starts as a stub with ~5 placeholder entries copied from v0.3 where applicable), `bharataddress/data/state_languages.json` (new), `bharataddress/language.py` (new), `bharataddress/parser.py` (refactor: replace flat `vernacular_mappings.json` load with language-aware loader), `tests/test_language_mapping.py` (new)

**What to build**
1. Split the existing `bharataddress/data/vernacular_mappings.json` into `mappings/common.json` (pan-Indian terms — Nagar, Colony, Road, Marg, Sector, Phase, Block, Tower, Apartments, etc.) and 6 stub language files. Stubs only need ~5 entries each in this issue; the bulk expansion is #3.
2. Create `state_languages.json`: maps every Indian state/UT code to its primary language(s) by ISO code. Source: Eighth Schedule of the Constitution + state official language acts. Example: `{"TN": ["ta"], "MH": ["hi", "mr"], "WB": ["bn"], ...}`.
3. Create `bharataddress/language.py` with `from_pincode(pin: str) -> list[str]` (pincode → state via existing pincode dataset → language codes) and `load_mappings(lang_codes: list[str]) -> dict` (always loads `common.json`, then merges the requested language files; later languages do not override earlier ones).
4. Refactor `parser.py` to call `language.load_mappings(...)` instead of loading the flat file. Default behaviour when no pincode/language hint: `common.json` only.
5. Test: `Salai` token in a Chennai (600xxx) address fires; same token in a Kolkata (700xxx) address does *not* fire. `Veedhi` fires in Hyderabad (500xxx). `Nagar` fires everywhere.

**Pass/fail**
- All v0.3 tests still pass (the restructure is behaviour-preserving for English input).
- New `test_language_mapping.py` passes the Salai/Veedhi/Nagar cases above.
- `test_en_regression_gate.py` from #1 still passes (no F1 drift).

---

## #3 — Vernacular term expansion to ≥400 entries

**Branch:** `feature/v04-vernacular-expansion`
**Depends on:** #2
**Files touched:** `bharataddress/data/mappings/common.json`, `mappings/hi.json`, `mappings/ta.json`, `mappings/te.json`, `mappings/kn.json`, `mappings/bn.json`, `mappings/ml.json`, `tests/test_vernacular_coverage.py` (new)

**What to build**
Pure data work. Expand the seven mapping files to:
- `common.json` ≥80 entries (pan-Indian terms)
- `hi.json` ≥40 entries (Marg, Gali, Mohalla, Chowk, Bagh, Vihar, Kunj, Dham, Puram, …)
- `ta.json` ≥40 entries (Salai, Theru, Nagar variants, Kovil, Pettai, Mandapam, Kulam, …)
- `te.json` ≥40 entries (Veedhi, Basthi, Peta, Palem, Gudem, Cheruvu, …)
- `kn.json` ≥40 entries (Cross, Layout, Hosa, Halli, Pura, Beedi, Mane, …)
- `bn.json` ≥40 entries (Para, Pally, Bagan, Lane variants, Gali, Math, Tala, …)
- `ml.json` ≥40 entries (Mukku, Kavala, Junction variants, Para, Kara, Theruvu, …)
- **Total ≥400 across all files.**

Each entry: `{"<surface>": {"latin": "<canonical>", "component": "<locality|sub_locality|street|landmark>", "notes": "<optional>"}}`.

Sources for term lists: Wikipedia "<language> placename suffixes" articles, OSM tag stats for India by state, and the existing v0.3 vernacular file as a starting point. **No content from `private/`.** All terms must be publicly attestable place-name elements, not addresses copied from any private dataset.

Test: `test_vernacular_coverage.py` asserts each file's minimum entry count and that no term appears in more than one language file (except via `common.json`).

**Pass/fail**
- Entry counts hit minimums.
- No cross-file duplicates.
- All v0.3 + #1 + #2 tests still pass.
- `test_en_regression_gate.py` still within ±0.02.

**Note on parallelisation:** this issue is the easiest one to crowdsource later. Consider opening it as a "good first issue" on GitHub with a checklist of languages so external contributors can PR a single language file.

---

## #4 — Transliteration shim + extras packaging

**Branch:** `feature/v04-transliteration`
**Depends on:** #2 (needs the language-aware mapping loader)
**Files touched:** `bharataddress/preprocessor.py` (add `transliterate_to_latin`), `bharataddress/parser.py` (add `transliterate` kwarg to `parse()`), `bharataddress/__init__.py` (re-export), `pyproject.toml` (add optional dep), `tests/test_transliteration.py` (new), `README.md` (add 5-line section on the extras install)

**What to build**
1. `preprocessor.transliterate_to_latin(text: str) -> tuple[str, str | None]`:
   - Detect script via Unicode block of the first non-ASCII character (Devanagari U+0900–U+097F, Bengali U+0980–U+09FF, Tamil U+0B80–U+0BFF, Telugu U+0C00–U+0C7F, Kannada U+0C80–U+0CFF, Malayalam U+0D00–U+0D7F).
   - Lazy-import `indic_transliteration.sanscript` inside the function. If `ImportError`, raise with message `"indic-transliteration is required for transliterate=True. Install with: pip install bharataddress[indic]"`.
   - Use the **ITRANS** scheme as the Latin target (ASCII-clean, no diacritics).
   - Return `(latin_text, detected_lang_code)`. If text is already ASCII, return `(text, None)` without importing anything.
2. Wire `transliterate=True` kwarg into `parse()`. When set: call `transliterate_to_latin` first, pass the detected language code into `language.load_mappings([detected])` (falling back to pincode-based resolution if detection returns `None`).
3. `pyproject.toml`: add `[project.optional-dependencies]` with `indic = ["indic-transliteration>=2.3"]`.
4. Test: parse a representative address in each of the 6 scripts and assert correct state + pincode extraction. Test that ASCII input with `transliterate=True` is a no-op (no import). Test that `ImportError` message is correct when the dep is missing.

**Pass/fail**
- All 6 script test addresses parse to correct state and pincode.
- `test_no_indic_dep.py` from #1 now passes (was previously failing because the kwarg didn't exist).
- `test_no_network_v04.py` from #1 now passes.
- `pip install bharataddress[indic]` resolves cleanly on a fresh venv.

---

## #5 — Per-language F1 reporting in evaluate.py

**Branch:** `feature/v04-per-language-eval`
**Depends on:** #1 (needs the `language` field plumbing in evaluate.py started there)
**Files touched:** `scripts/evaluate.py`, `tests/test_evaluate_per_language.py` (new)

**What to build**
Extend `evaluate.py` to:
1. Read the `language` field from each gold row (default `"en"` if absent — backward compatible with the current `gold_200.jsonl`).
2. Compute per-component F1 (building_name, locality, sub_locality, city, district, state, pincode) globally AND broken down per language.
3. Print a per-language table to stdout: `language | rows | exact_match% | building_F1 | locality_F1 | sub_locality_F1 | city_F1 | district_F1 | state_F1 | pincode_F1`.
4. Add a `per_language` block to the JSON report output.
5. Existing global numbers stay exactly where they are — additive only, no breaking changes to the JSON schema's existing keys.

Test: synthetic 10-row gold file with mixed languages → per-language block has the right keys, right row counts, F1 values match a hand-computed baseline.

**Pass/fail**
- All v0.3 evaluate.py invocations still produce the same output for English-only gold.
- Per-language block appears when gold has mixed languages.
- New test passes.

---

## #6 — Gold expansion to gold_500.jsonl

**Branch:** `feature/v04-gold-expansion`
**Depends on:** #5 (need per-language eval to actually use the new rows)
**Files touched:** `tests/data/gold_500.jsonl` (new — the canonical gold file going forward), `tests/data/gold_200_v03.jsonl` (renamed from `gold_200.jsonl`, kept frozen for the regression gate), `tests/data/SOURCES.md` (new), `scripts/source_osm_gold.py` (new — one-shot, not run in CI), `scripts/evaluate.py` (default `--gold` path → `gold_500.jsonl`)

**What to build**
1. Rename `gold_200.jsonl` → `gold_200_v03.jsonl`. The regression gate test (#1) reads this frozen file. Never edited again.
2. Create `gold_500.jsonl` starting from a copy of all 200 v0.3 rows, each tagged with `"language": "en"`.
3. Add ≥300 new rows tagged by language (`hi`, `ta`, `te`, `kn`, `bn`, `ml`), minimum 40 per language.
   - **Tier A (≥50 rows total, hand-curated by user):** real addresses the user can vouch for, distributed across the 6 vernacular languages. User provides via chat or a private staging file under `private/staging/` — the *content* is moved into the public gold file only after user confirms each row is OK to publish.
   - **Tier B (≤250 rows total, sourced):** OSM `name:hi`/`name:ta`/etc. tags + Wikipedia infoboxes for Indian places. Sourced by `scripts/source_osm_gold.py`. ODbL/CC-BY-SA attribution recorded in `tests/data/SOURCES.md`.
4. `scripts/source_osm_gold.py`:
   - One-shot, manual-run only, not in CI.
   - Polite to Nominatim (1 req/sec, custom User-Agent, caches to `.cache/osm/`).
   - Outputs candidate rows to `tests/data/gold_500_candidates.jsonl` for human review before they enter `gold_500.jsonl`.
5. `SOURCES.md`: per-row attribution for every Tier B row (OSM way/node ID + licence, or Wikipedia article + revision ID).

**Pass/fail**
- `gold_500.jsonl` has ≥500 rows total, ≥40 per vernacular language, all rows have a `language` field.
- `gold_200_v03.jsonl` is byte-identical to the old `gold_200.jsonl`.
- `test_en_regression_gate.py` still passes (uses the frozen file).
- `evaluate.py --gold tests/data/gold_500.jsonl` runs end-to-end and prints the per-language table from #5.
- `SOURCES.md` accounts for every Tier B row.

**Risk:** if Tier A bottlenecks on user availability, ship with ≥25/language instead of 40 and mark v0.4 release notes as "vernacular gold experimental, expanding in v0.4.1". Do not block the release.

---

## #7 — CLI `--transliterate` flag

**Branch:** `feature/v04-cli-transliterate`
**Depends on:** #4
**Files touched:** `bharataddress/cli.py`, `tests/test_cli.py` (extend), `README.md` (update CLI section)

**What to build**
Add `--transliterate` flag to `bharataddress parse`. When set, threads through to `parse(addr, transliterate=True)`. Same JSON output shape. Help text mentions the extras install requirement. If the flag is set but `indic-transliteration` is not installed, exit code 2 with the same error message as the Python API.

**Pass/fail**
- `bharataddress parse "मुंबई 400001" --transliterate` returns valid JSON with `state="Maharashtra"`, `pincode="400001"`.
- `bharataddress parse "MG Road Bangalore 560001"` (no flag) still works exactly as before.
- CLI test covers both paths and the missing-extras error path.

---

## #8 — Pincode dataset cross-check (sanity log)

**Branch:** `feature/v04-pincode-crosscheck`
**Depends on:** none (can run in parallel with anything)
**Files touched:** `scripts/verify_pincode_set.py` (new), `tests/test_pincode_crosscheck.py` (new), `reports/pincode_crosscheck_v0.4.json` (committed report)

**What to build**
1. `scripts/verify_pincode_set.py`:
   - Loads our `bharataddress/data/pincodes.json`.
   - Loads [`captn3m0/india-pincode-regex`](https://github.com/captn3m0/india-pincode-regex)'s 19,584 valid prefixes (vendored as a small JSON in `tests/data/external/captn3m0_pincode_prefixes.json`, with attribution).
   - Reports: count of pincodes valid in ours but not in theirs, valid in theirs but not in ours, total overlap.
   - Writes `reports/pincode_crosscheck_v0.4.json`.
2. `test_pincode_crosscheck.py`: runs the script and **logs** divergences. Does not fail on divergence — this is a sanity log, not a gate. Only fails if the script itself errors.

**Pass/fail**
- Script runs end-to-end.
- Report committed.
- Test passes (does not gate on divergence count).

---

## #9 — Release: v0.4.0 to PyPI + dev.to follow-up

**Branch:** `release/v0.4.0`
**Depends on:** #1–#8 all merged to `main`
**Files touched:** `pyproject.toml` (version bump), `CHANGELOG.md`, `README.md` (badge updates, new "Multilingual" section), `HANDOFF.md`, dev.to draft (saved to `~/Obsidian/agent-vault/raw/posts/v0.4-launch.md` first, not auto-published)

**What to build**
1. Bump version → `0.4.0` in `pyproject.toml`.
2. CHANGELOG entry covering: 6 scripts via opt-in extras, 400+ vernacular terms across 7 mapping files, gold_500 with per-language F1, ITRANS transliteration, language-aware mapping resolution, pincode cross-check report.
3. README: new "Multilingual support (opt-in)" section with the `pip install bharataddress[indic]` install line and a 5-line example. Update the test count and gold-set size badges.
4. Build + publish to PyPI: `python -m build && twine upload dist/*` (user runs the upload; Claude Code does not have credentials).
5. HANDOFF.md updated with v0.4 final eval numbers per language, decisions made, deferred items.
6. Draft a dev.to follow-up post at `~/Obsidian/agent-vault/raw/posts/v0.4-launch.md` titled "bharataddress v0.4: now reads addresses in 6 Indian scripts." User reviews and publishes manually — do not auto-publish.

**Pass/fail**
- `pip install bharataddress==0.4.0` works on a fresh venv.
- `pip install bharataddress[indic]==0.4.0` works on a fresh venv.
- All 60+ tests pass on the published wheel.
- HANDOFF.md committed and pushed.
- dev.to draft saved to vault, not auto-published.

---

## Cut-line / scope discipline

If the release is at risk of slipping, cut in this order (least painful first):
1. **Cut #8 (pincode cross-check)** — pure sanity, defer to v0.4.1.
2. **Cut Tier A gold rows from #6** — ship with Tier B only, 25/language minimum, mark gold "experimental" in release notes.
3. **Cut 2 of the 6 languages** (start with `ml` and `kn` — smallest absolute address volumes) — defer to v0.4.1.
4. **Never cut #1 (constraint tests).** That's the lesson from ContextKey.
5. **Never cut #5 (per-language F1).** Without it the release notes are unverifiable claims, which is the SheetPortal-rejection failure pattern.
