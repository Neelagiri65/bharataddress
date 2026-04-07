from bharataddress import is_deliverable, parse, validate
from bharataddress.parser import ParsedAddress


def test_deliverable_when_pincode_city_state_present():
    p = parse("Flat 302, Sector 31, Gurgaon 122001")
    assert is_deliverable(p) is True


def test_not_deliverable_when_pincode_missing():
    p = ParsedAddress(raw="x", cleaned="x", city="Mumbai", state="Maharashtra")
    assert is_deliverable(p) is False


def test_validate_returns_field_confidences():
    p = parse("Flat 302, Sector 31, Gurgaon 122001")
    r = validate(p)
    assert "fields" in r
    assert r["fields"]["pincode"] == 1.0
    assert r["is_deliverable"] is True
    assert r["overall"] > 0.5
    assert r["issues"] == []


def test_validate_flags_state_mismatch():
    p = parse("Flat 302, Sector 31, Gurgaon 122001")
    p.state = "Karnataka"
    r = validate(p)
    assert any("state mismatch" in i for i in r["issues"])
    assert r["fields"]["state"] < 1.0


def test_validate_unknown_pincode():
    p = ParsedAddress(raw="x", cleaned="x", pincode="000000")
    r = validate(p)
    assert any("not in India Post" in i for i in r["issues"])
    assert r["fields"]["pincode"] < 1.0
