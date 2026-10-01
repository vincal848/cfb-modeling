"""Audit/forecast contract database (SQLite prototype from the blueprint).

schema.sql is copied verbatim from docs/blueprint/schema.sql. Large raw, play, and
sample data lives in Parquet; this database holds keys, provenance, and immutable
forecast/decision/evaluation records.
"""

from __future__ import annotations

import sqlite3
from importlib.resources import files
from pathlib import Path


def schema_sql() -> str:
    return files("cfb.db").joinpath("schema.sql").read_text(encoding="utf-8")


def connect(path: Path | str = ":memory:", *, initialize: bool = True) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.execute("PRAGMA foreign_keys = ON")
    if initialize:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='raw_requests'"
        ).fetchone()
        if not exists:
            conn.executescript(schema_sql())
    return conn
