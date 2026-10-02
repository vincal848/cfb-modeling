"""D07: cutoff snapshots over versioned source_records.

A snapshot holds, for each entity, the latest version available at or before the
cutoff. Strict mode admits only prospective or archived-publication evidence;
reconstructed mode also admits reconstructed availability. `unknown` evidence and
records without `available_at` never enter either mode. The SQLite triggers enforce
the strict rule and sealing independently of this code.

Snapshots are deterministic: the ID and manifest hash depend only on the cutoff, mode
and admitted record versions, so rebuilding returns the same sealed snapshot.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from cfb.canonical.games import iso

ADMITTED_EVIDENCE = {
    "strict": ("prospective_observation", "archived_publication"),
    "reconstructed": ("prospective_observation", "archived_publication", "reconstructed"),
}


@dataclass(frozen=True)
class Snapshot:
    snapshot_id: str
    cutoff: str
    mode: str
    manifest_hash: str
    record_version_ids: tuple[str, ...]


def admitted_versions(conn: sqlite3.Connection, cutoff: str, mode: str) -> list[str]:
    evidence = ADMITTED_EVIDENCE[mode]
    marks = ",".join("?" * len(evidence))
    rows = conn.execute(
        f"""WITH eligible AS (
                SELECT record_version_id, entity_type, entity_key, available_at, ingested_at
                FROM source_records
                WHERE available_at IS NOT NULL AND julianday(available_at) <= julianday(?)
                  AND availability_evidence IN ({marks})
            ), ranked AS (
                SELECT record_version_id, row_number() OVER (
                    PARTITION BY entity_type, entity_key
                    ORDER BY julianday(available_at) DESC, julianday(ingested_at) DESC,
                             record_version_id DESC) AS rn
                FROM eligible
            )
            SELECT record_version_id FROM ranked WHERE rn = 1 ORDER BY record_version_id""",
        (cutoff, *evidence),
    ).fetchall()
    return [r[0] for r in rows]


def build_snapshot(
    conn: sqlite3.Connection, cutoff: datetime, mode: str, manifest_dir: Path
) -> Snapshot:
    if mode not in ADMITTED_EVIDENCE:
        raise ValueError(f"unknown replay mode {mode!r}")
    cutoff_s = iso(cutoff)
    members = admitted_versions(conn, cutoff_s, mode)
    manifest_hash = hashlib.sha256("\n".join(members).encode()).hexdigest()
    snapshot_id = "snap-" + hashlib.sha256(f"{mode}|{cutoff_s}|{manifest_hash}".encode()).hexdigest()[:24]
    snap = Snapshot(snapshot_id, cutoff_s, mode, manifest_hash, tuple(members))

    existing = conn.execute(
        "SELECT status, manifest_hash FROM feature_snapshots WHERE snapshot_id=?", (snapshot_id,)
    ).fetchone()
    if existing is not None:
        if existing != ("sealed", manifest_hash):
            raise RuntimeError(f"{snapshot_id} exists but is not the sealed snapshot it should be")
        return snap

    future, unknown = conn.execute(
        """SELECT sum(available_at IS NOT NULL AND julianday(available_at) > julianday(?)),
                  sum(available_at IS NULL OR availability_evidence = 'unknown')
           FROM source_records""",
        (cutoff_s,),
    ).fetchone()
    by_type = dict(conn.execute(
        """SELECT entity_type, count(*) FROM source_records
            WHERE record_version_id IN (SELECT value FROM json_each(?)) GROUP BY entity_type""",
        (json.dumps(members),),
    ).fetchall())
    coverage = {"admitted_by_entity_type": by_type, "excluded_future_versions": future or 0,
                "excluded_unknown_availability": unknown or 0}

    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"{snapshot_id}.json"
    manifest_path.write_text(json.dumps({
        "snapshot_id": snapshot_id, "information_cutoff": cutoff_s, "replay_mode": mode,
        "manifest_hash": manifest_hash, "record_version_ids": members, "coverage": coverage,
    }, indent=1), encoding="utf-8")

    with conn:
        conn.execute(
            "INSERT INTO feature_snapshots VALUES (?,?,?,'draft',?,?,?)",
            (snapshot_id, cutoff_s, mode, manifest_path.name, manifest_hash, json.dumps(coverage)),
        )
        conn.executemany("INSERT INTO snapshot_members VALUES (?,?)", [(snapshot_id, m) for m in members])
        conn.execute("UPDATE feature_snapshots SET status='sealed' WHERE snapshot_id=?", (snapshot_id,))
    return snap


def fact_as_of(
    conn: sqlite3.Connection, entity_type: str, entity_key: str, cutoff: datetime, mode: str
) -> dict | None:
    """The version of one fact a forecast at `cutoff` may use, under the same admission rule
    as snapshots. For a forecast's own target game, whose cutoff can be later than the
    fold snapshot's (a postseason fold spans weeks)."""
    found = version_as_of(conn, entity_type, entity_key, cutoff, mode)
    return found[1] if found else None


def version_as_of(
    conn: sqlite3.Connection, entity_type: str, entity_key: str, cutoff: datetime, mode: str
) -> tuple[str, dict] | None:
    """(record_version_id, payload) of the fact `fact_as_of` returns."""
    evidence = ADMITTED_EVIDENCE[mode]
    marks = ",".join("?" * len(evidence))
    row = conn.execute(
        f"""SELECT record_version_id, normalized_payload_json FROM source_records
            WHERE entity_type=? AND entity_key=? AND available_at IS NOT NULL
              AND julianday(available_at) <= julianday(?) AND availability_evidence IN ({marks})
            ORDER BY julianday(available_at) DESC, julianday(ingested_at) DESC, record_version_id DESC
            LIMIT 1""",
        (entity_type, entity_key, iso(cutoff), *evidence),
    ).fetchone()
    return (row[0], json.loads(row[1])) if row else None


def load_facts(conn: sqlite3.Connection, snapshot_id: str, entity_type: str) -> list[dict]:
    """Normalized payloads of one entity type in a sealed snapshot."""
    status = conn.execute("SELECT status FROM feature_snapshots WHERE snapshot_id=?", (snapshot_id,)).fetchone()
    if status is None or status[0] != "sealed":
        raise RuntimeError(f"{snapshot_id} is not a sealed snapshot")
    rows = conn.execute(
        """SELECT r.normalized_payload_json FROM snapshot_members m
           JOIN source_records r USING(record_version_id)
           WHERE m.snapshot_id=? AND r.entity_type=?""",
        (snapshot_id, entity_type),
    ).fetchall()
    return [json.loads(r[0]) for r in rows]
