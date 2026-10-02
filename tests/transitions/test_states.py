"""P01 preplay states and next-score labels on SYNTHETIC plays (fabricated, CFBD-shaped)."""

from cfb.state.scoring import ScoringRules
from cfb.state.table import game_states

RULES = ScoringRules(6, 3, 2, 1, 2, 2)


def play(n, period, minutes, ptype, offense, off_score, def_score, down=1, distance=10, ytg=75, gained=0,
         text=""):
    return {"id": str(1000 + n), "gameId": 1, "period": period, "clock": {"minutes": minutes, "seconds": 0},
            "playType": ptype, "playText": text, "offense": offense, "defense": "A" if offense == "H" else "H",
            "home": "H", "away": "A", "offenseScore": off_score, "defenseScore": def_score, "down": down,
            "distance": distance, "yardsToGoal": ytg, "yardsGained": gained, "scoring": "Touchdown" in ptype}


GAME = [
    play(1, 1, 15, "Kickoff", "A", 0, 0),
    play(2, 1, 14, "Rush", "H", 0, 0, 1, 10, 75, 4),
    play(3, 1, 13, "Pass Reception", "H", 0, 0, 2, 6, 71, 6),
    play(4, 1, 12, "Passing Touchdown", "H", 7, 0, 1, 10, 65, 65, "pass for a TD (K KICK)"),
    play(5, 1, 12, "Kickoff", "H", 7, 0),
    play(6, 2, 5, "Rush", "A", 0, 7, 1, 10, 80, 3),
    play(7, 3, 15, "Kickoff", "H", 7, 0),
    play(8, 3, 14, "Rush", "A", 0, 7, 1, 10, 75, 2),
    play(9, 4, 2, "Field Goal Good", "H", 10, 0, 4, 5, 20, 0, "37 yd FG GOOD"),
    play(10, 5, 15, "Rushing Touchdown", "A", 16, 10, 1, 10, 25, 25, "run for a TD (K KICK)"),  # overtime
]


def test_labels_margins_and_half_boundaries():
    df, _ = game_states(GAME, RULES)
    assert list(df["play_id"]) == ["1002", "1003", "1004", "1006", "1008", "1009"]  # scrimmage, regulation
    labels = dict(zip(df["play_id"], df["next_score"], strict=True))
    assert labels["1002"] == labels["1003"] == labels["1004"] == "TD_FOR"  # H scores on play 4
    assert labels["1006"] == "NONE"  # no more first-half scoring
    assert labels["1008"] == "FG_AGAINST" and labels["1009"] == "FG_FOR"
    margins = dict(zip(df["play_id"], df["score_margin"], strict=True))
    assert margins["1004"] == 0 and margins["1006"] == -7 and margins["1009"] == 7  # pre-play, offense view
    assert set(df["seconds_left_half"]) >= {14 * 60 + 900, 5 * 60, 2 * 60}


def test_transition_checks_count_consistent_rows():
    _, checks = game_states(GAME, RULES)
    # 1st & 10 gain 4 -> 2nd & 6 at the 71; 2nd & 6 gain 6 -> 1st down at the 65.
    assert checks["down_checked"] == checks["down_ok"] == 2
    assert checks["yards_ok"] == 2
    assert checks["kickoff_after_score_ok"] == checks["score_checked"] == 1
    assert checks["half_starts_with_kickoff"] == checks["halves"] == 2
    assert checks["clock_ok"] == checks["clock_checked"]


def test_play_points_and_try_points_come_from_score_changes():
    df, _ = game_states(GAME, RULES)
    rows = df.set_index("play_id")
    assert rows.loc["1004", "play_points"] == 7 and rows.loc["1004", "try_points"] == 1
    assert rows.loc["1009", "play_points"] == 3 and rows.loc["1002", "play_points"] == 0
