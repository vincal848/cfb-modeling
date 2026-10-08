"""K01 on synthetic prices: calibrated prices lose fees; an injected favorite bias is detected."""

import numpy as np
import pandas as pd

from cfb.evaluation import k01


def synth(edge: float, n: int = 1200, seed: int = 1) -> pd.DataFrame:
    """Favorites priced at p, winning with probability p + edge. Spread 2 cents around p."""
    rng = np.random.default_rng(seed)
    ko = pd.Timestamp("2025-09-01", tz="UTC") + pd.to_timedelta(rng.uniform(0, 150, n), unit="D")
    p = rng.uniform(0.6, 0.95, n)
    df = pd.DataFrame({"kickoff": ko, "yes_won": (rng.uniform(size=n) < np.minimum(p + edge, 1)).astype(float),
                       "volume": rng.uniform(1, 1e4, n)})
    flip = rng.uniform(size=n) < 0.5  # the sampled market is the underdog's half the time
    df.loc[flip, "yes_won"] = 1 - df.loc[flip, "yes_won"]
    for h in k01.HOURS:
        df[f"bid_{h}"] = np.where(flip, 1 - p - 0.01, p - 0.01)
        df[f"ask_{h}"] = np.where(flip, 1 - p + 0.01, p + 0.01)
    df["block"] = df["kickoff"].dt.strftime("%G-W%V")
    df["split"] = np.where(df["kickoff"] < k01.SPLIT, "select", "validate")
    return df


def test_calibrated_prices_lose_fees_and_null_does_not_pass():
    df = synth(0.0)
    assert evaluate_all(df) < 0
    res = k01.run(df)
    assert not res["real"]["passed"] and not res["null_failed"]


def evaluate_all(df):
    return k01.rule_pnl(df, 3, 0.6, "taker").mean()


def test_favorite_bias_is_detected():
    res = k01.run(synth(0.08))
    assert res["real"]["passed"] and res["real"]["validate"]["lo"] > 0
    assert not res["null_failed"]


def test_no_side_pays_one_minus_bid():
    df = pd.DataFrame({"yes_won": [0.0], "bid_3": [0.09], "ask_3": [0.11]})
    pnl = k01.rule_pnl(df, 3, 0.8, "taker").iloc[0]
    assert abs(pnl - (1 - 0.91 - 0.07 * 0.91 * 0.09)) < 1e-12
