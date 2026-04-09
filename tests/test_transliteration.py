"""v0.4 issue #4: opt-in transliteration shim end-to-end.

These tests require ``indic-transliteration`` to be installed
(``pip install bharataddress[indic]``). They are skipped — not failed —
when the extras are missing, so a bare-core developer can still run the
suite. The "core works without the extras" contract is locked separately
in tests/test_no_indic_dep.py and is the gating test, not this one.
"""

from __future__ import annotations

import pytest

pytest.importorskip(
    "indic_transliteration",
    reason="bharataddress[indic] extras not installed; skipping script tests",
)

from bharataddress import parse  # noqa: E402
from bharataddress.preprocessor import (  # noqa: E402
    _detect_script,
    transliterate_to_latin,
)


# --- _detect_script: which script is the input? -------------------------------

def test_detect_devanagari() -> None:
    assert _detect_script("मुंबई") == ("DEVANAGARI", "hi")


def test_detect_bengali() -> None:
    assert _detect_script("কলকাতা") == ("BENGALI", "bn")


def test_detect_tamil() -> None:
    assert _detect_script("சென்னை") == ("TAMIL", "ta")


def test_detect_telugu() -> None:
    assert _detect_script("హైదరాబాద్") == ("TELUGU", "te")


def test_detect_kannada() -> None:
    assert _detect_script("ಬೆಂಗಳೂರು") == ("KANNADA", "kn")


def test_detect_malayalam() -> None:
    assert _detect_script("കൊച്ചി") == ("MALAYALAM", "ml")


def test_detect_ascii_returns_none() -> None:
    assert _detect_script("MG Road, Bangalore 560001") is None


# --- transliterate_to_latin: ASCII passthrough is a true no-op ----------------

def test_ascii_input_is_passthrough() -> None:
    text = "Flat 302, MG Road, Bangalore 560001"
    out, lang = transliterate_to_latin(text)
    assert out == text
    assert lang is None


# --- parse(transliterate=True): end-to-end on each of the 6 scripts -----------
# Each address is "<city in native script> <pincode>". The pincode is the same
# in any script (Indic digits NFKC-normalise to ASCII), so even if the
# transliterated city name doesn't match the parser's locality logic exactly,
# the pincode -> state lookup is the load-bearing assertion.

@pytest.mark.parametrize(
    ("addr", "expected_state", "expected_pin"),
    [
        ("मुंबई, महाराष्ट्र 400001", "Maharashtra", "400001"),    # Devanagari/Hindi
        ("কলকাতা, পশ্চিমবঙ্গ 700001", "West Bengal", "700001"),  # Bengali
        ("சென்னை, தமிழ்நாடு 600001", "Tamil Nadu", "600001"),    # Tamil
        ("హైదరాబాద్, తెలంగాణ 500001", "Telangana", "500001"),    # Telugu
        ("ಬೆಂಗಳೂರು, ಕರ್ನಾಟಕ 560001", "Karnataka", "560001"),    # Kannada
        ("കൊച്ചി, കേരളം 682001", "Kerala", "682001"),            # Malayalam
    ],
)
def test_parse_native_script_resolves_state_and_pincode(
    addr: str, expected_state: str, expected_pin: str
) -> None:
    r = parse(addr, transliterate=True)
    assert r.pincode == expected_pin, (
        f"pincode wrong: expected {expected_pin}, got {r.pincode!r} "
        f"(cleaned={r.cleaned!r})"
    )
    assert r.state == expected_state, (
        f"state wrong: expected {expected_state}, got {r.state!r} "
        f"(cleaned={r.cleaned!r})"
    )


def test_parse_ascii_with_transliterate_flag_is_unchanged() -> None:
    """Passing transliterate=True on ASCII input must produce the same result
    as the default path. Confirms the flag is free when not needed."""
    addr = "Flat 302, MG Road, Bangalore 560001"
    a = parse(addr)
    b = parse(addr, transliterate=True)
    assert a.to_dict() == b.to_dict()
