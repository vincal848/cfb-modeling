"""V01 cohort labels for scored games. Labels describe games after the fact for reporting;
they are never model inputs, so they may use the latest data."""

from __future__ import annotations

import pandas as pd

from cfb.canonical.games import game_id
from cfb.ingestion.coverage import classify_drive_mismatch, reduce_drives
from cfb.ingestion.ledger import RawLedger

COHORTS = ("early_season", "fbs_vs_nonfbs", "postseason", "neutral_site", "season_2020",
           "pbp_unreconciled", "missing_team_stats", "no_line")


def _cached(ledger: RawLedger, path: str, params: dict) -> list:
    entry = ledger.latest_success(path, params)
    return ledger.load(entry) if entry is not None else []


def label_cohorts(games: pd.DataFrame, ledger: RawLedger) -> pd.DataFrame:
    """`games` has game_id, season, season_type, week, start, home, away, neutral, home_fbs,
    away_fbs, home_points, away_points (one row per scored game)."""
    df = games.sort_values(["start", "game_id"]).reset_index(drop=True)

    # Games each team completed earlier in the same season (a team never has two games at
    # the same kickoff, so kickoff order is enough).
    played: dict[tuple[str, int], int] = {}
    before = []
    for g in df.itertuples(index=False):
        before.append(min(played.get((g.home, g.season), 0), played.get((g.away, g.season), 0)))
        for t in (g.home, g.away):
            played[(t, g.season)] = played.get((t, g.season), 0) + 1
    # Counts population games only, so a non-FBS team's games against non-FBS opponents are
    # not counted; such teams can look earlier in their season than they are.
    df["_min_prior"] = before

    stats_ids, line_ids, drives = set(), set(), {}
    for season in sorted(df["season"].unique()):
        season = int(season)
        for wk in _cached(ledger, "/calendar", {"year": season}):
            p = {"year": season, "week": wk["week"], "seasonType": wk["seasonType"]}
            stats_ids |= {game_id(g["id"]) for g in _cached(ledger, "/games/teams", p)}
            for gid, d in reduce_drives(_cached(ledger, "/drives", p)).items():
                drives[game_id(gid)] = d
        for st in ("regular", "postseason"):
            for g in _cached(ledger, "/lines", {"year": season, "seasonType": st}):
                if any(ln.get("spread") is not None for ln in g.get("lines") or []):
                    line_ids.add(game_id(g["id"]))

    def unreconciled(row) -> bool:
        d = drives.get(row.game_id)
        return d is None or d[0] == 0 or classify_drive_mismatch(d, (row.home_points, row.away_points)) != "match"

    out = pd.DataFrame({"game_id": df["game_id"]})
    out["early_season"] = (df["season_type"] == "regular") & (df["_min_prior"] < 3)
    out["fbs_vs_nonfbs"] = df["home_fbs"] != df["away_fbs"]
    out["postseason"] = df["season_type"] == "postseason"
    out["neutral_site"] = df["neutral"].astype(bool)
    out["season_2020"] = df["season"] == 2020
    out["pbp_unreconciled"] = [unreconciled(r) for r in df.itertuples(index=False)]
    out["missing_team_stats"] = ~df["game_id"].isin(stats_ids)
    out["no_line"] = ~df["game_id"].isin(line_ids)
    return out
