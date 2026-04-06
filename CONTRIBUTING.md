# Contributing to bharataddress

Thank you for considering a contribution. This project exists because Indian addresses break every off-the-shelf parser, and the only way it gets better is real-world usage and contributions from people who hit edge cases the maintainers didn't anticipate.

## Most useful contributions for v0.1

### 1. Failing addresses (highest priority)

If `parse()` mangles a real address, **open an issue**. Include:

- The raw input string (anonymise PII — change names and exact house numbers)
- What `parse(addr).to_dict()` currently returns
- What the correct parse should look like
- The city/state context if relevant

These issues directly drive v0.2 priorities. The first 20 failing-address issues will shape whether v0.2 focuses on LLM parsing, fuzzy phonetic matching, Devanagari preprocessing, or something else entirely.

### 2. Vernacular mappings

`bharataddress/data/vernacular_mappings.json` contains Romanised Hindi locality terms and their canonical forms (`Ngr` → `Nagar`, `Gully` → `Gali`). It is incomplete by design.

To add a mapping:

1. Edit `vernacular_mappings.json` and add the variant on the left, the canonical form on the right.
2. Add at least one test case in `tests/test_parse.py` that exercises the new mapping.
3. Run `pytest`. All 37+ tests must pass.
4. Open a PR.

We want this file to grow to several hundred mappings. Tamil, Telugu, Bengali, Marathi, and Punjabi Romanisations are all welcome.

### 3. Test fixtures

The test suite in `tests/test_parse.py` is the parser's spec. New labelled examples — especially for tier 3 cities, rural addresses, and the north-east — make the parser measurably better and protect against regressions.

### 4. Pincode dataset corrections

The embedded `bharataddress/data/pincodes.json` is built from `kishorek/India-Codes`. If you find a wrong district/state for a pincode, the fix lives upstream — open an issue there too. For local fixes, edit `scripts/build_pincode_data.py` to apply patches and re-run it.

## What we are NOT accepting in v0.1 PRs

Save these for v0.2 / v0.3 — they need a coordinated design pass first:

- LLM integration (Claude API, OpenAI, Gemini)
- New Python dependencies (`rapidfuzz`, `shapely`, `requests`, …)
- Geocoding (lat/lng resolution)
- FastAPI server, Docker, deployment scripts
- Devanagari / non-Latin script preprocessing
- Custom ML models

The v0.1 promise is **deterministic, offline, dependency-free**. PRs that violate this will be politely redirected to a v0.2 discussion.

## Development setup

```bash
git clone https://github.com/Neelagiri65/bharataddress
cd bharataddress
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

All 37 tests should pass in under 0.1 seconds.

## Code style

- Python ≥3.10
- No new runtime dependencies
- Type hints on all public functions
- Pure functions in the preprocessor and parser (no global state beyond the lazy-loaded pincode table)
- British English in user-facing strings; American spellings in code identifiers are fine

## Commit messages

`type: short description` — `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Keep commits small and atomic.

## Code of Conduct

Be kind. Be specific. Assume good faith. We're building a public good for Indian developers — keep it that way.
