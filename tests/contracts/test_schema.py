"""Executable contract checks ported from docs/blueprint/verification.md (synthetic rows only)."""

import sqlite3

import pytest

T0 = "2025-09-01T00:00:00Z"
CUTOFF = "2025-09-05T00:00:00Z"


def seed(db, *, available_at="2025-09-02T00:00:00Z", evidence="prospective_observation"):
    db.executemany("INSERT INTO teams VALUES (?,?)", [("T-A", "Alpha"), ("T-B", "Bravo")])
    db.execute("INSERT INTO games VALUES ('G1', 2025, 'T-B', 'T-A')")
    db.execute(
        "INSERT INTO raw_requests VALUES ('R1','SYNTHETIC','/games','{}',?,200,1,0,'mem://r1','h')",
        (T0,),
    )
    db.execute(
        "INSERT INTO source_records VALUES ('V1','R1','game','G1',?,?,?,?,'v1','{}','h1')",
        (T0, available_at, "2025-09-03T00:00:00Z", evidence),
    )
    db.execute(
        "INSERT INTO feature_snapshots VALUES ('S1',?,'strict','draft','mem://s1','mh','{}')",
        (CUTOFF,),
    )


def seal_and_run(db):
    db.execute("INSERT INTO snapshot_members VALUES ('S1','V1')")
    db.execute("UPDATE feature_snapshots SET status='sealed' WHERE snapshot_id='S1'")
    db.execute(
        "INSERT INTO model_runs VALUES "
        "('RUN1','S1','team','m0',?,1,'lock','in','mem://a','ah','passed','{}')",
        (CUTOFF,),
    )


FORECAST_SQL = """INSERT INTO forecast_summaries VALUES
    (?, 'RUN1', 'G1', ?, ?, 'sv1', '2025-09-05T00:00:01Z', 'archived_replay', 'football_only',
     ?, ?, 28, 24, -10, 4, 18, 35, 52, 70, 'mem://s', 'sh', 20000, 0.003, '{}')"""


def forecast(db, fid="F1", p_home=0.6, p_away=None, horizon=1440):
    p_away = 1 - p_home if p_away is None else p_away
    db.execute(FORECAST_SQL, (fid, horizon, horizon, p_home, p_away))


def test_strict_snapshot_rejects_future_availability(db):
    seed(db, available_at="2025-09-03T00:00:00Z")
    db.execute("UPDATE feature_snapshots SET information_cutoff='2025-09-02T12:00:00Z'")
    with pytest.raises(sqlite3.DatabaseError, match="strict snapshot"):
        db.execute("INSERT INTO snapshot_members VALUES ('S1','V1')")


def test_strict_snapshot_rejects_unknown_availability(db):
    seed(db, available_at=None, evidence="unknown")
    with pytest.raises(sqlite3.DatabaseError, match="strict snapshot"):
        db.execute("INSERT INTO snapshot_members VALUES ('S1','V1')")


def test_source_versions_immutable(db):
    seed(db)
    with pytest.raises(sqlite3.DatabaseError, match="immutable"):
        db.execute("UPDATE source_records SET source_version='v2' WHERE record_version_id='V1'")


def test_sealed_snapshot_cannot_acquire_facts_or_move_cutoff(db):
    seed(db)
    seal_and_run(db)
    with pytest.raises(sqlite3.DatabaseError):
        db.execute("INSERT INTO snapshot_members VALUES ('S1','V1')")
    with pytest.raises(sqlite3.DatabaseError, match="sealed"):
        db.execute(
            "UPDATE feature_snapshots SET information_cutoff=? WHERE snapshot_id='S1'", (T0,)
        )


def test_training_cannot_extend_past_cutoff(db):
    seed(db)
    db.execute("INSERT INTO snapshot_members VALUES ('S1','V1')")
    db.execute("UPDATE feature_snapshots SET status='sealed' WHERE snapshot_id='S1'")
    with pytest.raises(sqlite3.DatabaseError, match="exceeds forecast cutoff"):
        db.execute(
            "INSERT INTO model_runs VALUES "
            "('RUN1','S1','team','m0','2025-09-06T00:00:00Z',1,'l','i','u','h','passed','{}')"
        )


def test_forecast_immutable(db):
    seed(db)
    seal_and_run(db)
    forecast(db)
    with pytest.raises(sqlite3.DatabaseError, match="immutable"):
        db.execute("UPDATE forecast_summaries SET home_win_probability=0.7")


def test_inconsistent_winner_probabilities_rejected(db):
    seed(db)
    seal_and_run(db)
    with pytest.raises(sqlite3.IntegrityError):
        forecast(db, p_home=0.6, p_away=0.5)


def test_exact_tie_uses_lexicographically_smaller_team_id(db):
    seed(db)  # home T-B, away T-A
    seal_and_run(db)
    forecast(db, p_home=0.5)
    (pick,) = db.execute(
        "SELECT winner_v1_forced_team_id FROM v_game_forecast WHERE forecast_id='F1'"
    ).fetchone()
    assert pick == "T-A"


def test_recorded_winner_cannot_contradict_policy(db):
    seed(db)
    seal_and_run(db)
    forecast(db, p_home=0.6)
    sql = "INSERT INTO decision_records VALUES ('D1','F1','winner_v1','winner',?,'PICK',NULL,NULL,'[]','i','d')"
    with pytest.raises(sqlite3.DatabaseError, match="contradicts"):
        db.execute(sql, ("T-A",))
    db.execute(sql, ("T-B",))
