"""S01 on SYNTHETIC games (fabricated): fair coins give no survivors; a planted 60% cell survives Holm."""

import numpy as np
import pandas as pd

from cfb.evaluation import s01


def synth(seed: int, dog_cover: float = 0.5, n: int = 9000) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    spread = rng.choice([-24.5, -10.5, -3.5, 3.5, 10.5, 24.5], n)
    dog_home = spread > 0
    dog_wins = rng.uniform(size=n) < np.where(np.abs(spread) >= 21, dog_cover, 0.5)
    cover = np.where(dog_home, dog_wins, ~dog_wins).astype(float)
    season = rng.integers(2014, 2024, n)
    week = rng.integers(1, 15, n)
    return pd.DataFrame({"game_id": [f"g{i}" for i in range(n)], "season": season, "week": week,
                         "date": [f"{s}-{9 + w // 5:02d}-{1 + w:02d}T{i % 24:02d}:00" for i, (s, w) in enumerate(zip(season, week))],
                         "home": rng.integers(0, 130, n), "away": rng.integers(130, 260, n),
                         "neutral": rng.uniform(size=n) < 0.05, "spread": spread, "m": 0, "home_cover": cover,
                         "block": [f"{s}-{w}" for s, w in zip(season, week)]})


def test_holm_pads_untested_hypotheses():
    assert s01.holm({"a": 0.004, "b": 0.5}, 15) == {"a": False, "b": False}  # 0.004 > 0.05 / 15
    assert s01.holm({"a": 0.003, "b": 0.5}, 15) == {"a": True, "b": False}


def test_fair_coins_have_no_survivors():
    df = synth(1)
    assert s01.run(df, 15, (2014, 2023))["holm_survivors"] == []
    assert s01.run(s01.permuted(df), 15, (2014, 2023))["holm_survivors"] == []


def test_planted_big_favorite_edge_survives():
    r = s01.run(synth(2, dog_cover=0.62), 15, (2014, 2023))
    assert "C2_big_fav" in r["holm_survivors"]


def test_two_ats_losses_membership_and_push_breaks_streak():
    rows = [("g1", "2020-09-01", 1, 2, 0.0), ("g2", "2020-09-08", 1, 3, 0.0), ("g3", "2020-09-15", 1, 4, 1.0),
            ("g4", "2020-09-22", 5, 1, np.nan), ("g5", "2020-09-29", 1, 6, 1.0)]  # team 1 is home in g1-g3, g5
    df = pd.DataFrame([{"game_id": g, "season": 2020, "date": d, "home": h, "away": a, "home_cover": c}
                       for g, d, h, a, c in rows])
    t = s01.team_ats(df).set_index("game_id")
    assert t.loc["g3", "home_two_losses"]  # team 1 failed to cover g1 and g2
    assert not t.loc["g2", "home_two_losses"] and not t.loc["g5", "home_two_losses"]  # push in g4 resets it


def test_teaser_legs():
    df = pd.DataFrame({"spread": [-7.5, -7.5, 1.5], "m": [2, 1, -7]})  # fav wins by 2 (leg wins), by 1 (loses); dog loses by 7
    r = s01.teaser_legs(df)
    assert r["fav -7.5 to -1.5"] == {"n": 2, "win_rate": 0.5} and r["dog +1.5 to +7.5"]["win_rate"] == 1.0
