"""P04: held-forward evaluation of skill-player effectiveness on the V01 development seasons.

For each development season s, in one process:

1. EP model fit on seasons before s (P02 fold, penalty from the P02 report), saved under
   artifacts/models/ so later stages reuse the same fold model;
2. EPA for every P01 state through season s from that model, so no label uses data from
   season s or later in fitting;
3. EPA joined to CFBD player play stats by play ID: passing (passer on dropbacks), rushing
   (rusher), receiving (targeted player). Only P01 exact-tier games have states;
4. per category, the development model fit on seasons before s, then season s predicted
   for every player who had opportunities in it and scored.

Baselines: the position-group mean (no player information) and last season's raw mean
(no shrinkage). Each baseline's predictive variance is calibrated on training seasons.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from cfb.models import ability, ep
from cfb.state.rules import scoring_rules

STAT_CATEGORY = {
    "Completion": "passing", "Incompletion": "passing", "Sack Taken": "passing", "Interception Thrown": "passing",
    "Rush": "rushing", "Reception": "receiving", "Target": "receiving",
}
EP_PENALTY = 1e-6  # selected in every P02 fold (experiments/p02/ep-development.md)


def fold_ep_model(states: pd.DataFrame, season: int, first: int, model_dir: Path, log=print) -> ep.EPModel:
    path = model_dir / f"ep-fold-{season}.npz"
    if path.exists():
        return ep.load(path)
    train = states[states["season"].between(first, season - 1)]
    log(f"  fitting EP fold {season} on {len(train):,} plays (one process, one thread)")
    model = ep.fit(train, scoring_rules(season), penalty=EP_PENALTY)
    if not model.converged:
        raise RuntimeError(f"EP fold {season} did not converge")
    model_dir.mkdir(parents=True, exist_ok=True)
    ep.save(model, path)
    return model


def play_epa(states: pd.DataFrame, model: ep.EPModel) -> pd.DataFrame:
    df = states.sort_values(["game_id", "period", "play_id"]).reset_index(drop=True)
    values = model.expected_points(df)
    return pd.DataFrame({"play_id": df["play_id"].astype(str), "season": df["season"], "epa": ep.epa(df, values)})


def load_play_stats(conn: sqlite3.Connection, ledger, seasons: list[int]) -> pd.DataFrame:
    from cfb.evaluation.backtest import latest_facts

    ids = [(int(s["game_id"].split("-")[-1]), s["season"]) for s in latest_facts(conn, "game_schedule")
           if s["season"] in seasons]
    rows = []
    for gid, _ in ids:
        e = ledger.latest_success("/plays/stats", {"gameId": gid})
        if e is not None and e.http_status == 200:
            for r in ledger.load(e):
                cat = STAT_CATEGORY.get(r.get("statType"))
                if cat and r.get("athleteId") is not None:
                    rows.append((str(r["playId"]), str(r["athleteId"]), cat, int(r["season"])))
    df = pd.DataFrame(rows, columns=["play_id", "athlete_id", "category", "season"])
    return df.drop_duplicates(["play_id", "athlete_id", "category"])


def positions(ledger, seasons: list[int]) -> dict[tuple[str, int], str]:
    out = {}
    for s in seasons:
        e = ledger.latest_success("/roster", {"year": s})
        for r in ledger.load(e) if e else []:
            if r.get("id") is not None:
                out[(str(r["id"]), s)] = ability.position_group(r.get("position"))
    return out


def player_seasons(stats: pd.DataFrame, epa: pd.DataFrame, pos: dict) -> tuple[pd.DataFrame, dict[str, float]]:
    """(athlete, season, category) rows with y = mean EPA per opportunity and n; plus the
    pooled within-player-season play variance per category (sigma2)."""
    joined = stats.merge(epa[["play_id", "epa"]], on="play_id", how="inner")
    g = joined.groupby(["athlete_id", "season", "category"])["epa"]
    agg = pd.DataFrame({"y": g.mean(), "n": g.size(), "ss": g.var(ddof=1) * (g.size() - 1)}).reset_index()
    sigma2 = {}
    for cat, sub in agg.groupby("category"):
        dof = (sub["n"] - 1).clip(lower=0).sum()
        sigma2[cat] = float(sub["ss"].fillna(0).sum() / dof)
    agg["group"] = [pos.get((a, s), "OTHER") for a, s in zip(agg["athlete_id"], agg["season"], strict=True)]
    return agg.drop(columns="ss"), sigma2


def _baseline_var(train: pd.DataFrame, mean: np.ndarray, sigma2: float) -> float:
    resid2 = (train["y"].to_numpy() - mean) ** 2 - sigma2 / train["n"].to_numpy()
    return max(float(np.average(resid2, weights=train["n"])), 1e-4)


def evaluate_category(rows: pd.DataFrame, season: int, sigma2: float) -> tuple[pd.DataFrame, ability.AbilityParams]:
    train, test = rows[rows["season"] < season], rows[rows["season"] == season]
    params = ability.fit_ability(train, sigma2)
    pred = ability.predict(train, test[["athlete_id", "season", "group"]], params)
    out = test.reset_index(drop=True).copy()
    out["model_mean"], out["model_var"], out["has_history"] = (
        pred["pred_mean"].to_numpy(), pred["pred_var"].to_numpy(), pred["has_history"].to_numpy())

    # Baseline 1: group mean from training; variance calibrated on training.
    gm = train.groupby("group").apply(lambda d: np.average(d["y"], weights=d["n"]), include_groups=False)
    pooled = float(np.average(train["y"], weights=train["n"]))
    out["group_mean"] = out["group"].map(gm).fillna(pooled)
    v_group = _baseline_var(train, train["group"].map(gm).to_numpy(), sigma2)
    # Baseline 2: last season's raw mean (group mean if none); variance calibrated on training returners.
    last = rows.sort_values("season").groupby("athlete_id")
    prev = {}
    for a, d in last:
        for s, y in zip(d["season"], d["y"], strict=True):
            prev[(a, s)] = y
    def last_raw(a, s, fallback):
        earlier = [prev[(a, t)] for t in range(s - 1, s - 4, -1) if (a, t) in prev]
        return earlier[0] if earlier else fallback
    out["last_raw"] = [last_raw(a, season, f) for a, f in zip(out["athlete_id"], out["group_mean"], strict=True)]
    train_last = np.array([last_raw(a, s, gm.get(gr, pooled)) for a, s, gr in
                           zip(train["athlete_id"], train["season"], train["group"], strict=True)])
    v_last = _baseline_var(train, train_last, sigma2)

    out["ls_model"] = ability.gaussian_log_score(out["y"], out["n"], out["model_mean"], out["model_var"], sigma2)
    out["ls_group"] = ability.gaussian_log_score(out["y"], out["n"], out["group_mean"], v_group, sigma2)
    out["ls_last"] = ability.gaussian_log_score(out["y"], out["n"], out["last_raw"], v_last, sigma2)
    z80 = 1.2815515655446004
    sd = np.sqrt(out["model_var"] + sigma2 / out["n"])
    out["covered80"] = (out["y"] - out["model_mean"]).abs() <= z80 * sd
    return out, params
