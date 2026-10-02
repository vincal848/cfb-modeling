"""R02: destination context and adaptation for players who change teams (methodology §5).

Descriptive and predictive, not causal: movers select themselves, so a mover-stayer gap is
an association conditional on the P04 forecast, not the effect of transferring.

- Mover: a player whose team (the team he recorded the most opportunities for) differs
  between consecutive seasons; stayers keep the same team.
- Adaptation: residual = actual season EPA per opportunity minus the P04 held-forward
  forecast from his history before that season; movers' mean residual minus stayers', by
  category, position group and move direction (P5, G5, FBS independent, FCS/other), with
  a bootstrap over players.
- Censoring: of players with opportunities in season t-1, the share with any opportunity
  in season t, for roster movers and stayers. Non-appearance is reported as such and never
  scored as zero ability.
- Support: every direction cell reports its count; cells under MIN_SUPPORT are flagged.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

P5 = {"SEC", "Big Ten", "Big 12", "ACC", "Pac-12"}
MIN_SUPPORT = 30


def tier(conference: str | None, fbs: bool) -> str:
    if not fbs:
        return "FCS/other"
    if conference in P5:
        return "P5"
    if conference in (None, "", "FBS Independents"):
        return "IND"
    return "G5"


def team_tiers(ledger, seasons: list[int]) -> dict[tuple[str, int], str]:
    """(team name, season) -> tier from /games conference fields and /teams/fbs."""
    out = {}
    for s in seasons:
        fbs_e = ledger.latest_success("/teams/fbs", {"year": s})
        fbs = {t["school"] for t in ledger.load(fbs_e)} if fbs_e else set()
        for st in ("regular", "postseason"):
            e = ledger.latest_success("/games", {"year": s, "seasonType": st})
            for g in ledger.load(e) if e else []:
                for side in ("home", "away"):
                    name = g.get(f"{side}Team")
                    if name and (name, s) not in out:
                        out[(name, s)] = tier(g.get(f"{side}Conference"), name in fbs)
    return out


def main_team(stats: pd.DataFrame) -> pd.DataFrame:
    """(athlete_id, season) -> team with the most opportunities that season."""
    c = stats.groupby(["athlete_id", "season", "team"]).size().rename("n").reset_index()
    return c.sort_values("n").groupby(["athlete_id", "season"]).tail(1)[["athlete_id", "season", "team"]]


def adaptation_table(pred: pd.DataFrame, teams: pd.DataFrame, tiers: dict) -> pd.DataFrame:
    """P04 predictions (with history) labelled mover/stayer and move direction."""
    cur = teams.rename(columns={"team": "team_now"})
    prev = teams.assign(season=teams["season"] + 1).rename(columns={"team": "team_before"})
    d = pred[pred["has_history"]].merge(cur, on=["athlete_id", "season"]).merge(prev, on=["athlete_id", "season"])
    d["mover"] = d["team_now"] != d["team_before"]
    d["from_tier"] = [tiers.get((t, s - 1), "FCS/other") for t, s in zip(d["team_before"], d["season"], strict=True)]
    d["to_tier"] = [tiers.get((t, s), "FCS/other") for t, s in zip(d["team_now"], d["season"], strict=True)]
    d["direction"] = np.where(d["mover"], d["from_tier"] + " -> " + d["to_tier"], "stayed")
    d["residual"] = d["y"] - d["model_mean"]
    return d


def weighted_gap(movers: pd.DataFrame, stayers: pd.DataFrame, reps: int, seed: int) -> tuple[float, float, float]:
    """Opportunity-weighted mean residual of movers minus stayers, bootstrap over players."""
    rng = np.random.Generator(np.random.PCG64(seed))

    def wmean(d, idx):
        return float(np.average(d["residual"].to_numpy()[idx], weights=d["n"].to_numpy()[idx]))

    m_idx, s_idx = np.arange(len(movers)), np.arange(len(stayers))
    point = wmean(movers, m_idx) - wmean(stayers, s_idx)
    boots = [wmean(movers, rng.choice(m_idx, len(m_idx))) - wmean(stayers, rng.choice(s_idx, len(s_idx)))
             for _ in range(reps)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return point, float(lo), float(hi)


def appearance(stats: pd.DataFrame, rosters: dict[int, dict[str, set[str]]], season: int) -> dict[str, tuple[int, int]]:
    """Among players with opportunities in season-1: (appeared in season, total) for roster
    movers (listed on a different team's roster in season) and stayers (same team's roster)."""
    prev_players = main_team(stats[stats["season"] == season - 1])
    played_now = set(stats.loc[stats["season"] == season, "athlete_id"])
    roster_team = {a: t for t, ids in rosters.get(season, {}).items() for a in ids}
    out = {"mover": [0, 0], "stayer": [0, 0], "not on a roster": [0, 0]}
    for a, team in zip(prev_players["athlete_id"], prev_players["team"], strict=True):
        now = roster_team.get(a)
        key = "not on a roster" if now is None else ("stayer" if now == team else "mover")
        out[key][1] += 1
        out[key][0] += a in played_now
    return {k: (v[0], v[1]) for k, v in out.items()}
