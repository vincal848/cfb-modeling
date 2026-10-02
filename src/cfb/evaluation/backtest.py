"""Forward backtest over V01 folds: snapshot per fold, then fit, simulate and score in parallel.

Snapshots are built sequentially in the main process (they write to the contract
database). Each fold then becomes one worker task that fits every model configuration
on that fold's snapshot and scores the fold's games. Draws use per-game derived seeds,
so the results do not depend on the number of workers or on task order.
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cfb.canonical.games import parse_utc
from cfb.evaluation.metrics import score_game
from cfb.evaluation.protocol import Fold, build_folds
from cfb.models.baselines import MODELS, GameFrame
from cfb.models.simulate import derive_seed, sample_scores
from cfb.snapshots.builder import build_snapshot, fact_as_of, load_facts

BLAS_THREAD_VARS = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")


@dataclass(frozen=True)
class Config:
    model: str  # key of MODELS; also the seed's model ID, so variants share random numbers
    params: tuple[tuple[str, float], ...]

    @property
    def label(self) -> str:
        return self.model + "".join(f"|{k}={v:g}" for k, v in self.params)


def latest_facts(conn: sqlite3.Connection, entity_type: str) -> list[dict]:
    """Latest version of each entity regardless of cutoff. For defining folds and scoring
    outcomes only; model inputs come from snapshots."""
    import json

    rows = conn.execute(
        """SELECT normalized_payload_json FROM source_records r
           WHERE entity_type=? AND ingested_at = (
               SELECT max(ingested_at) FROM source_records s
               WHERE s.entity_type=r.entity_type AND s.entity_key=r.entity_key)""",
        (entity_type,),
    ).fetchall()
    return [json.loads(r[0]) for r in rows]


def to_frame(schedules: list[dict], results: dict[str, dict] | None) -> pd.DataFrame:
    rows = []
    for s in schedules:
        row = {
            "game_id": s["game_id"], "season": s["season"], "season_type": s["season_type"],
            "week": s["week"], "start": pd.Timestamp(s["start_utc"]).tz_convert(None),
            "home": s["home_team_id"], "away": s["away_team_id"], "neutral": s["neutral_site"],
            "home_fbs": s["home_classification"] == "fbs", "away_fbs": s["away_classification"] == "fbs",
        }
        if results is not None:
            r = results.get(s["game_id"])
            if r is None:
                continue
            row["hp"], row["ap"] = r["home_points"], r["away_points"]
        rows.append(row)
    df = pd.DataFrame(rows)
    return df.sort_values(["start", "game_id"]).reset_index(drop=True) if len(df) else df


@dataclass(frozen=True)
class FoldTask:
    fold: Fold
    snapshot_id: str
    frame: GameFrame
    outcomes: dict[str, tuple[int, int]]
    configs: tuple[Config, ...]
    root_seed: int
    protocol_version: str
    horizon: int
    draws: int


def run_fold(task: FoldTask) -> list[dict[str, Any]]:
    out = []
    for cfg in task.configs:
        fc = MODELS[cfg.model](task.frame, **dict(cfg.params))
        for gid, mean, cov in zip(fc.game_ids, fc.means, fc.covs, strict=True):
            seed = derive_seed(task.root_seed, task.protocol_version, cfg.model, gid, task.horizon)
            samples = sample_scores(mean, cov, task.draws, seed)
            home, away = task.outcomes[gid]
            out.append({
                "config": cfg.label, "model": cfg.model, "game_id": gid,
                "season": task.fold.season, "season_type": task.fold.season_type,
                "week": task.fold.week, "role": task.fold.role, "snapshot_id": task.snapshot_id,
                "horizon_minutes": task.horizon, "home_points": home, "away_points": away,
                **score_game(samples, home, away),
            })
    return out


def prepare_tasks(
    conn: sqlite3.Connection, protocol: dict[str, Any], seasons: list[int], configs: list[Config],
    manifest_dir: Path, *, horizon: int | None = None, draws: int | None = None,
    log: Callable[[str], None] = print,
) -> list[FoldTask]:
    horizon = horizon or protocol["products"]["primary"]["horizon_minutes"]
    draws = draws or protocol["monte_carlo"]["draws_per_game"]
    mode = protocol["replay"]["historical_class"]
    schedules = {s["game_id"]: s for s in latest_facts(conn, "game_schedule")}
    results = {r["game_id"]: r for r in latest_facts(conn, "game_result")}
    tasks = []
    for season in seasons:
        scored = [s for gid, s in schedules.items() if s["season"] == season and gid in results]
        games = [{"id": s["game_id"], "season": s["season"], "seasonType": s["season_type"],
                  "week": s["week"], "startDate": s["start_utc"], "startTimeTBD": s["start_time_tbd"]}
                 for s in scored]
        folds = build_folds(protocol, season, games, horizon)
        for fold in folds:
            snap = build_snapshot(conn, fold.cutoff, mode, manifest_dir)
            snap_sched = load_facts(conn, snap.snapshot_id, "game_schedule")
            snap_res = {r["game_id"]: r for r in load_facts(conn, snap.snapshot_id, "game_result")}
            train = to_frame([s for s in snap_sched if s["game_id"] in snap_res], snap_res)
            # Each target game's schedule is the version available at its own cutoff
            # (kickoff minus horizon); parameters still come only from the fold snapshot.
            target_sched = []
            for g in fold.game_ids:
                game_cutoff = parse_utc(schedules[g]["start_utc"]) - timedelta(minutes=horizon)
                fact = fact_as_of(conn, "game_schedule", g, game_cutoff, mode)
                if fact is None:
                    raise RuntimeError(f"{g} has no schedule fact available at its own cutoff")
                target_sched.append(fact)
            target = to_frame(target_sched, None)
            leaked = set(target["game_id"]) & set(train["game_id"])
            if leaked:
                raise RuntimeError(f"fold {season} {fold.season_type} {fold.week}: target results in training")
            outcomes = {g: (results[g]["home_points"], results[g]["away_points"]) for g in fold.game_ids}
            tasks.append(FoldTask(fold, snap.snapshot_id, GameFrame(train, target), outcomes,
                                  tuple(configs), protocol["monte_carlo"]["root_seed"],
                                  protocol["protocol_version"], horizon, draws))
        log(f"season {season}: {len(folds)} folds, {sum(len(f.game_ids) for f in folds)} games")
    return tasks


def run_tasks(tasks: list[FoldTask], workers: int | None = None) -> pd.DataFrame:
    workers = workers or max(1, (os.cpu_count() or 2) - 1)
    if workers == 1:
        rows = [r for t in tasks for r in run_fold(t)]
    else:
        # Parallelism is across processes, so each worker gets one BLAS/OpenMP thread.
        # Workers inherit the environment at spawn, before they import numpy; without
        # this, every worker starts a thread per core and they oversubscribe the CPU.
        saved = {k: os.environ.get(k) for k in BLAS_THREAD_VARS}
        os.environ.update(dict.fromkeys(BLAS_THREAD_VARS, "1"))
        try:
            with ProcessPoolExecutor(max_workers=workers) as pool:
                rows = [r for chunk in pool.map(run_fold, tasks) for r in chunk]
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    df = pd.DataFrame(rows)
    return df.sort_values(["config", "game_id"]).reset_index(drop=True)


def mean_scores(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    cols = ["energy_score", "winner_log_loss", "winner_brier", "margin_crps", "total_crps",
            "margin_abs_error", "total_abs_error"] + [c for c in df.columns if c.endswith(("_covered", "_width"))]
    g = df.groupby(by)
    out = g[cols].mean()
    out.insert(0, "games", g.size())
    return out


def block_bootstrap(diff: pd.Series, blocks: pd.Series, reps: int, seed: int) -> tuple[float, float, float]:
    """Mean paired difference and 95% percentile interval, resampling whole blocks."""
    sums = diff.groupby(blocks).sum()
    counts = diff.groupby(blocks).size()
    s, c = sums.to_numpy(), counts.to_numpy()
    rng = np.random.Generator(np.random.PCG64(seed))
    pick = rng.integers(0, len(s), size=(reps, len(s)))
    means = s[pick].sum(axis=1) / c[pick].sum(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(s.sum() / c.sum()), float(lo), float(hi)
