"""P04 ability/development model: parameter recovery and predictive behaviour on SYNTHETIC
players with known parameters (fabricated)."""

import numpy as np
import pandas as pd
import pytest

from cfb.models.ability import (
    AbilityParams,
    fit_ability,
    gaussian_log_score,
    position_group,
    predict,
)

TRUE = {"mu": {"QB": 0.10, "WR": 0.30}, "tau2": 0.04, "rho": 0.6, "q": 0.01, "sigma2": 1.5}


def simulate(players=1500, seasons=(2015, 2016, 2017, 2018), seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(players):
        group = "QB" if i % 3 == 0 else "WR"
        mu = TRUE["mu"][group]
        a = rng.normal(mu, np.sqrt(TRUE["tau2"]))
        first = rng.integers(0, 2)
        for k, s in enumerate(seasons[first:]):
            if k:
                a = mu + TRUE["rho"] * (a - mu) + rng.normal(0, np.sqrt(TRUE["q"]))
            n = int(rng.integers(20, 300))
            y = rng.normal(a, np.sqrt(TRUE["sigma2"] / n))
            rows.append({"athlete_id": f"p{i}", "season": s, "group": group, "y": y, "n": n})
    return pd.DataFrame(rows)


def test_parameters_are_recovered():
    p = fit_ability(simulate(), sigma2=TRUE["sigma2"])
    assert p.converged
    assert p.mu["QB"] == pytest.approx(0.10, abs=0.02) and p.mu["WR"] == pytest.approx(0.30, abs=0.02)
    assert p.tau2 == pytest.approx(0.04, rel=0.3)
    assert p.rho == pytest.approx(0.6, abs=0.15)


def test_new_players_get_pooled_uncertainty_and_returners_shrink():
    p = AbilityParams({"QB": 0.1, "WR": 0.3, "OTHER": 0.2}, tau2=0.04, rho=0.6, q=0.01, sigma2=1.5)
    hist = pd.DataFrame([{"athlete_id": "vet", "season": 2017, "group": "WR", "y": 0.9, "n": 300},
                         {"athlete_id": "thin", "season": 2017, "group": "WR", "y": 0.9, "n": 5}])
    tg = pd.DataFrame([{"athlete_id": a, "season": 2018, "group": "WR"} for a in ("vet", "thin", "rookie")])
    out = predict(hist, tg, p).set_index("athlete_id")
    assert out.loc["rookie", "pred_mean"] == pytest.approx(0.3) and out.loc["rookie", "pred_var"] == pytest.approx(0.04)
    assert out.loc["rookie", "pred_var"] > out.loc["vet", "pred_var"]  # pooled prior is the widest
    # Same observed mean, fewer opportunities -> shrunk harder toward the group mean.
    assert 0.3 < out.loc["thin", "pred_mean"] < out.loc["vet", "pred_mean"] < 0.9


def test_history_after_the_target_season_is_ignored():
    p = AbilityParams({"WR": 0.3, "OTHER": 0.2}, tau2=0.04, rho=0.6, q=0.01, sigma2=1.5)
    hist = pd.DataFrame([{"athlete_id": "x", "season": 2019, "group": "WR", "y": 2.0, "n": 300}])
    out = predict(hist, pd.DataFrame([{"athlete_id": "x", "season": 2018, "group": "WR"}]), p)
    assert out["pred_mean"].iloc[0] == pytest.approx(0.3) and not out["has_history"].iloc[0]


def test_log_score_and_position_groups():
    assert gaussian_log_score(0.0, 100, 0.0, 0.0, 1.0) == pytest.approx(0.5 * np.log(2 * np.pi * 0.01))
    assert [position_group(x) for x in ("QB", "fb", "WR", "TE", "LB", None)] == ["QB", "RB", "WR", "TE", "OTHER", "OTHER"]


def test_vectorized_likelihood_matches_per_player_filter_with_gaps():
    from cfb.models.ability import _filter, _grid, _loglik, _unpack

    df = simulate(players=60, seasons=(2015, 2016, 2017, 2018, 2019), seed=3)
    df = df[~((df["athlete_id"].str[-1] == "7") & (df["season"] == 2017))]  # gap seasons
    groups = sorted(df["group"].unique())
    theta = np.array([0.12, 0.28, np.log(0.05), np.log(0.02), 0.4])
    p = _unpack(theta, groups, 1.5)
    per_player = sum(_filter(g.sort_values("season"), p)[0] for _, g in df.groupby("athlete_id"))
    assert _loglik(theta, groups, 1.5, _grid(df, groups)) == pytest.approx(per_player, rel=1e-10)


def test_thin_position_groups_fall_back_to_their_mean_and_do_not_distort_others():
    from cfb.evaluation.p04 import evaluate_category

    qbs = simulate(players=400, seasons=(2015, 2016, 2017, 2018), seed=5).query("group == 'QB'")
    rng = np.random.default_rng(9)
    trick = pd.DataFrame([{"athlete_id": f"w{i}", "season": s, "group": "WR", "y": rng.normal(2.0, 1.5), "n": 1}
                          for i in range(400) for s in (2016, 2017, 2018)])  # many one-attempt seasons
    out, fits = evaluate_category(pd.concat([qbs, trick], ignore_index=True), 2018, 1.5)
    fitted = {f["group"]: f for f in fits}
    assert fitted["QB"]["fitted"] and not fitted["WR"]["fitted"]
    assert fitted["QB"]["tau"] == pytest.approx(0.2, rel=0.35)  # QB spread is not inflated by trick plays
    wr = out[out["group"] == "WR"]
    assert (wr["model_mean"] == wr["group_mean"]).all()
