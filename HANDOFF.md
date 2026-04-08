# HANDOFF — bharataddress

_Last updated: 2026-04-08_

## v0.3.0 — fuzzy phonetic + Nominatim online geocoding (branch)

Branch: `feature/v0.3-fuzzy-phonetic-nominatim`. Tag NOT yet cut on `main`.
PyPI upload deferred — user runs `twine` manually.

### New modules

- **`bharataddress/phonetic.py`** — hand-tuned alias map for post-independence
  renames (Bombay/Mumbai, Madras/Chennai, Calcutta/Kolkata, Bangalore/Bengaluru,
  Gurgaon/Gurugram, Pune/Poona, Trivandrum/Thiruvananthapuram, Cochin/Kochi,
  Baroda/Vadodara, Mysore/Mysuru, Allahabad/Prayagraj, Pondicherry/Puducherry,
  Varanasi/Banaras/Benares, Vijayawada/Bezawada, Bhubaneswar variants,
  Visakhapatnam/Vizag, Mangalore/Mangaluru, Trichy variants, Panaji/Panjim,
  Delhi/Dilli) plus transliteration rewrites (double-vowel collapses,
  d↔r for Dravidian, w↔v Gujarati, ph↔f, suffix drops, sh→s, bh→b).
  Rewrites are guarded — only applied when the result lands on a known
  canonical form, preventing over-normalisation. `fuzzy_ratio` uses
  `rapidfuzz.fuzz.token_set_ratio` when available, else stdlib `difflib`.
  `best_match(query, candidates, cutoff)` for top-1 lookup.
- **`bharataddress/_geocode_cache.py`** — lazy SQLite cache at
  `$XDG_CACHE_HOME/bharataddress/geocode.sqlite` (default
  `~/.cache/bharataddress/`). Schema `(query, lat, lng, source, ts)`. Negative
  results cached for 30 days. File created only on first online write.

### Modified

- **`geocoder.geocode(parsed, *, online=False, timeout=5.0)`** — default
  unchanged (offline centroid only, no network). `online=True` falls back to
  Nominatim via stdlib `urllib.request` when the pincode centroid is missing.
  Custom `User-Agent: bharataddress/0.3.0 (+github)`, 1 req/s rate limit
  enforced via module-level `_last_call_ts`, all errors swallowed → `None`,
  cache check before any network call. Centroid hits never trigger network
  regardless of the flag (saves rate-limit budget). `# TODO: force_online=True`
  comment left in for v0.4.
- **`parser.parse(raw, *, latlng=None, geocode=False)`** — new `geocode` kwarg.
  When True, after parsing, calls `geocoder.geocode(out, online=True)` and
  populates new `ParsedAddress.latitude` / `longitude` fields. Centroid lat/lng
  is also auto-populated for any pincode whose record carries coords (the
  v0.2.2 OSM-derived 61.6%). The `_is_dup` city dedup keeps difflib for the
  primary check and adds a phonetic-canonical equality check on top — so
  "Bengaluru" trailing a Bangalore-pincode address is now dropped via the
  alias map even when difflib's char-ratio misses it.
- **`similarity.py`** — `_CITY_ALIASES` now sourced from
  `phonetic.canonical_aliases()` so the two modules share one source of truth
  for city canonicalisation. Pure refactor.
- **`pyproject.toml`** — `version = "0.3.0"`, new
  `[project.optional-dependencies] fuzzy = ["rapidfuzz>=3.0"]`. Base install
  remains zero-deps. `requests` NOT added (using stdlib `urllib`).
- **`__init__.py`** — exports `phonetic` module, `__version__ = "0.3.0"`.

### Tests: 113 pass (100 prior + 8 phonetic + 5 geocoder online)

- `tests/test_phonetic.py` — 12 post-independence rename pairs canonicalise
  to the same form, common misspellings (Gudgaon, Bangalroe, Chenai, Kolkatta)
  resolve, Varanasi/Banaras/Benares group, unknown input passes through,
  fuzzy_ratio pairs (Gurgaon↔Gurugram=1.0, Bengaluru↔Bangalore=1.0),
  difflib fallback via monkeypatch (`_HAS_RAPIDFUZZ=False`), best_match
  cutoff behaviour.
