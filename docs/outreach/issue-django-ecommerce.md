# Issue: sa1if3/django_ecommerce

**Repo**: https://github.com/sa1if3/django_ecommerce (28 stars, Django e-commerce marketplace)
**File**: `genesis/forms.py` — `AddressForm`
**Status**: DRAFT — review before opening

---

## Title

Auto-fill city and state from pincode — fewer form fields, fewer user errors

## Body

Hey! Was looking at the address handling in `genesis/forms.py` and noticed a
pattern I've seen in a lot of Indian e-commerce projects — collecting pincode,
city, and state as three separate manual-entry fields:

```python
# genesis/forms.py (current)
city = forms.CharField(min_length=5, max_length=100)
state = forms.CharField(min_length=5, max_length=100)
pincode = forms.CharField(min_length=6, validators=[RegexValidator(
    '^[1-9][0-9]{5}$', message="Enter a Valid Indian Pincode")])
```

Two issues here:

**1. The regex accepts non-existent pincodes.** `^[1-9][0-9]{5}$` passes
`999999`, `111111`, and any other 6-digit number. India Post has ~26,700 valid
pincodes — the regex accepts ~900,000.

**2. City and state are redundant.** Indian pincodes map deterministically to
state and district. If the user types `560001`, you already know it's
Karnataka / Bangalore. Asking them to type that manually means more form
friction and more typos (`Banglore`, `Karnatka`, etc.).

### Suggested fix

[bharataddress](https://pypi.org/project/bharataddress/) is a Python library
with 26,711 embedded India Post pincodes. Zero runtime dependencies, works
offline, MIT licensed.

```python
from bharataddress import parse

result = parse("560001")
# result.pincode  → '560001'
# result.state    → 'Karnataka'
# result.district → 'Bangalore'
```

The `AddressForm` could validate pincode against real data and auto-populate
city/state on the backend (or via an AJAX call on pincode blur for instant
frontend feedback):

```python
# genesis/forms.py (suggested)
from bharataddress import parse

class AddressForm(forms.ModelForm):
    name = forms.CharField(min_length=5, max_length=200)
    address_line_1 = forms.CharField(min_length=20, max_length=200)
    address_line_2 = forms.CharField(min_length=10, max_length=200, required=False)
    pincode = forms.CharField(min_length=6, max_length=6)
    # city and state auto-filled from pincode — no manual entry needed
    contact_name = forms.CharField(min_length=5, max_length=100)
    contact_number = forms.CharField(min_length=10, max_length=10, validators=[...])
    delivery_instructions = forms.CharField(min_length=10, max_length=100, required=False)

    def clean_pincode(self):
        pincode = self.cleaned_data['pincode']
        result = parse(pincode)
        if not result.state:
            raise ValidationError("Enter a valid Indian pincode")
        # Store derived fields for save()
        self._parsed_address = result
        return pincode

    def save(self, commit=True):
        instance = super().save(commit=False)
        if hasattr(self, '_parsed_address'):
            instance.city = self._parsed_address.district or ''
            instance.state = self._parsed_address.state or ''
        if commit:
            instance.save()
        return instance
```

The `Address` model in `genesis/models.py` doesn't need to change — `city` and
`state` fields stay, they're just populated automatically instead of manually.

This is a small change (one file, ~15 lines) that:
- Eliminates 2 form fields from the user's perspective
- Validates pincodes against real India Post data instead of a regex
- Prevents city/state typos entirely

Happy to open a PR if this would be useful. `pip install bharataddress` to try
it out.
