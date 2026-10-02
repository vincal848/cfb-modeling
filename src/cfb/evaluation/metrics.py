"""Proper scores from paired final-score samples (V01 metrics). Lower is better for all.

Every summary of a forecast comes from the same samples: winner probability is P(M>0),
margin is H-A and total is H+A (methodology §7).
"""

from __future__ import annotations

import numpy as np

INTERVAL_LEVELS = (0.5, 0.8, 0.95)


def energy_score(samples: np.ndarray, y: np.ndarray) -> float:
    """ES = E||X-y|| - 0.5 E||X-X'||, Euclidean on (home, away).

    The first term uses every draw. The second pairs the first half of the draws with
    the second half (V01 "split-pairing"), which is unbiased for independent draws.
    """
    x = samples.astype(float)
    term1 = np.linalg.norm(x - y, axis=1).mean()
    half = len(x) // 2
    term2 = np.linalg.norm(x[:half] - x[half : 2 * half], axis=1).mean()
    return float(term1 - 0.5 * term2)


def crps(draws: np.ndarray, y: float) -> float:
    """CRPS of the empirical distribution of `draws`: E|X-y| - 0.5 E|X-X'| (exact)."""
    return _crps_sorted(np.sort(draws.astype(float)), y)


def _crps_sorted(x: np.ndarray, y: float) -> float:
    n = len(x)
    term1 = np.abs(x - y).mean()
    # E|X-X'| over all ordered pairs of the empirical distribution, via order statistics.
    weights = 2 * np.arange(1, n + 1) - n - 1
    term2 = 2 * (weights * x).sum() / (n * n)
    return float(term1 - 0.5 * term2)


def win_probability(samples: np.ndarray) -> float:
    """P(home wins) with add-half smoothing so a finite sample never gives exactly 0 or 1."""
    wins = int((samples[:, 0] > samples[:, 1]).sum())
    return (wins + 0.5) / (len(samples) + 1)


def sorted_quantile(x: np.ndarray, q: float) -> float:
    """np.quantile's default (linear) method on an already sorted array."""
    pos = q * (len(x) - 1)
    lo = int(np.floor(pos))
    hi = min(lo + 1, len(x) - 1)
    return float(x[lo] + (pos - lo) * (x[hi] - x[lo]))


def score_game(samples: np.ndarray, home: int, away: int) -> dict[str, float]:
    # Sort margin and total once; CRPS, medians and interval bounds all read the sorted draws.
    s = samples.astype(float)
    margin, total = np.sort(s[:, 0] - s[:, 1]), np.sort(s[:, 0] + s[:, 1])
    y_margin, y_total = home - away, home + away
    p = win_probability(samples)
    won = 1.0 if home > away else 0.0
    out = {
        "energy_score": energy_score(samples, np.array([home, away], dtype=float)),
        "winner_log_loss": float(-np.log(p if won else 1 - p)),
        "winner_brier": float((p - won) ** 2),
        "home_win_probability": p,
        "margin_crps": _crps_sorted(margin, y_margin),
        "total_crps": _crps_sorted(total, y_total),
        "margin_abs_error": abs(sorted_quantile(margin, 0.5) - y_margin),
        "total_abs_error": abs(sorted_quantile(total, 0.5) - y_total),
        "expected_home": float(s[:, 0].mean()),
        "expected_away": float(s[:, 1].mean()),
    }
    for level in INTERVAL_LEVELS:
        lo_q, hi_q = (1 - level) / 2, 1 - (1 - level) / 2
        for name, draws, y in (("margin", margin, y_margin), ("total", total, y_total)):
            lo, hi = sorted_quantile(draws, lo_q), sorted_quantile(draws, hi_q)
            tag = f"{name}_{int(level * 100)}"
            out[f"{tag}_covered"] = float(lo <= y <= hi)
            out[f"{tag}_width"] = float(hi - lo)
    return out
