"""B01 baselines: each returns a bivariate normal for (home, away) final points per game.

All three fit only on games in the fold's snapshot and are sampled by
`cfb.models.simulate.sample_scores`.

- `hfa_only`: the trivial sanity case. League home and away means and nothing about teams.
- `elo`: recomputed margin-of-victory Elo for the margin; a decayed league mean for the
  total. Elo's own pregame predictions on past games are already out of sample, so the
  margin scale and residual covariance come from them.
- `ridge`: the regularized past-only champion (config `initial_champion`). Paired score
  regression with team offense and defense effects, a non-FBS group effect, home
  advantage, exponential time decay and a ridge penalty on team effects.

Residual covariances are estimated on the training games, with a degrees-of-freedom
correction for the ridge fit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import sparse

FBS = "fbs"
DAY = np.timedelta64(1, "D")


@dataclass(frozen=True)
class GameFrame:
    """Past games (with results) and target games (schedule only) for one fold."""

    train: pd.DataFrame  # game_id, start, season, home, away, neutral, home_fbs, away_fbs, hp, ap
    target: pd.DataFrame  # same columns without hp, ap


@dataclass(frozen=True)
class Forecast:
    game_ids: list[str]
    means: np.ndarray  # (n, 2) home, away
    covs: np.ndarray  # (n, 2, 2)


def decay_weights(starts: pd.Series, reference: np.datetime64, half_life_days: float) -> np.ndarray:
    age = (reference - starts.to_numpy()) / DAY
    return np.power(0.5, np.maximum(age, 0) / half_life_days)


def weighted_cov(res: np.ndarray, w: np.ndarray, inflate: float = 1.0) -> np.ndarray:
    w = w / w.sum()
    centered = res - (w[:, None] * res).sum(axis=0)
    cov = (w[:, None, None] * centered[:, :, None] * centered[:, None, :]).sum(axis=0)
    return cov * inflate


# ---- trivial -----------------------------------------------------------------

def fit_hfa_only(frame: GameFrame, *, half_life_days: float = 365.0) -> Forecast:
    tr, tg = frame.train, frame.target
    ref = tg["start"].min().to_datetime64()
    w = decay_weights(tr["start"], ref, half_life_days)
    site = ~tr["neutral"].to_numpy()
    home_mean = np.average(tr["hp"][site], weights=w[site])
    away_mean = np.average(tr["ap"][site], weights=w[site])
    both = (home_mean + away_mean) / 2
    pred_tr = np.where(site[:, None], [home_mean, away_mean], [both, both])
    cov = weighted_cov(tr[["hp", "ap"]].to_numpy(float) - pred_tr, w)
    neutral = tg["neutral"].to_numpy()
    means = np.where(neutral[:, None], [both, both], [home_mean, away_mean])
    return Forecast(list(tg["game_id"]), means, np.repeat(cov[None], len(tg), axis=0))


# ---- Elo ---------------------------------------------------------------------

def _elo_win_p(diff: float) -> float:
    return 1.0 / (1.0 + 10 ** (-diff / 400))


def run_elo(
    train: pd.DataFrame, *, k: float, hfa: float, carryover: float, non_fbs_start: float = 1200.0
) -> tuple[dict[str, float], np.ndarray]:
    """Ratings after all training games, and each training game's pregame rating difference."""
    ratings: dict[str, float] = {}
    base: dict[str, float] = {}
    last_season: dict[str, int] = {}
    diffs = np.empty(len(train))
    rows = train.sort_values(["start", "game_id"])
    for i, g in enumerate(rows.itertuples(index=False)):
        for team, fbs in ((g.home, g.home_fbs), (g.away, g.away_fbs)):
            if team not in ratings:
                base[team] = 1500.0 if fbs else non_fbs_start
                ratings[team] = base[team]
            elif last_season[team] != g.season:
                ratings[team] = base[team] + carryover * (ratings[team] - base[team])
            last_season[team] = g.season
        diff = ratings[g.home] - ratings[g.away] + (0.0 if g.neutral else hfa)
        diffs[i] = diff
        margin = g.hp - g.ap
        p = _elo_win_p(diff)
        outcome = 1.0 if margin > 0 else 0.0 if margin < 0 else 0.5
        winner_diff = diff if margin > 0 else -diff
        mult = math.log(abs(margin) + 1) * 2.2 / (winner_diff * 0.001 + 2.2)
        delta = k * mult * (outcome - p)
        ratings[g.home] += delta
        ratings[g.away] -= delta
    out = pd.Series(diffs, index=rows.index).reindex(train.index).to_numpy()
    return ratings, out