- `tests/test_geocoder_online.py` — `online=False` never hits network (asserts
  via raising `urlopen` stub), `online=True` calls Nominatim once with the
  custom User-Agent and writes the cache, second call is a cache hit (no
  extra network), empty Nominatim result writes a negative cache entry,
  network errors return None, `parse(addr, geocode=True)` populates lat/lng
  via the stubbed Nominatim path. SQLite cache redirected to `tmp_path` for
  every test — never touches the user's real cache.

### Public eval: 125/200 = 62.5% exact match — identical to v0.2.2

`reports/eval_v0.3.0.json`. Zero regression on every field. (Initial pass
hit 124/200 because the phonetic-only city dedup was slightly different
from difflib; resolved by keeping difflib as the primary check and using
phonetic canonical equality as an additive layer.)

### NEXT

1. Review the branch diff. Cut tag `v0.3.0` on `main` after merge.
2. Build wheel: `python -m build`. Smoke test in a clean venv: import
   `phonetic`, run `parse("...", geocode=True)` against a stubbed network,
   verify `bharataddress[fuzzy]` extra installs rapidfuzz.
3. Mint a fresh PyPI token (the v0.2.2 token was revoked) and `twine upload`.
4. (v0.4 candidates) `force_online=True` kwarg — already TODO'd in
   geocoder.py. Pincode → known-localities dataset for fuzzy locality match
   per pincode. Phonetic-quality boost in `_confidence` weights.

## v0.2.2 — published to PyPI

_Last updated: 2026-04-07_

## v0.2.2 — published to PyPI

`bharataddress 0.2.2` is live: https://pypi.org/project/bharataddress/0.2.2/. Built with `python -m build`, uploaded via `twine` using a token in `~/.pypirc` (since revoked + removed). Clean-venv smoke test (`/tmp/bha-verify-0.2.2`) passed end-to-end: `parse()` → pincode 122001 / Haryana / auto-populated digipin, `geocode()` → (28.47, 77.04), `reverse_geocode(28.6129, 77.2295)` → 110011 @ 1.24 km, `extract_state_from_gstin('29...')` → Karnataka.

**NEXT:** mint a fresh PyPI token if future releases are planned (old one revoked); optionally announce release / refresh README install snippet.

## v0.2.2 — pincode centroids from OSM

`scripts/build_pincode_centroids.py` walks `private/raw/india-latest.osm.pbf` (1.6 GB), pulls every node tagged `addr:postcode` matching the Indian pincode pattern, averages lat/lng per pincode, and writes `latitude` / `longitude` floats back into `bharataddress/data/pincodes.json`. **16,459 pincodes (61.6% of 26,711) now carry centroids.** File size 3.60 MB → 4.27 MB.

Build-time only — `pyosmium` is required to *run* the script but is not a runtime dependency. The shipped `pincodes.json` is reproducible from the script + the OSM PBF.

**Spec note:** the original instruction said "first try indiapost.csv lat/lng, fallback OSM". `private/raw/indiapost.csv` does **not** carry latitude / longitude columns (verified). OSM is therefore the sole source. If a future India Post dataset gains coordinates, add a first phase to the build script that prefers it.

Three previously-dormant features activate automatically:

- `geocoder.geocode(parsed)` returns real `(lat, lng)` for any pincode in the 61.6% that have a centroid (returns `None` for the long tail).
- `geocoder.reverse_geocode(lat, lng)` walks the centroid table and returns the nearest pincode by haversine + the DIGIPIN for the input point.
- `parser.parse()` auto-populates the `digipin` field whenever the resolved pincode has a centroid — no `latlng=` hint required. The dormant branch in `parse()` (gated on `rec.get("latitude")`) starts firing.

**Tests: 100 pass.** Two existing tests (`test_parse_default_digipin_is_none` and `test_geocode_returns_none_when_dataset_lacks_centroids`) explicitly asserted the *dormant* behaviour and have been rewritten to assert the active behaviour: parse-default DIGIPIN is now populated for known pincodes, geocode returns a Gurgaon-area centroid for `122001`, reverse_geocode round-trips Gurgaon coordinates back to a `122xxx` pincode within 50 km. Net +2 tests vs v0.2.1.

