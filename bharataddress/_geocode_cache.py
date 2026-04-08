"""SQLite cache for online geocoding lookups.

Lazy: the cache file is not created until ``put`` is called for the first
time. Honours ``XDG_CACHE_HOME``; defaults to ``~/.cache/bharataddress/``.

Negative results (lookup returned no coordinates) are cached for
``_NEGATIVE_TTL_SECONDS`` so we don't hammer Nominatim for queries that
will never resolve.

Single-writer / single-process. Not safe for concurrent writers.
"""
from __future__ import annotations

import os
import sqlite3
import time
from pathlib import Path

_NEGATIVE_TTL_SECONDS = 30 * 24 * 60 * 60  # 30 days

_SCHEMA = """
CREATE TABLE IF NOT EXISTS geocode (
    query  TEXT PRIMARY KEY,
    lat    REAL,
    lng    REAL,
    source TEXT,
    ts     INTEGER NOT NULL
)
"""


def default_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache")
    return Path(base) / "bharataddress" / "geocode.sqlite"


def _connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.execute(_SCHEMA)
    return conn


def get(query: str, *, path: Path | None = None) -> tuple[float, float] | None | str:
    """Return ``(lat, lng)`` if cached positive, ``"miss"`` if not cached or
    expired, ``None`` if cached negative and still valid.
    """
    p = path or default_path()
    if not p.exists():
        return "miss"
    conn = _connect(p)
    try:
        row = conn.execute(
            "SELECT lat, lng, ts FROM geocode WHERE query = ?", (query,)
        ).fetchone()
    finally:
        conn.close()
    if row is None:
        return "miss"
    lat, lng, ts = row
    if lat is None or lng is None:
        if int(time.time()) - int(ts) > _NEGATIVE_TTL_SECONDS:
            return "miss"
        return None
    return (float(lat), float(lng))


def put(
    query: str,
    lat: float | None,
    lng: float | None,
    source: str,
    *,
    path: Path | None = None,
) -> None:
    p = path or default_path()
    conn = _connect(p)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO geocode(query, lat, lng, source, ts) VALUES (?, ?, ?, ?, ?)",
            (query, lat, lng, source, int(time.time())),
        )
        conn.commit()
    finally:
        conn.close()
