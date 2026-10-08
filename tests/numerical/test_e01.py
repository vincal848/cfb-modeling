"""E01 efficiency rating on SYNTHETIC plays and games (fabricated)."""

import numpy as np
import pandas as pd

from cfb.evaluation.e01 import BASE, SCALE, efficiency_history, game_efficiency, kept
from cfb.models.dynamic import DynamicParams, TeamFilter


def test_garbage_time_uses_sp_plus_thresholds():
    s = pd.DataFrame({"period": [1, 1, 2, 3, 4, 4, 5], "score_margin": [28, -29, 24, 22, 16, -17, 0]})
    assert kept(s).tolist() == [True, False, True, False, True, False, False]  # overtime is never kept


def test_game_efficiency_needs_min_plays_and_maps_teams():
    n = 25
    states = pd.DataFrame({"play_id": range(2 * n + 5), "game_id": "g1", "period": 1, "score_margin": 0,
                           "offense": ["A"] * n + ["B"] * n + ["C"] * 5})
    epa = pd.DataFrame({"play_id": [str(i) for i in range(2 * n + 5)],
                        "epa": [0.2] * n + [-0.1] * n + [1.0] * 5})
    g = game_efficiency(states, epa, {"A": "ta", "B": "tb", "C": "tc"}).set_index("team")["epa_pp"]
    assert g.to_dict() == {"ta": 0.2, "tb": -0.1}  # C has too few plays


def test_efficiency_history_scales_and_drops_one_sided_games():
    train = pd.DataFrame({"game_id": ["g1", "g2"], "home": ["ta", "ta"], "away": ["tb", "tc"], "hp": [1, 2], "ap": [3, 4]})
    eff = pd.DataFrame({"game_id": ["g1", "g1", "g2"], "team": ["ta", "tb", "ta"], "epa_pp": [0.1, -0.2, 0.3]})
    h = efficiency_history(train, eff)
    assert h["game_id"].tolist() == ["g1"]
    assert np.allclose(h[["hp", "ap"]].iloc[0], [BASE + SCALE * 0.1, BASE - SCALE * 0.2])


def test_power_clean_efficiency_beats_noisy_scores():
    """Same filter; observations that are truth + small noise must rank teams better than truth + big noise."""
    rng = np.random.default_rng(3)
    n_teams, weeks = 20, 12
    strength = rng.normal(0, 7, n_teams)
    names = [f"t{i}" for i in range(n_teams)]
    errs = {}
    for label, noise, sigma in (("eff", 3.0, 4.0), ("score", 14.0, 14.0)):
        r = np.random.default_rng(4)
        filt = TeamFilter(DynamicParams(q_week=0.01, rho=0.9, s0=8, sigma=sigma), capacity=n_teams)
        gid = 0
        for w in range(1, weeks + 1):
            for h, a in r.permutation(n_teams).reshape(-1, 2):
                true = np.array([27 + strength[h] - strength[a] / 2, 27 + strength[a] - strength[h] / 2])
                hp, ap = true + r.normal(0, noise, 2)
                g = pd.Series({"game_id": f"g{gid}", "season": 2020, "season_type": "regular", "week": w,
                               "home": names[h], "away": names[a], "neutral": True, "home_fbs": True,
                               "away_fbs": True, "hp": hp, "ap": ap})
                filt.update(g)
                gid += 1
        est = np.array([filt.x[filt._slots(t)[0]] + filt.x[filt._slots(t)[1]] for t in names])
        errs[label] = np.corrcoef(est, strength)[0, 1]
    assert errs["eff"] > errs["score"] + 0.05 and errs["eff"] > 0.9
