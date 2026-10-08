"""K04 on SYNTHETIC ladders (fabricated): nothing is found when the market is right; planted key mass is found."""

import numpy as np
import pandas as pd

from cfb.evaluation import k04


def test_trade_pnl_and_fees():
    df = pd.DataFrame({"game_id": ["a", "b", "c"], "block": "w", "q": [0.20, 0.20, 0.20],
                       "ask_lo": [0.50, 0.50, np.nan], "bid_hi": [0.42, 0.45, 0.42], "hit": [True, False, True]})
    t = k04.trades(df)
    assert list(t["game_id"]) == ["a", "b"]  # c has no quote
    fees = 0.0175 + 0.0175  # one cent-rounded fee per leg near 50c
    assert abs(t["pnl"].iloc[0] - (1 - 0.08 - fees)) < 1e-9
    assert abs(t["pnl"].iloc[1] - (0 - 0.05 - fees)) < 1e-9


def test_crossed_ladder_is_no_trade():
    df = pd.DataFrame({"game_id": ["a"], "block": "w", "q": [0.5], "ask_lo": [0.40], "bid_hi": [0.45], "hit": [True]})
    assert k04.trades(df).empty


def test_kernel_sees_the_spike():
    rng = np.random.default_rng(0)
    m = rng.choice(k04.MARGINS, size=4000, p=k04.spiked_pmf(3.0, 13, 2.0))
    q = k04.kernel_q(np.full(4000, 3.0), m, 1.0, np.array([3.0, 3.0]), np.array([3, 4]))
    assert q[0] > 1.5 * q[1]


def test_efficient_market_finds_nothing():
    r = k04.run_sim(market_boost=2.0, true_boost=2.0, seed=1)
    assert not r["real"]["passed"] and not r["placebo"]["passed"]


def test_planted_key_mass_is_found():
    r = k04.run_sim(market_boost=1.0, true_boost=3.0, seed=2, n_train=6000, n_test=2500)
    assert r["gate_passed"] and r["real"]["passed"] and not r["placebo"]["passed"]


def test_no_key_mass_finds_nothing():
    r = k04.run_sim(market_boost=1.0, true_boost=1.0, seed=3)
    assert not r["real"]["passed"]
