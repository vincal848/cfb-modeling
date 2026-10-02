"""B03: immutable model-run, forecast, decision, outcome and evaluation records.

IDs are content-derived: a run ID depends on the snapshot, model configuration, protocol
version, horizon and dependency lock. Recording the same run twice is a no-op, so there
is exactly one forecast per run, game, horizon and product. The contract schema's
triggers reject updates, deletes, unsealed snapshots and winner picks that contradict
the stored probability.

Workers fit, simulate and write each run's artifacts (fitted per-game parameters and
the paired score samples, both hashed). The main process inserts the rows, one
transaction per run.
"""

from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from cfb.decisions.winner import POLICY_VERSION, winner_v1
from cfb.evaluation.backtest import Config, FoldTask, parallel_map
from cfb.evaluation.metrics import score_game, sorted_quantile, win_probability
from cfb.models.baselines import MODELS
from cfb.models.simulate import derive_seed, sample_scores

PRODUCT = "football_only"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def lock_hash(lock_file: Path) -> str:
    """Dependency lock hash, independent of checkout line endings."""
    return sha256_bytes(lock_file.read_bytes().replace(b"\r\n", b"\n"))


def short_id(prefix: str, *parts: Any) -> str:
    return f"{prefix}-" + sha256_bytes("|".join(str(p) for p in parts).encode())[:24]


def run_id_for(task: FoldTask, cfg: Config, dep_lock: str) -> str:
    return short_id("run", task.snapshot_id, cfg.label, task.protocol_version, task.horizon,
                    task.root_seed, task.draws, dep_lock)


def samples_digest(samples: np.ndarray) -> str:
    return sha256_bytes(np.ascontiguousarray(samples, dtype=np.int16).tobytes())


@dataclass(frozen=True)
class RunJob:
    task: FoldTask
    config: Config
    dep_lock: str
    artifact_dir: Path


def produce_run(job: RunJob) -> dict[str, Any]:
    """Worker: fit, simulate, write artifacts, and return the rows to insert."""
    task, cfg = job.task, job.config
    run_id = run_id_for(task, cfg, job.dep_lock)
    fc = MODELS[cfg.model](task.frame, **dict(cfg.params))
    params = {gid: {"mean": m.tolist(), "cov": c.tolist()}
              for gid, m, c in zip(fc.game_ids, fc.means, fc.covs, strict=True)}
    params_bytes = json.dumps({"run_id": run_id, "config": cfg.label, "games": params},
                              sort_keys=True).encode()
    runs_dir, samples_dir = job.artifact_dir / "runs", job.artifact_dir / "samples"
    runs_dir.mkdir(parents=True, exist_ok=True)
    samples_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = runs_dir / f"{run_id}.json"
    artifact_path.write_bytes(params_bytes)

    target = task.frame.target.set_index("game_id")
    forecasts, tables = [], []
    for gid, mean, cov in zip(fc.game_ids, fc.means, fc.covs, strict=True):
        seed = derive_seed(task.root_seed, task.protocol_version, cfg.model, gid, task.horizon)
        samples = sample_scores(mean, cov, task.draws, seed)
        s = samples.astype(float)
        margin, total = np.sort(s[:, 0] - s[:, 1]), np.sort(s[:, 0] + s[:, 1])
        p = win_probability(samples)
        home, away = task.outcomes[gid]
        g = target.loc[gid]
        flags = {"start_time_tbd": bool(gid in task.fold.tbd_game_ids),
                 "non_fbs_team": not (bool(g["home_fbs"]) and bool(g["away_fbs"])),
                 "ties_redrawn": True}
        forecasts.append({
            "game_id": gid, "home_team_id": g["home"], "away_team_id": g["away"],
            "kickoff": g["start"].isoformat(), "seed": seed,
            "home_win_probability": p, "away_win_probability": 1 - p,
            "expected_home_score": float(s[:, 0].mean()), "expected_away_score": float(s[:, 1].mean()),
            "margin_q": [sorted_quantile(margin, q) for q in (0.1, 0.5, 0.9)],
            "total_q": [sorted_quantile(total, q) for q in (0.1, 0.5, 0.9)],
            "samples_hash": samples_digest(samples),
            "monte_carlo_se": float(np.sqrt(p * (1 - p) / len(samples))),
            "quality_flags": flags,
            "outcome": (home, away),
            "metrics": score_game(samples, home, away),
        })
        tables.append(pa.table({"game_id": [gid] * len(samples), "draw_id": np.arange(len(samples), dtype=np.int32),
                                "home_score": samples[:, 0], "away_score": samples[:, 1]}))
    buf = io.BytesIO()
    pq.write_table(pa.concat_tables(tables), buf, compression="zstd")
    samples_path = samples_dir / f"{run_id}.parquet"
    samples_path.write_bytes(buf.getvalue())
    return {
        "run_id": run_id, "config": cfg.label, "snapshot_id": task.snapshot_id,
        "training_end": task.fold.cutoff.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "root_seed": task.root_seed, "train_games": len(task.frame.train),
        "artifact_uri": f"runs/{artifact_path.name}", "artifact_hash": sha256_bytes(params_bytes),
        "samples_uri": f"samples/{samples_path.name}", "forecasts": forecasts,
        "fold": [task.fold.season, task.fold.season_type, task.fold.week],
        "draws": task.draws,
    }


