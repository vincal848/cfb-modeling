"""B01 sampling, metrics, models and parallel determinism on SYNTHETIC games (fabricated)."""

from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from cfb.evaluation.backtest import Config, FoldTask, block_bootstrap, run_tasks
from cfb.evaluation.metrics import crps, energy_score, score_game
from cfb.evaluation.protocol import Fold
from cfb.models.baselines import GameFrame, fit_elo, fit_hfa_only, fit_ridge, run_elo
from cfb.models.simulate import derive_seed, sample_scores


def test_samples_are_nonnegative_untied_integers_and_seeded():
    mean, cov = np.array([3.0, 3.0]), np.array([[25.0, 5.0], [5.0, 25.0]])
    a = sample_scores(mean, cov, 5000, 7)
    assert a.dtype == np.int16 and (a >= 0).all() and (a[:, 0] != a[:, 1]).all()
    assert np.array_equal(a, sample_scores(mean, cov, 5000, 7))
    assert not np.array_equal(a, sample_scores(mean, cov, 5000, 8))


def test_seed_depends_on_every_registered_component():
    base = derive_seed(1, "1.0", "ridge", "cfbd-game-1", 1440)
    assert base == derive_seed(1, "1.0", "ridge", "cfbd-game-1", 1440)
    for args in ((2, "1.0", "ridge", "cfbd-game-1", 1440), (1, "1.1", "ridge", "cfbd-game-1", 1440),
                 (1, "1.0", "elo", "cfbd-game-1", 1440), (1, "1.0", "ridge", "cfbd-game-2", 1440),
                 (1, "1.0", "ridge", "cfbd-game-1", 60)):
        assert derive_seed(*args) != base


def test_crps_exact_on_small_sample_and_close_to_normal_closed_form():
    assert crps(np.array([0, 1]), 0.0) == pytest.approx(0.25)
    draws = np.random.default_rng(0).normal(0, 1, 200_000)
    y = 0.7
    closed = y * (2 * stats.norm.cdf(y) - 1) + 2 * stats.norm.pdf(y) - 1 / np.sqrt(np.pi)
    assert crps(draws, y) == pytest.approx(closed, abs=0.005)


def test_energy_score_is_zero_for_a_point_mass_and_grows_with_error():
    point = np.tile([28, 21], (100, 1))
    assert energy_score(point, np.array([28.0, 21.0])) == 0.0
    assert energy_score(point, np.array([35.0, 21.0])) == pytest.approx(7.0)
    s = score_game(point, 35, 21)
    assert s["winner_log_loss"] < -np.log(0.5) and s["margin_crps"] == pytest.approx(7.0)


def synthetic_season(seed=0, n_weeks=12, n_teams=20, hfa=3.0):
    """Round-robin-ish schedule with known offense/defense; team 0 strongest."""
    rng = np.random.default_rng(seed)
    off = np.linspace(10, -10, n_teams)
    dfn = np.linspace(8, -8, n_teams)
    rows, gid = [], 0
    start = pd.Timestamp("2019-08-31 16:00")
    for w in range(n_weeks):
        perm = rng.permutation(n_teams)
        for h, a in perm.reshape(-1, 2):
            mu_h = 28 + hfa / 2 + off[h] - dfn[a]
            mu_a = 28 - hfa / 2 + off[a] - dfn[h]
            hp, ap = (max(0, round(v)) for v in rng.normal([mu_h, mu_a], 10))
            if hp == ap:
                hp += 3
            rows.append({"game_id": f"g{gid:04d}", "season": 2019, "season_type": "regular", "week": w + 1,
                         "start": start + pd.Timedelta(days=7 * w), "home": f"t{h:02d}", "away": f"t{a:02d}",
                         "neutral": False, "home_fbs": True, "away_fbs": True, "hp": hp, "ap": ap})
            gid += 1
    return pd.DataFrame(rows)


def target_games(n_teams=20):
    return pd.DataFrame([{"game_id": f"x{i}", "season": 2019, "season_type": "regular", "week": 13,
                          "start": pd.Timestamp("2019-11-30 16:00"), "home": f"t{i:02d}",
                          "away": f"t{n_teams - 1 - i:02d}", "neutral": False, "home_fbs": True,
                          "away_fbs": True} for i in range(3)])


def test_ridge_recovers_team_order_and_home_advantage():
    frame = GameFrame(synthetic_season(), target_games())
    fc = fit_ridge(frame, half_life_days=10_000, penalty=1.0)
    margins = fc.means[:, 0] - fc.means[:, 1]
    assert margins[0] > margins[1] > margins[2] > 0  # stronger home teams, larger margins
    assert np.sqrt(fc.covs[0, 0, 0]) == pytest.approx(10, rel=0.2)


def test_elo_ranks_the_strongest_team_highest_and_trivial_model_ignores_teams():
    train = synthetic_season(n_weeks=30)
    ratings, diffs = run_elo(train, k=30, hfa=65, carryover=0.7)
    order = [ratings[f"t{i:02d}"] for i in range(20)]
    assert max(ratings, key=ratings.get) == "t00"
    assert stats.spearmanr(order, -np.arange(20)).statistic > 0.9
    assert len(diffs) == len(train)
    frame = GameFrame(train, target_games())
    assert fit_elo(frame).means[0, 0] > fit_elo(frame).means[0, 1]
    trivial = fit_hfa_only(frame)
    assert np.allclose(trivial.means, trivial.means[0])


def make_tasks():
    train = synthetic_season()
    tasks = []
    for i in range(4):
        tg = target_games().assign(game_id=lambda d, i=i: d["game_id"] + f"-{i}")
        outcomes = {g: (24 + i, 17) for g in tg["game_id"]}
        fold = Fold(2019, "regular", 13 + i, "development", datetime(2019, 11, 29, tzinfo=UTC),
                    tuple(tg["game_id"]), ())
        tasks.append(FoldTask(fold, f"snap-{i}", GameFrame(train, tg), outcomes,
                              (Config("ridge", (("penalty", 5.0),)), Config("hfa_only", ())),
                              20261001, "1.0", 1440, 2000))
    return tasks


def test_results_identical_for_any_worker_count():
    tasks = make_tasks()
    serial = run_tasks(tasks, workers=1)
    parallel = run_tasks(list(reversed(tasks)), workers=3)
    pd.testing.assert_frame_equal(serial, parallel)
    assert len(serial) == 4 * 3 * 2


def test_block_bootstrap_constant_difference_has_degenerate_interval():
    diff = pd.Series([-0.5] * 30)
    blocks = pd.Series(np.repeat(np.arange(10), 3))
    assert block_bootstrap(diff, blocks, 500, 1) == pytest.approx((-0.5, -0.5, -0.5))


def test_sorted_quantile_matches_numpy_linear_method():
    from cfb.evaluation.metrics import sorted_quantile

    x = np.sort(np.random.default_rng(3).integers(-40, 60, 20001).astype(float))
    for q in (0.025, 0.1, 0.25, 0.5, 0.75, 0.9, 0.975):
        assert sorted_quantile(x, q) == pytest.approx(np.quantile(x, q), abs=1e-12)
