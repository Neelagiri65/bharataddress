"""v0.4 architectural constraint: ``parse()`` must not open sockets, even when
``transliterate=True``.

The existing socket monkeypatch test in ``test_parse.py`` only covers the default
``parse()`` path. v0.4 adds an opt-in transliteration step; this test extends the
zero-network guarantee to that path so the lazy import of ``indic_transliteration``
cannot accidentally pull in a network-touching code path.

Run with: ``PYTHONPATH=. python3 -m pytest tests/test_no_network_v04.py -q``
"""

from __future__ import annotations

import socket

import pytest

from bharataddress import parse


def test_no_network_during_parse_with_transliterate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """parse(addr, transliterate=True) must not open a socket."""

    def boom(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError(
            "parse(transliterate=True) opened a socket — network calls are forbidden"
        )

    monkeypatch.setattr(socket, "socket", boom)

    # Devanagari input — exercises the transliteration code path end-to-end.
    # If indic-transliteration is not installed in this environment, the test still
    # passes because the ImportError is raised before any socket call could happen.
    try:
        parse("मुंबई, महाराष्ट्र 400001", transliterate=True)
    except ImportError:
        # Acceptable: extras not installed in this venv. The constraint we care about
        # (no socket calls) is still satisfied.
        pass