def insert_run(
    conn: sqlite3.Connection, run: dict[str, Any], *, stage: str, dep_lock: str, protocol_version: str,
    horizon: int, evaluation_class: str, schedule_versions: dict[str, str],
    result_versions: dict[str, tuple[str, str]],
) -> bool:
    """Insert one run's rows in a single transaction. Returns False if already recorded."""
    if conn.execute("SELECT 1 FROM model_runs WHERE run_id=?", (run["run_id"],)).fetchone():
        return False
    now = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
    cutoff = datetime.fromisoformat(run["training_end"])
    with conn:
        conn.execute(
            "INSERT INTO model_runs VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
            (run["run_id"], run["snapshot_id"], stage, f"{stage.lower()}:{run['config']}",
             run["training_end"], run["root_seed"], dep_lock,
             short_id("in", run["snapshot_id"], run["config"]), run["artifact_uri"], run["artifact_hash"],
             "passed", json.dumps({"train_games": run["train_games"], "fold": run["fold"]})),
        )
        for f in run["forecasts"]:
            gid = f["game_id"]
            forecast_id = short_id("fc", run["run_id"], gid, horizon, PRODUCT)
            lead = (datetime.fromisoformat(f["kickoff"]).replace(tzinfo=UTC) - cutoff).total_seconds() / 60
            conn.execute(
                "INSERT INTO forecast_summaries VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (forecast_id, run["run_id"], gid, horizon, lead, schedule_versions[gid], now,
                 evaluation_class, PRODUCT, f["home_win_probability"], f["away_win_probability"],
                 f["expected_home_score"], f["expected_away_score"], *f["margin_q"], *f["total_q"],
                 f"{run['samples_uri']}#game_id={gid}", f["samples_hash"], run["draws"],
                 f["monte_carlo_se"], json.dumps(f["quality_flags"], sort_keys=True)),
            )
            choice = winner_v1(f["home_win_probability"], f["home_team_id"], f["away_team_id"])
            decision = {"forecast_id": forecast_id, "policy": POLICY_VERSION, "choice": choice,
                        "p": f["home_win_probability"]}
            conn.execute(
                "INSERT INTO decision_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (short_id("dec", forecast_id, POLICY_VERSION, "winner"), forecast_id, POLICY_VERSION,
                 "winner", choice, "FORCED_PICK_ONLY", None, None,
                 json.dumps(["winner_v1_has_no_recommendation"]), f["samples_hash"],
                 sha256_bytes(json.dumps(decision, sort_keys=True).encode())),
            )
            rv_id, observed_at = result_versions[gid]
            outcome_id = f"out-{rv_id}"
            conn.execute(
                "INSERT OR IGNORE INTO outcome_versions VALUES (?,?,?,?,?,?,?)",
                (outcome_id, gid, f["outcome"][0], f["outcome"][1], "final", observed_at, rv_id),
            )
            conn.execute(
                "INSERT INTO evaluation_results VALUES (?,?,?,?,?)",
                (short_id("ev", forecast_id, outcome_id, protocol_version), forecast_id, outcome_id,
                 protocol_version, json.dumps(f["metrics"], sort_keys=True)),
            )
    return True


