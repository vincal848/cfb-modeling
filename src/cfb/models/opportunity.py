"""P03: hierarchical opportunity shares (methodology §4).

Categories (CFBD /plays/stats statTypes, by athlete ID):

- dropbacks: Completion, Incompletion, Sack Taken (and Interception Thrown when present);
- carries: Rush;
- targets: Reception, Target.

Team totals come from the team's own plays in /plays. Opportunities the play stats do not
attribute to a player form an explicit `UNASSIGNED` count, never dropped (methodology §4:
"explicit unassigned category where attribution is incomplete").

Share model (empirical-Bayes Dirichlet), per team, category and game, using only earlier
games of the season, the previous season, and the season's roster:

    weight_i = decayed past counts_i + w_prev * prior-season share_i * N_ref + alpha
    weight_unknown = kappa + decayed past unassigned counts
    share = weight / sum(weight)

Candidates are players with earlier opportunities this season for the team, plus players
on the team's roster this season who had opportunities in the category last season (on
any team: a transfer keeps his history). New players and unassigned opportunities fall in
the UNKNOWN group, so mass is never renormalized onto only the known players. Shares sum
to one, so expected counts (share * team total) conserve the team total exactly.

P(any opportunity) for player i is 1 - (1 - s_i)^N for team total N: derived from the same
shares, so the two estimands cannot contradict each other.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

import numpy as np
import pandas as pd

CATEGORIES = {
    "dropbacks": ("Completion", "Incompletion", "Sack Taken", "Interception Thrown"),
    "carries": ("Rush",),
    "targets": ("Reception", "Target"),
}
UNKNOWN = "UNKNOWN"  # new players plus unassigned opportunities
UNASSIGNED = "UNASSIGNED"

# Team-level play types counted toward each category's total (CFBD /plays).
TEAM_PLAY_TYPES = {
    "dropbacks": ("Pass Reception", "Pass Incompletion", "Passing Touchdown", "Sack", "Interception",
                  "Pass Interception Return", "Interception Return Touchdown"),
    "carries": ("Rush", "Rushing Touchdown"),
    "targets": ("Pass Reception", "Pass Incompletion", "Passing Touchdown", "Interception",
                "Pass Interception Return", "Interception Return Touchdown"),
}


@dataclass(frozen=True)
class ShareParams:
    half_life_games: float = 3.0
    prior_season_weight: float = 0.5
    alpha: float = 0.5  # pseudo-count per candidate
    kappa: float = 2.0  # pseudo-count for the unknown group
    n_ref: float = 30.0  # typical team total used to scale prior-season shares


def player_counts(play_stats: pd.DataFrame) -> pd.DataFrame:
    """game_id, team, athlete_id, category, n from /plays/stats rows (one row per play and
    athlete per category, so duplicate stat rows on one play count once)."""
    frames = []
    for cat, types in CATEGORIES.items():
        sub = play_stats[play_stats["statType"].isin(types)]
        sub = sub.drop_duplicates(["playId", "athleteId"])
        g = sub.groupby(["gameId", "team", "athleteId"]).size().rename("n").reset_index()
        frames.append(g.assign(category=cat))
    out = pd.concat(frames, ignore_index=True)
    return out.rename(columns={"gameId": "game_id", "athleteId": "athlete_id"})


def team_totals(plays: pd.DataFrame) -> pd.DataFrame:
    """game_id, team, category, total from the team's own plays."""
    frames = []
    for cat, types in TEAM_PLAY_TYPES.items():
        sub = plays[plays["playType"].isin(types)]
        g = sub.groupby(["gameId", "offense"]).size().rename("total").reset_index()
        frames.append(g.assign(category=cat))
    return pd.concat(frames, ignore_index=True).rename(columns={"gameId": "game_id", "offense": "team"})


@dataclass
class Forecast:
    shares: dict[str, float]  # athlete_id or UNKNOWN -> share
    total: int

    def expected_counts(self) -> dict[str, float]:
        return {k: v * self.total for k, v in self.shares.items()}

    def p_any(self, athlete_id: str) -> float:
        return 1.0 - (1.0 - self.shares.get(athlete_id, 0.0)) ** self.total


def forecast_shares(history: list[dict[str, int]], unassigned_history: list[int],
                    prior_shares: dict[str, float], params: ShareParams) -> dict[str, float]:
    """Shares for the next game.

    `history` holds earlier games of this season in order (oldest first), each a dict of
    athlete_id -> attributed count; `unassigned_history` the matching unassigned counts;
    `prior_shares` the prior-season shares of players on this season's roster.
    """
    decay = np.power(0.5, np.arange(len(history))[::-1] / params.half_life_games) if history else np.array([])
    weights: dict[str, float] = defaultdict(float)
    for w, game in zip(decay, history, strict=True):
        for aid, n in game.items():
            weights[aid] += w * n
    for aid, s in prior_shares.items():
        weights[aid] += params.prior_season_weight * s * params.n_ref
    unknown = params.kappa + float(sum(w * u for w, u in zip(decay, unassigned_history, strict=True)))
    out = {aid: w + params.alpha for aid, w in weights.items()}
    out[UNKNOWN] = unknown
    total = sum(out.values())
    return {k: v / total for k, v in out.items()}


def log_score(shares: dict[str, float], observed: dict[str, int], unassigned: int) -> tuple[float, int]:
    """Sum of -log share over the game's opportunities (new players and unassigned count
    against UNKNOWN), and the number of opportunities."""
    loss, n_total = 0.0, 0
    unknown_n = unassigned
    for aid, n in observed.items():
        if aid in shares:
            loss -= n * np.log(shares[aid])
        else:
            unknown_n += n
        n_total += n
    loss -= unknown_n * np.log(shares[UNKNOWN])
    return loss, n_total + unassigned
