"""G01: dynamic joint-score expert (methodology §7, expert 1).

Regulation scores are simulated from a correlated count model,

    G ~ Gamma(k, 1/k)                    shared game pace (mean 1)
    E_h, E_a ~ Gamma(r, 1/r)             team-specific overdispersion (mean 1)
    H_reg ~ Poisson(mu_h * G * E_h),  A_reg ~ Poisson(mu_a * G * E_a)

with (mu_h, mu_a) drawn per simulation from the B02 Kalman filter's state distribution
(mean and state covariance, i.e. predictive covariance minus observation noise), refit on
regulation scores (line scores), so team-strength uncertainty is propagated (methodology
§9) and regulation parameters are learned from regulation labels, not final scores. Counts
are an approximation to football scoring (no key numbers); the methodology says so.

Ties after regulation get an overtime kernel: a (home, away) overtime point pair drawn
from earlier games that went to overtime under the same rules regime (registry periods
2014-2018, 2019-2020, 2021+), orientation randomized. Empirical overtime pairs are never
equal, so final scores never tie. When a regime has too few earlier overtime games, all
earlier overtime games are used and the forecast is flagged.
"""

from __future__ import annotations

import numpy as np

OT_REGIMES = ((2014, 2018), (2019, 2020), (2021, 2100))
MIN_REGIME_OT_GAMES = 30


def regime(season: int) -> int:
    for i, (lo, hi) in enumerate(OT_REGIMES):
        if lo <= season <= hi:
            return i
    raise ValueError(f"no overtime regime for {season}")


def ot_kernel(ot_games: list[tuple[int, int, int]], season: int) -> tuple[np.ndarray, bool]:
    """Overtime point pairs for `season` from earlier games: (season, home_ot, away_ot).
    Returns the pairs and whether the regime fallback (all earlier regimes) was used."""
    earlier = [(s, h, a) for s, h, a in ot_games if s < season and h != a]
    same = np.array([(h, a) for s, h, a in earlier if regime(s) == regime(season)], dtype=np.int16).reshape(-1, 2)
    if len(same) >= MIN_REGIME_OT_GAMES:
        return same, False
    pooled = np.array([(h, a) for _, h, a in earlier], dtype=np.int16).reshape(-1, 2)
    if len(pooled) == 0:
        raise ValueError(f"no earlier overtime games before {season}")
    return pooled, True


def sample_joint(mu_h: float, mu_a: float, pace_k: float, disp_r: float, ot_pairs: np.ndarray,
                 n: int, seed: int, state_cov: np.ndarray | None = None) -> np.ndarray:
    """n paired nonnegative integer final scores (home, away) with no ties. With
    `state_cov`, each draw first samples its regulation means from N((mu_h, mu_a), state_cov)."""
    rng = np.random.Generator(np.random.PCG64(seed))
    if state_cov is not None:
        w, v = np.linalg.eigh((state_cov + state_cov.T) / 2)
        root = v * np.sqrt(np.clip(w, 0, None))
        mus = np.array([mu_h, mu_a]) + rng.standard_normal((n, 2)) @ root.T
    else:
        mus = np.tile([mu_h, mu_a], (n, 1))
    mus = np.maximum(mus, 0.1)
    g = rng.gamma(pace_k, 1.0 / pace_k, n)
    e = rng.gamma(disp_r, 1.0 / disp_r, (n, 2))
    lam = mus * g[:, None] * e
    out = rng.poisson(lam).astype(np.int16)
    tied = np.flatnonzero(out[:, 0] == out[:, 1])
    if tied.size:
        pick = ot_pairs[rng.integers(0, len(ot_pairs), tied.size)]
        swap = rng.random(tied.size) < 0.5
        pick = np.where(swap[:, None], pick[:, ::-1], pick)
        out[tied] += pick
    return out
