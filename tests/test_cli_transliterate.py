"""v0.4 issue #7: CLI --transliterate flag.

Locks the CLI surface for native-script parsing:
* ``bharataddress parse "<ascii>"`` is unchanged.
* ``bharataddress parse --transliterate "<native>"`` parses native-script
  input by routing it through the transliteration shim.
* The flag is documented in --help.
* Without the optional extras installed, the flag fails with a clear
  error message that mentions ``bharataddress[indic]``.
"""
from __future__ import annotations

import json

import pytest

from bharataddress.cli import main


def test_help_mentions_transliterate(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["parse", "--help"])
    out = capsys.readouterr().out
    assert "--transliterate" in out
    assert "bharataddress[indic]" in out


def test_ascii_parse_unchanged(capsys: pytest.CaptureFixture[str]) -> None:
    rc = main(["parse", "Flat 302, MG Road, Bangalore 560001"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pincode"] == "560001"
    assert payload["state"] == "Karnataka"


def test_transliterate_flag_on_native_script(
    capsys: pytest.CaptureFixture[str],
) -> None:
    pytest.importorskip("indic_transliteration")
    rc = main(["parse", "--transliterate", "मुंबई, महाराष्ट्र 400001"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["pincode"] == "400001"
    assert payload["state"] == "Maharashtra"


def test_transliterate_flag_on_ascii_is_noop(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Passing --transliterate on ASCII input must produce the same JSON
    as the default path. Confirms the flag is free when not needed."""
    pytest.importorskip("indic_transliteration")
    rc1 = main(["parse", "Flat 302, MG Road, Bangalore 560001"])
    out1 = capsys.readouterr().out
    rc2 = main(["parse", "--transliterate", "Flat 302, MG Road, Bangalore 560001"])
    out2 = capsys.readouterr().out
    assert rc1 == rc2 == 0
    assert json.loads(out1) == json.loads(out2)
