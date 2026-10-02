"""D05 canonical games and D07 snapshots on SYNTHETIC CFBD-shaped records (fabricated)."""

import json
import sqlite3
from datetime import UTC, datetime

import pytest

from cfb.canonical.games import canonicalize_games, game_id, team_id
from cfb.ingestion.client import ApiResponse
from cfb.ingestion.ledger import RawLedger
from cfb.snapshots.builder import build_snapshot, load_facts

LAG = 6


def raw_game(gid, home, away, start, hp=None, ap=None, completed=True, **kw):
    return {"id": gid, "season": 2019, "week": 1, "seasonType": "regular", "startDate": start,
            "startTimeTBD": False, "neutralSite": False, "conferenceGame": False,
            "homeId": home, "homeTeam": f"T{home}", "homeClassification": "fbs",
            "awayId": away, "awayTeam": f"T{away}", "awayClassification": "fbs",
            "homePoints": hp, "awayPoints": ap, "completed": completed,
            "homeLineScores": None, "awayLineScores": None, "homePostgameElo": 1500, **kw}


class Store:
    def __init__(self, db, tmp_path):
        self.db, self.ledger, self.n = db, RawLedger(tmp_path / "raw", db, provider="SYNTHETIC"), 0

    def put(self, path, params, body):
        self.n += 1
        resp = ApiResponse(200, json.dumps(body).encode(), f"2026-10-01T00:00:{self.n:02d}.000000Z", None, 1)
        self.ledger.record(path, params, resp, None)

    def canon(self):
        return canonicalize_games(self.db, self.ledger, LAG, log=lambda s: None)


@pytest.fixture
def store(db, tmp_path):
    s = Store(db, tmp_path)
    s.put("/calendar", {"year": 2019}, [{"week": 1, "seasonType": "regular", "startDate": "2019-08-24T07:00:00.000Z"}])
    s.put("/teams/fbs", {"year": 2019}, [{"id": 1, "school": "A"}, {"id": 2, "school": "B"}])
    s.put("/games", {"year": 2019, "seasonType": "regular"}, [
        raw_game(10, 1, 2, "2019-08-31T16:00:00.000Z", 28, 21),
        raw_game(11, 2, 3, "2019-08-31T20:00:00.000Z", completed=False),  # vs FCS team 3, unplayed
        raw_game(12, 3, 4, "2019-08-31T20:00:00.000Z", 10, 7),  # no FBS team: outside population
    ])
    return s


def facts(db, etype):
    return db.execute("SELECT entity_key, normalized_payload_json, available_at FROM source_records "
                      "WHERE entity_type=? ORDER BY entity_key", (etype,)).fetchall()


def test_schedule_and_result_are_separate_facts_with_own_availability(store):
    summary = store.canon()
    sched, res = facts(store.db, "game_schedule"), facts(store.db, "game_result")
    assert [k for k, *_ in sched] == [game_id(10), game_id(11)]  # game 12 excluded
    assert [k for k, *_ in res] == [game_id(10)]  # unplayed game has no result, not 0-0
    assert sched[0][2] == "2019-08-24T16:00:00Z" and res[0][2] == "2019-08-31T22:00:00Z"
    payload = json.loads(sched[0][1])
    assert "home_points" not in payload and "homePostgameElo" not in json.loads(res[0][1])
    assert payload["home_team_id"] == team_id(1)
    assert summary["games_seen"] == 2


def test_recanonicalizing_adds_nothing_and_corrections_add_versions(store):
    store.canon()
    n = store.db.execute("SELECT count(*) FROM source_records").fetchone()[0]
    assert store.canon()["versions_added"] == 0
    # A later identical retrieval also adds nothing.
    store.put("/games", {"year": 2019, "seasonType": "regular"},
              [raw_game(10, 1, 2, "2019-08-31T16:00:00.000Z", 28, 21)])
    assert store.canon()["versions_added"] == 0
    # A score correction adds a result version and keeps the old one.
    store.put("/games", {"year": 2019, "seasonType": "regular"},
              [raw_game(10, 1, 2, "2019-08-31T16:00:00.000Z", 28, 24)])
    assert store.canon()["versions_added"] == 1
    assert store.db.execute("SELECT count(*) FROM source_records").fetchone()[0] == n + 1
    with pytest.raises(sqlite3.DatabaseError):
        store.db.execute("DELETE FROM source_records")


def cut(s):
    return datetime.fromisoformat(s).replace(tzinfo=UTC)


def test_snapshot_excludes_results_before_their_availability(store, tmp_path):
    store.canon()
    db = store.db
    pre = build_snapshot(db, cut("2019-08-30T16:00:00"), "reconstructed", tmp_path / "m")
    assert {f["game_id"] for f in load_facts(db, pre.snapshot_id, "game_schedule")} == {game_id(10), game_id(11)}
    assert load_facts(db, pre.snapshot_id, "game_result") == []
    # Kickoff plus 5 hours is still before the registered 6-hour result availability.
    assert load_facts(db, build_snapshot(db, cut("2019-08-31T21:00:00"), "reconstructed",
                                         tmp_path / "m").snapshot_id, "game_result") == []
    post = build_snapshot(db, cut("2019-08-31T22:00:00"), "reconstructed", tmp_path / "m")
    assert [f["home_points"] for f in load_facts(db, post.snapshot_id, "game_result")] == [28]


def test_strict_snapshot_admits_no_reconstructed_history(store, tmp_path):
    store.canon()
    snap = build_snapshot(store.db, cut("2026-01-01T00:00:00"), "strict", tmp_path / "m")
    assert snap.record_version_ids == ()


def test_snapshots_are_deterministic_sealed_and_use_latest_correction(store, tmp_path):
    store.canon()
    db = store.db
    before = build_snapshot(db, cut("2019-09-02T00:00:00"), "reconstructed", tmp_path / "m")
    assert build_snapshot(db, cut("2019-09-02T00:00:00"), "reconstructed", tmp_path / "m") == before
    with pytest.raises(sqlite3.DatabaseError, match="sealed"):
        db.execute("INSERT INTO snapshot_members VALUES (?, ?)",
                   (before.snapshot_id, db.execute("SELECT record_version_id FROM source_records").fetchone()[0]))

    store.put("/games", {"year": 2019, "seasonType": "regular"},
              [raw_game(10, 1, 2, "2019-08-31T16:00:00.000Z", 28, 24)])
    store.canon()
    after = build_snapshot(db, cut("2019-09-02T00:00:00"), "reconstructed", tmp_path / "m")
    assert after.snapshot_id != before.snapshot_id  # old snapshot untouched, new one differs
    assert [f["away_points"] for f in load_facts(db, after.snapshot_id, "game_result")] == [24]
    assert [f["away_points"] for f in load_facts(db, before.snapshot_id, "game_result")] == [21]


def test_fact_as_of_uses_the_forecasts_own_cutoff(store):
    from cfb.snapshots.builder import fact_as_of

    store.canon()
    gid = game_id(10)  # kickoff 2019-08-31T16:00Z; schedule available 7 days earlier
    assert fact_as_of(store.db, "game_schedule", gid, cut("2019-08-30T16:00:00"), "reconstructed")["game_id"] == gid
    assert fact_as_of(store.db, "game_schedule", gid, cut("2019-08-24T15:59:00"), "reconstructed") is None
    assert fact_as_of(store.db, "game_schedule", gid, cut("2019-08-30T16:00:00"), "strict") is None
