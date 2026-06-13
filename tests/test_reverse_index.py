"""Tests for the city -> (district, state) reverse-index and the parser
behaviour it backs.

The index is inverted from the shipped India Post directory (no new data file,
no network). It powers two things:

  1. State recovery on addresses that carry no pincode.
  2. (Indirectly) confidence that a resolved city is a real town.

These tests also lock the ``_is_dup`` fix: a locality that merely *contains*
the city name as a substring (``Navi Mumbai`` when the city is ``Mumbai``,
``Thane West`` when the city is ``Thane``) must not be silently dropped.

Run with: ``PYTHONPATH=. python3 -m pytest tests/test_reverse_index.py -q``
"""
from __future__ import annotations

from bharataddress import parse
from bharataddress import pincode


def test_city_to_admin_resolves_known_city() -> None:
    admin = pincode.city_to_admin("Hyderabad")
    assert admin is not None
    _district, state = admin
    assert state == "Telangana"


def test_city_to_admin_is_case_insensitive() -> None:
    assert pincode.city_to_admin("hyderabad") == pincode.city_to_admin("Hyderabad")


def test_city_to_admin_unknown_returns_none() -> None:
    assert pincode.city_to_admin("Notacityxyz") is None
    assert pincode.city_to_admin("") is None
    assert pincode.city_to_admin(None) is None


def test_is_known_city() -> None:
    assert pincode.is_known_city("Pune") is True
    assert pincode.is_known_city("Notacityxyz") is False
    assert pincode.is_known_city(None) is False


def test_index_is_substantially_larger_than_hardcoded_set() -> None:
    # The whole point of the reverse-index: thousands of real towns rather
    # than the ~95 hand-picked metros in the parser's _KNOWN_CITIES frozenset.
    assert len(pincode._city_index()) > 1000


def test_state_recovered_without_pincode() -> None:
    # No pincode in the string; state must be recovered from the city name.
    out = parse("MG Road, Pune")
    assert out.pincode is None
    assert out.state == "Maharashtra"


def test_state_recovery_is_additive_only() -> None:
    # When a pincode is present, the pincode lookup wins; recovery never
    # overrides it.
    out = parse("Gachibowli, Hyderabad 500032")
    assert out.pincode == "500032"
    assert out.state == "Telangana"


def test_stray_state_abbrev_does_not_seed_wrong_state() -> None:
    # A trailing token that is not a real town must not trigger a fill.
    out = parse("Some Locality, XX")
    # 'XX' is not a known city, so no bogus state is invented.
    assert out.state in (None, "")  # nothing fabricated


def test_locality_containing_city_name_not_dropped() -> None:
    # Regression: the old bidirectional substring match dropped any locality
    # that merely contained the resolved city as a substring. "Thane West" was
    # dropped because the city resolved to "Thane" ("thane" in "thane west").
    out = parse("Flat 5, Thane West, Maharashtra 400601")
    assert out.city == "Thane"
    found = " ".join(
        str(v).lower() for v in (out.locality, out.sub_locality) if v
    )
    assert "thane west" in found
