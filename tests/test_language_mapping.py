"""v0.4 issue #2: language-aware vernacular mapping selection.

Locks the contract that:
* shared (``common.json``) terms fire everywhere,
* language-specific terms (``ta.json``, ``te.json``, ...) fire only when the
  pincode resolves to a state whose primary language matches the file,
* a Tamil-only term does NOT fire on a Bengal address (and vice versa).

These tests guard the SheetPortal-rejection failure pattern: never claim a
vernacular language is supported without a test that proves it doesn't bleed
into a different region.
"""

from __future__ import annotations

from bharataddress import language
from bharataddress.preprocessor import normalise_vernacular, preprocess


# --- Pincodes used as language anchors ----------------------------------------
# Each is a real, India-Post-published pincode in the relevant state. We're
# resolving via the embedded pincode dataset, so these must exist in pincodes.json.
CHENNAI_PIN = "600017"      # Tamil Nadu  -> ta
KOLKATA_PIN = "700001"      # West Bengal -> bn
HYDERABAD_PIN = "500001"    # Telangana   -> te
BANGALORE_PIN = "560001"    # Karnataka   -> kn
MUMBAI_PIN = "400001"       # Maharashtra -> hi
KOCHI_PIN = "682001"        # Kerala      -> ml
DELHI_PIN = "110001"        # Delhi       -> hi


# --- from_pincode resolution --------------------------------------------------

def test_from_pincode_chennai_returns_ta() -> None:
    assert language.from_pincode(CHENNAI_PIN) == ["ta"]


def test_from_pincode_kolkata_returns_bn() -> None:
    assert language.from_pincode(KOLKATA_PIN) == ["bn"]


def test_from_pincode_hyderabad_returns_te() -> None:
    assert language.from_pincode(HYDERABAD_PIN) == ["te"]


def test_from_pincode_bangalore_returns_kn() -> None:
    assert language.from_pincode(BANGALORE_PIN) == ["kn"]


def test_from_pincode_kochi_returns_ml() -> None:
    assert language.from_pincode(KOCHI_PIN) == ["ml"]


def test_from_pincode_delhi_returns_hi() -> None:
    assert language.from_pincode(DELHI_PIN) == ["hi"]


def test_from_pincode_unknown_returns_empty() -> None:
    assert language.from_pincode(None) == []
    assert language.from_pincode("999999") == []


# --- load_mappings merge semantics --------------------------------------------

def test_load_mappings_common_only_when_no_lang() -> None:
    m = language.load_mappings([])
    assert "nagar" not in m  # 'nagar' is a value, not a key
    assert m.get("ngr") == "nagar"
    # Tamil-only term must not appear when no language is requested.
    assert "salai" not in m


def test_load_mappings_includes_requested_language() -> None:
    m = language.load_mappings(["ta"])
    assert m.get("salai") == "salai"
    assert m.get("ngr") == "nagar"  # common still loaded


def test_load_mappings_unknown_language_silently_ignored() -> None:
    m = language.load_mappings(["xx"])
    assert "salai" not in m
    assert m.get("ngr") == "nagar"


# --- Salai / Veedhi / Nagar fire-only-where-they-should -----------------------

def test_salai_fires_in_chennai() -> None:
    out = normalise_vernacular("Anna Saalai", pincode=CHENNAI_PIN)
    assert "salai" in out.lower()


def test_salai_does_not_fire_in_kolkata() -> None:
    # 'saalai' is Tamil-only — must remain unchanged in West Bengal.
    out = normalise_vernacular("Anna Saalai", pincode=KOLKATA_PIN)
    assert "salai" not in out.lower(), f"Tamil term leaked into Bengal address: {out!r}"
    assert "saalai" in out.lower()


def test_veedhi_fires_in_hyderabad() -> None:
    out = normalise_vernacular("Gandhi Vidhi", pincode=HYDERABAD_PIN)
    assert "veedhi" in out.lower()


def test_veedhi_does_not_fire_in_chennai() -> None:
    out = normalise_vernacular("Gandhi Vidhi", pincode=CHENNAI_PIN)
    assert "veedhi" not in out.lower()


def test_nagar_fires_everywhere() -> None:
    for pin in (CHENNAI_PIN, KOLKATA_PIN, HYDERABAD_PIN, BANGALORE_PIN, MUMBAI_PIN, KOCHI_PIN):
        out = normalise_vernacular("Indira Ngr", pincode=pin)
        assert "nagar" in out.lower(), f"common term failed to fire for pincode {pin}: {out!r}"


# --- End-to-end through preprocess() (the path parser actually uses) ----------

def test_preprocess_threads_pincode_into_vernacular_chennai() -> None:
    cleaned, pin = preprocess("123, Anna Saalai, T Nagar, Chennai 600017")
    assert pin == "600017"
    assert "salai" in cleaned.lower()


def test_preprocess_does_not_apply_tamil_terms_to_kolkata() -> None:
    cleaned, pin = preprocess("12, Anna Saalai, Park Street, Kolkata 700001")
    assert pin == "700001"
    assert "salai" not in cleaned.lower()
    assert "saalai" in cleaned.lower()
