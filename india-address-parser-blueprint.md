# India Address Parser — Technical Blueprint for Claude Code

## What We're Building

An open-source Python library (`bharataddress`) that parses messy, unstructured Indian addresses into structured, geocoded JSON. Free core + paid data freshness layer.

**Input:** `"Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001"`

**Output:**
```json
{
  "building_number": "302",
  "building_name": "Raheja Atlantis",
  "landmark": "Hanuman Mandir",
  "locality": "Sector 31",
  "city": "Gurgaon",
  "state": "Haryana",
  "pincode": "122001",
  "confidence": 0.92,
  "lat": 28.4595,
  "lng": 77.0266
}
```

---

## Why This Matters (The Gap)

- **Libpostal** (the global gold standard, CRF-based, trained on 1B+ addresses from OSM) performs poorly on Indian addresses. Open GitHub issue since 2018, still unresolved. India's address format is fundamentally different — relational, landmark-based, no street numbering in most areas.
- **Deepparse** (Seq2Seq/LSTM, Canadian research group) has no India-specific training data.
- **Lokly** (99roomz) — India-specific, abandoned, demo site dead.
- **indian_address_parser** (shriekdj) — regex-level, extracts pincode/state only. Not ML.
- **Delhivery's AddFix** — the best solution, but proprietary & patented. Built on 1B+ delivery records. Achieves 200m median geocode precision and 90%+ locality detection. NOT available as open source.
- **HyperVerge** — commercial address matching for KYC/fintech. Closed-source API.

**Nobody has built a production-grade, open-source, India-specific address parser.** The opportunity is wide open.

---

## India's Unique Address Challenges

1. **Landmark-based addressing:** "Near temple", "Opp. SBI Bank", "Behind petrol pump" — these are valid address components, not noise.
2. **No street numbering in most areas:** Unlike US/EU, most Indian localities don't have numbered streets.
3. **Transliteration chaos:** Same locality written as "Gurgaon", "Gurugram", "Gudgaon" — phonetic variations across Hindi/English.
4. **Pin code covers huge areas:** Median pin code area is ~90 sq km, can contain up to 1M households. Pin code alone gives you almost nothing.
5. **Mixed languages:** Hindi + English in the same address string. "Gomti Nagar" vs "गोमती नगर".
6. **Abbreviations everywhere:** "H.No.", "S/O", "D/O", "W/O", "B.O.", "S.O.", "Opp.", "Nr."
7. **Missing components:** Rural addresses may lack house numbers entirely. "Village Ramapur, PO Jhanjharpur" is a complete address.
8. **Evolving geography:** New colonies, renamed streets, rezoned pin codes happen constantly.

---

## Available Public Data Sources

### 1. India Post Pincode Directory (PRIMARY)
- **Source:** data.gov.in — "All India Pincode Directory"
- **What it contains:** 155,000+ post offices mapped to 19,100 pin codes. Fields: Office Name, Pincode, Office Type, Delivery Status, Division, Region, Circle, Taluk, District, State.
- **Format:** CSV download, also available via API (data.gov.in API)
- **Updated:** Monthly (last update Oct 2025)
- **GitHub mirrors:** `kishorek/India-Codes`, `saravanakumargn/All-India-Pincode-Directory`, `dropdevrahul/pincodes-india`

### 2. India Pincode Boundary GeoJSON (CRITICAL)
- **Source:** data.gov.in — "All India Pincode Boundary Geo JSON"
- **What it contains:** Polygon boundaries for every delivery post office pin code in India
- **Format:** GeoJSON
- **This is gold.** Gives you spatial boundaries, not just point coordinates.
- **Also see:** `sanand0/pincode-shapes` on GitHub for computed Voronoi-based post office boundaries

### 3. OpenStreetMap India Data
- **Source:** planet.openstreetmap.org (India extract from Geofabrik)
- **What it contains:** Street names, POIs, building footprints, locality names
- **Coverage:** Patchy in rural India, good in metros. Being actively improved.
- **Access:** Nominatim API for geocoding, or download the India extract and run locally
- **Note:** OSM community is actively discussing importing India Post pincode data into Nominatim (Dec 2025 forum thread)

### 4. India Post Office Locations (Bhuvan/ISRO)
- **Source:** Bhuvan NSRC (National Spatial Reference Catalogue)
- **What it contains:** Lat/long coordinates for every post office in India
- **Access:** Not directly downloadable but has been scraped — see `sanand0/pincode-shapes`

### 5. Libpostal/Senzing Training Data
- **Source:** Senzing GitHub (`Senzing/libpostal-data`)
- **What it contains:** 1.7B+ tagged address training examples from OSM + OpenAddresses. Publicly downloadable TSV files.
- **Use:** Filter for India-tagged examples to create a baseline training set. Also useful for understanding the tagging schema.

---

## Architecture Decision: Don't Train a Model from Scratch

### The Pragmatic Approach

Don't build a CRF or Seq2Seq from scratch. Instead:

