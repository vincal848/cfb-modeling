"""G01 joint-score sampler and overtime kernel on SYNTHETIC inputs (fabricated)."""

import numpy as np
import pytest

from cfb.models.joint import ot_kernel, regime, sample_joint

OT = [(2016, 7, 0), (2017, 3, 0), (2018, 8, 6)] * 15 + [(2019, 2, 0)] * 5


def test_regimes_follow_the_rules_registry_periods():
    assert [regime(s) for s in (2014, 2018, 2019, 2020, 2021, 2025)] == [0, 0, 1, 1, 2, 2]


def test_kernel_uses_same_regime_or_flags_fallback():
    pairs, fallback = ot_kernel(OT, 2018)  # regime 0 has 30 earlier games (2016-2017)
    assert not fallback and len(pairs) == 30
    pairs, fallback = ot_kernel(OT, 2020)  # regime 1 has only 5 earlier games -> pooled
    assert fallback and len(pairs) == 50
    with pytest.raises(ValueError):
        ot_kernel(OT, 2015)


def test_samples_are_nonnegative_integers_never_tied_and_correlated_by_pace():
    pairs, _ = ot_kernel(OT, 2019)
    s = sample_joint(28.0, 24.0, pace_k=5.0, disp_r=20.0, ot_pairs=pairs, n=50_000, seed=3)
    assert s.dtype == np.int16 and (s >= 0).all() and (s[:, 0] != s[:, 1]).all()
    assert s[:, 0].mean() == pytest.approx(28.0, rel=0.03)
    assert np.corrcoef(s[:, 0], s[:, 1])[0, 1] > 0.1  # shared pace -> positive correlation
    loose = sample_joint(28.0, 24.0, pace_k=1e6, disp_r=1e6, ot_pairs=pairs, n=50_000, seed=3)
    assert abs(np.corrcoef(loose[:, 0], loose[:, 1])[0, 1]) < 0.05
    assert np.array_equal(s, sample_joint(28.0, 24.0, 5.0, 20.0, pairs, 50_000, 3))


def test_state_uncertainty_widens_margins():
    pairs, _ = ot_kernel(OT, 2019)
    base = sample_joint(28.0, 24.0, 200.0, 20.0, pairs, 40_000, 5)
    wide = sample_joint(28.0, 24.0, 200.0, 20.0, pairs, 40_000, 5, state_cov=np.array([[16.0, -4.0], [-4.0, 16.0]]))
    assert np.std(wide[:, 0] - wide[:, 1]) > np.std(base[:, 0] - base[:, 1]) * 1.1
    assert abs(wide[:, 0].mean() - base[:, 0].mean()) < 0.5
