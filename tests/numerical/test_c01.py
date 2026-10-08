import pandas as pd

from cfb.evaluation import c01


def games():
    return pd.DataFrame({
        "game_id": ["a", "b", "c", "d"], "season_type": "regular", "week": [1, 5, 2, 9],
        "date": ["2023-09-02T23:00:00Z", "2023-10-04T23:00:00Z", "2023-09-09T23:00:00Z", "2023-10-28T20:00:00Z"],
        "home_class": ["fbs", "fbs", "fbs", "fbs"], "away_class": ["fcs", "fbs", "fbs", "fbs"],
        "home_conf": ["SEC", "Sun Belt", "Big Ten", "Mid-American"], "away_conf": ["X", "SEC", "Mountain West", "ACC"]})


def test_cohort_definitions():
    df = games()
    assert c01.cohort_ids(df, "fcs") == {"a"}
    assert c01.cohort_ids(df, "g5_midweek") == {"b"}  # Wednesday with a Sun Belt team; c and d are Saturdays
    assert c01.cohort_ids(df, "early") == {"a", "c"}


def test_low_volume_tercile():
    assert c01.terciles({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6}) == {"a", "b"}
