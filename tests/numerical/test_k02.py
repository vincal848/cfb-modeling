import numpy as np
import pandas as pd

from cfb.evaluation import k02


def synth(kalshi_is_noisy: bool, n=3000, seed=1) -> dict[int, pd.DataFrame]:
    """Truth = book. Power: Kalshi = truth + noise. Null: truth = Kalshi, book = Kalshi + noise."""
    rng = np.random.default_rng(seed)
    base = rng.uniform(0.15, 0.85, n)
    noise = rng.normal(0, 0.06, n)
    book, mid = (base, np.clip(base + noise, 0.05, 0.95)) if kalshi_is_noisy else (np.clip(base + noise, 0.05, 0.95), base)
    truth = base if kalshi_is_noisy else mid
    week = rng.integers(1, 15, n)
    df = pd.DataFrame({"block": [f"regular-{w}" for w in week], "fit": week <= 7,
                       "y": (rng.uniform(size=n) < truth).astype(float), "book": book, "mid": mid,
                       "bid": mid - 0.01, "ask": mid + 0.01, "ref": mid})
    return {1: df}


def test_power_book_is_truth():
    r = k02.select_and_validate(synth(True))
    assert r["passed"] and r["validation"]["lo"] > 0


def test_null_kalshi_is_truth():
    r = k02.select_and_validate(synth(False))
    assert not r.get("passed")


def test_permuted_book_does_not_pass():
    r = k02.select_and_validate(k02.permuted(synth(True)))
    assert not r.get("passed")


def test_logit_fit_recovers_coefficients():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(20000, 2))
    y = (rng.uniform(size=20000) < 1 / (1 + np.exp(-(0.3 + x @ [1.0, 0.0])))).astype(float)
    b, se = k02.logit_fit(x, y)
    assert abs(b[1] - 1) < 4 * se[1] and abs(b[2]) < 4 * se[2]


def test_build_picks_home_market_and_quotes():
    mk = lambda t, team, home: {"ticker": t, "event_ticker": "KXNCAAFGAME-25SEP06AAAABBB", "title": "Aaa at Bbb Winner?",
                                "yes_sub_title": team, "result": "yes"}
    markets = [mk("a", "Aaa", 0), mk("b", "Bbb", 1)]
    sched = [{"game_id": "g1", "home_team_id": "B", "away_team_id": "A", "season_type": "regular", "week": 2,
              "start_utc": "2025-09-06T23:00:00+00:00"}]
    k = pd.Timestamp("2025-09-06T23:00:00Z").timestamp()
    candles = [{"end_period_ts": k - 25 * 3600, "yes_bid": {"close": "0.50"}, "yes_ask": {"close": "0.54"}},
               {"end_period_ts": k - 3600, "yes_bid": {"close": "0.60"}, "yes_ask": {"close": "0.62"}}]
    frames, c = k02.build(markets, lambda m: candles if m["ticker"] == "b" else [], sched,
                          {"g1": {"home_points": 30, "away_points": 10}}, {"g1": 0.7},
                          {"A": {"aaa"}, "B": {"bbb"}})
    assert c["mapped"] == 1 and c["ambiguous_side"] == 0
    assert frames[24].iloc[0]["mid"] == 0.52 and frames[1].iloc[0]["mid"] == 0.61 and frames[1].iloc[0]["y"] == 1
