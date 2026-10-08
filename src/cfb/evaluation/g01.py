"""G01: development evaluation of the joint-score expert (one process).

Regulation means come from the B02 filter (its selected configuration, not re-tuned)
refit on regulation scores, with the filter's state covariance propagated into every
draw; the count sampler's pace and dispersion are chosen on the development seasons by
energy score. Draws use per-game seeds under model ID "g01", so the grid shares random
numbers.

Pass 2. Pass 1 used only the filter means: margins were too narrow (46/76/93% coverage at
nominal 50/80/95), it lost to B02 by 0.105 energy score, and selected the largest pace
setting tried (50). Pass 2 propagates the state covariance and extends pace to 200 and
1,000 (about no shared pace). No further pass.
"""

from __future__ import annotations

import itertools
from typing import Any

import numpy as np
import pandas as pd

from cfb.evaluation.backtest import Config, FoldTask, latest_facts
from cfb.evaluation.metrics import score_game
from cfb.models.dynamic import DynamicParams, filter_and_predict, ids_digest
from cfb.models.joint import ot_kernel, sample_joint
from cfb.models.simulate import derive_seed

MODEL_ID = "g01"
GRID = {"pace_k": [15.0, 50.0, 200.0, 1000.0], "disp_r": [5.0, 10.0, 20.0, 50.0]}


def grid() -> list[Config]:
    keys = sorted(GRID)
    return [Config(MODEL_ID, tuple(zip(keys, v, strict=True))) for v in itertools.product(*(GRID[k] for k in keys))]


def regulation_and_ot(conn) -> tuple[dict[str, tuple[int, int]], list[tuple[int, int, int]]]:
    """game_id -> regulation (home, away); and (season, home OT points, away OT points)."""
    seasons = {s["game_id"]: s["season"] for s in latest_facts(conn, "game_schedule")}
    reg, ot = {}, []
    for r in latest_facts(conn, "game_result"):
        h, a = r.get("home_line_scores"), r.get("away_line_scores")
        ok = h and a and len(h) >= 4 and len(a) >= 4 and sum(h) == r["home_points"] and sum(a) == r["away_points"]
        if not ok:
            reg[r["game_id"]] = (r["home_points"], r["away_points"])  # no usable line scores: final as label
            continue
        reg[r["game_id"]] = (sum(h[:4]), sum(a[:4]))
        if len(h) > 4:
            ot.append((seasons[r["game_id"]], r["home_points"] - reg[r["game_id"]][0],
                       r["away_points"] - reg[r["game_id"]][1]))
    return reg, ot


def run(tasks: list[FoldTask], reg: dict, ot_games: list, dynamic_label: str, lag_hours: float) -> pd.DataFrame:
    tasks = sorted(tasks, key=lambda t: t.fold.cutoff)
    history = tasks[-1].frame.train.copy()
    labels = history["game_id"].map(reg)
    history["hp"] = [lab[0] for lab in labels]
    history["ap"] = [lab[1] for lab in labels]
    folds = [(t.fold.cutoff.isoformat(), ids_digest(t.frame.train["game_id"]), t.frame.target) for t in tasks]
    params = DynamicParams(**dict(Config.from_label(dynamic_label).params))
    preds = filter_and_predict(history, folds, params, lag_hours)
    rows: list[dict[str, Any]] = []
    noise = np.eye(2) * params.sigma**2
    for task, (_, gids, means, covs) in zip(tasks, preds, strict=True):
        pairs, fallback = ot_kernel(ot_games, task.fold.season)
        for gid, mean, cov in zip(gids, means, covs, strict=True):
            state_cov = cov - noise
            seed = derive_seed(task.root_seed, task.protocol_version, MODEL_ID, gid, task.horizon)
            home, away = task.outcomes[gid]
            for cfg in grid():
                p = dict(cfg.params)
                s = sample_joint(float(mean[0]), float(mean[1]), p["pace_k"], p["disp_r"], pairs, task.draws,
                                 seed, state_cov)
                rows.append({"config": cfg.label, "model": MODEL_ID, "game_id": gid, "season": task.fold.season,
                             "season_type": task.fold.season_type, "week": task.fold.week, "role": task.fold.role,
                             "snapshot_id": task.snapshot_id, "horizon_minutes": task.horizon,
                             "home_points": home, "away_points": away, "ot_fallback": fallback,
                             **score_game(s, home, away)})
    return pd.DataFrame(rows).sort_values(["config", "game_id"]).reset_index(drop=True)

