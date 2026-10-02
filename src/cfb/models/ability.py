"""P04: skill-player effectiveness and development (methodology §4).

For one opportunity category (passing per dropback, rushing per carry, receiving per
target), a player's observed season mean EPA per opportunity is

    y_it = a_it + e_it,  e_it ~ N(0, sigma2 / n_it)

with latent ability following the methodology's development equation

    a_i,first ~ N(mu_g, tau2)                         (new player, position group g)
    a_it = mu_g + rho * (a_i,t-1 - mu_g) + eta,  eta ~ N(0, q)   per elapsed season.

sigma2 is the pooled within-player-season variance of play EPA, so the measurement noise
of a season mean is known from its opportunity count. (mu_g, tau2, rho, q) are fit by
maximizing the marginal likelihood of training seasons, filtering each player forward
in time only. Forecasts for a season use only earlier seasons; a player with no history
gets the pooled prior N(mu_g, tau2), the widest uncertainty (new players receive pooled
uncertainty). rho is constrained to [0, 1] and variances to be positive.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import expit

GROUPS = ("QB", "RB", "WR", "TE", "OTHER")


def position_group(position: str | None) -> str:
    p = (position or "").upper()
    if p == "QB":
        return "QB"
    if p in ("RB", "FB", "HB", "TB"):
        return "RB"
    if p in ("WR",):
        return "WR"
    if p in ("TE",):
        return "TE"
    return "OTHER"


@dataclass
class AbilityParams:
    mu: dict[str, float]
    tau2: float
    rho: float
    q: float
    sigma2: float
    converged: bool = True


def _unpack(theta: np.ndarray, groups: list[str], sigma2: float) -> AbilityParams:
    mu = dict(zip(groups, theta[: len(groups)], strict=True))
    tau2, q = np.exp(theta[len(groups)]), np.exp(theta[len(groups) + 1])
    rho = expit(theta[len(groups) + 2])  # logistic, without overflow at large arguments
    return AbilityParams(mu, float(tau2), float(rho), float(q), sigma2)


def _filter(seq: pd.DataFrame, p: AbilityParams) -> tuple[float, list[tuple[float, float]]]:
    """Log-likelihood of one player's seasons (sorted) and the one-step predictive
    (mean, ability variance) for each season."""
    ll, preds = 0.0, []
    mean = var = None
    last = None
    for r in seq.itertuples(index=False):
        mu = p.mu[r.group]
        if mean is None:
            m, v = mu, p.tau2
        else:
            gap = r.season - last
            m, v = mean, var
            for _ in range(max(gap, 1)):
                m = mu + p.rho * (m - mu)
                v = p.rho**2 * v + p.q
        preds.append((m, v))
        obs_var = p.sigma2 / r.n
        s = v + obs_var
        ll += -0.5 * (np.log(2 * np.pi * s) + (r.y - m) ** 2 / s)
        k = v / s
        mean, var = m + k * (r.y - m), (1 - k) * v
        last = r.season
    return ll, preds


def _grid(train: pd.DataFrame, groups: list[str]):
    """Players x seasons arrays for the vectorized likelihood. A player's group is his most
    frequent group in the data passed in."""
    seasons = np.arange(train["season"].min(), train["season"].max() + 1)
    players = train["athlete_id"].unique()
    pi = {a: i for i, a in enumerate(players)}
    y = np.zeros((len(players), len(seasons)))
    n = np.ones_like(y)
    obs = np.zeros_like(y, dtype=bool)
    rows = [pi[a] for a in train["athlete_id"]]
    cols = (train["season"].to_numpy() - seasons[0]).astype(int)
    y[rows, cols], n[rows, cols], obs[rows, cols] = train["y"].to_numpy(), train["n"].to_numpy(), True
    main_group = train.groupby("athlete_id")["group"].agg(lambda s: s.value_counts().index[0])
    gidx = np.array([groups.index(main_group[a]) for a in players])
    return y, n, obs, gidx


def _loglik(theta: np.ndarray, groups: list[str], sigma2: float, grid) -> float:
    """Total log-likelihood over all players at once; seasons step forward together and a
    player's unobserved seasons apply the transition without an update."""
    y, n, obs, gidx = grid
    p = _unpack(theta, groups, sigma2)
    mu = np.array([p.mu[g] for g in groups])[gidx]
    started = np.zeros(len(gidx), dtype=bool)
    m = mu.copy()
    v = np.full(len(gidx), p.tau2)
    ll = 0.0
    for s in range(y.shape[1]):
        if s:  # step started players one season forward
            m = np.where(started, mu + p.rho * (m - mu), m)
            v = np.where(started, p.rho**2 * v + p.q, v)
        o = obs[:, s]
        new = o & ~started
        m = np.where(new, mu, m)
        v = np.where(new, p.tau2, v)
        tot = v + sigma2 / n[:, s]
        r = y[:, s] - m
        ll += float(np.sum(np.where(o, -0.5 * (np.log(2 * np.pi * tot) + r**2 / tot), 0.0)))
        k = np.where(o, v / tot, 0.0)
        m, v = m + k * r, (1 - k) * v
        started |= o
    return ll


