"""D02 coverage logic on SYNTHETIC game records (fabricated; not CFBD data)."""

from cfb.ingestion.coverage import (
    SeasonInputs,
    classify_drive_mismatch,
    reduce_drives,
    reduce_plays,
    summarize_season,
)


def game(gid, home, away, hp, ap, completed=True, **kw):
    return {"id": gid, "homeId": home, "awayId": away, "homePoints": hp, "awayPoints": ap,
            "completed": completed, "homeClassification": "fbs", "awayClassification": "fbs", **kw}


def drive(n, home_off, off, dfn, period=4, gid=1):
    return {"gameId": gid, "driveNumber": n, "isHomeOffense": home_off,
            "endOffenseScore": off, "endDefenseScore": dfn, "endPeriod": period}


def test_drive_reduction_maps_offense_to_home_away():
    drives = [drive(1, True, 7, 0, 1), drive(2, False, 3, 7, 2), drive(3, True, 14, 3)]
    assert reduce_drives(drives) == {1: (3, 14, 3, 4)}


def test_drive_reduction_uses_last_drive_not_corrupt_maximum():
    # Drive 2 carries a corrupt defense score (35); the game ends 14-3.
    drives = [drive(3, True, 14, 3), drive(1, True, 7, 0), drive(2, False, 3, 35)]
    assert reduce_drives(drives) == {1: (3, 14, 3, 4)}


def test_drive_mismatch_classification():
    assert classify_drive_mismatch((10, 14, 3, 4), (14, 3)) == "match"
    assert classify_drive_mismatch((10, 14, 3, 3), (31, 13)) == "pbp_ends_before_q4"
    assert classify_drive_mismatch((10, 14, 3, 4), (17, 3)) == "pbp_short_of_final"
    assert classify_drive_mismatch((10, 15, 3, 4), (14, 3)) == "pbp_over_or_mixed"
    assert classify_drive_mismatch((10, -1, -1, 4), (14, 3)) == "pbp_short_of_final"


def test_play_reduction_uses_team_names_for_perspective():
    plays = [
        {"gameId": 2, "home": "A", "offense": "A", "defense": "B", "offenseScore": 0, "defenseScore": 0},
        {"gameId": 2, "home": "A", "offense": "B", "defense": "A", "offenseScore": 6, "defenseScore": 10},
    ]
    assert reduce_plays(plays) == {2: (2, 10, 6)}


def test_summary_population_denominators_and_unavailable_not_zero():
    fbs = {10, 11}
    games = [
        game(1, 10, 11, 14, 3),
        game(2, 10, 99, 35, 7, awayClassification=None),  # FBS vs non-FBS with null class
        game(3, 98, 99, 21, 20),  # no FBS team: outside population
        game(4, 11, 10, None, None, completed=False),  # canceled/unresolved
    ]
    x = SeasonInputs(
        2024, fbs, games,
        lines=[{"id": 1, "lines": [{"spread": -3.5, "spreadOpen": None, "homeMoneyline": None}]}],
        team_stat_ids={1, 2},
        drives={1: (20, 14, 3, 4), 2: (22, 35, 0, 4)},  # game 2 drive score short of final
        plays={},
        failed_partitions=["/plays {...} -> 500"],
    )
    s = summarize_season(x)
    assert s["games_fbs_involving"] == 3 and s["scored_games"] == 2
    assert s["not_completed_or_unscored"] == 1 and s["null_classification"] == 1
    assert s["fbs_vs_nonfbs"] == 1
    assert s["team_stats_share"] == 1.0
    assert s["drives_share"] == 1.0 and s["drive_score_match_share"] == 0.5
    assert s["drive_mismatch_kinds"] == {"pbp_short_of_final": 1} and s["pbp_ends_before_q4"] == 0
    assert s["plays_share"] == 0.0 and s["play_score_match_share"] is None  # no denominator
    assert s["lines_share"] == 0.5 and s["spread_open_share"] == 0.0
    assert s["failed_partitions"]
