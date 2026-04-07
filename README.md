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

## DIGIPIN

`bharataddress` ships a verbatim Python port of the official India Post DIGIPIN
algorithm (Apache-2.0, [github.com/INDIAPOST-gov/digipin](https://github.com/INDIAPOST-gov/digipin)).
DIGIPIN is the 10-character geocode published by the Department of Posts in 2025
that maps any point in India to a ~3.8 m grid cell. Pure math, no network, no
dependencies.

```python
from bharataddress import digipin

# Encode lat/lng -> DIGIPIN (XXX-XXX-XXXX)
digipin.encode(28.6129, 77.2295)
# '39J-429-L4TK'

# Decode back to the centre lat/lng of the cell
digipin.decode('39J-429-L4TK')
# (28.612906..., 77.229494...)

# Validate
digipin.validate('39J-429-L4TK')   # True
digipin.validate('AAA-BBB-CCCC')   # False
```

`parse()` accepts an optional `latlng=` hint and populates a `digipin` field
on the result when a coordinate is supplied:

```python
from bharataddress import parse

result = parse(
    "Plot 88, Basheer Bagh, Hyderabad 500001",
    latlng=(17.3850, 78.4867),
)
result.digipin
# '422-594-J546'
```

The parser does not geocode addresses on its own — `digipin` stays `None`
unless you pass a coordinate. The bounding box is hard-coded to India
(lat 2.5–38.5, lng 63.5–99.5); points outside raise `ValueError`.

---

## v0.2 modules

v0.2 ships six new modules around the core parser. All offline, all
zero-dependency, all importable straight from the top-level package.

### `formatter` — reconstruct a clean address

```python
>>> from bharataddress import parse, format
>>> p = parse("Flat 302, Raheja Atlantis, Sector 31, Gurgaon 122001")
>>> print(format(p, style="india_post"))
302 Raheja Atlantis
Sector 31
Gurgaon, Gurgaon
Haryana, 122001
>>> format(p, style="single_line")
'302 Raheja Atlantis, Sector 31, Gurgaon, Gurgaon, Haryana, 122001'
>>> print(format(p, style="label"))
Building: 302 Raheja Atlantis
Locality: Sector 31
City: Gurgaon
...
```

### `validator` — confidence + consistency

```python
>>> from bharataddress import parse, validate, is_deliverable
>>> p = parse("Flat 302, Sector 31, Gurgaon 122001")
>>> is_deliverable(p)
True
>>> validate(p)
{'fields': {'pincode': 1.0, 'state': 1.0, ...}, 'issues': [], 'is_deliverable': True, 'overall': 0.91}
```

`validate` flags state / district / city mismatches against the embedded India
Post directory. `is_deliverable` is the minimum-fields check (pincode + city +
state).

### `geocoder` — pincode centroid + reverse geocoding

```python
>>> from bharataddress import parse, geocode, reverse_geocode
>>> geocode(parse("Sector 31, Gurgaon 122001"))  # None until pincodes.json gains centroids
None
>>> reverse_geocode(28.6129, 77.2295)
{'digipin': '39J-438-TJC7', 'pincode': None, 'distance_km': None}
```

DIGIPIN is always returned (it's pure math). The nearest pincode is returned
once a future dataset refresh adds latitude / longitude per pincode — the
hook is wired and dormant today.

### `similarity` — fuzzy address matching

```python
>>> from bharataddress import address_similarity
>>> address_similarity("MG Road, Bengaluru 560001",
...                    "Mahatma Gandhi Road, Bangalore 560001")
0.9
```

Pincode is the strongest signal, then city (with Bengaluru/Bangalore,
Mumbai/Bombay, etc. aliasing), then locality token overlap. Returns a float
in `[0, 1]`.

### `batch` — list / CSV / DataFrame helpers

```python
>>> from bharataddress import parse_batch, parse_csv, parse_dataframe
>>> parse_batch(["Sector 31, Gurgaon 122001", "Anna Salai, Chennai 600002"])
[ParsedAddress(...), ParsedAddress(...)]
>>> parse_csv("addresses.csv", column="address")  # writes addresses_parsed.csv
PosixPath('addresses_parsed.csv')
>>> parse_dataframe(df, column="address")  # pandas optional, lazy import
```

### `enrichment` — non-address sources

```python
>>> from bharataddress import extract_state_from_gstin
>>> extract_state_from_gstin("29ABCDE1234F1Z5")
'Karnataka'
```

The first two digits of a GSTIN are the GST Council state code. Pure lookup,
no network.

---

## What's NOT in v0.2

By design, kept out so the package stays small, fast, and dependency-free:

- ❌ LLM parsing (Claude API)
- ❌ Phonetic fuzzy matching (Gurgaon ↔ Gudgaon)
- ❌ Pincode boundary GeoJSON — **v0.3**
- ❌ FastAPI server — **v0.3**
- ❌ Devanagari / Tamil / Bengali script parsing — English + Romanised Hindi only

The architecture already accommodates all of these. v0.2 ships the foundation everything else builds on.

---

## Tests

```bash
pip install -e ".[dev]"
pytest
```

95 tests covering parser, DIGIPIN, formatter, validator, geocoder, similarity, batch, and enrichment modules. All passing on v0.2.0.

There is also an architectural-constraint test that monkeypatches `socket.socket` and asserts `parse()` opens **zero** network connections. The "offline by default" promise is enforced in CI.

---

## Benchmarks

`bharataddress` ships with a 200-row hand-labelled gold set (`tests/data/gold_200.jsonl`) covering metro / tier-2 / rural / landmark-heavy / vernacular / no-pincode / irregular-punctuation / S-O-format inputs. `scripts/evaluate.py` reports per-field precision / recall / F1 plus exact-match. The matcher is two-way substring (`a in b or b in a`), case-insensitive.

### bharataddress v0.1.2 vs Shiprocket TinyBERT NER

The only other open-source Indian address parser of comparable scope is [`shiprocket-ai/open-tinybert-indian-address-ner`](https://huggingface.co/shiprocket-ai/open-tinybert-indian-address-ner) — a fine-tuned TinyBERT (~760 MB, Apache-2.0). It claims Micro F1 0.94 on a private set; this is the first public head-to-head I'm aware of. Both models were run over the same `gold_200.jsonl`. Reproduce with `python scripts/eval_competitor.py`.

| Field             | bharataddress v0.1.2 F1 | TinyBERT F1 | Winner             |
| ----------------- | ----------------------: | ----------: | ------------------ |
| `pincode`         |               **0.995** |       0.984 | bharataddress      |
| `city`            |               **0.959** |       0.718 | bharataddress (+0.24) |
| `building_number` |                   0.958 |   **0.973** | TinyBERT (+0.02)   |
| `state`           |               **0.923** |       0.268 | bharataddress (+0.66) |
| `landmark`        |               **0.918** |       0.580 | bharataddress (+0.34) |
| `district`        |               **0.933** |        N/A* | bharataddress      |
| `locality`        |               **0.723** |       0.634 | bharataddress (+0.09) |
| `building_name`   |                   0.635 |   **0.643** | TinyBERT (+0.01)   |
| `sub_locality`    |                   0.472 |       0.470 | tied               |

\* TinyBERT has no `district` label; closest equivalent in its label set is `state`.

**Exact-match (all 9 fields must match):** bharataddress **48.5%** (97/200) vs TinyBERT 1.0% (2/200). The exact-match gap is misleading because TinyBERT can never produce a `district` and can't reach `state` reliably without the pincode lookup, but the per-field F1 is the apples-to-apples view.

**Where each model wins:**
- `bharataddress` wins decisively on pincode-derived fields (`city`, `district`, `state`, `pincode`) because the embedded India Post directory turns these into a lookup, not a prediction. It also handles `landmark` better thanks to the `Near/Opp/Behind/Beside` cue list.
- `TinyBERT` is essentially tied on `building_number`, `building_name`, and `sub_locality` — fields where context matters more than vocabulary.
- Neither model is good at `sub_locality` yet (~0.47) — both struggle to disambiguate "MG Road" (sub_locality) from "Indiranagar" (locality) when the input is sparse.

**Footprint comparison:**

|                              | bharataddress v0.1.2 | TinyBERT NER |
| ---------------------------- | -------------------- | ------------ |
| Install size                 | ~5 MB (incl. 23k pincodes) | ~760 MB |
| Runtime dependencies         | none                 | torch, transformers (~2 GB) |
| First-call latency           | ~5 ms                | ~150 ms (CPU) |
| Network calls during parse   | zero (enforced)      | zero (after download) |
| GPU required                 | no                   | no, but recommended |
| Pincode → district/state     | yes (lookup)         | no |

For high-throughput pipelines, batch geocoding, or any environment where dropping a 760 MB model is a non-starter (serverless, mobile, edge), `bharataddress` is the better fit. For free-form addresses where you don't have a pincode at all, TinyBERT's text-only approach is competitive on the structural fields.

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