1. **Use an LLM (Claude API) for the heavy lifting** — structured extraction from messy text. Zero-shot or few-shot, no training needed.
2. **Use deterministic rules + lookup tables for validation** — pin code → district/state mapping, known locality lists, landmark keyword detection.
3. **Use fuzzy matching for spelling correction** — phonetic similarity (Soundex/Metaphone tuned for Indian languages), Levenshtein distance.
4. **Use geocoding for coordinate resolution** — Nominatim (self-hosted with India data) or Google Geocoding API as fallback.

### Why This Beats a Custom ML Model

- **No training data needed upfront** — LLMs already understand address structure
- **Handles edge cases naturally** — "S/O Ramesh, Near Shiv Mandir" is trivially parsed by an LLM
- **Multilingual out of the box** — Hindi, Tamil, Bengali addresses work without separate models
- **Ship in weeks, not months** — the data pipeline and API wrapper are the real work

### Architecture Layers

```
Layer 1: Preprocessing
  - Normalize unicode, fix encoding issues
  - Detect and normalize abbreviations (H.No., Opp., Nr., S/O, D/O etc.)
  - Extract pin code via regex (always 6 digits, first digit 1-8)
  - Detect language script (Devanagari, Tamil, Latin etc.)

Layer 2: Pin Code Enrichment
  - Lookup pin code → district, state, region, delivery post office
  - Load pin code boundary polygon for spatial validation
  - If no pin code found, defer to Layer 3

Layer 3: LLM-Powered Parsing (Claude API)
  - Send the address string + pin code context to Claude
  - Prompt: "Parse this Indian address into structured components"
  - Output: JSON with building_number, building_name, street, landmark,
    locality, sub_locality, city, district, state, pincode
  - Few-shot examples in the prompt for edge cases

Layer 4: Validation & Geocoding
  - Validate parsed city/district against pin code lookup
  - Fuzzy match locality names against known locality list for that pin code
  - Geocode using Nominatim (India instance) or Google Geocoding
  - Calculate confidence score based on component match rates

Layer 5: Caching & Learning
  - Cache parsed results keyed by normalized address hash
  - Log corrections/overrides for future model improvement
  - Build the training data flywheel for eventual custom model
```

---

## Technical Stack

### Core Library (Python)
```
bharataddress/
├── __init__.py           # Main parse() function
├── preprocessor.py       # Unicode normalization, abbreviation expansion
├── pincode.py           # Pin code lookup, boundary checks
├── parser.py            # LLM-based parsing (Claude API)
├── validator.py         # Cross-validation against known data
├── geocoder.py          # Coordinate resolution
├── fuzzy.py             # Phonetic matching for Indian names
├── data/
│   ├── pincodes.json    # India Post directory (embedded)
│   ├── localities.json  # Known locality names per pin code
│   ├── abbreviations.json # H.No., Opp., S/O etc.
│   └── landmarks.json   # Common landmark keywords
├── cli.py               # Command-line interface
└── api.py               # FastAPI server (optional)
```

### Dependencies
- `anthropic` — Claude API for LLM parsing
- `rapidfuzz` — Fast fuzzy string matching
- `pyphonetics` — Soundex/Metaphone for Indian name matching
- `shapely` — Geometry operations for pin code boundary checks
- `requests` — Nominatim geocoding calls
- `fastapi` + `uvicorn` — Optional API server

### Data Pipeline (Separate repo or scripts/)
```
scripts/
├── download_pincode_data.py    # Fetch from data.gov.in
├── download_osm_india.py       # Fetch India OSM extract
├── build_locality_index.py     # Extract locality names from OSM
├── build_pincode_boundaries.py # Process GeoJSON boundaries
├── build_training_set.py       # Generate labeled examples for evaluation
└── evaluate.py                 # Test parser against labeled dataset
```

---

## Implementation Plan (For Claude Code)

### Phase 1: Data Foundation (Day 1-2)

**Prompt for Claude Code:**
```
Build a Python data pipeline that:
1. Downloads the All India Pincode Directory from data.gov.in (CSV format)
2. Downloads pincode boundary GeoJSON from data.gov.in
3. Downloads the India-Codes dataset from github.com/kishorek/India-Codes
4. Processes these into two JSON files:
   - pincodes.json: keyed by 6-digit pincode, value = {district, state, region, offices: [{name, type, delivery_status, lat, lng}]}
   - pincode_boundaries.json: keyed by pincode, value = GeoJSON polygon
5. Build an abbreviations.json mapping common Indian address abbreviations to full forms
6. Include a CLI command to refresh the data
Put everything in a bharataddress/ Python package structure.
```

### Phase 2: Core Parser (Day 3-5)

