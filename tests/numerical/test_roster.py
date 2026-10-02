"""R01 roster scenarios on SYNTHETIC rosters (fabricated)."""

import pytest

from cfb.models.opportunity import UNKNOWN, ShareParams
from cfb.models.roster import Ability, build, move, paired_change, strength_draws

P = ShareParams(half_life_games=2, prior_season_weight=0.5, alpha=0.1, kappa=3, n_ref=30)
REPL = {c: Ability(-0.1, 0.04) for c in ("passing", "rushing", "receiving")}


def teams():
    a = build("A", 2021, {"qbA", "qbA2", "rbA"},
              {"passing": {"qbA": 0.9, "qbA2": 0.1, "qbB": 0.8}, "rushing": {"rbA": 0.6, "qbA": 0.1}},
              {"passing": {"qbA": Ability(0.30, 0.01), "qbA2": Ability(0.0, 0.03)},
               "rushing": {"rbA": Ability(0.1, 0.01), "qbA": Ability(0.05, 0.02)}}, REPL, P)
    b = build("B", 2021, {"qbB"}, {"passing": {"qbB": 0.8}}, {"passing": {"qbB": Ability(0.10, 0.01)}}, REPL, P)
    return a, b


def test_shares_sum_to_one_with_unknown_and_roster_filter():
    a, b = teams()
    for scn in (a, b):
        for cat in ("passing", "rushing", "receiving"):
            assert sum(scn.shares(cat).values()) == pytest.approx(1.0)
            assert UNKNOWN in scn.shares(cat)
    assert "qbB" not in a.shares("passing")  # not on A's roster


def test_transfer_redistributes_and_preserves_ids():
    a, b = teams()
    a2, b2 = move(a, b, "qbA", P)
    assert "qbA" not in a2.players() and "qbA" in b2.players()
    for scn in (a2, b2):
        assert sum(scn.shares("passing").values()) == pytest.approx(1.0)
    # Origin: the backup and UNKNOWN absorb the starter's share; destination incumbent is diluted.
    assert a2.shares("passing")["qbA2"] > a.shares("passing")["qbA2"]
    assert a2.shares("passing")[UNKNOWN] > a.shares("passing")[UNKNOWN]
    assert b2.shares("passing")["qbB"] < b.shares("passing")["qbB"]
    # His ability travels with him unchanged; nobody else's changes.
    assert b2.abilities["passing"]["qbA"] == a.abilities["passing"]["qbA"]
    assert b2.abilities["passing"]["qbB"] == b.abilities["passing"]["qbB"]
    # Rushing: he leaves A's rushing group too.
    assert "qbA" not in a2.shares("rushing")


def test_paired_change_uses_common_random_numbers():
    a, b = teams()
    _, b2 = move(a, b, "qbA", P)
    change = paired_change(b, b2, "passing", 4000, 7)
    assert change["expected"] == pytest.approx(b2.strength("passing") - b.strength("passing"), abs=0.01)
    assert change["p_improve"] > 0.9  # adding a much better QB
    # Common random numbers: identical scenarios give exactly zero change on every draw.
    same = strength_draws(b, "passing", 1000, 7) - strength_draws(b, "passing", 1000, 7)
    assert (same == 0).all()
