"""B03 immutable records and replay, end to end on SYNTHETIC CFBD-shaped data (fabricated)."""

import json
import sqlite3

import numpy as np
import pytest

from cfb.canonical.games import canonicalize_games
from cfb.decisions.winner import winner_v1
from cfb.evaluation.backtest import Config, prepare_tasks
from cfb.evaluation.protocol import load_protocol
from cfb.ingestion.client import ApiResponse
from cfb.ingestion.ledger import RawLedger
from cfb.operations.records import record_runs, replay_check

TEAMS = list(range(1, 11))


def season_games(season, weeks, rng, first_id):
    games, gid = [], first_id
    for w in weeks:
        perm = rng.permutation(TEAMS)
        for h, a in perm.reshape(-1, 2):
            hp, ap = (int(x) for x in rng.integers(0, 50, 2))
            ap = ap + 1 if ap == hp else ap
            games.append({"id": gid, "season": season, "week": w, "seasonType": "regular",
                          "startDate": f"{season}-09-{w * 7:02d}T16:00:00.000Z", "startTimeTBD": False,
                          "neutralSite": False, "conferenceGame": True, "completed": True,
                          "homeId": int(h), "homeTeam": f"T{h}", "homeClassification": "fbs",
                          "awayId": int(a), "awayTeam": f"T{a}", "awayClassification": "fbs",
                          "homePoints": hp, "awayPoints": ap})
            gid += 1
    return games


@pytest.fixture
def recorded(db, tmp_path):
    ledger = RawLedger(tmp_path / "raw", db, provider="SYNTHETIC")
    rng = np.random.default_rng(5)
    for n, (path, params, body) in enumerate([
        ("/calendar", {"year": 2018}, [{"week": 1, "seasonType": "regular", "startDate": "2018-09-01T07:00:00.000Z"}]),
        ("/calendar", {"year": 2019}, [{"week": 1, "seasonType": "regular", "startDate": "2019-09-01T07:00:00.000Z"}]),
        ("/teams/fbs", {"year": 2018}, [{"id": t, "school": f"T{t}"} for t in TEAMS]),
        ("/teams/fbs", {"year": 2019}, [{"id": t, "school": f"T{t}"} for t in TEAMS]),
        ("/games", {"year": 2018, "seasonType": "regular"}, season_games(2018, [1, 2, 3, 4], rng, 100)),
        ("/games", {"year": 2019, "seasonType": "regular"}, season_games(2019, [1], rng, 500)),
    ]):
        ledger.record(path, params, ApiResponse(200, json.dumps(body).encode(),
                                                f"2026-10-01T00:00:{n:02d}.000000Z", None, 1), None)
    canonicalize_games(db, ledger, 6, log=lambda s: None)
    protocol = load_protocol()
    configs = [Config("ridge", (("penalty", 1.0),)), Config("hfa_only", ())]
    tasks = prepare_tasks(db, protocol, [2019], configs, tmp_path / "snapshots", draws=4000, log=lambda s: None)
    kw = {"stage": "B01", "dep_lock": "lock-abc", "artifact_dir": tmp_path / "art",
          "evaluation_class": "reconstructed", "workers": 1}
    summary = record_runs(db, tasks, configs, **kw)
    return db, tasks, configs, kw, summary, protocol, tmp_path


def test_one_forecast_per_run_game_and_reruns_add_nothing(recorded):
    db, tasks, configs, kw, summary, *_ = recorded
    assert summary == {"runs_requested": 2, "already_recorded": 0, "inserted": 2}
    counts = [db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for t in ("model_runs", "forecast_summaries", "decision_records", "evaluation_results")]
    assert counts == [2, 10, 10, 10]  # 5 games x 2 models
    assert db.execute("SELECT count(*) FROM outcome_versions").fetchone()[0] == 5
    again = record_runs(db, tasks, configs, **kw)
    assert again == {"runs_requested": 2, "already_recorded": 2, "inserted": 0}
    assert db.execute("SELECT count(*) FROM forecast_summaries").fetchone()[0] == 10


def test_forecasts_are_reconstructed_coherent_and_picks_follow_policy(recorded):
    db, *_ = recorded
    rows = db.execute("""SELECT f.evaluation_class, f.home_win_probability, f.away_win_probability,
                                f.actual_lead_minutes, g.home_team_id, g.away_team_id, d.forced_choice
                         FROM forecast_summaries f JOIN games g USING(game_id)
                         JOIN decision_records d USING(forecast_id)""").fetchall()
    for cls, ph, pa, lead, home, away, choice in rows:
        assert cls == "reconstructed" and ph + pa == pytest.approx(1.0) and lead >= 1440
        assert choice == winner_v1(ph, home, away)


def test_replay_reproduces_samples_and_pick(recorded):
    db, *_, protocol, tmp_path = recorded
    for (fid, model_version) in db.execute(
            "SELECT forecast_id, model_version FROM forecast_summaries JOIN model_runs USING(run_id)"):
        model = model_version.split(":")[1].split("|")[0]
        assert replay_check(db, tmp_path / "art", fid, protocol["monte_carlo"]["root_seed"],
                            protocol["protocol_version"], model, 4000)


def test_records_cannot_be_edited_or_contradicted(recorded):
    db, *_ = recorded
    fid, home, away, p = db.execute(
        """SELECT f.forecast_id, g.home_team_id, g.away_team_id, f.home_win_probability
           FROM forecast_summaries f JOIN games g USING(game_id) LIMIT 1""").fetchone()
    with pytest.raises(sqlite3.DatabaseError, match="immutable"):
        db.execute("UPDATE forecast_summaries SET home_win_probability=0.5 WHERE forecast_id=?", (fid,))
    with pytest.raises(sqlite3.DatabaseError, match="immutable"):
        db.execute("DELETE FROM decision_records")
    wrong = away if winner_v1(p, home, away) == home else home
    with pytest.raises(sqlite3.DatabaseError, match="contradicts"):
        db.execute("INSERT INTO decision_records VALUES ('x', ?, 'winner_v1', 'winner', ?, 'PASS', "
                   "NULL, NULL, '[]', 'h', 'h')", (fid, wrong))
