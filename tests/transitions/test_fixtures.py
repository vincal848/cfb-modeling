"""P01 on real CFBD play-by-play, checked against independent sources.

Each fixture in tests/fixtures/football/ is a trimmed CFBD /plays extract for one game
(CFBD game IDs are ESPN game IDs). The expected facts below come from ESPN play-by-play
and, where noted, written recaps, as listed in docs/rules/fixture-candidates.md. They are
not derived from CFBD. Point values and overtime formats come from the cited rules
registry (config/rules_registry.json).

Where CFBD itself is known to be incomplete for a game, the test asserts that P01 reports
the failure rather than claiming the game reconciles.
"""

import json
from pathlib import Path

import pytest

from cfb.state.machine import reconcile_game
from cfb.state.rules import overtime_rules, scoring_rules
from cfb.state.scoring import classify_play

FIXTURES = Path(__file__).parents[1] / "fixtures" / "football"


def load(game_id: int) -> dict:
    return json.loads((FIXTURES / f"{game_id}.json").read_text(encoding="utf-8"))


def reconcile(game_id: int):
    g = load(game_id)
    return g, reconcile_game(g["plays"], scoring_rules(g["season"]), tuple(g["official_final"]),
                             overtime_rules(g["season"]))


def events(game_id: int) -> list[tuple[int, str, str, str | None]]:
    """(period, kind, scoring team, try result) for every scoring event, in game order."""
    g = load(game_id)
    rules = scoring_rules(g["season"])
    out = []
    for p in sorted(g["plays"], key=lambda q: (q["period"] or 0, int(q["id"]))):
        e = classify_play(p, rules)
        if e.kind not in ("none", "unknown"):
            team = p["offense"] if e.scorer == "offense" else p["defense"]
            out.append((p["period"], e.kind, team, e.try_result))
    return out


# Official finals per ESPN (home, away in CFBD's canonical orientation).
FINALS = {
    401403871: (16, 26), 401403879: (25, 45), 401403893: (23, 21), 401012356: (74, 72), 401405062: (7, 3),
    401416569: (58, 44), 401520156: (3, 23), 401405098: (33, 14), 401282717: (18, 20), 401403867: (24, 23),
    401411096: (20, 21), 401405069: (21, 22), 401403857: (29, 26), 401532588: (35, 26), 401532410: (26, 23),
    401525860: (51, 22), 401013353: (44, 47), 401112489: (43, 41), 401236005: (53, 45), 401628439: (44, 42),
}


@pytest.mark.parametrize("game_id", sorted(FINALS))
def test_official_final_matches_independent_source(game_id):
    assert tuple(load(game_id)["official_final"]) == FINALS[game_id]


@pytest.mark.parametrize("game_id, period, team, try_result", [
    (401403871, 3, "Kentucky", "kick_good"),  # 1a Keidron Smith 65-yd INT return TD
    (401403879, 1, "Wake Forest", "kick_good"),  # 1b Coby Davis 31-yd INT return TD
    (401403893, 2, "Texas A&M", "two_failed"),  # 1c Richardson 82-yd fumble return TD, 2-pt failed
])
def test_return_touchdowns_score_for_the_returning_team(game_id, period, team, try_result):
    assert (period, "touchdown", team, try_result) in events(game_id)


def test_fumble_return_touchdown_labelled_as_recovery_is_found_from_text():
    # 1d: LSU's Divinity 58-yd fumble return TD; CFBD types it "Fumble Recovery (Opponent)".
    assert any(e[:3] == (4, "touchdown", "LSU") for e in events(401012356))


@pytest.mark.parametrize("game_id, safeties", [
    (401405062, [(3, "Iowa"), (4, "Iowa")]),  # 2a two Iowa safeties
    (401416569, [(1, "Oklahoma State")]),  # 2b
    (401403871, [(2, "Florida")]),  # 2c team safety for Florida
])
def test_safeties_score_for_the_defense(game_id, safeties):
    assert [(e[0], e[2]) for e in events(game_id) if e[1] == "safety"] == safeties