def replay_check(conn: sqlite3.Connection, artifact_dir: Path, forecast_id: str, root_seed: int,
                 protocol_version: str, model: str, draws: int) -> bool:
    """Regenerate one stored forecast's samples from its run artifact and seed, and confirm
    the samples hash and the winner pick both reproduce."""
    row = conn.execute(
        """SELECT f.game_id, f.horizon_minutes, f.samples_hash, f.home_win_probability, r.artifact_uri,
                  g.home_team_id, g.away_team_id, d.forced_choice
           FROM forecast_summaries f JOIN model_runs r USING(run_id) JOIN games g USING(game_id)
           JOIN decision_records d ON d.forecast_id=f.forecast_id AND d.decision_type='winner'
           WHERE f.forecast_id=?""", (forecast_id,)).fetchone()
    gid, horizon, stored_hash, p, uri, home_id, away_id, choice = row
    params = json.loads((artifact_dir / uri).read_text(encoding="utf-8"))["games"][gid]
    seed = derive_seed(root_seed, protocol_version, model, gid, horizon)
    samples = sample_scores(np.array(params["mean"]), np.array(params["cov"]), draws, seed)
    return (samples_digest(samples) == stored_hash and win_probability(samples) == p
            and winner_v1(win_probability(samples), home_id, away_id) == choice)


def result_versions(conn: sqlite3.Connection) -> dict[str, tuple[str, str]]:
    """game_id -> (record_version_id, ingested_at) of the latest result fact."""
    rows = conn.execute(
        """SELECT entity_key, record_version_id, ingested_at FROM source_records r
           WHERE entity_type='game_result' AND ingested_at = (
               SELECT max(ingested_at) FROM source_records s
               WHERE s.entity_type='game_result' AND s.entity_key=r.entity_key)""").fetchall()
    return {k: (v, at) for k, v, at in rows}


def record_runs(
    conn: sqlite3.Connection, tasks: list[FoldTask], configs: list[Config], *, stage: str,
    dep_lock: str, artifact_dir: Path, evaluation_class: str, workers: int | None = None,
) -> dict[str, int]:
    """Produce runs in parallel (skipping runs already recorded) and insert them."""
    jobs = [RunJob(t, c, dep_lock, artifact_dir) for t in tasks for c in configs]
    existing = {r[0] for r in conn.execute("SELECT run_id FROM model_runs")}
    todo = [j for j in jobs if run_id_for(j.task, j.config, dep_lock) not in existing]
    runs = parallel_map(produce_run, todo, workers)
    results = result_versions(conn)
    by_run = {run_id_for(j.task, j.config, dep_lock): j.task for j in todo}
    inserted = 0
    for run in runs:
        task = by_run[run["run_id"]]
        inserted += insert_run(conn, run, stage=stage, dep_lock=dep_lock,
                               protocol_version=task.protocol_version, horizon=task.horizon,
                               evaluation_class=evaluation_class,
                               schedule_versions=dict(task.schedule_versions), result_versions=results)
    return {"runs_requested": len(jobs), "already_recorded": len(jobs) - len(todo), "inserted": inserted}
