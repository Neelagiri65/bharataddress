# r/developersIndia Post: "Your pincode regex validates nothing"

**Subreddit**: r/developersIndia
**Flair**: Code Review / Discussion
**Status**: DRAFT — review before posting

---

## Title

I searched GitHub for how Indian devs validate pincodes. Most of you aren't validating anything.

## Body

I was building an Indian address parser and got curious: how do other projects
handle pincode validation? So I searched GitHub for `pincode` across Python,
JavaScript, and Django codebases.

What I found was... remarkably consistent.

### The pattern

**20+ repos** use some variation of this:

```python
# Django
pincode = models.CharField(max_length=6)
pincode = forms.CharField(validators=[RegexValidator(r'^[1-9][0-9]{5}$')])

# FastAPI / Pydantic
pincode: str = Field(..., min_length=6, max_length=6)

# JavaScript
function validate(pincode) { return /^[1-9]\d{5}$/.test(pincode); }
```

This validates **format**, not **existence**. It accepts:
- `999999` — not a real pincode
- `111111` — not a real pincode
- `100000` — not a real pincode
- literally 899,999 fake pincodes out of 900,000 possible values

India Post has **26,711** active pincodes. Your 6-digit regex has a 3% hit rate
on reality.

### The "3 fields too many" problem

Even worse, I found **15+ checkout/address forms** that collect pincode, city,
AND state as separate user inputs:

```python
city = forms.CharField(max_length=100)
state = forms.CharField(max_length=100)
pincode = forms.CharField(max_length=6)
```

Indian pincodes map deterministically to state and district. If someone types
`400001`, you already know it's Maharashtra, Mumbai. Asking users to type that
manually gives you:
- `Bombay` vs `Mumbai` inconsistency in your DB
- `Maharastra` (typo) vs `Maharashtra`
- `Banglore` for Bangalore/Bengaluru entries
- Three fields of friction that should be one

### The city aliasing problem

**12 repos** I found maintain hand-rolled dicts like this:

```python
CITY_ALIASES = {
    'gurgaon': 'gurugram',
    'bombay': 'mumbai',
    'bangalore': 'bengaluru',
    'calcutta': 'kolkata',
}
```

Every single one was incomplete. None handled misspellings (`Banglore`,
`Hydrebad`, `Chenai`). Most missed half the officially renamed cities (Madras→
Chennai, Trivandrum→Thiruvananthapuram, Allahabad→Prayagraj, etc.).

### What actually works

I built [bharataddress](https://pypi.org/project/bharataddress/) to solve this
for my own projects. It's a Python library that:

- Ships **26,711 embedded India Post pincodes** — validates against real data,
  not a regex
- **Derives city, state, and district from pincode** — one field replaces three
- **Phonetic city matching** — `normalise("Gurgaon") == normalise("Gurugram")`,
  handles misspellings
- **Parses free-text Indian addresses** — give it a full address string, get
  structured fields back
- **Zero runtime dependencies**, works offline, MIT licensed
- **Indic script support** (Hindi, Tamil, Telugu, Kannada, Bengali, Malayalam)
  via opt-in transliteration

```python
from bharataddress import parse

result = parse("42 MG Road, Bangalore 560001")
# result.pincode   → '560001'
# result.state     → 'Karnataka'
# result.district  → 'Bangalore'
# result.street    → '42 MG Road'
```

It's on PyPI: `pip install bharataddress`

### The point

If you're building anything in India that touches addresses — e-commerce,
logistics, fintech KYC, hospital finders, food delivery — you probably have a
pincode field somewhere. Check what's actually validating it.

---

**Edit**: To be clear, this isn't just "use my library." The underlying point is
that a 6-digit regex is theatre, not validation. Whether you use bharataddress
or build your own lookup against the
[India Post directory](https://data.gov.in/catalog/all-india-pincode-directory),
validate against real data. Your users will thank you.
