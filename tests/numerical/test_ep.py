"""P02 EP model and EPA conventions on SYNTHETIC states (fabricated)."""

import numpy as np
import pandas as pd
import pytest

from cfb.models.ep import epa, fit, label_values, learned_try_value
from cfb.state.scoring import ScoringRules
from cfb.state.table import LABELS

RULES = ScoringRules(6, 3, 2, 1, 2, 2)


def synthetic_states(n=20000, seed=0):
    """Closer to the goal -> more likely the next score is the offense's touchdown."""
    rng = np.random.default_rng(seed)
    ytg = rng.integers(1, 100, n)
    p_td_for = 0.75 - 0.6 * ytg / 100
    u = rng.random(n)
    label = np.where(u < p_td_for, "TD_FOR", np.where(u < p_td_for + 0.15, "FG_FOR",
                     np.where(u < 0.95, "TD_AGAINST", "NONE")))
    return pd.DataFrame({
        "yards_to_goal": ytg, "down": rng.integers(1, 5, n), "distance": rng.integers(1, 15, n),
        "seconds_left_half": rng.integers(0, 1800, n), "score_margin": rng.integers(-21, 22, n),
        "half": rng.integers(1, 3, n), "offense_timeouts": 3, "next_score": label,
        "try_points": np.where(label == "TD_FOR", rng.choice([0, 1, 1, 1, 2], n), np.nan),
    })


def test_fit_gives_valid_probabilities_and_ep_falls_with_distance_to_goal():
    df = synthetic_states()
    model = fit(df, RULES, penalty=1e-4)
    assert model.converged
    p = model.probabilities(df.head(500))
    assert np.allclose(p.sum(axis=1), 1.0) and (p >= 0).all()
    probe = df.head(9).assign(yards_to_goal=[5, 15, 25, 35, 50, 65, 75, 85, 95], down=1, distance=10,
                              seconds_left_half=1500, score_margin=0, half=1)
    ep = model.expected_points(probe)
    assert (np.diff(ep) < 0).all()  # farther from the goal -> lower EP


def test_try_value_is_learned_and_clipped():
    df = pd.DataFrame({"try_points": [1, 1, 0, 2, 5, -1, np.nan]})
    assert learned_try_value(df) == pytest.approx((1 + 1 + 0 + 2 + 2 + 0) / 6)
    values = dict(zip(LABELS, label_values(RULES, 0.9), strict=True))
    assert values["TD_FOR"] == pytest.approx(6.9) and values["TD_AGAINST"] == pytest.approx(-6.9)
    assert values["SAFETY_AGAINST"] == -2 and values["NONE"] == 0


def drive_rows():
    # H drives and scores a TD (7 incl. try); A gets the ball, throws a pick-six (H +7);
    # then A has one more play before the half ends.
    return pd.DataFrame({
        "game_id": ["g"] * 6, "half": [1] * 6,
        "offense": ["H", "H", "H", "A", "A", "A"],
        "play_points": [0, 0, 7, 0, -7, 0],
    })


def test_epa_telescopes_over_a_scoring_drive_and_never_double_counts():
    ep = np.array([0.8, 1.9, 4.5, 0.5, -0.2, 0.3])
    e = epa(drive_rows(), ep)
    # Scoring drive: sum of EPA = points - EP at the drive's first play.
    assert e[:3].sum() == pytest.approx(7 - ep[0])
    # Scoring play: reward minus EP, with no value added for the following state.
    assert e[2] == pytest.approx(7 - 4.5) and e[4] == pytest.approx(-7 - (-0.2))
    # Possession change without a score flips the sign of the next state's value.
    assert e[3] == pytest.approx(-0.2 - 0.5)
    # Last play of the half: the next state is worth nothing.
    assert e[5] == pytest.approx(-0.3)


def test_turnover_on_downs_flips_sign():
    rows = pd.DataFrame({"game_id": ["g", "g"], "half": [1, 1], "offense": ["H", "A"], "play_points": [0, 0]})
    e = epa(rows, np.array([1.0, 2.5]))
    assert e[0] == pytest.approx(-2.5 - 1.0)
