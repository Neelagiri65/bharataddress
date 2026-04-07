"""Test suite for bharataddress v0.1.

30+ real Indian addresses across metro, tier 2/3, rural, S/O, landmark-heavy,
and missing-pincode cases. Acceptance bar: ≥80% pass.
"""
from __future__ import annotations

import socket

import pytest

from bharataddress import parse

# (label, raw, expected partial dict — only fields we assert on)
CASES: list[tuple[str, str, dict]] = [
    (
        "blueprint_demo",
        "Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001",
        {"building_number": "302", "pincode": "122001", "state": "Haryana"},
    ),
    (
        "mumbai_fort",
        "12, Dalal Street, Fort, Mumbai 400001",
        {"pincode": "400001", "city": "Mumbai", "state": "Maharashtra"},
    ),
    (
        "delhi_cp",
        "A-15, Connaught Place, New Delhi 110001",
        {"pincode": "110001", "state": "Delhi"},
    ),
    (
        "bangalore_mg",
        "#42, Brigade Road, Bangalore 560001",
        {"pincode": "560001", "city": "Bangalore", "state": "Karnataka"},
    ),
    (
        "chennai_anna",
        "23, Anna Salai, Chennai 600001",
        {"pincode": "600001", "state": "Tamil Nadu"},
    ),
    (
        "kolkata_park",
        "7, Park Street, Kolkata 700001",
        {"pincode": "700001", "state": "West Bengal"},
    ),
    (
        "hyderabad_basheer",
        "Plot 88, Basheer Bagh, Hyderabad 500001",
        {"pincode": "500001", "state": "Telangana"},
    ),
    (
        "lucknow_hazratganj",
        "House No. 19, Hazratganj, Lucknow 226001",
        {"pincode": "226001", "state": "Uttar Pradesh", "building_number": "19"},
    ),
    (
        "gurgaon_dlf",
        "Tower B, Flat 1204, DLF Phase 2, Gurgaon 122001",
        {"pincode": "122001", "state": "Haryana"},
    ),
    (
        "noida_sector",
        "C-101, Sector 18, Noida 201301",
        {"pincode": "201301", "state": "Uttar Pradesh"},
    ),
    (
        "rohini",
        "House Number 245, Pocket B, Sector 7, Rohini, New Delhi 110085",
        {"pincode": "110085", "state": "Delhi", "building_number": "245"},
    ),
    (
        "surat_athwa",
        "B-204, Sai Apartments, Athwa Lines, Surat 395007",
        {"pincode": "395007", "state": "Gujarat"},
    ),
    (
        "pune_kothrud",
        "Flat 7, Shivaji Heights, Opp. SBI Bank, Kothrud, Pune 411038",
        {"pincode": "411038", "state": "Maharashtra"},
    ),
    (
        "ahmedabad_satellite",
        "12, Sun Society, Near Mansi Circle, Satellite, Ahmedabad 380015",
        {"pincode": "380015", "state": "Gujarat"},
    ),
    (
        "jaipur_cscheme",
        "B-15, Bhagwan Das Road, C-Scheme, Jaipur 302001",
        {"pincode": "302001", "state": "Rajasthan"},
    ),
    (
        "kochi_mg",
        "Door No. 34/1245, MG Road, Ernakulam, Kochi 682016",
        {"pincode": "682016", "state": "Kerala"},
    ),
    (
        "indore_vijay",
        "201, Vijay Nagar, Indore 452001",
        {"pincode": "452001", "state": "Madhya Pradesh"},
    ),
    (
        "patna_boring",
        "Flat 3B, Boring Road, Patna 800001",
        {"pincode": "800001", "state": "Bihar"},
    ),
    (
        "bhopal_arera",
        "E-7/204, Arera Colony, Bhopal 462016",
        {"pincode": "462016", "state": "Madhya Pradesh"},
    ),
    (
        "ranchi_kanke",
        "Flat 102, Kanke Road, Ranchi 834008",
        {"pincode": "834008", "state": "Jharkhand"},
    ),
    # Landmark-heavy
    (
        "landmark_heavy",
        "Behind Reliance Fresh, Opposite Gupta Sweets, Near Metro Station, Andheri East, Mumbai 400069",
        {"pincode": "400069", "state": "Maharashtra"},
    ),
    # S/O format
    (
        "rural_so",
        "S/O Ramesh Kumar, Village Ramapur, Post Jhanjharpur, Madhubani, Bihar 847404",
        {"pincode": "847404", "state": "Bihar"},
    ),
    (
        "rural_village",
        "Village Khairapur, PO Khairapur, Tehsil Sadar, Aligarh, Uttar Pradesh 202001",
        {"pincode": "202001", "state": "Uttar Pradesh"},
    ),
    # Vernacular variants
    (
        "vernacular_ngr",
        "55, Lajpat Ngr, New Delhi 110024",
        {"pincode": "110024", "state": "Delhi"},
    ),
    (
        "vernacular_chowk",
        "Shop 12, Chandni Chawk, Delhi 110006",
        {"pincode": "110006", "state": "Delhi"},
    ),
    # Mixed-case, irregular punctuation
    (
        "messy_punctuation",
        "h.no.45/2 ; phase-2 ; sector 14 ; gurgaon - 122001",
        {"pincode": "122001", "state": "Haryana"},
    ),
    # Missing pincode — must still parse what it can
    (
        "no_pincode",
        "Flat 10, Sunshine Apartments, Koramangala 4th Block, Bangalore",
        {"pincode": None},
    ),
    (
        "no_pincode_2",
        "Near City Hospital, Civil Lines, Allahabad",
        {"pincode": None},
    ),
    # Building only
    (
        "building_only",
        "House Number 12, Gandhi Road, Trichy 620008",
        {"pincode": "620008", "building_number": "12", "state": "Tamil Nadu"},
    ),
    # Sector + city only
    (
        "sector_only",
        "Sector 18, Noida 201301",
        {"pincode": "201301", "state": "Uttar Pradesh"},
    ),
    # Long urban
    (
        "long_urban",
        "Flat 1502, Tower 4, Prestige Shantiniketan, Whitefield Main Road, ITPL, Bangalore 560048",
        {"pincode": "560048", "state": "Karnataka"},
    ),
    # Hinglish + landmark
    (
        "hinglish_landmark",
        "302, Sai Krupa Bldg, Opp Gurudwara, Mulund West, Mumbai 400080",
        {"pincode": "400080", "state": "Maharashtra"},
    ),
]


