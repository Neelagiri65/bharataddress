"""v0.4 architectural constraint: the core install must work without ``indic-transliteration``.

These tests lock the promise that ``pip install bharataddress`` (no extras) gives a
fully-functional parser for Latin-script input, and that requesting transliteration
without the extras installed fails with a clear, actionable error message.

Run with: ``PYTHONPATH=. python3 -m pytest tests/test_no_indic_dep.py -q``
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _run_in_subprocess(code: str) -> subprocess.CompletedProcess[str]:
    """Run a Python snippet in a fresh subprocess with indic_transliteration blocked.

    We use a subprocess (rather than monkeypatching ``sys.modules`` in-process) so the
    test result is independent of whether the dev machine happens to have
    indic-transliteration installed. The block is enforced via a sitecustomize.py-style
    import hook injected through ``-c``.
    """
    # MetaPathFinder that pretends indic_transliteration is not installed.
    block = (
        "import sys\n"
        "class _Block:\n"
        "    def find_spec(self, name, path=None, target=None):\n"
        "        if name == 'indic_transliteration' or name.startswith('indic_transliteration.'):\n"
        "            raise ModuleNotFoundError(name)\n"
        "        return None\n"
        "sys.meta_path.insert(0, _Block())\n"
    )
    return subprocess.run(
        [sys.executable, "-c", block + code],
        cwd=REPO_ROOT,
        env={"PYTHONPATH": str(REPO_ROOT), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
        timeout=30,
    )


def test_core_import_without_indic_transliteration() -> None:
    """``from bharataddress import parse`` must succeed with indic-transliteration absent."""
    result = _run_in_subprocess(
        "from bharataddress import parse\n"
        "r = parse('Flat 302, MG Road, Bangalore 560001')\n"
        "assert r.pincode == '560001', f'expected 560001, got {r.pincode!r}'\n"
        "assert r.state == 'Karnataka', f'expected Karnataka, got {r.state!r}'\n"
        "print('OK')\n"
    )
    assert result.returncode == 0, (
        f"core import/parse failed without indic-transliteration:\n"
        f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
    assert "OK" in result.stdout


def test_transliterate_kwarg_raises_clear_importerror_when_dep_missing() -> None:
    """``parse(addr, transliterate=True)`` must raise ImportError with the install hint."""
    result = _run_in_subprocess(
        "from bharataddress import parse\n"
        "try:\n"
        "    parse('मुंबई 400001', transliterate=True)\n"
        "except ImportError as e:\n"
        "    msg = str(e)\n"
        "    assert 'bharataddress[indic]' in msg, f'missing install hint: {msg!r}'\n"
        "    print('OK')\n"
        "else:\n"
        "    raise AssertionError('expected ImportError')\n"
    )
    assert result.returncode == 0, (
        f"transliterate=True did not raise the expected ImportError:\n"
        f"STDOUT: {result.stdout}\nSTDERR: {result.stderr}"
    )
    assert "OK" in result.stdout
