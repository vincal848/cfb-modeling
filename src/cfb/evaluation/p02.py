"""P02: fold-specific EP evaluation on the V01 development seasons.

For each development season s (parallel across seasons and penalties):

1. Penalty selection, past-only: fit each candidate on seasons before s-1 and score next-
   score log loss on s-1. Fixed before any season-s result is seen.
2. Refit on every season before s with the chosen penalty; score season s.

Models: `full` (all preplay features), `yardline` (yards to goal only), and the class
prior from training. The try value is learned inside each fold. States come from P01
(exact-tier games, regulation scrimmage plays), so every training label is past-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from cfb.models.ep import epa, fit, label_index, log_loss, realized_points
from cfb.state.rules import scoring_rules
from cfb.state.table import LABELS

# Smallest penalty 1e-6: an unpenalized fit (0) does not converge, because rare outcomes such as
# safeties let coefficients grow without bound (3,000 iterations, still rising); 1e-6 converges.
# The methodology also calls for a regularized classifier.
PENALTIES = (1e-6, 1e-5, 1e-4, 1e-3)
KINDS = ("full", "yardline")
# Serial by default: the fits are memory- and CPU-heavy, and running them in parallel took
# too much of the machine at once. Pass --workers to opt into parallel fits.
EP_WORKERS = 1


@dataclass(frozen=True)
class Job:
    states_path: Path
    train_seasons: tuple[int, ...]
    eval_season: int
    kind: str
    penalty: float
    phase: str  # "select" or "final"


def _load(path: Path, seasons) -> pd.DataFrame:
    df = pd.read_parquet(path)
    return df[df["season"].isin(seasons)].sort_values(["game_id", "period", "play_id"]).reset_index(drop=True)


def run_job(job: Job) -> dict[str, Any]:
    train = _load(job.states_path, job.train_seasons)
    test = _load(job.states_path, [job.eval_season])
    rules = scoring_rules(job.eval_season)
    model = fit(train, rules, kind=job.kind, penalty=job.penalty)
    out = {"job": job, "log_loss": float(log_loss(model, test).mean()), "converged": model.converged,
           "try_value": model.try_value, "train_rows": model.train_rows}
    if job.phase == "final":
        ep = model.expected_points(test)
        prior = np.bincount(label_index(train), minlength=len(LABELS)) / len(train)
        frame = test[["game_id", "season", "week", "season_type", "play_id", "half", "offense", "down",
                      "distance", "yards_to_goal", "seconds_left_half", "score_margin", "play_type",
                      "play_points", "next_score"]].copy()
        frame["ep"] = ep
        frame["log_loss"] = log_loss(model, test)
        frame["prior_log_loss"] = -np.log(prior[label_index(test)])
        frame["realized"] = realized_points(test, model.values)
        probs = model.probabilities(test)
        for i, lab in enumerate(LABELS):
            frame[f"p_{lab}"] = probs[:, i]
        frame["epa"] = epa(frame, ep)
        grid = test.head(1).iloc[[0] * 9].assign(
            yards_to_goal=[5, 15, 25, 35, 50, 65, 75, 85, 95], down=1, distance=10, seconds_left_half=1700,
            score_margin=0, half=1, offense_timeouts=3)
        out.update(frame=frame, ep_by_yardline=dict(zip(grid["yards_to_goal"], model.expected_points(grid),
                                                        strict=True)))
    return out


def plan_selection(states_path: Path, seasons: list[int], first: int) -> list[Job]:
    return [Job(states_path, tuple(range(first, s - 1)), s - 1, kind, pen, "select")
            for s in seasons for kind in KINDS for pen in PENALTIES]


def choose(selection: list[dict[str, Any]], seasons: list[int]) -> dict[tuple[int, str], float]:
    best: dict[tuple[int, str], tuple[float, float]] = {}
    for r in selection:
        j = r["job"]
        key = (j.eval_season + 1, j.kind)
        if key not in best or r["log_loss"] < best[key][0]:
            best[key] = (r["log_loss"], j.penalty)
    return {k: v[1] for k, v in best.items() if k[0] in seasons}


def plan_final(states_path: Path, chosen: dict[tuple[int, str], float], first: int) -> list[Job]:
    return [Job(states_path, tuple(range(first, s)), s, kind, pen, "final") for (s, kind), pen in sorted(chosen.items())]
