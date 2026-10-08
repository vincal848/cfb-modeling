"""M01 market math: consensus closing prices from cached CFBD lines, closed-form model
probabilities from a Gaussian score predictive, and Kalshi-style trade P&L.

CFBD `spread` is the home line (negative = home favored), so the home side covers when
home - away + spread > 0. Every price here is a probability in (0, 1)."""

from __future__ import annotations

from statistics import median

import numpy as np
import pandas as pd
from scipy.special import expit, logit
from scipy.stats import norm

from cfb.canonical.games import game_id

FEE_RATE = 0.07  # Kalshi taker fee: ceil(0.07 * C * P * (1 - P)) dollars per order
HALF_SPREAD = 0.01  # ponytail: flat 1c over fair; replace with recorded Kalshi asks once logged
MARKETS = ("win", "cover", "over")


def american_to_prob(ml: float) -> float:
    return -ml / (-ml + 100) if ml < 0 else 100 / (ml + 100)


def consensus_lines(games: list[dict]) -> pd.DataFrame:
    """One row per game with any line: median closing home spread, total, and de-vigged
    home moneyline probability across providers (NaN when no provider has one)."""
    rows = []
    for g in games:
        lines = g.get("lines") or []
        spread = [ln["spread"] for ln in lines if ln.get("spread") is not None]
        total = [ln["overUnder"] for ln in lines if ln.get("overUnder") is not None]
        p_home = []
        for ln in lines:
            h, a = ln.get("homeMoneyline"), ln.get("awayMoneyline")
            if h is None or a is None or h == 0 or a == 0:
                continue
            ph, pa = american_to_prob(h), american_to_prob(a)
            if 1.0 < ph + pa < 1.25:  # a real two-sided price; anything else is a data error
                p_home.append(ph / (ph + pa))
        if spread or total or p_home:
            rows.append({"game_id": game_id(g["id"]),
                         "spread": median(spread) if spread else np.nan,
                         "total": median(total) if total else np.nan,
                         "p_win_market": median(p_home) if p_home else np.nan})
    return pd.DataFrame(rows, columns=["game_id", "spread", "total", "p_win_market"])


def model_probabilities(means: np.ndarray, covs: np.ndarray, spread: np.ndarray,
                        total: np.ndarray) -> dict[str, np.ndarray]:
    """P(home wins), P(home covers), P(over) from (home, away) means (n, 2) and covariances (n, 2, 2)."""
    margin = means[:, 0] - means[:, 1]
    margin_sd = np.sqrt(covs[:, 0, 0] + covs[:, 1, 1] - 2 * covs[:, 0, 1])
    points = means.sum(axis=1)
    points_sd = np.sqrt(covs[:, 0, 0] + covs[:, 1, 1] + 2 * covs[:, 0, 1])
    return {"win": norm.cdf(margin / margin_sd),
            "cover": norm.cdf((margin + spread) / margin_sd),
            "over": norm.cdf((points - total) / points_sd)}


def outcomes(home: np.ndarray, away: np.ndarray, spread: np.ndarray, total: np.ndarray) -> dict[str, np.ndarray]:
    """1.0 / 0.0 per market, NaN on a push (no trade settles)."""
    def binary(x: np.ndarray) -> np.ndarray:
        return np.where(x > 0, 1.0, np.where(x < 0, 0.0, np.nan))
    return {"win": binary(home - away), "cover": binary(home - away + spread),
            "over": binary(home + away - total)}


def fee(price: np.ndarray) -> np.ndarray:
    return FEE_RATE * price * (1 - price)


def trade_pnl(p_model: np.ndarray, p_market: np.ndarray, y: np.ndarray, w: float, t: float) -> np.ndarray:
    """Per-game P&L of one contract (NaN = no trade). Buys YES or NO at fair + HALF_SPREAD
    when the blended probability beats price plus fee by at least `t`."""
    eps = 1e-6
    p = expit(w * logit(np.clip(p_model, eps, 1 - eps)) + (1 - w) * logit(np.clip(p_market, eps, 1 - eps)))
    yes, no = p_market + HALF_SPREAD, 1 - p_market + HALF_SPREAD
    buy_yes = p - yes - fee(yes) >= t
    buy_no = (1 - p) - no - fee(no) >= t
    pnl = np.full(len(p), np.nan)
    pnl[buy_yes] = (y - yes - fee(yes))[buy_yes]
    pnl[buy_no] = ((1 - y) - no - fee(no))[buy_no]
    pnl[np.isnan(y)] = np.nan
    return pnl