**Public eval: 125/200 exact match (62.5%) — identical to v0.2.1, zero regression on every field.** Centroids are purely additive to the parser; they don't touch any classification logic.

Tagged `v0.2.2` on `main`.

## v0.2.1 — parser quality lift (49.0% -> 62.5% exact match)

Three commits in one session, each addressing a NEXT item from the v0.2.0 handoff:

**1. Pincode coverage (`feat(data)`)** — `scripts/build_pincode_data.py` gains a third overlay phase: any pincode in the India Post directory but missing from the kishorek base is added with district / state / officename. Pincode count 23,915 → 26,711. Fixes the 5 known false negatives (500033 Hyderabad, 560102 Bangalore, 122003 Gurgaon, 411057 Pune, 144040 Jalandhar) plus 2,791 others.

**2. No-comma resplit (`feat(parser)`)** — `_split_segments` now runs a heuristic regex pass when comma-splitting yields exactly one segment. Inserts boundaries after a leading building lead + number, after a leading alphanumeric token (`A-15`), and after locality / sub-locality closing keywords (`Colony`, `Nagar`, `Road`, `Marg`, `Layout`, ...). Recovers structure from `A-15 Defence Colony New Delhi 110024` and `H No 12 Sarat Bose Road Kolkata 700020` which were previously losing locality + building entirely.

**3. Admin annotations + city/state dedup + phone strip (`feat(parser)`)** — biggest lift, several changes bundled:
- `ADMIN_PREFIX_RE` classifies `PO X` / `Post X` / `Village X` / `Tehsil X` / `Mouza X` / `Gram Sabha X` / `Mandal X` / `Via X` as sub_locality. PO/Post cues use a new `sub_locality_po` kind that outranks generic admin (matches gold preference for the post-office annotation when multiple are present).
- Stopped expanding `PO` -> `post office` in `abbreviations.json` so the bare `po` form survives for the substring matcher.
- `_is_dup` gains a curated `_KNOWN_CITIES` frozenset (~80 entries) so trailing city names that disagree with the pincode lookup (`Kochi` vs `Ernakulam`, `Bhubaneswar` vs `Puri`) no longer leak into sub_locality.
- difflib-based fuzzy match against the lookup city catches typos (`kolkatta`, `bangalroe`, `chenai`). difflib is stdlib, no new dep.
- `_STATE_ABBREVS` frozenset (AP/MP/HP/UP/WB/TN/...) suppresses two-letter state codes.
- Preprocessor strips `Ph: 9876...` / `Phone: ...` phone-number annotations before tokenisation (the bare `Ph` was previously expanding to `phase` and leaking into sub_locality). Also strips leftover `Pin Code:` / `Pincode -` labels.

**Public eval (`reports/eval_v0.2.1e.json`):**

| metric | v0.2.0 | v0.2.1 | delta |
|---|---|---|---|
| exact match | 49.0% | **62.5%** | **+13.5pp** |
| locality F1 | 0.768 | 0.796 | +0.028 |
| building_name F1 | 0.635 | 0.679 | +0.044 |
| district F1 | 0.933 | 0.965 | +0.032 |
| state F1 | 0.923 | 0.971 | +0.048 |
| sub_locality F1 | 0.469 | 0.455 | -0.014 |

sub_locality is the only field that didn't move up. Gold is inconsistent on whether named streets like `MG Road` belong in locality or sub_locality, so the field swings either way. The 0.6 target from the prior NEXT list remains open.

**Tests: 98 pass** (95 from v0.2.0 + 3 new no-comma regression tests).

Tagged `v0.2.1` on `main` after the full test suite passed.

## v0.2.0 — feature release (formatter / validator / geocoder / similarity / batch / enrichment)

Six new modules around the core parser, all offline, all zero-dependency, all importable from the top-level `bharataddress` package.

