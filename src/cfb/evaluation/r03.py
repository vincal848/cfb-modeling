"""R03: player-informed team decomposition by forward-residual correction (methodology §6).

The team-only B02 model already learns from past results. Roster information is added as
a correction to B02's held-forward forecasts, never appended to an already player-informed
rating:

    margin residual (actual - B02 expected margin) ~ beta * (feature_home - feature_away)

fit on earlier development seasons and applied to the next (2019 -> 2020; 2019-2020 -> 2021).

Ablation for double counting, two features per team-season from R01:

- `raw`: the roster projection itself, which overlaps with last season's results that
  B02's filter has already absorbed;
- `residualized`: roster projection minus its calibrated naive counterpart (last season's
  team EPA), the roster information B02 cannot already have.

If the raw feature helps in training but not out of sample while the residualized one
behaves differently, the raw signal is duplicating B02. Scores: margin squared error of
the corrected mean and Gaussian margin CRPS with a spread fit on training residuals.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

FEATURES = ("raw", "residualized")


def team_features(roster: pd.DataFrame) -> pd.DataFrame:
    """(team, season) -> raw and residualized offense features from R01's development output."""
    out = roster[["team", "season"]].copy()
    out["raw"] = roster["pred_roster"] - roster.groupby("season")["pred_roster"].transform("mean")
    out["residualized"] = roster["pred_both"] - roster["pred_naive"]
    return out


def game_table(b02: pd.DataFrame, schedule_names: dict[str, tuple[str, str]], feats: pd.DataFrame) -> pd.DataFrame:
    g = b02[["game_id", "season", "week", "season_type", "home_points", "away_points", "expected_home",
             "expected_away"]].copy()
    g["home"], g["away"] = zip(*(schedule_names[x] for x in g["game_id"]), strict=True)
    g["residual"] = (g["home_points"] - g["away_points"]) - (g["expected_home"] - g["expected_away"])
    for side in ("home", "away"):
        f = feats.rename(columns={"team": side, **{k: f"{k}_{side}" for k in FEATURES}})
        g = g.merge(f, on=[side, "season"], how="left")
    for k in FEATURES:
        g[f"{k}_diff"] = (g[f"{k}_home"] - g[f"{k}_away"]).fillna(0.0)  # no feature -> no correction
    return g


def crps_normal(y: np.ndarray, mean: np.ndarray, sd: float) -> np.ndarray:
    z = (y - mean) / sd
    return sd * (z * (2 * stats.norm.cdf(z) - 1) + 2 * stats.norm.pdf(z) - 1 / np.sqrt(np.pi))


def forward_correction(games: pd.DataFrame, test_season: int) -> pd.DataFrame:
    train, test = games[games["season"] < test_season], games[games["season"] == test_season].copy()
    margin = (test["home_points"] - test["away_points"]).to_numpy(float)
    base = (test["expected_home"] - test["expected_away"]).to_numpy(float)
    sd = float(np.sqrt(np.mean(train["residual"] ** 2)))
    test["sq_base"] = (margin - base) ** 2
    test["crps_base"] = crps_normal(margin, base, sd)
    for k in FEATURES:
        x = train[f"{k}_diff"].to_numpy()
        beta = float((x * train["residual"]).sum() / max((x * x).sum(), 1e-12))  # through the origin
        pred = base + beta * test[f"{k}_diff"].to_numpy()
        resid_after = train["residual"] - beta * x
        sd_k = float(np.sqrt(np.mean(resid_after ** 2)))
        test[f"beta_{k}"] = beta
        test[f"train_gain_{k}"] = float(np.mean(train["residual"] ** 2) - np.mean(resid_after ** 2))
        test[f"sq_{k}"] = (margin - pred) ** 2
        test[f"crps_{k}"] = crps_normal(margin, pred, sd_k)
    return test
