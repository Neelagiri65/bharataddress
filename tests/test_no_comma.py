"""Regression tests for no-comma input handling.

Before v0.2.1 the segmenter only split on commas, so addresses written as a
single space-separated line lost everything except pincode-derived fields.
"""
from bharataddress import parse


def test_alphanum_lead_defence_colony():
    p = parse("A-15 Defence Colony New Delhi 110024")
    assert p.building_number == "A-15"
    assert p.locality == "Defence Colony"
    assert p.pincode == "110024"
    assert p.state == "Delhi"


def test_house_number_sarat_bose_road():
    p = parse("H No 12 Sarat Bose Road Kolkata 700020")
    assert p.building_number == "12"
    assert p.locality and "Sarat Bose Road" in p.locality
    assert p.city == "Kolkata"
    assert p.pincode == "700020"


def test_no_comma_does_not_break_existing_comma_inputs():
    # Comma-based inputs must still parse exactly as before.
    p = parse("Flat 302, Raheja Atlantis, Sector 31, Gurgaon 122001")
    assert p.building_number == "302"
    assert p.pincode == "122001"
