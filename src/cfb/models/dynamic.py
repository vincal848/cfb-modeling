"""B02: dynamic team-only strength as a Kalman filter on paired final scores.

Observation for each game (the same parameterization as the B01 ridge):

    home = mu + hfa*site + off[home] - def[away] + g_off*[home non-FBS] - g_def*[away non-FBS] + e
    away = mu            + off[away] - def[home] + g_off*[away non-FBS] - g_def*[home non-FBS] + e

with e ~ N(0, sigma^2 I). Team effects evolve as a random walk with variance `q_week` per
calendar week in season, and between seasons shrink by `rho` with innovation
(1 - rho^2) * s0^2, which keeps a team's long-run spread at the prior s0. A team enters
the state at its first game with prior N(0, s0^2). League effects (mu, hfa, group
effects) get a small fixed weekly innovation.

The filter only ever moves forward: states are filtered, never smoothed (config
`team_state_estimator`). Predictions apply the pending weekly or off-season step on the
relevant entries without changing the state. The predictive covariance includes state
uncertainty, so intervals widen for teams with little evidence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

N_GLOBAL = 4  # mu, hfa, g_off, g_def
GLOBAL_PRIOR_MEAN = np.array([27.0, 3.0, 0.0, 0.0])
GLOBAL_PRIOR_SD = np.array([5.0, 2.0, 10.0, 10.0])
GLOBAL_WEEKLY_Q = 0.01


@dataclass
class DynamicParams:
    q_week: float = 1.0
    rho: float = 0.75
    s0: float = 7.0
    sigma: float = 11.5


@dataclass
class TeamFilter:
    """Filtered state over league effects and every team seen so far."""

    params: DynamicParams
    capacity: int
    x: np.ndarray = field(init=False)
    p: np.ndarray = field(init=False)
    index: dict[str, int] = field(default_factory=dict)
    period: tuple[int, str, int] | None = None  # (season, season_type, week) last processed
    processed: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        n = N_GLOBAL + 2 * self.capacity
        self.x = np.zeros(n)
        self.p = np.zeros((n, n))
        self.x[:N_GLOBAL] = GLOBAL_PRIOR_MEAN
        self.p[:N_GLOBAL, :N_GLOBAL] = np.diag(GLOBAL_PRIOR_SD**2)

    # -- layout ---------------------------------------------------------------
    def _slots(self, team: str) -> tuple[int, int]:
        i = self.index[team]
        return N_GLOBAL + 2 * i, N_GLOBAL + 2 * i + 1  # off, def

    def _activate(self, team: str) -> None:
        if team in self.index:
            return
        if len(self.index) >= self.capacity:
            raise RuntimeError("team capacity exceeded")
        self.index[team] = len(self.index)
        o, d = self._slots(team)
        self.p[[o, d], [o, d]] = self.params.s0**2

    def _team_slots(self) -> np.ndarray:
        return np.arange(N_GLOBAL, N_GLOBAL + 2 * len(self.index))

    # -- time steps -------------------------------------------------------------
    def _step(self, new_period: tuple[int, str, int]) -> None:
        if self.period is None or new_period == self.period:
            self.period = new_period
            return
        slots = self._team_slots()
        g = np.arange(N_GLOBAL)
        self.p[g, g] += GLOBAL_WEEKLY_Q
        if new_period[0] != self.period[0]:  # off-season: shrink toward 0, restore spread
            rho = self.params.rho
            self.x[slots] *= rho
            self.p[slots, :] *= rho
            self.p[:, slots] *= rho
            self.p[slots, slots] += (1 - rho**2) * self.params.s0**2
        else:
            self.p[slots, slots] += self.params.q_week
        self.period = new_period

    # -- observation --------------------------------------------------------------
    def _design(
        self, home: str, away: str, neutral: bool, home_fbs: bool, away_fbs: bool
    ) -> list[list[tuple[int, float]]]:
        rows = []
        for atk, dfn, atk_fbs, dfn_fbs, site in ((home, away, home_fbs, away_fbs, not neutral),
                                                  (away, home, away_fbs, home_fbs, False)):
            r = [(0, 1.0)]
            if site:
                r.append((1, 1.0))
            if not atk_fbs:
                r.append((2, 1.0))
            if not dfn_fbs:
                r.append((3, -1.0))
            r.append((self._slots(atk)[0], 1.0))
            r.append((self._slots(dfn)[1], -1.0))
            rows.append(r)
        return rows

    def update(self, g) -> None:
        self._step((g.season, g.season_type, g.week))
        self._activate(g.home)
        self._activate(g.away)
        rows = self._design(g.home, g.away, g.neutral, g.home_fbs, g.away_fbs)
        idx = sorted({i for r in rows for i, _ in r})
        pos = {i: k for k, i in enumerate(idx)}
        h = np.zeros((2, len(idx)))
        for k, r in enumerate(rows):
            for i, v in r:
                h[k, pos[i]] += v
        ph = self.p[:, idx] @ h.T  # n x 2
        s = h @ ph[idx, :] + np.eye(2) * self.params.sigma**2
        k_gain = ph @ np.linalg.inv(s)
        resid = np.array([g.hp, g.ap], float) - h @ self.x[idx]
        self.x += k_gain @ resid
        self.p -= k_gain @ s @ k_gain.T
        self.processed.add(g.game_id)
        if len(self.processed) % 200 == 0:  # rank-2 updates drift slightly from symmetry
            self.p = (self.p + self.p.T) / 2

    def predict(self, g) -> tuple[np.ndarray, np.ndarray]:
        """Predictive mean and covariance of (home, away) for a game not yet observed.

        Builds the few state entries the game loads on, applies the pending weekly or
        off-season step to them, and gives unseen teams their prior.
        """
        period = (g.season, g.season_type, g.week)
        season_change = self.period is not None and g.season != self.period[0]
        week_change = self.period is not None and period != self.period
        rows = [
            [(0, 1.0)] + ([(1, 1.0)] if not g.neutral else [])
            + ([(2, 1.0)] if not g.home_fbs else []) + ([(3, -1.0)] if not g.away_fbs else [])
            + [((g.home, 0), 1.0), ((g.away, 1), -1.0)],
            [(0, 1.0)]
            + ([(2, 1.0)] if not g.away_fbs else []) + ([(3, -1.0)] if not g.home_fbs else [])
            + [((g.away, 0), 1.0), ((g.home, 1), -1.0)],
        ]
        keys = sorted({k for r in rows for k, _ in r}, key=str)
        pos = {k: a for a, k in enumerate(keys)}
        n = len(keys)
        is_team = np.array([not isinstance(k, int) for k in keys])
        unseen = np.array([not isinstance(k, int) and k[0] not in self.index for k in keys])

        state = [k if isinstance(k, int) else self._slots(k[0])[k[1]] for k in keys if
                 isinstance(k, int) or k[0] in self.index]
        known = np.flatnonzero(~unseen)
        xm, pm = np.zeros(n), np.zeros((n, n))
        xm[known] = self.x[state]
        pm[np.ix_(known, known)] = self.p[np.ix_(state, state)]

        if season_change or week_change:
            glob = np.flatnonzero(~is_team)
            pm[glob, glob] += GLOBAL_WEEKLY_Q
        team = np.flatnonzero(is_team & ~unseen)
        if season_change:
            rho = self.params.rho
            xm[team] *= rho
            pm[team, :] *= rho
            pm[:, team] *= rho
            pm[team, team] += (1 - rho**2) * self.params.s0**2
        elif week_change:
            pm[team, team] += self.params.q_week
        new = np.flatnonzero(unseen)
        pm[new, new] = self.params.s0**2  # prior for a team with no games yet

        h = np.zeros((2, n))
        for row, r in enumerate(rows):
            for k, v in r:
                h[row, pos[k]] += v
        return h @ xm, h @ pm @ h.T + np.eye(2) * self.params.sigma**2


def ids_digest(game_ids) -> str:
    return hashlib.sha256("\n".join(sorted(game_ids)).encode()).hexdigest()


def filter_and_predict(
    history: pd.DataFrame, folds: list[tuple[str, str, pd.DataFrame]], params: DynamicParams,
    result_lag_hours: float,
) -> list[tuple[str, list[str], np.ndarray, np.ndarray]]:
    """One forward pass. `folds` are (cutoff ISO, digest of the admitted result game IDs,
    target games), sorted by cutoff. Before each fold's predictions the filter must have
    absorbed exactly that fold's admitted results; anything else is an error, never a
    silent leak."""
    hist = history.assign(available=history["start"] + pd.Timedelta(hours=result_lag_hours))
    hist = hist.sort_values(["available", "game_id"]).reset_index(drop=True)
    teams = set(hist["home"]) | set(hist["away"])
    for _, _, tg in folds:
        teams |= set(tg["home"]) | set(tg["away"])
    filt = TeamFilter(params, capacity=len(teams))
    out = []
    i = 0
    rows = list(hist.itertuples(index=False))
    for cutoff, admitted_digest, target in folds:
        cut = pd.Timestamp(cutoff).tz_convert(None) if pd.Timestamp(cutoff).tzinfo else pd.Timestamp(cutoff)
        while i < len(rows) and rows[i].available <= cut:
            filt.update(rows[i])
            i += 1
        if ids_digest(filt.processed) != admitted_digest:
            raise RuntimeError(f"fold {cutoff}: filter state differs from snapshot "
                               f"({len(filt.processed)} results absorbed)")
        means, covs = [], []
        for g in target.itertuples(index=False):
            m, c = filt.predict(g)
            means.append(m)
            covs.append(c)
        out.append((cutoff, list(target["game_id"]), np.array(means), np.array(covs)))
    return out