# 3c (2021 Illinois-Penn State) is not included: CFBD has no row for that nullified play.
@pytest.mark.parametrize("game_id", [401520156, 401405098])
def test_penalty_nullified_touchdowns_do_not_score(game_id):
    g = load(game_id)
    rules = scoring_rules(g["season"])
    nullified = [p for p in g["plays"] if "nullified" in (p["playText"] or "").lower()]
    assert nullified, "fixture should contain the nullified play"
    assert all(classify_play(p, rules).kind == "none" for p in nullified)


def test_nullified_touchdown_game_reconciles():
    _, rec = reconcile(401520156)  # 3a Ohio State at Indiana
    assert rec.tier == "exact"


@pytest.mark.parametrize("game_id, period, team, try_result", [
    (401411096, 4, "East Carolina", "kick_failed"),  # 4b PAT missed
    (401405069, 2, "Rutgers", "kick_failed"),  # 4c PAT missed
    (401403857, 3, "Utah", "two_failed"),  # 4d two-point run failed
])
def test_failed_tries(game_id, period, team, try_result):
    assert (period, "touchdown", team, try_result) in events(game_id)


def test_blocked_pat_at_zero_and_swapped_score_columns():
    # 4a: LSU's TD as time expired, PAT blocked. CFBD's text omits the try, so it is unparsed;
    # the exact reconciliation to LSU's official 23 shows the try scored 0, as ESPN reports.
    assert events(401403867)[-1] == (4, "touchdown", "LSU", "unparsed")
    _, rec = reconcile(401403867)
    # CFBD swaps the offense/defense score columns throughout this game.
    assert rec.tier == "exact" and rec.score_columns_swapped and rec.final_from_plays == (24, 23)


@pytest.mark.parametrize("game_id, team", [(401532588, "New Mexico"), (401532410, "Eastern Michigan")])
def test_defensive_two_point_returns_reconcile_at_events_tier(game_id, team):
    # 5a/5b: blocked PAT returned for 2; CFBD records only the block in the TD text.
    assert any(e[2] == team and e[3] == "kick_failed" for e in events(game_id))
    _, rec = reconcile(game_id)
    assert rec.tier in ("exact", "events")


@pytest.mark.parametrize("game_id, overtimes", [
    (401012356, 7),  # 6a 2018, 7OT
    (401013353, 3),  # 6b 2018, 3OT, all OT plays in period 5
    (401236005, 4),  # 6d 2020, 4OT
    (401628439, 8),  # 6f 2024, 8OT, all OT plays in period 5
])
def test_overtime_count(game_id, overtimes):
    assert reconcile(game_id)[1].overtime_periods == overtimes


@pytest.mark.parametrize("game_id", [401012356, 401013353, 401112489, 401236005, 401628439])
def test_overtime_rules_respected(game_id):
    issues = reconcile(game_id)[1].issues
    assert not issues["ot_kick_try_in_mandatory_period"] and not issues["ot_shootout_violation"]


def test_2020_mandatory_two_point_period_and_2024_shootout():
    # 6d: Oklahoma's OT4 TD is followed by the mandatory two-point pass (good).
    assert (8, "touchdown", "Oklahoma", "two_good") in events(401236005)
    # 6f: Georgia Tech's OT2 TD needs a two-point try (2021+ rules), which failed.
    assert (5, "touchdown", "Georgia Tech", "two_failed") in events(401628439)
    _, rec = reconcile(401628439)
    assert rec.tier == "exact"


def test_2019_single_two_point_play_wins_the_game():
    # 6c: Quincy Patterson's two-point run in the final OT. CFBD has no plays for the
    # scoreless OT3-OT5, so the inferred overtime count is 5, not 6; the score still reconciles.
    assert (5, "two_point_play", "Virginia Tech", "two_good") in events(401112489)
    _, rec = reconcile(401112489)
    assert rec.tier == "exact" and rec.overtime_periods == 5


def test_missing_shootout_plays_are_reported_not_hidden():
    # 6e: 2021 Illinois-Penn State, 9OT. CFBD lacks the OT3-OT9 two-point plays.
    _, rec = reconcile(401282717)
    assert rec.tier == "failed" and rec.issues["final_mismatch"] == 1