**Prompt for Claude Code:**
```
Build the core parsing engine for the bharataddress Python package:

1. preprocessor.py:
   - Unicode normalization (NFKC)
   - Expand abbreviations from abbreviations.json
   - Extract pincode via regex (6 consecutive digits, first digit 1-8)
   - Normalize whitespace and punctuation
   - Handle mixed Hindi/English text

2. pincode.py:
   - Load pincodes.json on init (singleton, lazy load)
   - lookup(pincode) → {district, state, offices, region}
   - validate(pincode) → bool
   - get_boundary(pincode) → shapely Polygon or None

3. parser.py:
   - Use Claude API (anthropic SDK) to parse addresses
   - System prompt with 20 diverse Indian address examples covering:
     * Metro addresses (Mumbai, Delhi, Bangalore)
     * Tier 2/3 city addresses
     * Rural addresses with village/PO format
     * Addresses with S/O, D/O, W/O prefixes
     * Landmark-heavy addresses ("Near temple, behind school")
     * Addresses in mixed Hindi-English
   - Return structured JSON with confidence score
   - Include a fallback regex-based parser for when API is unavailable

4. Main parse() function in __init__.py:
   - Orchestrates: preprocess → extract pincode → enrich → LLM parse → validate
   - Returns ParsedAddress dataclass

Include comprehensive tests with 50+ real Indian address examples.
```

### Phase 3: Fuzzy Matching & Geocoding (Day 6-7)

**Prompt for Claude Code:**
```
Add fuzzy matching and geocoding to the bharataddress package:

1. fuzzy.py:
   - Implement phonetic matching tuned for Indian names
   - "Gurgaon" should match "Gudgaon" and "Gurugram"
   - "Laxmi Nagar" should match "Lakshmi Nagar"
   - Use a combination of Soundex + Levenshtein with Indian phonetic rules
   - match_locality(input, known_localities) → best match + score

2. validator.py:
   - Cross-validate parsed components against pincode data
   - Check if parsed city/district matches pincode lookup
   - Fuzzy match locality against known localities for that pincode
   - Generate confidence score (0-1) based on validation results

3. geocoder.py:
   - Primary: Nominatim API geocoding (rate-limited, cached)
   - Fallback: Use pincode centroid from pincode data
   - point_in_boundary(): Check if geocoded point falls within pincode polygon
   - Cache results in SQLite for repeat lookups

Add tests for each module.
```

### Phase 4: CLI & API (Day 8)

**Prompt for Claude Code:**
```
Add CLI and API interfaces to bharataddress:

1. cli.py (using click or argparse):
   - `bharataddress parse "Flat 302, Raheja Atlantis, Sector 31, Gurgaon 122001"`
   - `bharataddress parse --file addresses.csv --output parsed.json`
   - `bharataddress validate 122001`
   - `bharataddress update-data`

2. api.py (FastAPI):
   - POST /parse — parse single address
   - POST /parse/batch — parse multiple addresses
   - GET /pincode/{pincode} — lookup pincode info
   - GET /health — health check
   - Include rate limiting, CORS, and API key auth

3. Package setup:
   - pyproject.toml with all dependencies
   - README.md with installation, usage examples, API docs
   - Publish-ready for PyPI

4. Docker:
   - Dockerfile for the API server
   - docker-compose.yml with the API + optional Nominatim instance
```

### Phase 5: Evaluation & Open Source Launch (Day 9-10)

**Prompt for Claude Code:**
```
Build an evaluation framework for bharataddress:

1. Create a test dataset of 200 labeled Indian addresses covering:
   - 50 metro addresses (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Hyderabad)
   - 50 tier 2/3 city addresses
   - 50 rural/village addresses
   - 50 edge cases (missing pincode, landmark-only, mixed language, S/O format)

2. Build evaluate.py that:
   - Runs each address through the parser
   - Compares output against ground truth labels
   - Reports accuracy per component (pincode, city, state, locality, building)
   - Reports overall parse accuracy (all components correct)
   - Generates a markdown report

3. Benchmark against libpostal on the same dataset

4. Create GitHub README with:
   - Problem statement
   - Installation instructions
   - Quick start examples
   - API documentation
   - Accuracy benchmarks
   - Contributing guide
   - Open source license (MIT)
```

---

## Monetisation Model

### Free Tier (Open Source - MIT License)
- Core parsing library
- Static pincode data (updated quarterly by community)
- Regex + LLM parsing (users bring their own Claude API key)
- Basic fuzzy matching

### Paid Tier ($49-499/mo depending on volume)
- Pre-built, continuously updated locality database
- Real-time pincode boundary updates
- Managed API (no need for own Claude API key)
- Higher geocoding precision
- Bulk parsing endpoints
- Webhook for address validation at checkout

### Enterprise
- On-premise deployment
- Custom model training on customer's delivery data
- SLA, support, dedicated instance

---

## Key References

- Delhivery AddFix architecture: medium.com/@kabirrustogi/learning-to-decode-unstructured-indian-addresses
- Libpostal architecture: mapzen.com/blog/inside-libpostal/
- Libpostal India issues: github.com/openvenues/libpostal/issues/304
- Deepparse paper: aclanthology.org/2023.nlposs-1.3.pdf
- India Post data: data.gov.in/catalog/all-india-pincode-directory-through-webservice
- Pincode boundaries: data.gov.in/catalog/all-india-pincode-boundary-geo-json
- Pincode shapes: github.com/sanand0/pincode-shapes
- HyperVerge address matching: cdn.hyperverge.co/blog/address-match-onboarding-ai-india/
- Indian Address Parser (Hugging Face demo): medium.com/data-and-beyond/the-ai-that-understands-indian-addresses
- Senzing libpostal data: github.com/Senzing/libpostal-data
