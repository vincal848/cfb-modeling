"""M01 market math on SYNTHETIC prices and outcomes (fabricated)."""

import numpy as np
from scipy.special import expit, logit

from cfb.markets import consensus_lines, model_probabilities, outcomes, trade_pnl


def world(seed, n=20000, market_noise=0.0, model_noise=0.0):
    rng = np.random.default_rng(seed)
    p = rng.uniform(0.2, 0.8, n)
    y = (rng.uniform(size=n) < p).astype(float)
    market = expit(logit(p) + rng.normal(0, market_noise, n)) if market_noise else p
    model = expit(logit(p) + rng.normal(0, model_noise, n))
    return model, market, y


def test_null_loses_money():
    # Efficient market, model is the market plus noise: every rule must lose after costs.
    model, market, y = world(1, model_noise=0.5)
    for w in (0.25, 0.5, 1.0):
        pnl = trade_pnl(model, market, y, w, 0.02)
        assert np.nansum(~np.isnan(pnl)) > 500
        assert np.nanmean(pnl) < 0


def test_power_finds_real_edge():
    # Noisy market, model knows the truth: trading on the model must profit.
    model, market, y = world(2, market_noise=0.5)
    pnl = trade_pnl(model, market, y, 1.0, 0.04)
    assert np.nanmean(pnl) > 0.03


def test_consensus_and_outcomes():
    games = [{"id": 7, "lines": [
        {"spread": 3.0, "overUnder": 50.0, "homeMoneyline": 130, "awayMoneyline": -150},
        {"spread": 4.0, "overUnder": 52.0, "homeMoneyline": 150, "awayMoneyline": 150},  # not two-sided
        {"spread": 3.5, "overUnder": None, "homeMoneyline": None, "awayMoneyline": None}]}]
    row = consensus_lines(games).iloc[0]
    assert row.game_id == "cfbd-game-7" and row.spread == 3.5 and row.total == 51.0
    assert abs(row.p_win_market - (100 / 230) / (100 / 230 + 0.6)) < 1e-12
    ys = outcomes(np.array([20, 20]), np.array([23, 24]), np.array([3.0, 3.5]), np.array([43.0, 40.0]))
    assert np.isnan(ys["cover"][0]) and ys["cover"][1] == 0.0 and np.isnan(ys["over"][0]) and ys["over"][1] == 1.0


def test_model_probabilities_symmetry():
    means = np.array([[28.0, 28.0]])
    covs = np.array([[[121.0, 0.0], [0.0, 121.0]]])
    p = model_probabilities(means, covs, np.array([0.0]), np.array([56.0]))
    assert all(abs(v[0] - 0.5) < 1e-12 for v in p.values())
