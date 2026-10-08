"""K03 rule, fee and event filters on SYNTHETIC markets (fabricated)."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd

from cfb.evaluation.k03 import (
    event_row,
    events,
    fee,
    frame,
    permuted,
    rule_pnl,
    select_and_validate,
)


def test_fee_rounds_per_order():
    # 100 contracts at 95c: 0.07 * 100 * 0.95 * 0.05 = $0.3325 -> $0.34 per order.
    assert abs(fee(np.array([0.95]))[0] - 0.0034) < 1e-12
    assert abs(fee(np.array([0.50]))[0] - 0.0175) < 1e-12


def test_events_keep_only_clean_pairs():
    mk = lambda ev, t, r: {"event_ticker": ev, "ticker": t, "result": r, "expected_expiration_time": "2026-01-02T03:00:00Z"}
    ms = [mk("E1", "E1-B", "yes"), mk("E1", "E1-A", "no"), mk("E2", "E2-A", "no"), mk("E2", "E2-B", "no"),
          mk("E3", "E3-A", "yes")]
    evs, drops = events(ms)
    assert [(e, m["ticker"]) for e, m, _ in evs] == [("E1", "E1-A")]
    assert evs[0][2] == datetime(2026, 1, 2, 0, 0, tzinfo=UTC)
    assert drops == {"not_two_markets": 1, "not_one_yes_one_no": 1}


def test_entry_uses_last_valid_candle_before_cutoff():
    start = datetime(2026, 1, 2, tzinfo=UTC)
    c = lambda h, b, a: {"end_period_ts": int((start - timedelta(hours=h)).timestamp()),
                         "yes_bid": {"close": b}, "yes_ask": {"close": a}}
    row = event_row("S", "E", {"result": "yes"}, start, [c(26, "0.10", "0.12"), c(25, "0.20", "0.22"),
                                                         c(23, "0.30", "0.32"), c(7, "0", "1")])
    assert (row["bid_24"], row["ask_24"]) == (0.20, 0.22)  # 23h candle is after the 24h cutoff
    assert (row["bid_6"], row["ask_6"]) == (0.30, 0.32)  # empty book at 7h is skipped


def synthetic(seed, bias):
    """Favorites priced at p; true win rate p + bias. Weekly blocks over two splits."""
    rng = np.random.default_rng(seed)
    n = 8000
    p = rng.uniform(0.86, 0.97, n)
    yes_fav = rng.uniform(size=n) < 0.5
    won = rng.uniform(size=n) < np.minimum(p + bias, 1)
    starts = pd.Timestamp("2025-09-01", tz="UTC") + pd.to_timedelta(rng.integers(0, 300, n), unit="D")
    ask = np.where(yes_fav, p, 1 - p + 0.01)
    rows = {"series": "S", "event": [f"e{i}" for i in range(n)], "start": starts,
            "yes_won": np.where(yes_fav, won, ~won).astype(float)}
    for h in (24, 6):
        rows[f"ask_{h}"], rows[f"bid_{h}"] = ask, ask - 0.01
    return frame([dict(zip(rows, v)) for v in zip(*[np.broadcast_to(np.asarray(x, dtype=object), n) for x in rows.values()])])


def test_null_fair_prices_lose_the_fee():
    df = synthetic(1, bias=0.0)
    pnl = rule_pnl(df, 24, 0.90)
    assert len(pnl) > 1000 and pnl.mean() < 0
    assert not select_and_validate(df)["passed"]


def test_power_detects_longshot_bias_and_shuffle_kills_it():
    df = synthetic(2, bias=0.03)
    assert select_and_validate(df)["passed"]
    assert not select_and_validate(permuted(df))["passed"]
