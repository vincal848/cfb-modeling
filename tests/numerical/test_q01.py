"""Q01 on SYNTHETIC tapes (fabricated): a fair martingale market gives a maker no edge; a noisy market around a known anchor does."""

import numpy as np
import pandas as pd

from cfb.evaluation import q01


def tp(rows):
    return pd.DataFrame(rows, columns=["ts", "yes", "n"])


def test_fill_needs_a_strict_trade_through_of_size_at_least_one():
    t = tp([(1, 0.40, 5), (2, 0.39, 0.5), (3, 0.38, 2), (4, 0.60, 3)])
    assert q01.first_fill(t, "yes", 0.40, 0, 10) == 3.0  # 0.40 is not through 0.40; 0.5 contracts is too small
    assert q01.first_fill(t, "yes", 0.40, 0, 3) is None  # window is half open
    assert q01.first_fill(t, "no", 0.40, 0, 10) is None  # yes 0.60 is not strictly above 1 - 0.40
    assert q01.first_fill(t, "no", 0.41, 0, 10) == 4.0  # yes 0.60 > 1 - 0.41 = 0.59


def test_fair_value_uses_only_pre_kickoff_trades():
    t = tp([(100, 0.50, 1), (200, 0.55, 1)])
    assert q01.fair_after(t, 50, 2, start=1000) == 0.50  # 50 + 120 = 170 -> last trade at 100
    assert np.isnan(q01.fair_after(t, 50, 2, start=150))  # the horizon passes kickoff


def test_fill_row_pnl_and_drift_signs():
    t = tp([(100, 0.50, 1)])
    r = q01.fill_row("g", "w", "Q1", "yes", 0.40, 1.0, t, 0, 10_000)
    assert abs(r["pnl"] - (1 - 0.40 - q01.maker_fee(0.40))) < 1e-12 and abs(r["adv5"] - 0.10) < 1e-12
    r = q01.fill_row("g", "w", "Q1", "no", 0.40, 0.0, t, 0, 10_000)
    assert abs(r["adv5"] - (0.50 - 0.40)) < 1e-12  # NO is worth 1 - 0.50 = 0.50


def run(martingale: bool, seed: int, n: int = 600) -> dict:
    games, tapes = q01.simulate_world(n, seed, martingale)
    return q01.summarize(q01.winner_fills(games, tapes, "anchor", "Q1"))


def test_martingale_market_gives_the_maker_no_edge():
    s = run(True, 1)
    assert s["fills"] > 100 and s["hi"] < 0.02 and s["lo"] < 0


def test_noisy_market_around_a_known_anchor_is_found():
    s = run(False, 2)
    assert s["lo"] > 0 and s["p"] < 0.001
