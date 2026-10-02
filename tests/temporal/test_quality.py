"""D08 quality flags and quarantine on SYNTHETIC drives (fabricated, shaped like the D02 cases)."""

import pytest

from cfb.canonical.quality import drive_flags, quarantined


def drv(n, home_off, start, end, period=1, gid=1):
    """start/end are (home, away) scores; stored in offense/defense terms like CFBD."""
    so, sd = start if home_off else start[::-1]
    eo, ed = end if home_off else end[::-1]
    return {"gameId": gid, "driveNumber": n, "isHomeOffense": home_off, "startPeriod": period,
            "endPeriod": period, "startOffenseScore": so, "startDefenseScore": sd,
            "endOffenseScore": eo, "endDefenseScore": ed}


CLEAN = [drv(1, True, (0, 0), (7, 0)), drv(2, False, (7, 0), (7, 3), 2),
         drv(3, True, (7, 3), (7, 3), 3), drv(4, False, (7, 3), (7, 3), 4)]


def test_clean_game_has_no_flags_and_is_usable_everywhere():
    flags = drive_flags(CLEAN, (7, 3))
    assert flags == set()
    assert not quarantined(flags, "team_score") and not quarantined(flags, "play_derived")


def test_pbp_ending_early_quarantines_play_models_only():
    flags = drive_flags(CLEAN[:3], (31, 13))  # stops in Q3, like 2024 California-UC Davis
    assert "reconcile_pbp_ends_before_q4" in flags
    assert quarantined(flags, "play_derived") and not quarantined(flags, "team_score")


def test_corrupt_mid_game_score_is_caught_even_when_final_matches():
    # Like 2024 Tulane-Kansas State: one drive with a negative start and a jump to 35.
    bad = [drv(1, True, (0, 0), (7, 0)), drv(2, False, (7, -7), (35, 10), 2),
           drv(3, True, (7, 10), (14, 10), 3), drv(4, False, (14, 10), (14, 10), 4)]
    flags = drive_flags(bad, (14, 10))
    assert {"score_negative", "score_jump", "score_decrease"} <= flags
    assert not any(f.startswith("reconcile_") for f in flags)  # final still reconciles


@pytest.mark.parametrize("drives, final, expected", [
    ([], (7, 3), "no_drives"),
    ([drv(1, True, (0, 0), (7, 0)), drv(3, False, (7, 0), (7, 3), 4)], (7, 3), "drive_number_gap"),
    ([drv(1, True, (7, 0), (7, 3), 2), drv(2, False, (0, 0), (7, 0), 1)], (7, 3), "drive_number_order"),
    ([drv(1, True, (0, 0), (7, 0)), drv(2, False, (10, 3), (10, 6), 4)], (10, 6), "score_gap"),
    ([drv(1, True, (0, 0), (7, 0)), drv(2, False, (7, 0), (7, 0), 4)], (7, 0), None),
    ([drv(1, True, (0, 0), (7, 0)), drv(2, False, (11, 0), (11, 3), 4)], (11, 3), "score_gap"),
    ([dict(drv(1, True, (0, 0), (7, 0)), driveResult="TD"), drv(2, False, (6, 0), (6, 3), 4)], (6, 3),
     "try_inconsistency"),
    ([dict(drv(1, True, (0, 0), (3, 0)), driveResult="FG"), drv(2, False, (2, 0), (2, 3), 4)], (2, 3),
     "score_decrease"),
    ([drv(1, True, (0, 0), (7, 0)), drv(2, False, (7, 0), (7, 3), 4)], (8, 3), "reconcile_pbp_short_of_final"),
    ([drv(1, True, (0, 0), (8, 0)), drv(2, False, (8, 0), (8, 3), 4)], (7, 3), "reconcile_pbp_over_or_mixed"),
])
def test_each_flag(drives, final, expected):
    flags = drive_flags(drives, final)
    assert expected in flags if expected else flags == set()


def test_return_touchdown_between_drives_is_a_warning_not_a_quarantine():
    # Drive 2 ends in a punt; the punt is returned for a TD, so drive 3 starts 7 higher.
    drives = [drv(1, True, (0, 0), (7, 0)), dict(drv(2, False, (7, 0), (7, 0), 2), driveResult="PUNT"),
              drv(3, False, (14, 0), (14, 3), 3), drv(4, True, (14, 3), (14, 3), 4)]
    flags = drive_flags(drives, (14, 3))
    assert flags == {"score_between_drives"}
    assert not quarantined(flags, "play_derived")


def test_overtime_drives_are_not_jump_checked_but_decreases_are():
    ot = CLEAN[:-1] + [drv(4, False, (7, 3), (7, 10), 4), drv(5, True, (7, 10), (21, 10), 5)]
    assert "score_jump" not in drive_flags(ot, (21, 10))
    ot_bad = CLEAN[:-1] + [drv(4, False, (7, 3), (7, 10), 4), drv(5, True, (7, 10), (5, 10), 5)]
    assert "score_decrease" in drive_flags(ot_bad, (5, 10))


def test_misnumbered_drives_are_checked_in_game_order():
    # CFBD numbered these out of game order; in clock order the scores are consistent.
    d1 = dict(drv(1, True, (7, 0), (14, 0), 2), startTime={"minutes": 10, "seconds": 0})
    d2 = dict(drv(2, False, (0, 0), (7, 0), 1), startTime={"minutes": 12, "seconds": 0})
    d3 = dict(drv(3, False, (14, 0), (14, 3), 4), startTime={"minutes": 5, "seconds": 0})
    flags = drive_flags([d1, d2, d3], (14, 3))
    assert flags == {"drive_number_order"}
    assert not quarantined(flags, "play_derived")
