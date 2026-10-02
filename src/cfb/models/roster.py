"""R01: roster scenarios (methodology §5-6).

A scenario is one team's projected opportunity allocation and player abilities for a
season, built from information before the season:

- opportunity weights use the P03 game-1 rule: each roster player with prior-season
  opportunities in the category (on any team, so a transfer keeps his history) gets
  prior_weight * prior_share * n_ref + alpha; the UNKNOWN group (freshmen, unseen players,
  unassigned plays) gets kappa. Shares are weights normalized, so they sum to one;
- abilities are P04 predictive (mean, variance) per player and category; UNKNOWN gets the
  category's replacement level (new-player prior);
- strength per category is R = sum_i share_i * ability_i (methodology §6).

Moving a player between teams removes him from the origin, whose remaining players and
UNKNOWN absorb his share by renormalization, and adds him to the destination, diluting the
incumbents. Player IDs are never changed or merged. Paired comparisons draw each player's
ability once per draw and reuse it in both scenarios (common random numbers), so the
difference reflects the move, not simulation noise.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace

import numpy as np

from cfb.models.opportunity import UNKNOWN, ShareParams

CATS = ("passing", "rushing", "receiving")


@dataclass(frozen=True)
class Ability:
    mean: float
    var: float


@dataclass(frozen=True)
class Scenario:
    team: str
    season: int
    weights: dict[str, dict[str, float]]  # category -> athlete_id or UNKNOWN -> weight
    abilities: dict[str, dict[str, Ability]]  # category -> athlete_id or UNKNOWN -> ability
    prior_shares: dict[str, dict[str, float]] = field(default_factory=dict)  # category -> athlete -> share

    def shares(self, cat: str) -> dict[str, float]:
        w = self.weights.get(cat, {UNKNOWN: 1.0})
        total = sum(w.values())
        return {k: v / total for k, v in w.items()}

    def strength(self, cat: str) -> float:
        s = self.shares(cat)
        return float(sum(sh * self.abilities[cat][k].mean for k, sh in s.items()))

    def players(self) -> set[str]:
        return {a for w in self.weights.values() for a in w if a != UNKNOWN}


def build(team: str, season: int, roster: set[str], prior_shares: dict[str, dict[str, float]],
          abilities: dict[str, dict[str, Ability]], replacement: dict[str, Ability],
          params: ShareParams) -> Scenario:
    """`prior_shares[cat][athlete]`: last-season share (any team); `abilities[cat][athlete]`."""
    weights, abil, priors = {}, {}, {}
    for cat in CATS:
        w = {a: params.prior_season_weight * s * params.n_ref + params.alpha
             for a, s in prior_shares.get(cat, {}).items() if a in roster}
        w[UNKNOWN] = params.kappa
        weights[cat] = w
        abil[cat] = {a: abilities.get(cat, {}).get(a, replacement[cat]) for a in w if a != UNKNOWN}
        abil[cat][UNKNOWN] = replacement[cat]
        priors[cat] = {a: prior_shares[cat][a] for a in w if a != UNKNOWN}
    return Scenario(team, season, weights, abil, priors)


def move(origin: Scenario, dest: Scenario, athlete: str, params: ShareParams,
         abilities: dict[str, Ability] | None = None) -> tuple[Scenario, Scenario]:
    """New (origin, destination) scenarios with `athlete` moved. His prior shares and
    abilities travel with him; nothing else about either team changes."""
    o_w, d_w, o_a, d_a, d_p = {}, {}, {}, {}, {}
    for cat in CATS:
        o_w[cat] = {k: v for k, v in origin.weights[cat].items() if k != athlete}
        o_a[cat] = {k: v for k, v in origin.abilities[cat].items() if k != athlete}
        d_w[cat], d_a[cat], d_p[cat] = dict(dest.weights[cat]), dict(dest.abilities[cat]), dict(dest.prior_shares[cat])
        share = origin.prior_shares.get(cat, {}).get(athlete)
        if share is not None:
            d_w[cat][athlete] = params.prior_season_weight * share * params.n_ref + params.alpha
            d_p[cat][athlete] = share
            d_a[cat][athlete] = (abilities or {}).get(cat) or origin.abilities[cat][athlete]
    return (replace(origin, weights=o_w, abilities=o_a),
            replace(dest, weights=d_w, abilities=d_a, prior_shares=d_p))


def _seed(root: int, athlete: str, cat: str) -> int:
    return int.from_bytes(hashlib.sha256(f"{root}|{athlete}|{cat}".encode()).digest()[:8], "little")


def strength_draws(scn: Scenario, cat: str, draws: int, root_seed: int) -> np.ndarray:
    """Category strength draws. Each player's ability draws depend only on (seed, athlete,
    category), so two scenarios containing the same player share his draws."""
    out = np.zeros(draws)
    for k, sh in scn.shares(cat).items():
        a = scn.abilities[cat][k]
        z = np.random.Generator(np.random.PCG64(_seed(root_seed, k, cat))).standard_normal(draws)
        out += sh * (a.mean + np.sqrt(a.var) * z)
    return out


def paired_change(before: Scenario, after: Scenario, cat: str, draws: int, root_seed: int) -> dict[str, float]:
    """Expected change, 80% interval and probability of improvement for one team's
    category strength between two scenarios, using common random numbers."""
    d = strength_draws(after, cat, draws, root_seed) - strength_draws(before, cat, draws, root_seed)
    lo, hi = np.quantile(d, [0.1, 0.9])
    return {"expected": float(d.mean()), "q10": float(lo), "q90": float(hi), "p_improve": float((d > 0).mean())}
