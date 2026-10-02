"""R01: does the preseason roster projection predict team offense better than last season?

For each development season s (one process), with every EPA label from the EP model fit
before s:

- projection for season t (2017..s): roster scenarios (models.roster) built from season-t
  rosters, season t-1 opportunity shares and P04 abilities fit on seasons before t;
  offense = pass_rate(t-1) * R_passing + (1 - pass_rate(t-1)) * R_rushing;
- naive: the team's offensive EPA per play in t-1;
- realized: offensive EPA per play in t (P01 exact-tier games, regulation scrimmage plays).

Each predictor is linearly calibrated on seasons 2017..s-1 and then predicts s. Teams need
at least MIN_PLAYS plays in both t-1 and t. Paired differences use a bootstrap over teams.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from cfb.evaluation import p04
from cfb.models.opportunity import TEAM_PLAY_TYPES, ShareParams
from cfb.models.roster import CATS, Ability, build

MAIN_GROUP = {"passing": "QB", "rushing": "RB", "receiving": "WR"}
FIRST_TARGET = 2017
MIN_PLAYS = 300
# P03 selected share configuration (experiments/p03/opportunity-development.md).
SHARE_PARAMS = ShareParams(half_life_games=2.0, prior_season_weight=0.5, alpha=0.1, kappa=3.0)


def team_offense(states: pd.DataFrame, epa: pd.DataFrame) -> pd.DataFrame:
    """(team, season) -> EPA per play, plays, pass rate."""
    df = states[["play_id", "season", "offense", "play_type"]].assign(play_id=lambda d: d["play_id"].astype(str))
    df = df.merge(epa[["play_id", "epa"]], on="play_id")
    is_pass = df["play_type"].isin(TEAM_PLAY_TYPES["dropbacks"])
    is_rush = df["play_type"].isin(TEAM_PLAY_TYPES["carries"])
    g = df.assign(is_pass=is_pass, is_rush=is_rush).groupby(["offense", "season"])
    out = pd.DataFrame({"epa_per_play": g["epa"].mean(), "plays": g.size(),
                        "pass_rate": g["is_pass"].sum() / (g["is_pass"].sum() + g["is_rush"].sum())})
    return out.reset_index().rename(columns={"offense": "team"})


def prior_shares(stats: pd.DataFrame, season: int) -> dict[str, dict[str, float]]:
    """category -> athlete -> his share of his team's attributed opportunities in season - 1
    (the largest if he played for several teams)."""
    prev = stats[stats["season"] == season - 1]
    out: dict[str, dict[str, float]] = defaultdict(dict)
    counts = prev.groupby(["team", "category", "athlete_id"]).size()
    totals = counts.groupby(level=[0, 1]).sum()
    for (team, cat, aid), n in counts.items():
        out[cat][aid] = max(out[cat].get(aid, 0.0), n / totals[(team, cat)])
    return out


def projections(rows: pd.DataFrame, stats: pd.DataFrame, rosters: dict[int, dict[str, set[str]]],
                pos: dict, sigma2: dict[str, float], season: int) -> pd.DataFrame:
    shares = prior_shares(stats, season)
    abilities: dict[str, dict[str, Ability]] = {}
    replacement: dict[str, Ability] = {}
    for cat in CATS:
        train = rows[(rows["category"] == cat) & (rows["season"] < season)]
        fitted = p04.fit_groups(train, sigma2[cat])
        main = fitted.get(MAIN_GROUP[cat], fitted["_pooled"])
        if "params" in main:
            p = main["params"]
            replacement[cat] = Ability(p.mu[MAIN_GROUP[cat]], p.tau2)
        else:
            replacement[cat] = Ability(main["mean"], main["var"])
        targets = pd.DataFrame([{"athlete_id": a, "season": season, "group": pos.get((a, season), "OTHER")}
                                for a in shares.get(cat, {})])
        if targets.empty:
            abilities[cat] = {}
            continue
        pred = p04.predict_groups(fitted, targets)
        abilities[cat] = {a: Ability(m, v) for a, m, v in zip(pred["athlete_id"], pred["pred_mean"], pred["pred_var"],
                                                               strict=True)}
    out = []
    for team, roster in rosters.get(season, {}).items():
        scn = build(team, season, roster, shares, abilities, replacement, SHARE_PARAMS)
        out.append({"team": team, "season": season, "proj_passing": scn.strength("passing"),
                    "proj_rushing": scn.strength("rushing"),
                    "known_passers": len(scn.shares("passing")) - 1})
    return pd.DataFrame(out)


def season_dataset(rows, stats, rosters, pos, sigma2, offense: pd.DataFrame, last_target: int) -> pd.DataFrame:
    frames = []
    for t in range(FIRST_TARGET, last_target + 1):
        proj = projections(rows, stats, rosters, pos, sigma2, t)
        prev = offense[offense["season"] == t - 1][["team", "epa_per_play", "plays", "pass_rate"]].rename(
            columns={"epa_per_play": "naive", "plays": "plays_prev", "pass_rate": "pass_rate_prev"})
        cur = offense[offense["season"] == t][["team", "epa_per_play", "plays"]].rename(
            columns={"epa_per_play": "realized"})
        d = proj.merge(prev, on="team").merge(cur, on="team")
        d = d[(d["plays_prev"] >= MIN_PLAYS) & (d["plays"] >= MIN_PLAYS)]
        d["roster"] = d["pass_rate_prev"] * d["proj_passing"] + (1 - d["pass_rate_prev"]) * d["proj_rushing"]
        frames.append(d)
    return pd.concat(frames, ignore_index=True)


PREDICTORS = {"naive": ["naive"], "roster": ["roster"], "both": ["naive", "roster"]}


def calibrated_predictions(data: pd.DataFrame, season: int) -> pd.DataFrame:
    train, test = data[data["season"] < season], data[data["season"] == season].copy()
    for name, cols in PREDICTORS.items():
        x = np.column_stack([np.ones(len(train)), train[cols].to_numpy()])
        beta, *_ = np.linalg.lstsq(x, train["realized"].to_numpy(), rcond=None)
        test[f"pred_{name}"] = np.column_stack([np.ones(len(test)), test[cols].to_numpy()]) @ beta
        test[f"coef_{name}"] = [beta.round(4).tolist()] * len(test)
    return test


def team_bootstrap(diff: pd.Series, teams: pd.Series, reps: int, seed: int) -> tuple[float, float, float]:
    by = diff.groupby(teams).agg(["sum", "size"])
    s, c = by["sum"].to_numpy(), by["size"].to_numpy()
    pick = np.random.Generator(np.random.PCG64(seed)).integers(0, len(s), size=(reps, len(s)))
    means = s[pick].sum(axis=1) / c[pick].sum(axis=1)
    lo, hi = np.percentile(means, [2.5, 97.5])
    return float(s.sum() / c.sum()), float(lo), float(hi)