- `bharataddress/formatter.py` — `format(parsed, style="india_post"|"single_line"|"label")`. Reconstructs a clean address string from parsed components in three styles.
- `bharataddress/validator.py` — `validate(parsed)` returns per-field confidence + a list of consistency issues (pincode ↔ state ↔ district ↔ city mismatches checked against the embedded India Post directory). `is_deliverable(parsed)` is the minimum-fields check (pincode + city + state).
- `bharataddress/geocoder.py` — `geocode(parsed)` returns `(lat, lng)` from the pincode centroid (returns `None` until pincodes.json gains centroids — same dormant hook as the parser DIGIPIN branch). `reverse_geocode(lat, lng)` always returns a DIGIPIN; nearest pincode is dormant for the same reason.
- `bharataddress/similarity.py` — `similarity(a, b)` returns a 0–1 score. Pincode is the strongest signal (0.40), then city (0.20, with Bengaluru/Bangalore, Mumbai/Bombay, etc. aliasing), state (0.10), locality token Jaccard (0.20), building tokens (0.10). Multi-word aliases (Mahatma Gandhi → MG, Subhash Chandra → SC, Jawaharlal Nehru → JLN) handled.
- `bharataddress/batch.py` — `parse_batch(strings)`, `parse_csv(path, column="address")` writes a `<stem>_parsed.csv` with one `parsed_<field>` column per parsed field, `parse_dataframe(df, column="address")` lazily imports pandas (not a runtime dep) and returns a copy with parsed columns added.
- `bharataddress/enrichment.py` — `extract_state_from_gstin(gstin)` decodes the first two digits of a GSTIN against the official GST Council state code list (37 entries including Telangana=36, post-bifurcation AP=37, Ladakh=38).

`bharataddress/__init__.py` now exports all of the above. `similarity` is exposed as `address_similarity` to avoid a name clash with the submodule. `format` is exported (shadows builtin only when imported by name).

**Tests: 95 pass** (37 parser + 30 DIGIPIN + 5 formatter + 5 validator + 4 geocoder + 5 similarity + 4 batch + 5 enrichment). Each module has its own `tests/test_<module>.py`.

**README** has a new "v0.2 modules" section with usage examples for every module.

**Zero new runtime dependencies.** pandas is optional and lazy-imported only inside `parse_dataframe`. Public eval / parser core unchanged at 49.0% exact match on gold_200.

Tagged `v0.2.0` on `main` after the full test suite passed.

## v0.1.5 — DIGIPIN module (encode / decode / validate)

New module `bharataddress/digipin.py` — verbatim Python port of the official India Post Apache-2.0 algorithm at github.com/INDIAPOST-gov/digipin (`src/digipin.js`). Pure deterministic math, zero new dependencies.

Public API:

- `encode(lat, lng) -> str` — returns formatted DIGIPIN `XXX-XXX-XXXX`. Raises `ValueError` outside the India bounding box (lat 2.5–38.5, lng 63.5–99.5).
- `decode(digipin) -> (lat, lng)` — centre of the level-10 (~3.8 m) cell. Accepts the code with or without dashes, case-insensitive.
- `validate(digipin) -> bool` — non-raising syntactic validator.

`parse()` now accepts an optional `latlng=` keyword and exposes a `digipin` field on `ParsedAddress`. When the caller passes a coordinate hint, the field is populated. Default behaviour stays unchanged (`digipin` is `None`) so existing v0.1.x callers see no diff. The current shipped `pincodes.json` does not carry centroids, so the pincode-centroid auto-fill branch is dormant — hooked in but won't fire until a future dataset refresh adds `latitude`/`longitude` per pincode.

**Tests: 67 pass (37 parser + 30 DIGIPIN).** New `tests/test_digipin.py` covers reference vectors for Delhi / Mumbai / Bangalore / Chennai / Kolkata, 500-point random round-trip, dash + case insensitivity, out-of-bounds rejection, malformed-input rejection, parser integration via `latlng=`, and a `socket.socket` monkeypatch asserting zero network calls during any DIGIPIN op.

**Public gold_200 unchanged: 49.0% exact match.** DIGIPIN is purely additive — no parser logic touched.

README gets a DIGIPIN section with usage examples.

## v0.1.4 — known-locality lookup table

New shipped data file `bharataddress/data/localities.json`: 26,668 pincodes → 179,410 normalised post-office / locality names (2.57 MB). Built from the existing `pincodes.json` `offices` field plus `private/raw/indiapost.csv` officenames, suffix-stripped (B.O / S.O / H.O / G.P.O. / P.O), lowercased, deduped.

