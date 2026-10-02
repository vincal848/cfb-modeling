"""winner_v1 forced pick (methodology §9, config policies.winner)."""

from __future__ import annotations

POLICY_VERSION = "winner_v1"


def winner_v1(home_win_probability: float, home_team_id: str, away_team_id: str) -> str:
    """Home above 0.5, away below, and the lexicographically smaller canonical ID on an
    exact tie. Uses the unrounded probability."""
    if home_win_probability > 0.5:
        return home_team_id
    if home_win_probability < 0.5:
        return away_team_id
    return min(home_team_id, away_team_id)
