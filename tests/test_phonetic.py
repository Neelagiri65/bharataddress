"""Tests for bharataddress.phonetic — alias canonicalisation + fuzzy matching."""
from bharataddress import phonetic


def test_post_independence_renames_canonicalise():
    pairs = [
        ("Mumbai", "Bombay"),
        ("Bengaluru", "Bangalore"),
        ("Kolkata", "Calcutta"),
        ("Chennai", "Madras"),
        ("Gurugram", "Gurgaon"),
        ("Pune", "Poona"),
        ("Thiruvananthapuram", "Trivandrum"),
        ("Kochi", "Cochin"),
        ("Vadodara", "Baroda"),
        ("Mysuru", "Mysore"),
        ("Prayagraj", "Allahabad"),
        ("Puducherry", "Pondicherry"),
    ]
    for a, b in pairs:
        assert phonetic.normalise(a) == phonetic.normalise(b), (a, b)


def test_misspellings_canonicalise_to_known():
    assert phonetic.normalise("Gudgaon") == phonetic.normalise("Gurgaon")
    assert phonetic.normalise("Bangalroe") == phonetic.normalise("Bangalore")
    assert phonetic.normalise("Chenai") == phonetic.normalise("Chennai")
    assert phonetic.normalise("Kolkatta") == phonetic.normalise("Kolkata")


def test_varanasi_aliases():
    n = phonetic.normalise("Varanasi")
    assert phonetic.normalise("Banaras") == n
    assert phonetic.normalise("Benares") == n


def test_unknown_input_passes_through():
    assert phonetic.normalise("zzzplaceholder") == "zzzplaceholder"
    assert phonetic.normalise("") == ""
    assert phonetic.normalise(None) == ""


def test_fuzzy_ratio_pairs():
    assert phonetic.fuzzy_ratio("Gurgaon", "Gurugram") == 1.0
    assert phonetic.fuzzy_ratio("Bengaluru", "Bangalore") == 1.0
    assert phonetic.fuzzy_ratio("foo", "bar") < 0.6
    assert phonetic.fuzzy_ratio("", "Bangalore") == 0.0


def test_fuzzy_ratio_difflib_fallback(monkeypatch):
    monkeypatch.setattr(phonetic, "_HAS_RAPIDFUZZ", False)
    monkeypatch.setattr(phonetic, "_rf_fuzz", None)
    # Identical canonical still returns 1.0.
    assert phonetic.fuzzy_ratio("Mumbai", "Bombay") == 1.0
    # Plain ascii similarity still works through difflib.
    assert phonetic.fuzzy_ratio("kolkatta", "kolkata") > 0.8


def test_best_match_above_cutoff():
    candidates = ["Bangalore", "Mumbai", "Delhi"]
    result = phonetic.best_match("Bengaluru", candidates, cutoff=0.85)
    assert result is not None
    assert result[0] == "Bangalore"
    assert result[1] >= 0.85


def test_best_match_below_cutoff_returns_none():
    assert phonetic.best_match("zzzz", ["Bangalore", "Mumbai"], cutoff=0.85) is None
