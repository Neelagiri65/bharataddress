# Issue: leadpoet/leadpoet

**Repo**: https://github.com/leadpoet/leadpoet (8 stars, updated today, Python)
**File**: `gateway/utils/geo_normalize.py` — `INTERNATIONAL_CITY_ALIASES` India section
**Status**: DRAFT — review before opening

---

## Title

India city aliases: missing entries and no fuzzy/misspelling coverage

## Body

Your `geo_normalize.py` has a solid city normalisation system. The India
section in `INTERNATIONAL_CITY_ALIASES` currently covers 5 aliases:

```python
# gateway/utils/geo_normalize.py (current India section)
'bangalore': 'bengaluru',
'bombay': 'mumbai',
'gurgaon': 'gurugram',
'ernakulam': 'kochi',
'calcutta': 'kolkata',
```

Two gaps worth flagging:

### 1. Missing common aliases

These officially renamed cities aren't covered:

| Old name | Current name | Renamed |
|---|---|---|
| Madras | Chennai | 1996 |
| Trivandrum | Thiruvananthapuram | 1991 |
| Baroda | Vadodara | 1974 |
| Poona | Pune | 1978 |
| Simla | Shimla | 1972 |
| Pondicherry | Puducherry | 2006 |
| Allahabad | Prayagraj | 2018 |
| Cochin | Kochi | 1996 |

You have `ernakulam → kochi` but not `cochin → kochi`, which is the more common
alias people actually type.

### 2. No misspelling tolerance

The current approach uses exact string matching, which works for known aliases
but misses the misspellings that real users type:
- `Banglore` (very common — missing the 'a')
- `Bangaluru` (transposed vowels)
- `Hydrebad` / `Hydrabad` (common for Hyderabad)
- `Chenai` (single 'n')
- `Kolkatta` (double 't')

For your India leads, these misspellings are probably more frequent than the
old-name aliases.

### Possible approach

If you wanted to handle both gaps for the India portion specifically,
[bharataddress](https://pypi.org/project/bharataddress/) has a phonetic
normalisation module that covers all Indian city renames + fuzzy matching for
misspellings:

```python
from bharataddress.phonetic import normalise, fuzzy_ratio

normalise("Gurugram") == normalise("Gurgaon")      # True
normalise("Madras") == normalise("Chennai")          # True
fuzzy_ratio("Banglore", "Bangalore")                 # > 0.9
fuzzy_ratio("Hydrebad", "Hyderabad")                 # > 0.9
```

Zero runtime dependencies in the base install, MIT licensed. The phonetic
module is independent of the address parser — you could use just
`bharataddress.phonetic` for city normalisation without pulling in the full
parser.

Could integrate as a fallback in `_normalize_for_validation()` — try exact
alias match first (your current approach), then fall through to phonetic match
for India entries only. Keeps the existing system intact for all other countries.

Not sure if the India lead volume justifies adding a dependency. Just flagging
the gap in case it's causing silent mismatches in your pipeline.
