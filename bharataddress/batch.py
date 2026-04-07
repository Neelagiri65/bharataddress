"""Batch helpers for parsing many addresses at once.

- ``parse_batch(strings)`` — list-in, list-of-``ParsedAddress``-out.
- ``parse_csv(path, column="address")`` — read a CSV, write a structured CSV
  with one column per parsed field next to the original.
- ``parse_dataframe(df, column="address")`` — pandas DataFrame in, DataFrame
  with parsed columns added. ``pandas`` is *not* a runtime dependency; the
  function imports it lazily and raises if missing.

All operations are pure-Python and offline. ``parse_csv`` writes to a path
next to the input by default.
"""
from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Iterable

from .parser import ParsedAddress, parse

_FIELDS = (
    "building_number",
    "building_name",
    "landmark",
    "sub_locality",
    "locality",
    "city",
    "district",
    "state",
    "pincode",
    "digipin",
    "confidence",
)


def parse_batch(addresses: Iterable[str]) -> list[ParsedAddress]:
    """Parse a sequence of address strings. Empty / non-string entries return an empty ``ParsedAddress``."""
    return [parse(a) if isinstance(a, str) else ParsedAddress(raw="", cleaned="") for a in addresses]


def parse_csv(
    filepath: str | Path,
    column: str = "address",
    output: str | Path | None = None,
) -> Path:
    """Parse a CSV file and write a structured CSV alongside it.

    The output file has every original column plus one ``parsed_<field>``
    column for each parsed field. Returns the output ``Path``.
    """
    in_path = Path(filepath)
    out_path = Path(output) if output else in_path.with_name(in_path.stem + "_parsed.csv")

    with in_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or column not in reader.fieldnames:
            raise ValueError(f"column {column!r} not found in {in_path}")
        rows = list(reader)
        in_fields = list(reader.fieldnames)

    parsed_fields = [f"parsed_{f}" for f in _FIELDS]
    out_fields = in_fields + parsed_fields

    with out_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=out_fields)
        writer.writeheader()
        for row in rows:
            p = parse(row.get(column) or "")
            for f in _FIELDS:
                row[f"parsed_{f}"] = getattr(p, f) if getattr(p, f) is not None else ""
            writer.writerow(row)

    return out_path


def parse_dataframe(df: Any, column: str = "address") -> Any:
    """Add ``parsed_<field>`` columns to a pandas DataFrame.

    Lazily imports pandas. Returns a *new* DataFrame; the input is not mutated.
    """
    try:
        import pandas as pd  # noqa: F401
    except ImportError as e:  # pragma: no cover - depends on user env
        raise ImportError("parse_dataframe requires pandas; install with `pip install pandas`") from e

    if column not in df.columns:
        raise ValueError(f"column {column!r} not found in DataFrame")

    out = df.copy()
    parsed = [parse(a or "") for a in out[column].tolist()]
    for f in _FIELDS:
        out[f"parsed_{f}"] = [getattr(p, f) for p in parsed]
    return out
