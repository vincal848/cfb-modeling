"""B02 Kalman team filter on SYNTHETIC games (fabricated)."""

import copy

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from cfb.models.dynamic import DynamicParams, TeamFilter, filter_and_predict, ids_digest


def games(seed=1, seasons=(2018, 2019), weeks=10, n_teams=12):
    rng = np.random.default_rng(seed)
    strength = np.linspace(8, -8, n_teams)
    rows, gid = [], 0
    for season in seasons:
        for w in range(1, weeks + 1):
            for h, a in rng.permutation(n_teams).reshape(-1, 2):
                mh, ma = 28 + 1.5 + strength[h] - strength[a] / 2, 28 - 1.5 + strength[a] - strength[h] / 2
                hp, ap = (max(0, round(v)) for v in rng.normal([mh, ma], 10))
                ap = ap + 1 if ap == hp else ap
                rows.append({"game_id": f"g{gid:05d}", "season": season, "season_type": "regular", "week": w,
                             "start": pd.Timestamp(f"{season}-09-01") + pd.Timedelta(days=7 * (w - 1)),
                             "home": f"t{h:02d}", "away": f"t{a:02d}", "neutral": False,
                             "home_fbs": True, "away_fbs": True, "hp": hp, "ap": ap})
                gid += 1
    return pd.DataFrame(rows)


def reference_predict(filt, g):
    """Full-state computation: copy, take the pending step, activate teams, apply H."""
    f = copy.deepcopy(filt)
    f._step((g.season, g.season_type, g.week))
    f._activate(g.home)
    f._activate(g.away)
    h = np.zeros((2, len(f.x)))
    for k, r in enumerate(f._design(g.home, g.away, g.neutral, g.home_fbs, g.away_fbs)):
        for i, v in r:
            h[k, i] += v
    return h @ f.x, h @ f.p @ h.T + np.eye(2) * f.params.sigma ** 2


@pytest.mark.parametrize("next_game", ["same_week", "next_week", "next_season", "new_team"])
def test_fast_predict_matches_full_state_computation(next_game):
    df = games()
    filt = TeamFilter(DynamicParams(q_week=1.5, rho=0.7, s0=6, sigma=10), capacity=20)
    hist = df[df["season"] == 2018]
    for g in hist.itertuples(index=False):
        filt.update(g)
    last = hist.iloc[-1]
    g = last.copy()
    if next_game == "next_week":
        g["week"] = last["week"] + 1
    elif next_game == "next_season":
        g["season"], g["week"] = 2019, 1
    elif next_game == "new_team":
        g["away"], g["week"] = "t99", last["week"] + 1
    g = next(pd.DataFrame([g]).itertuples(index=False))
    m, c = filt.predict(g)
    rm, rc = reference_predict(filt, g)
    assert np.allclose(m, rm) and np.allclose(c, rc)


def test_filter_learns_strength_and_unknown_teams_get_wider_intervals():
    df = games(weeks=12)
    filt = TeamFilter(DynamicParams(q_week=0.5, rho=0.9, s0=8, sigma=10), capacity=20)
    for g in df.itertuples(index=False):
        filt.update(g)
    off = [filt.x[filt._slots(f"t{i:02d}")[0]] for i in range(12)]
    assert stats.spearmanr(off, -np.arange(12)).statistic > 0.8
    probe = df.iloc[-1].copy()
    probe["week"] += 1
    known = next(pd.DataFrame([probe]).itertuples(index=False))
    probe["away"] = "t99"
    unknown = next(pd.DataFrame([probe]).itertuples(index=False))
    assert filt.predict(unknown)[1][1, 1] > filt.predict(known)[1][1, 1]


def test_fold_state_must_equal_snapshot_admissions():
    df = games()
    target = df[(df["season"] == 2019) & (df["week"] == 5)].drop(columns=["hp", "ap"])
    cutoff = (target["start"].min() - pd.Timedelta(hours=24)).isoformat()
    admitted = frozenset(df.loc[df["start"] + pd.Timedelta(hours=6) <= pd.Timestamp(cutoff), "game_id"])
    out = filter_and_predict(df, [(cutoff, ids_digest(admitted), target)], DynamicParams(), 6)
    assert out[0][1] == list(target["game_id"]) and out[0][2].shape == (len(target), 2)
    with pytest.raises(RuntimeError, match="differs from snapshot"):
        filter_and_predict(df, [(cutoff, ids_digest(admitted - {next(iter(admitted))}), target)],
                           DynamicParams(), 6)
