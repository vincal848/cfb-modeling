"""R03 forward-residual correction on SYNTHETIC games (fabricated)."""

import numpy as np
import pandas as pd
import pytest

from cfb.evaluation.r03 import crps_normal, forward_correction


def test_crps_normal_matches_known_value():
    assert crps_normal(np.array([0.0]), np.array([0.0]), 1.0)[0] == pytest.approx(0.2336, abs=1e-4)


def games(beta=10.0, n=3000, seed=0):
    rng = np.random.default_rng(seed)
    x = rng.normal(0, 0.1, n)
    resid = beta * x + rng.normal(0, 14, n)
    return pd.DataFrame({"season": np.repeat([2019, 2020, 2021], n // 3), "home_points": 30 + resid,
                         "away_points": 20.0, "expected_home": 30.0, "expected_away": 20.0, "residual": resid,
                         "raw_diff": x, "residualized_diff": x})


def test_correction_recovers_a_planted_effect_and_improves_out_of_sample():
    out = forward_correction(games(beta=40.0), 2021)
    assert out["beta_raw"].iloc[0] == pytest.approx(40.0, rel=0.25)
    assert (out["sq_raw"] - out["sq_base"]).mean() < 0


def test_no_signal_gives_no_reliable_gain():
    out = forward_correction(games(beta=0.0), 2021)
    assert abs(out["beta_raw"].iloc[0]) < 10
