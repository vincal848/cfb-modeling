"""R02 mover/stayer labelling, gaps and censoring on SYNTHETIC players (fabricated)."""

import numpy as np
import pandas as pd
import pytest

from cfb.evaluation.r02 import adaptation_table, appearance, main_team, tier, weighted_gap


def test_tiers():
    assert tier("SEC", True) == "P5" and tier("Sun Belt", True) == "G5"
    assert tier("FBS Independents", True) == "IND" and tier("Big Sky", False) == "FCS/other"


def stats():
    return pd.DataFrame([
        ("m", 2020, "Low U", "p1"), ("m", 2020, "Low U", "p2"), ("m", 2021, "Big U", "p3"),
        ("s", 2020, "Big U", "p4"), ("s", 2021, "Big U", "p5"),
        ("gone", 2020, "Big U", "p6"),
    ], columns=["athlete_id", "season", "team", "play_id"])


def test_movers_get_directions_and_residuals():
    pred = pd.DataFrame([{"athlete_id": a, "season": 2021, "category": "rushing", "group": "RB", "y": y,
                          "n": 50, "model_mean": 0.0, "has_history": True} for a, y in (("m", -0.2), ("s", 0.1))])
    tiers = {("Low U", 2020): "G5", ("Big U", 2021): "P5", ("Big U", 2020): "P5"}
    d = adaptation_table(pred, main_team(stats()), tiers).set_index("athlete_id")
    assert d.loc["m", "mover"] and d.loc["m", "direction"] == "G5 -> P5"
    assert not d.loc["s", "mover"] and d.loc["s", "direction"] == "stayed"
    assert d.loc["m", "residual"] == pytest.approx(-0.2)


def test_weighted_gap_has_an_interval_around_the_point():
    rng = np.random.default_rng(0)
    mv = pd.DataFrame({"residual": rng.normal(-0.1, 0.2, 200), "n": 40})
    st = pd.DataFrame({"residual": rng.normal(0.0, 0.2, 800), "n": 40})
    gap, lo, hi = weighted_gap(mv, st, 500, 1)
    assert lo < gap < hi and -0.15 < gap < -0.05


def test_appearance_separates_movers_stayers_and_exits():
    rosters = {2021: {"Big U": {"m", "s"}}}
    out = appearance(stats(), rosters, 2021)
    assert out["mover"] == (1, 1) and out["stayer"] == (1, 1) and out["not on a roster"] == (0, 1)