def fit_elo(
    frame: GameFrame, *, k: float = 30.0, hfa: float = 65.0, carryover: float = 0.7,
    half_life_days: float = 365.0,
) -> Forecast:
    tr, tg = frame.train, frame.target
    ratings, diffs = run_elo(tr, k=k, hfa=hfa, carryover=carryover)
    ref = tg["start"].min().to_datetime64()
    w = decay_weights(tr["start"], ref, half_life_days)
    margin = (tr["hp"] - tr["ap"]).to_numpy(float)
    total = (tr["hp"] + tr["ap"]).to_numpy(float)
    # Margin points per Elo point, weighted least squares through the origin on pregame diffs.
    slope = float((w * diffs * margin).sum() / (w * diffs * diffs).sum())
    total_mean = float(np.average(total, weights=w))
    cov_mt = weighted_cov(np.column_stack([margin - slope * diffs, total - total_mean]), w)
    to_scores = np.array([[0.5, 0.5], [-0.5, 0.5]])  # (margin, total) -> (home, away)
    cov = to_scores @ cov_mt @ to_scores.T

    seasons = tr.groupby("home")["season"].max().combine(tr.groupby("away")["season"].max(), max, 0)
    means = np.empty((len(tg), 2))
    for i, g in enumerate(tg.itertuples(index=False)):
        r = {}
        for team, fbs in ((g.home, g.home_fbs), (g.away, g.away_fbs)):
            b = 1500.0 if fbs else 1200.0
            rt = ratings.get(team, b)
            if team in ratings and seasons.get(team, g.season) != g.season:
                rt = b + carryover * (rt - b)  # season carryover not yet applied
            r[team] = rt
        diff = r[g.home] - r[g.away] + (0.0 if g.neutral else hfa)
        m = slope * diff
        means[i] = [(total_mean + m) / 2, (total_mean - m) / 2]
    return Forecast(list(tg["game_id"]), means, np.repeat(cov[None], len(tg), axis=0))


# ---- ridge -------------------------------------------------------------------

def fit_ridge(
    frame: GameFrame, *, half_life_days: float = 365.0, penalty: float = 20.0, cov_scale: float = 1.0
) -> Forecast:
    """y_home = mu + hfa*site + off[home] - def[away];  y_away = mu + off[away] - def[home].

    Non-FBS teams also load on shared non-FBS offense/defense columns, so their own
    effects shrink toward the non-FBS group rather than toward the FBS average.

    `cov_scale` multiplies the residual covariance. In-sample residuals understate
    forecast error even after the degrees-of-freedom correction (B01 pass 1: intervals
    covered 48.8 / 77.3 / 93.5% at nominal 50 / 80 / 95%), so the scale is tuned on
    development folds by energy score, which rewards correct width.
    """
    tr, tg = frame.train, frame.target
    teams = sorted(set(tr["home"]) | set(tr["away"]))
    idx = {t: i for i, t in enumerate(teams)}
    n_t = len(teams)
    # Columns: mu, hfa, nonfbs_off, nonfbs_def, off[0..n_t), def[0..n_t)
    n_cols = 4 + 2 * n_t

    def design(df: pd.DataFrame) -> sparse.csr_matrix:
        """Two rows per game (home scoring, away scoring); at most six nonzeros per row."""
        n = len(df)
        neutral = df["neutral"].to_numpy(bool)
        sides = (
            (df["home"].to_numpy(), df["away"].to_numpy(), df["home_fbs"].to_numpy(bool),
             df["away_fbs"].to_numpy(bool), ~neutral),
            (df["away"].to_numpy(), df["home"].to_numpy(), df["away_fbs"].to_numpy(bool),
             df["home_fbs"].to_numpy(bool), np.zeros(n, bool)),
        )
        r_idx, c_idx, vals = [], [], []
        for s, (atk, dfn, atk_fbs, dfn_fbs, home_site) in enumerate(sides):
            row = 2 * np.arange(n) + s
            atk_col = np.array([idx.get(t, -1) for t in atk])
            dfn_col = np.array([idx.get(t, -1) for t in dfn])
            for mask, col, val in (
                (np.ones(n, bool), np.zeros(n, int), 1.0),
                (home_site, np.ones(n, int), 1.0),
                (~atk_fbs, np.full(n, 2), 1.0),
                (~dfn_fbs, np.full(n, 3), -1.0),
                (atk_col >= 0, 4 + atk_col, 1.0),
                (dfn_col >= 0, 4 + n_t + dfn_col, -1.0),
            ):
                r_idx.append(row[mask])
                c_idx.append(col[mask])
                vals.append(np.full(mask.sum(), val))
        return sparse.csr_matrix(
            (np.concatenate(vals), (np.concatenate(r_idx), np.concatenate(c_idx))), shape=(2 * n, n_cols)
        )

    x = design(tr)
    y = np.column_stack([tr["hp"], tr["ap"]]).reshape(-1).astype(float)
    ref = tg["start"].min().to_datetime64()
    w = np.repeat(decay_weights(tr["start"], ref, half_life_days), 2)
    xtw = (x.T @ sparse.diags(w)).tocsr()
    gram = (xtw @ x).toarray()
    reg = np.zeros(n_cols)
    reg[4:] = penalty
    reg[2:4] = 1e-6  # group effects essentially unpenalized
    reg[:2] = 1e-9
    a = gram + np.diag(reg)
    beta = np.linalg.solve(a, xtw @ y)

    resid = (y - x @ beta).reshape(-1, 2)
    df_eff = float(np.trace(np.linalg.solve(a, gram)))
    n_obs = len(y)
    inflate = n_obs / max(n_obs - df_eff, 1.0)
    cov = weighted_cov(resid, w[::2], inflate) * cov_scale

    means = (design(tg) @ beta).reshape(-1, 2)
    return Forecast(list(tg["game_id"]), means, np.repeat(cov[None], len(tg), axis=0))


MODELS = {"hfa_only": fit_hfa_only, "elo": fit_elo, "ridge": fit_ridge}
