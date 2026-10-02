"""P03 opportunity shares on SYNTHETIC counts (fabricated)."""

import math

import pandas as pd
import pytest

from cfb.evaluation.p03 import last_game_shares
from cfb.models.opportunity import (
    UNKNOWN,
    Forecast,
    ShareParams,
    forecast_shares,
    log_score,
    player_counts,
    team_totals,
)

P = ShareParams(half_life_games=2.0, prior_season_weight=0.5, alpha=0.5, kappa=2.0, n_ref=30.0)
HISTORY = [{"rb1": 15, "rb2": 5}, {"rb1": 12, "rb2": 8}, {"rb1": 6, "rb2": 14}]


def test_shares_sum_to_one_keep_unknown_and_conserve_totals():
    shares = forecast_shares(HISTORY, [1, 0, 2], {"rb3": 0.3}, P)
    assert sum(shares.values()) == pytest.approx(1.0)
    assert shares[UNKNOWN] > 0 and "rb3" in shares  # returning roster player keeps a share
    fc = Forecast(shares, total=37)
    assert sum(fc.expected_counts().values()) == pytest.approx(37)


def test_recent_games_weigh_more():
    shares = forecast_shares(HISTORY, [0, 0, 0], {}, P)
    assert shares["rb2"] > shares["rb1"]  # rb2 led the most recent game by a wide margin
    flat = forecast_shares(HISTORY, [0, 0, 0], {}, ShareParams(half_life_games=1e9, alpha=0.5, kappa=2.0))
    assert flat["rb1"] > flat["rb2"]  # without decay, rb1's season total (33 vs 27) wins


def test_first_game_uses_prior_season_roster_shares_and_unknown():
    shares = forecast_shares([], [], {"qb1": 0.9, "qb2": 0.1}, P)
    assert shares["qb1"] > shares["qb2"] > 0 and shares[UNKNOWN] > 0
    assert sum(shares.values()) == pytest.approx(1.0)


def test_log_score_charges_new_players_and_unassigned_to_unknown():
    shares = {"a": 0.5, "b": 0.3, UNKNOWN: 0.2}
    loss, n = log_score(shares, {"a": 2, "new": 1}, unassigned=1)
    assert n == 4
    assert loss == pytest.approx(-(2 * math.log(0.5) + 2 * math.log(0.2)))


def test_participation_is_derived_from_shares():
    fc = Forecast({"a": 0.1, UNKNOWN: 0.9}, total=10)
    assert fc.p_any("a") == pytest.approx(1 - 0.9 ** 10)
    assert fc.p_any("absent") == 0.0


def test_last_game_baseline_keeps_a_floor_for_unknown():
    s = last_game_shares([{"a": 10}], [0], {})
    assert s[UNKNOWN] == pytest.approx(0.02) and sum(s.values()) == pytest.approx(1.0)


def test_counts_and_totals_from_cfbd_shaped_rows():
    stats = pd.DataFrame([
        {"gameId": 1, "team": "T", "athleteId": "q", "statType": "Completion", "playId": "p1"},
        {"gameId": 1, "team": "T", "athleteId": "w", "statType": "Reception", "playId": "p1"},
        {"gameId": 1, "team": "T", "athleteId": "w", "statType": "Touchdown", "playId": "p1"},
        {"gameId": 1, "team": "T", "athleteId": "q", "statType": "Sack Taken", "playId": "p2"},
        {"gameId": 1, "team": "T", "athleteId": "r", "statType": "Rush", "playId": "p3"},
        {"gameId": 1, "team": "T", "athleteId": "r", "statType": "Rush", "playId": "p3"},  # duplicate row
    ])
    c = player_counts(stats).set_index(["athlete_id", "category"])["n"]
    assert c[("q", "dropbacks")] == 2 and c[("w", "targets")] == 1 and c[("r", "carries")] == 1
    plays = pd.DataFrame([{"gameId": 1, "offense": "T", "playType": t} for t in
                          ("Pass Reception", "Sack", "Rush", "Rushing Touchdown", "Punt")])
    t = team_totals(plays).set_index("category")["total"]
    assert t["dropbacks"] == 2 and t["carries"] == 2 and t["targets"] == 1
