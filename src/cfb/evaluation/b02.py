"""B02: forward evaluation of the dynamic team filter on the V01 development seasons.

One job per configuration: a single forward pass from 2014, predicting each fold's games
from the state at that fold's cutoff. `filter_and_predict` checks that the state has
absorbed exactly the fold snapshot's results, so every prediction is past-only and
matches the snapshot discipline used by B01. Jobs run in parallel; draws use the same
per-game seeds, so results do not depend on worker count.

The grid was fixed before B02's first run. The off-season innovation is tied to the
prior spread, (1 - rho^2) * s0^2, rather than tuned separately. Comparisons are against
the selected B01 models on identical games.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from typing import Any

import pandas as pd

from cfb.evaluation.backtest import Config, FoldTask, parallel_map
from cfb.evaluation.metrics import score_game
from cfb.models.dynamic import DynamicParams, filter_and_predict, ids_digest
from cfb.models.simulate import derive_seed, sample_scores

MODEL_ID = "dynamic"
GRID: dict[str, list[float]] = {
    "q_week": [0.25, 1.0, 4.0],
    "rho": [0.6, 0.75, 0.9],
    "s0": [5.0, 8.0],
    "sigma": [11.0, 12.0],
}
PAIRS = (("dynamic", "ridge"), ("dynamic", "elo"), ("dynamic", "hfa_only"))
SENSITIVITY_PAIRS = (("dynamic", "ridge"),)


def grid_configs() -> list[Config]:
    keys = sorted(GRID)
    return [Config(MODEL_ID, tuple(zip(keys, v, strict=True)))
            for v in itertools.product(*(GRID[k] for k in keys))]


@dataclass(frozen=True)
class DynamicJob:
    config: Config
    history: pd.DataFrame
    folds: tuple[tuple[str, str, pd.DataFrame], ...]  # (cutoff, admitted-ID digest, targets)
    tasks: tuple[FoldTask, ...]  # same order as folds, with frames stripped; outcomes and seeds
    result_lag_hours: float


def run_dynamic(job: DynamicJob) -> list[dict[str, Any]]:
    params = DynamicParams(**dict(job.config.params))
    preds = filter_and_predict(job.history, list(job.folds), params, job.result_lag_hours)
    rows = []
    for task, (_, gids, means, covs) in zip(job.tasks, preds, strict=True):
        for gid, mean, cov in zip(gids, means, covs, strict=True):
            seed = derive_seed(task.root_seed, task.protocol_version, MODEL_ID, gid, task.horizon)
            samples = sample_scores(mean, cov, task.draws, seed)
            home, away = task.outcomes[gid]
            rows.append({
                "config": job.config.label, "model": MODEL_ID, "game_id": gid,
                "season": task.fold.season, "season_type": task.fold.season_type, "week": task.fold.week,
                "role": task.fold.role, "snapshot_id": task.snapshot_id, "horizon_minutes": task.horizon,
                "home_points": home, "away_points": away, **score_game(samples, home, away),
            })
    return rows


def run_grid(tasks: list[FoldTask], result_lag_hours: float, workers: int | None = None) -> pd.DataFrame:
    tasks = sorted(tasks, key=lambda t: t.fold.cutoff)
    # The last fold's snapshot holds every result admitted to any earlier fold (no
    # corrections exist yet), so it is the history for the single forward pass.
    history = tasks[-1].frame.train
    folds = tuple((t.fold.cutoff.isoformat(), ids_digest(t.frame.train["game_id"]), t.frame.target)
                  for t in tasks)
    # Jobs are pickled to workers, so drop each task's training frame (the history covers it).
    light = tuple(replace(t, frame=None) for t in tasks)
    jobs = [DynamicJob(c, history, folds, light, result_lag_hours) for c in grid_configs()]
    rows = [r for chunk in parallel_map(run_dynamic, jobs, workers) for r in chunk]
    return pd.DataFrame(rows).sort_values(["config", "game_id"]).reset_index(drop=True)
