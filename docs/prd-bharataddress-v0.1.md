# PRD — bharataddress v0.1 (deterministic thin slice)

## Problem Statement
Indian addresses are messy, landmark-based, and poorly handled by every existing open-source parser (libpostal, deepparse, lokly). Developers building logistics, fintech, KYC, and e-commerce on India have no `pip install`-able tool that turns `"Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001"` into structured JSON in one line. v0.1 closes that gap with a fully deterministic parser — zero config, zero API keys, zero network calls — so a developer can install it and demo it in 60 seconds.

## User Story
As a Python developer integrating Indian addresses into my app, I want to `pip install bharataddress` and call `parse(addr)` to get a structured, validated address object so that I can stop writing regex by hand and stop sending PII to a third-party API just to extract a pincode.

## Acceptance Criteria
1. `pip install -e .` from the repo succeeds with no extra steps.
2. `from bharataddress import parse; parse("Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001")` returns a `ParsedAddress` with at least: `building_number="302"`, `building_name` containing "Raheja Atlantis", `landmark` containing "Hanuman Mandir", `locality` containing "Sector 31", `pincode="122001"`, `district="Gurgaon"` (or "Gurugram"), `state="Haryana"`, `confidence > 0.7`.
3. `bharataddress parse "<addr>"` CLI command prints the same JSON.
4. Pincode → district/state lookup works for any valid 6-digit Indian pincode shipped in the embedded dataset.
5. Parsing 1000 addresses runs in under 2 seconds on a laptop (deterministic, no network).
6. Zero outbound network calls during `parse()`. Verified by test.
7. Test suite with ≥30 real Indian addresses covering metro, tier-2, rural, S/O, landmark-heavy, and missing-pincode cases. ≥80% pass.
8. README with the 60-second demo at the top.

## Technical Approach

**Package layout (minimal):**
```
bharataddress/
├── __init__.py          # parse() entry point, ParsedAddress dataclass
├── preprocessor.py      # unicode NFKC, abbreviation expansion, pincode regex
├── pincode.py           # lazy-loaded singleton; lookup(pin) -> {district, state, ...}
├── parser.py            # rule-based extractor: building, landmark, locality, city
├── data/
│   ├── pincodes.json    # pin -> {district, state, region, office_name}
│   └── abbreviations.json  # H.No., Opp., Nr., S/O, D/O, W/O, B.O., S.O., ...
└── cli.py               # argparse: `bharataddress parse "..."`
tests/
└── test_parse.py        # 30+ labeled examples
scripts/
└── build_pincode_data.py  # one-shot: fetch India-Codes CSV -> pincodes.json
pyproject.toml
README.md
```

**Data flow:**
1. **Preprocess:** NFKC normalize → expand abbreviations (`H.No.` → `House Number`, `Opp.` → `Opposite`, `Nr.` → `Near`) → strip extra punctuation.
2. **Pincode extract:** regex `\b[1-8]\d{5}\b` → lookup in `pincodes.json` → fill district, state, region.
3. **Tokenize on commas.** Walk segments left-to-right with rules:
   - First segment with `flat|h.?no|house|#|^\d+` → `building_number` + `building_name`.
   - Segment starting with `near|opp|behind|beside|next to` → `landmark`.
   - Segment matching `sector \d+|phase \d+|block [a-z0-9]+|<word> nagar|<word> colony|<word> layout` → `locality`.
   - Last non-pincode segment → `city` (cross-checked against pincode lookup; pincode wins on conflict).
4. **Confidence:** weighted sum — pincode found (0.4) + city matches pincode (0.2) + locality found (0.2) + building found (0.1) + landmark found (0.1).

**Pincode dataset:** v0.1 ships a snapshot of `kishorek/India-Codes` (or `dropdevrahul/pincodes-india`) processed into `pincodes.json`. ~19k unique pincodes, file size <5 MB. Dataset refresh is a separate script, not a runtime concern.

## Architectural Constraint Test
Non-negotiables for v0.1:
- **No network calls during `parse()`.** Verified by a test that monkeypatches `socket.socket` and asserts no connection is opened.
- **No API keys, no env vars required.** Verified by running tests in a clean env.
- **No heavy ML deps.** No torch, no transformers, no sklearn. Only stdlib + a tiny set: `rapidfuzz` (optional later), nothing else for v0.1.
- **Deterministic output.** Same input → same output, always. No randomness, no LLM.

The proposed approach satisfies all four: pure Python rules + a static JSON lookup, no network, no keys, no ML, deterministic by construction.

## Out of Scope (v0.1)
- LLM parsing (Claude API) — v0.2
- Fuzzy phonetic matching (Gurgaon ↔ Gudgaon) — v0.2
- Geocoding (lat/lng) — v0.2
- Pincode boundary GeoJSON — v0.3
- FastAPI server — v0.3
- Docker — v0.3
- PyPI publish — after v0.1 acceptance
- Hindi/Devanagari script parsing beyond NFKC normalization — v0.2

## Dependencies
- Python ≥3.10 (for `dataclass(slots=True)` and modern typing)
- One of the GitHub pincode CSV mirrors must be reachable once at build time (not at runtime)
- No other runtime deps for v0.1

## Estimated Complexity
**M.** The parser rules and dataclass are small (~300 LOC). The unglamorous work is (a) sourcing and cleaning the pincode CSV into a usable JSON, (b) writing the 30+ test fixtures by hand with correct ground truth, (c) tuning regex rules until the test suite hits 80%. Realistically a focused day of work in one session.

## Session deliverable
A working `pip install -e .` package in `/Users/srinathprasannancs/India address parser/` that passes the 60-second demo from the README and ≥80% of the test suite. Committed in a fresh git repo.