def _matches(actual_dict: dict, expected: dict) -> tuple[bool, list[str]]:
    failures: list[str] = []
    for key, want in expected.items():
        got = actual_dict.get(key)
        if want is None:
            if got is not None:
                failures.append(f"{key}: expected None, got {got!r}")
            continue
        if got is None or str(want).lower() not in str(got).lower():
            failures.append(f"{key}: expected ~{want!r}, got {got!r}")
    return (not failures, failures)


@pytest.mark.parametrize("label,raw,expected", CASES, ids=[c[0] for c in CASES])
def test_parse_components(label: str, raw: str, expected: dict) -> None:
    result = parse(raw).to_dict()
    ok, failures = _matches(result, expected)
    assert ok, f"[{label}] failed: {failures} | parsed={result}"


def test_blueprint_demo_full() -> None:
    """The headline example from the README must produce a high-confidence parse."""
    r = parse("Flat 302, Raheja Atlantis, Near Hanuman Mandir, Sector 31, Gurgaon 122001")
    assert r.pincode == "122001"
    assert r.state == "Haryana"
    assert r.building_number == "302"
    assert r.landmark and "hanuman" in r.landmark.lower()
    assert r.locality and "sector" in r.locality.lower()
    assert r.confidence > 0.7, f"confidence too low: {r.confidence}"


def test_pincode_lookup_size() -> None:
    from bharataddress import pincode

    assert pincode.size() > 19_000


def test_no_network_during_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    """Architectural constraint: parse() must not open a socket."""

    def boom(*args, **kwargs):
        raise AssertionError("parse() opened a socket — network calls are forbidden")

    monkeypatch.setattr(socket, "socket", boom)
    parse("Flat 302, Raheja Atlantis, Sector 31, Gurgaon 122001")


def test_empty_input() -> None:
    r = parse("")
    assert r.pincode is None
    assert r.confidence == 0.0


def test_to_dict_serialisable() -> None:
    import json as _json

    r = parse("12, MG Road, Bangalore 560001")
    _json.dumps(r.to_dict())  # must not raise