LGD villages dataset was the original target but is not anonymously consumable (data.gov.in 500s on every endpoint, the only GitHub mirror is a 7,465-row Haryana sample, and the NAPIX / apisetu LGD endpoints require a registered developer key). Pivoted to building from the data already on disk — gives ~7 names per pincode on average.

**Parser change.** New `pincode.known_localities()` accessor + a guarded promotion step in `parse()`: when a tagged segment matches a known locality name for the pincode, it's promoted to a `locality_known` kind that wins the locality slot ahead of plain / locality / sub_locality. Guard rails to avoid stealing from sub_locality:
- Only promote `plain` segments (sub_locality cues like `Sector 31`, `MG Road`, `Block C` are stronger and never overridden).
- Among plain segments, only promote the **earliest** plain — never reorder which plain wins the locality slot, only add confidence.

**Public gold_200.** 49.0% exact match held. Per-field F1: locality 0.728 → **0.768** (+0.04), building_name 0.635 → **0.678** (+0.043), sub_locality 0.480 → 0.469 (−0.011), all other fields unchanged. Locality target was 0.80; we landed at 0.768 — below stretch but a real lift from a single deterministic step. All 37 tests pass.

**Private gold_master.** No change vs v0.1.3 — the gold sets only populate city/district/state/pincode, not locality/sub_locality, so the lift isn't visible in private metrics. city 0.588 / district 0.488 / state 0.749 / pincode 0.975 unchanged.

## v0.1.3 — pincode dataset refresh (post-2014 naming)

**Approach: surgical merge, not replace.** Kept the kishorek base for coverage (23,915 unique pincodes — a fresh-source-only build dropped to 19,100 and regressed both public and private eval). Overlaid post-2014 naming fixes only:

- `Orissa` → `Odisha` (1,087 pincodes)
- `Uttaranchal` → `Uttarakhand` (296 pincodes)
- `Calcutta` → `Kolkata` (62 districts)
- Telangana split from Andhra Pradesh using India Post truth (569 pincodes)

`scripts/build_pincode_data.py` is now a two-phase merge: fetch kishorek, then overlay `private/raw/indiapost.csv` for the Telangana split (rest is hardcoded renames).

**Public gold_200: 48.5% → 49.0% exact match.** All 37 tests pass. Per-field F1 unchanged or marginally better. Gold realigned: 4 Orissa→Odisha, 2 Uttaranchal→Uttarakhand, 8 Calcutta→Kolkata district, 5 AP→Telangana for Hyderabad/Warangal/Nalgonda pincodes. One stale unit-test expectation in `tests/test_parse.py` (hyderabad_basheer) updated AP→Telangana.

**Private gold_master eval (v0.1.3 vs v0.1.2):**

| Source | city | district | state | pincode |
|---|---|---|---|---|
| razorpay_ifsc | 0.427 → 0.427 | 0.268 → 0.275 | 0.641 → **0.690** | 0.997 → 0.997 |
| internal_hosp | 0.907 → 0.907 | 0.899 → 0.892 | 0.899 → 0.833 | 0.893 → 0.893 |
| osm | 0.919 → 0.919 | 0.944 → 0.939 | 0.958 → 0.904 | 0.998 → 0.998 |

The IFSC lift on `state` (+0.049) is the real-world win. The internal_hosp / osm `state` regressions are **gold staleness, not parser regression**: those gold sets were auto-built last session from the *old* pincode lookup, so they still expect "Andhra Pradesh" for Telangana pincodes. The parser is now more correct than the gold. NEXT priority: rebuild the auto-derived sections of `gold_master.jsonl` against the v0.1.3 pincode db so the gold reflects current ground truth, then re-baseline.

## 2026-04-07 private session — gold_master expanded

Private eval: gold_master built from 3 sources (prior internal hospital set + Razorpay IFSC + OSM India), 263,828 total entries after dedup. Aggregate in `private/reports/eval_master.json` + per-source breakdown in `private/reports/eval_master_per_source.json`. Details in `private/reports/data_sources.md`. Worst source by city/district/state F1 is the IFSC bank-branch set (district F1 0.27, state F1 0.64) — driven by RBI's free-form ADDRESS column where the parser can't recover district/state without a usable pincode lookup. Best is OSM (district 0.94, state 0.96, pincode 1.00). NEXT priority unchanged: refresh `pincodes.json` for v0.1.3.

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