def fit_ability(train: pd.DataFrame, sigma2: float) -> AbilityParams:
    """`train`: athlete_id, season, group, y (mean EPA per opportunity), n (opportunities)."""
    groups = sorted(train["group"].unique())
    grid = _grid(train, groups)
    w = train["n"].to_numpy(float)
    start_mu = [float(np.average(train.loc[train["group"] == g, "y"], weights=train.loc[train["group"] == g, "n"]))
                for g in groups]
    theta0 = np.array([*start_mu, np.log(max(np.average((train["y"] - np.average(train["y"], weights=w)) ** 2,
                                                        weights=w), 1e-4)), np.log(1e-3), 0.0])

    def nll(theta):
        return -_loglik(theta, groups, sigma2, grid)

    res = minimize(nll, theta0, method="L-BFGS-B", options={"maxiter": 500})
    out = _unpack(res.x, groups, sigma2)
    out.converged = bool(res.success)
    for g in GROUPS:  # groups absent from training fall back to the pooled mean
        out.mu.setdefault(g, float(np.average(train["y"], weights=w)))
    return out


def predict(history: pd.DataFrame, targets: pd.DataFrame, p: AbilityParams) -> pd.DataFrame:
    """Predictive mean and ability variance for each target row (athlete_id, season, group)
    from that athlete's history rows with season < target season."""
    rows = []
    hist = {a: g.sort_values("season") for a, g in history.groupby("athlete_id")}
    for t in targets.itertuples(index=False):
        h = hist.get(t.athlete_id)
        h = h[h["season"] < t.season] if h is not None else None
        mu = p.mu.get(t.group, p.mu.get("OTHER"))
        if h is None or h.empty:
            rows.append((mu, p.tau2, False))
            continue
        _, preds = _filter(h, p)
        # Posterior after the last observed season, then step to the target season.
        last = h.iloc[-1]
        m_pred, v_pred = preds[-1]
        s = v_pred + p.sigma2 / last["n"]
        k = v_pred / s
        m, v = m_pred + k * (last["y"] - m_pred), (1 - k) * v_pred
        for _ in range(max(int(t.season - last["season"]), 1)):
            m = mu + p.rho * (m - mu)
            v = p.rho**2 * v + p.q
        rows.append((m, v, True))
    out = targets.copy()
    out["pred_mean"], out["pred_var"], out["has_history"] = zip(*rows, strict=True) if rows else ([], [], [])
    return out


def gaussian_log_score(y, n, mean, var, sigma2) -> np.ndarray:
    """-log predictive density of an observed season mean with n opportunities."""
    s = np.asarray(var) + sigma2 / np.asarray(n)
    return 0.5 * (np.log(2 * np.pi * s) + (np.asarray(y) - np.asarray(mean)) ** 2 / s)
