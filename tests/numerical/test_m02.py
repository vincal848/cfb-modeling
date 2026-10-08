"""M02 on synthetic data: the opener rule must not pass on a null and must detect a real move."""

import numpy as np
import pandas as pd

from cfb.evaluation.m02 import evaluate, slope


def synth(beta: float, n: int = 6000, seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    gap = rng.normal(0, 3, n)
    open_ = rng.normal(0, 8, n).round(1)
    move = beta * gap + rng.normal(0, 1.5, n)
    # truth: result margin vs the close is noise, so the open's edge equals the move
    result = -(open_ + move) + rng.normal(0, 12, n)
    return pd.DataFrame({"gap": gap, "open": open_, "close": open_ + move, "result": result,
                         "block": rng.integers(0, 40, n).astype(str)})


def test_null_does_not_pass():
    df = synth(0.0)
    r = evaluate(df, 1.0)
    assert r["lo"] < 0 and r["per_trade"] < 0
    s = slope(df)
    assert s["lo"] < 0 < s["hi"]


def test_power_detects_move():
    df = synth(0.5)
    r = evaluate(df, 2.0)
    assert r["lo"] > 0 and r["clv"] > 0 and r["clv_share"] > 0.5
    s = slope(df)
    assert s["lo"] > 0.4
