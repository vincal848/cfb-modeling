import pandas as pd

from cfb.evaluation import t01


def test_shift_uses_offsets_on_the_game_date():
    summer, winter = pd.Timestamp("2023-09-30", tz="UTC"), pd.Timestamp("2023-12-02", tz="UTC")
    diff = lambda a, b, t: abs(t01.utc_offset(a, t) - t01.utc_offset(b, t))
    assert diff("America/New_York", "America/Chicago", summer) == 1 == diff("America/New_York", "America/Chicago", winter)
    assert diff("America/Phoenix", "America/Los_Angeles", summer) == 0  # Arizona skips DST
    assert diff("America/Phoenix", "America/Los_Angeles", winter) == 1


def test_cell_keeps_only_late_regular_away_underdogs_one_zone_apart():
    base = {"season_type": "regular", "week": 10, "neutral": False, "spread": -3.0, "date": "2023-11-04T20:00:00Z"}
    df = pd.DataFrame([{**base, "game_id": "ok", "home": 1, "away": 2},
                       {**base, "game_id": "early", "home": 1, "away": 2, "week": 5},
                       {**base, "game_id": "far", "home": 1, "away": 3},
                       {**base, "game_id": "home_dog", "home": 1, "away": 2, "spread": 3.0},
                       {**base, "game_id": "neutral", "home": 1, "away": 2, "neutral": True}])
    tz = {1: "America/New_York", 2: "America/Chicago", 3: "America/Los_Angeles"}
    got, counts = t01.cell(df, tz)
    assert list(got["game_id"]) == ["ok"] and counts["candidates"] == 2
