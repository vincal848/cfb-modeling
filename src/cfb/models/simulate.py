"""Seeded paired final-score sampling (V01 monte_carlo).

Each game's draws depend only on a seed derived from the protocol version, model ID,
game ID and horizon, so games can be simulated in any order on any number of workers
and give identical results. Hyperparameter variants of one model share the model ID,
which gives them common random numbers and keeps tuning comparisons low-noise.
"""

from __future__ import annotations

import hashlib

import numpy as np

MAX_TIE_REDRAWS = 1000


def derive_seed(root_seed: int, protocol_version: str, model_id: str, game_id: str, horizon: int) -> int:
    key = f"{root_seed}|{protocol_version}|{model_id}|{game_id}|{horizon}".encode()
    return int.from_bytes(hashlib.sha256(key).digest()[:8], "little")


def sample_scores(mean: np.ndarray, cov: np.ndarray, n: int, seed: int) -> np.ndarray:
    """n paired nonnegative integer final scores (home, away) with no ties.

    Draws a bivariate normal, rounds to the nearest integer and floors at zero. The
    baselines are fit on final scores, so tied draws are redrawn: the sample is
    conditioned on unequal final scores (methodology §7) rather than given an
    overtime kernel on top of final-score parameters.
    """
    rng = np.random.Generator(np.random.PCG64(seed))
    chol = np.linalg.cholesky(cov)

    def draw(k: int) -> np.ndarray:
        x = mean + rng.standard_normal((k, 2)) @ chol.T
        return np.maximum(np.rint(x), 0).astype(np.int16)

    out = draw(n)
    for _ in range(MAX_TIE_REDRAWS):
        tied = np.flatnonzero(out[:, 0] == out[:, 1])
        if tied.size == 0:
            return out
        out[tied] = draw(tied.size)
    raise RuntimeError("could not draw untied scores; the score distribution is degenerate")
