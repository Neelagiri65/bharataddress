# bharataddress

**The deterministic Indian address parser. Zero config. Zero API keys. Zero network calls.**

`pip install bharataddress` → parse messy Indian addresses into structured JSON in one line. No model downloads, no Claude API key, no Nominatim instance, nothing to set up. The pincode directory ships embedded in the package.

```python
>>> from bharataddress import parse
>>> parse("Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001").to_dict()
{
  "building_number": "302",
  "building_name": "Raheja Atlantis",
  "landmark": "Hanuman mandir",
  "locality": "Sector 31",
  "city": "Gurgaon",
  "district": "Gurgaon",
  "state": "Haryana",
  "pincode": "122001",
  "confidence": 1.0
}
```

That's the whole pitch. Sixty seconds from `pip install` to a parsed address.

---

## Why this exists

Indian addresses break every off-the-shelf parser. **Libpostal** (the global gold standard) has had an open issue for India support since 2018. **Deepparse** has no India training data. **Lokly** is abandoned. **Delhivery's AddFix** is the best solution but proprietary, patented, and unavailable. **HyperVerge** is closed-source, paid-only.

Indian addresses are different:

- **Landmark-based** — "Near Hanuman Mandir", "Opp SBI Bank", "Behind Reliance Fresh" are valid components, not noise
- **No street numbering** in most localities
- **Transliteration chaos** — Gurgaon / Gurugram / Gudgaon all refer to the same place
- **Pincodes cover huge areas** — median 90 km², up to 1M households
- **Mixed Hindi + English** in the same string
- **Abbreviation soup** — H.No., S/O, D/O, W/O, B.O., S.O., Opp., Nr., Ngr., Clny, Mohalla, Marg

`bharataddress` handles all of these in v0.1 with pure rules + the embedded India Post directory. No ML model. No API. No network.

---

## Install

```bash
pip install bharataddress
```

Or from source:

```bash
git clone https://github.com/Neelagiri65/bharataddress
cd bharataddress
pip install -e .
```

Requires Python ≥3.10. Zero runtime dependencies.

---

## Usage

### Python

```python
from bharataddress import parse

result = parse("h.no.45/2 ; phase-2 ; sector 14 ; gurgaon - 122001")
print(result.pincode)     # '122001'
print(result.state)       # 'Haryana'
print(result.locality)    # 'sector 14'
print(result.confidence)  # 1.0

# JSON-friendly dict
result.to_dict()
```

### CLI

```bash
bharataddress parse "12, Dalal Street, Fort, Mumbai 400001" --pretty
bharataddress lookup 560001
bharataddress --version
```

### Pincode lookup (no parsing)

```python
from bharataddress import pincode
pincode.lookup("122001")
# {'pincode': '122001', 'district': 'Gurgaon', 'city': 'Gurgaon',
#  'state': 'Haryana', 'offices': [...]}
```

---

## What you get back

| Field             | Type            | Source                                       |
| ----------------- | --------------- | -------------------------------------------- |
| `building_number` | `str \| None`   | First numeric segment / `Flat`/`H.No.` lead  |
| `building_name`   | `str \| None`   | Segment after building number                |
| `landmark`        | `str \| None`   | `Near/Opp/Behind/Beside/Next to/...` segment |
| `locality`        | `str \| None`   | `Sector/Phase/Block/<x> Nagar/<x> Colony/…`  |
| `sub_locality`    | `str \| None`   | Second locality match if present             |
| `city`            | `str \| None`   | Pincode lookup; falls back to text guess     |
| `district`        | `str \| None`   | Pincode lookup                               |
| `state`           | `str \| None`   | Pincode lookup                               |
| `pincode`         | `str \| None`   | `[1-8]\d{5}` regex, validated against DB     |
| `confidence`      | `float (0..1)`  | Weighted component-presence score            |
| `cleaned`         | `str`           | Normalised input after preprocessing         |
| `raw`             | `str`           | Original input                               |

**Confidence weights:** pincode 0.40, city-matches-pincode 0.20, locality 0.20, building 0.10, landmark 0.10.

---

## How it works

```
input string
    │
    ▼
Layer 1 — Preprocess           NFKC unicode → expand abbreviations
                               → normalise vernacular tokens
                               → tidy whitespace
    │
    ▼
Layer 2 — Extract pincode      regex [1-8]\d{5} → embedded India Post lookup
                               → district / state / city
    │
    ▼
Layer 3 — Segment & classify   walk comma-separated parts; rules for
                               building / landmark / locality
    │
    ▼
Layer 4 — Confidence scoring   weighted component presence
    │
    ▼
ParsedAddress
```

The embedded `pincodes.json` contains 23,915 Indian pincodes derived from the India Post directory mirror at [`kishorek/India-Codes`](https://github.com/kishorek/India-Codes). Refresh it any time with `python scripts/build_pincode_data.py`.

---

## What's NOT in v0.1

By design, kept out so the package stays small, fast, and dependency-free:

- ❌ LLM parsing (Claude API) — **v0.2**
- ❌ Phonetic fuzzy matching (Gurgaon ↔ Gudgaon) — **v0.2**
- ❌ Geocoding (lat/lng) — **v0.2**
- ❌ Pincode boundary GeoJSON — **v0.3**
- ❌ FastAPI server — **v0.3**
- ❌ Devanagari / Tamil / Bengali script parsing — **v0.2** (English + Romanised Hindi only for v0.1)

The architecture already accommodates all of these. v0.1 ships the foundation everything else builds on.

---

## Tests

```bash
pip install -e ".[dev]"
pytest
```

37 tests covering metro, tier 2/3, rural village, S/O format, landmark-heavy, vernacular, missing-pincode, and irregular-punctuation cases. All passing on v0.1.0.

There is also an architectural-constraint test that monkeypatches `socket.socket` and asserts `parse()` opens **zero** network connections. The "offline by default" promise is enforced in CI.

---

## Roadmap

- **v0.2** — Opt-in Claude API parser for the messy 20% • phonetic fuzzy matching • Nominatim geocoding • Devanagari preprocessing
- **v0.3** — Pincode boundary GeoJSON • spatial validation • FastAPI server • Docker
- **v0.4** — Distilled local model trained on Claude-generated parses (eliminates LLM cost at scale)

**The moat is the data, not the parser.** Every paid-tier user who corrects an address makes the dataset better. Free core (this package, MIT) + paid layer for continuously updated, validated locality and boundary data.

---

## Contributing

Issues and PRs welcome. The most useful contributions for v0.1:

1. **Failing addresses** — open an issue with a real-world string the parser mangles
2. **Vernacular mappings** — add to `bharataddress/data/vernacular_mappings.json`
3. **Test cases** — add to `tests/test_parse.py`

---

## License

MIT. Use it for anything. The data sources (India Post directory) are public domain via data.gov.in.
