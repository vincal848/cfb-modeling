"""D08: per-game score and coverage quality flags, and quarantine per model family.

The official `/games` result is the outcome of record (D02). Play-by-play is checked
against it and against itself; a game failing a play-level check is quarantined from
play-derived models only. Team-score models need just the official result. A game is
marked incomplete rather than repaired (methodology §2).

Drive-level checks, in home/away terms, with drives ordered by `driveNumber`:

- `no_drives`: the game has no drive records.
- `reconcile_<kind>`: the last drive's end score versus the official final (D02 kinds).
- `score_negative`: any negative score on a drive boundary.
- `score_decrease`: a team's score drops within or between drives.
- `score_gap`: between drives, both teams' scores change, or one changes by an amount
  no single score produces.
- `score_between_drives` (warning): one team's score rises between drives by a valid
  single-score amount. Inspection of 2023 showed these follow punts, interceptions and
  fumbles: return touchdowns that CFBD does not credit to a drive.
- `try_inconsistency` (warning): after a touchdown drive, the scoring team's score
  drops by 1 or 2 at the next drive's start; the drive's end score assumed a try that
  failed.
- `score_jump`: in regulation, a drive changes a team's score by an amount one
  possession cannot produce (allowed: 0, 1, 2, 3, 6, 7, 8 per team). Overtime drives
  (period > 4) are checked only for decreases, since provider overtime drive records
  can span several scores.
- `drive_number_gap`: drive numbers are not 1..n.
- `drive_number_order` (warning): drive numbers do not follow game order (period, then
  clock). Found in 2021+ games; every check, including reconciliation with the final,
  then uses game order.
- `missing_team_stats`: no `/games/teams` record (informational).

Warnings are not quarantine flags. These drive-level checks are proxies; the P01 play
state machine reconciles scoring play by play and supersedes them for play models.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

PER_DRIVE_POINTS = {0, 1, 2, 3, 6, 7, 8}

PLAY_FLAGS = (
    "no_drives", "reconcile_pbp_ends_before_q4", "reconcile_pbp_short_of_final",
    "reconcile_pbp_over_or_mixed", "score_negative", "score_decrease", "score_gap",
    "score_jump", "drive_number_gap",
)
FAMILIES = {
    # Model family -> flags that quarantine a game for it.
    "team_score": ("result_missing",),
    "play_derived": ("result_missing", *PLAY_FLAGS),
}


def _home_away(d: dict[str, Any], which: str) -> tuple[int, int] | None:
    off, dfn = d.get(f"{which}OffenseScore"), d.get(f"{which}DefenseScore")
    if off is None or dfn is None or d.get("isHomeOffense") is None:
        return None
    return (off, dfn) if d["isHomeOffense"] else (dfn, off)


def _between_drives(prev_end: tuple[int, int], start: tuple[int, int], prev_result: str | None) -> str:
    """Classify a score change between one drive's end and the next drive's start."""
    dh, da = start[0] - prev_end[0], start[1] - prev_end[1]
    if dh >= 0 and da >= 0:
        # A return touchdown, safety or other non-drive score: one team, one valid amount.
        one_team = (dh == 0) != (da == 0)
        return "score_between_drives" if one_team and {dh, da} <= PER_DRIVE_POINTS else "score_gap"
    # A touchdown drive's end score that assumed the try succeeded, corrected at the next
    # drive's start (missed kick or failed two-point try): -1 or -2 for the scoring team only.
    if "TD" in (prev_result or "") and {dh, da} - {0} in ({-1}, {-2}):
        return "try_inconsistency"
    return "score_decrease"


def _game_order(d: dict[str, Any]) -> tuple[int, int, int]:
    clock = d.get("startTime") or {}
    remaining = 60 * (clock.get("minutes") or 0) + (clock.get("seconds") or 0)
    return (d.get("startPeriod") or 0, -remaining, d.get("driveNumber") or 0)


def drive_flags(drives: Iterable[dict[str, Any]], final: tuple[int, int] | None) -> set[str]:
    from cfb.ingestion.coverage import classify_drive_mismatch

    by_number = sorted(drives, key=lambda d: d.get("driveNumber") or 0)
    flags: set[str] = set()
    if not by_number:
        return {"no_drives"}
    numbers = [d.get("driveNumber") for d in by_number]
    if numbers != list(range(1, len(by_number) + 1)):
        flags.add("drive_number_gap")
    # Score checks follow game order (period, then clock counting down), not driveNumber:
    # in some 2021+ games CFBD numbers drives out of game order.
    ds = sorted(by_number, key=_game_order)
    if [d.get("driveNumber") for d in ds] != numbers:
        flags.add("drive_number_order")

    prev_end, prev_result = None, None
    for d in ds:
        start, end = _home_away(d, "start"), _home_away(d, "end")
        if start is None or end is None:
            flags.add("score_gap")
            prev_end = end
            continue
        if min(*start, *end) < 0:
            flags.add("score_negative")
        if prev_end is not None and start != prev_end:
            flags.add(_between_drives(prev_end, start, prev_result))
        delta = (end[0] - start[0], end[1] - start[1])
        if delta[0] < 0 or delta[1] < 0:
            flags.add("score_decrease")
        elif (d.get("startPeriod") or 0) <= 4 and not all(x in PER_DRIVE_POINTS for x in delta):
            flags.add("score_jump")
        prev_end, prev_result = end, d.get("driveResult") or ""

    if final is not None:
        last = ds[-1]  # last drive in game order
        end = _home_away(last, "end") or (-1, -1)
        kind = classify_drive_mismatch((len(ds), *end, last.get("endPeriod") or 0), final)
        if kind != "match":
            flags.add(f"reconcile_{kind}")
    return flags


def quarantined(flags: set[str], family: str) -> bool:
    return bool(flags & set(FAMILIES[family]))


def assess(conn, ledger, seasons: list[int]):
    """Flags for every population game in `seasons` (canonical facts plus cached drives and
    team stats). Returns a DataFrame with one row per game."""
    import pandas as pd

    from cfb.canonical.games import game_id
    from cfb.evaluation.backtest import latest_facts

    schedules = [s for s in latest_facts(conn, "game_schedule") if s["season"] in seasons]
    results = {r["game_id"]: r for r in latest_facts(conn, "game_result")}
    drives: dict[str, list] = {}
    stats: set[str] = set()
    for season in seasons:
        cal = ledger.latest_success("/calendar", {"year": season})
        for wk in ledger.load(cal) if cal else []:
            p = {"year": season, "week": wk["week"], "seasonType": wk["seasonType"]}
            e = ledger.latest_success("/drives", p)
            for d in ledger.load(e) if e else []:
                drives.setdefault(game_id(d["gameId"]), []).append(d)
            e = ledger.latest_success("/games/teams", p)
            stats |= {game_id(g["id"]) for g in (ledger.load(e) if e else [])}
    rows = []
    for s in schedules:
        gid = s["game_id"]
        r = results.get(gid)
        final = (r["home_points"], r["away_points"]) if r else None
        flags = set() if final else {"result_missing"}
        flags |= drive_flags(drives.get(gid, []), final)
        if gid not in stats:
            flags.add("missing_team_stats")
        rows.append({"game_id": gid, "season": s["season"], "season_type": s["season_type"],
                     "week": s["week"], "flags": sorted(flags),
                     **{f"quarantine_{fam}": quarantined(flags, fam) for fam in FAMILIES}})
    return pd.DataFrame(rows).sort_values(["season", "game_id"]).reset_index(drop=True)
