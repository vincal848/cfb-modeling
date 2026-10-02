"""P01 scoring classification and play-level reconciliation on SYNTHETIC plays (fabricated,
shaped like CFBD rows). Point values are passed in explicitly."""

import pytest

from cfb.state.machine import reconcile_game
from cfb.state.scoring import ScoringRules, classify_play, classify_try

RULES = ScoringRules(touchdown=6, field_goal=3, safety=2, try_kick=1, try_two_point=2, defensive_try_return=2)


@pytest.mark.parametrize("text, expected", [
    ("Joe run for 5 yds for a TD (Sam Kicker KICK)", "kick_good"),
    ("Joe run for 5 yds for a TD (Sam Kicker PAT MISSED)", "kick_failed"),
    ("Joe 0 Yd Fumble Return (Sam Kicker PAT blocked)", "kick_failed"),
    ("pass from QB (Two-Point Pass Conversion Failed)", "two_failed"),
    ("run for 11 yds for a TD (Two-Point Conversion failed)", "two_failed"),
    ("run for 13 yds for a TD (Q. Judkins Run For Two-point Conversion)", "two_good"),
    ("run for 2 yds for a TD (Defensive Two-Point Return by X)", "defensive_return"),
    ("run for 2 yds for a TD", "unparsed"),
])
def test_try_classification(text, expected):
    assert classify_try(text) == expected


def test_return_touchdowns_score_for_the_defense():
    ev = classify_play({"playType": "Interception Return Touchdown", "playText": "returned for a TD (K KICK)"}, RULES)
    assert ev.scorer == "defense" and ev.points == {"defense": 7}
    ev = classify_play({"playType": "Safety", "playText": "sacked in the end zone, SAFETY"}, RULES)
    assert ev.points == {"defense": 2}


def play(n, ptype, offense, off_score, def_score, text="", home="H", away="A", scoring=False):
    return {"id": str(1000 + n), "gameId": 1, "playType": ptype, "playText": text, "offense": offense,
            "defense": away if offense == home else home, "home": home, "away": away,
            "offenseScore": off_score, "defenseScore": def_score, "scoring": scoring}


def test_clean_game_reconciles_exactly():
    plays = [play(1, "Rush", "H", 0, 0),
             play(2, "Passing Touchdown", "H", 7, 0, "pass for a TD (K KICK)", scoring=True),
             play(3, "Kickoff", "H", 7, 0),
             play(4, "Field Goal Good", "A", 3, 7, "34 yd FG GOOD", scoring=True),
             play(5, "Interception Return Touchdown", "A", 3, 15, "returned for a TD (Two-Point Conversion)",
                  scoring=True)]
    rec = reconcile_game(plays, RULES, (15, 3))
    assert rec.reconciles and rec.tier == "exact" and rec.final_from_plays == (15, 3)


def test_stale_scores_on_administrative_rows_are_ignored():
    plays = [play(1, "Rushing Touchdown", "H", 7, 0, "run for a TD (K KICK)", scoring=True),
             play(2, "Timeout", "A", 0, 0, "Timeout A"),  # stale pre-TD score
             play(3, "Kickoff", "H", 7, 0)]
    assert reconcile_game(plays, RULES, (7, 0)).tier == "exact"


def test_try_points_on_the_next_play_are_accepted_once():
    plays = [play(1, "Rushing Touchdown", "H", 6, 0, "run for a TD (K KICK)", scoring=True),
             play(2, "Kickoff", "H", 7, 0)]
    rec = reconcile_game(plays, RULES, (7, 0))
    assert rec.tier == "exact" and rec.split_tries == 1


def test_missing_scoring_play_fails_exact_but_is_reported():
    plays = [play(1, "Rush", "H", 0, 0), play(2, "Kickoff", "A", 7, 0)]  # A gained 7 with no scoring play
    rec = reconcile_game(plays, RULES, (0, 7))
    assert not rec.reconciles and rec.issues["score_change_on_non_scoring_play"] == 1
    assert rec.tier == "failed"  # no event explains A's 7 points


def test_events_tier_tolerates_a_misordered_record():
    # The touchdown row is listed after the kickoff that followed it; per-play deltas break,
    # but the events still sum to the final.
    plays = [play(1, "Rush", "H", 0, 0), play(2, "Kickoff", "H", 7, 0),
             play(3, "Rushing Touchdown", "H", 7, 0, "run for a TD (K KICK)", scoring=True)]
    rec = reconcile_game(plays, RULES, (7, 0))
    assert not rec.reconciles and rec.tier == "events"


def test_unparsed_try_is_inferred_from_a_legal_delta_only():
    ok = [play(1, "Rushing Touchdown", "H", 8, 0, "run for a TD", scoring=True)]
    assert reconcile_game(ok, RULES, (8, 0)).inferred_tries == 1
    bad = [play(1, "Rushing Touchdown", "H", 10, 0, "run for a TD", scoring=True)]
    assert reconcile_game(bad, RULES, (10, 0)).issues["touchdown_try_unexplained"] == 1
