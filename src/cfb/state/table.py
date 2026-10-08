"""P01 (state): per-play preplay states, next-score labels and transition checks.

Built only for games whose scoring reconciles exactly (P01 scoring tier), so pre-play
scores and the scoring timeline are trustworthy. Overtime plays are excluded: the EP
model covers regulation (methodology §3 fits EP on regulation states; overtime has its
own possession rules).

State per scrimmage play, from the offense's perspective: down, distance, yards to goal,
seconds left in the half, score margin before the play, timeouts, and the next scoring
event in the same half (`next_score`): one of TD/FG/SAFETY for or against the offense,
or NONE if the half ends first.

Transition checks are diagnostics. They measure how consistent CFBD's own fields are
between consecutive scrimmage plays of one possession; they do not drop plays:

- `down_ok`: the next play's down is 1 after a gain of at least the distance, otherwise
  down + 1 (plays with penalties in their text are not checked);
- `yards_ok`: the next yards to goal equals this one minus the yards gained;
- `clock_ok`: the clock does not run backwards within a period;
- `kickoff_after_score_ok`: after a touchdown or field goal the next row is a kickoff by
  the scoring team (end-of-half rows aside);
- `half_starts_with_kickoff`: each half's first play is a kickoff (registry: halftime).
"""

from __future__ import annotations

from itertools import pairwise
from typing import Any

import pandas as pd

from cfb.state.machine import SCORELESS_TYPES, _drop_stale, _home_away
from cfb.state.scoring import ScoringRules, classify_play

KICK_TYPES = {"Kickoff", "Kickoff Return (Offense)", "Kickoff Return Touchdown", "Onside Kick"}
NON_SCRIMMAGE = SCORELESS_TYPES | KICK_TYPES | {"Two Point Pass", "Two Point Rush", "Two Point Conversion",
                                                "Extra Point Good", "Extra Point Missed"}
LABELS = ("TD_FOR", "FG_FOR", "SAFETY_FOR", "TD_AGAINST", "FG_AGAINST", "SAFETY_AGAINST", "NONE")


def _seconds(clock: dict | None) -> int | None:
    if not clock:
        return None
    return 60 * (clock.get("minutes") or 0) + (clock.get("seconds") or 0)


def game_states(plays: list[dict[str, Any]], rules: ScoringRules,
                score_columns_swapped: bool = False) -> tuple[pd.DataFrame, dict[str, int]]:
    """States for one exact-reconciling game, and transition-check counts.

    Pre-play scores come from CFBD's after-play scores on the previous score-bearing row,
    read the same way the reconciliation read them (stale rows dropped, columns swapped
    if the game needed it), so inferred tries are included.
    """
    ordered = sorted((p for p in plays if (p.get("period") or 0) <= 4), key=lambda p: (p["period"], int(p["id"])))
    bearing = [(p, s) for p in ordered if p.get("playType") not in SCORELESS_TYPES
               and (s := _home_away(p, score_columns_swapped)) is not None]
    kept, _ = _drop_stale(bearing)
    after = {p["id"]: s for p, s in kept}
    # Scoring events in order, with the half they fall in and the scoring team.
    events = []
    for i, p in enumerate(ordered):
        e = classify_play(p, rules)
        if e.kind in ("touchdown", "field_goal", "safety"):
            team = p["offense"] if e.scorer == "offense" else p["defense"]
            events.append((i, 1 if p["period"] <= 2 else 2, e.kind, team))

    rows, checks = [], dict.fromkeys(
        ("down_checked", "down_ok", "yards_checked", "yards_ok", "clock_checked", "clock_ok",
         "score_checked", "kickoff_after_score_ok", "halves", "half_starts_with_kickoff"), 0)
    last = (0, 0)  # (home, away) after the previous score-bearing row
    ev_ptr = 0
    prev_clock, prev_period = None, None
    for i, p in enumerate(ordered):
        half = 1 if p["period"] <= 2 else 2
        sec = _seconds(p.get("clock"))
        if prev_period == p["period"] and sec is not None and prev_clock is not None:
            checks["clock_checked"] += 1
            checks["clock_ok"] += sec <= prev_clock
        prev_clock, prev_period = sec, p["period"]
        while ev_ptr < len(events) and events[ev_ptr][0] < i:
            ev_ptr += 1
        e = classify_play(p, rules)
        off, dfn = p["offense"], p["defense"]
        home_off = off == p.get("home")
        pre_margin = (last[0] - last[1]) if home_off else (last[1] - last[0])
        new = after.get(p["id"], last)
        delta_home, delta_away = new[0] - last[0], new[1] - last[1]
        off_pts, def_pts = (delta_home, delta_away) if home_off else (delta_away, delta_home)
        if p.get("playType") not in NON_SCRIMMAGE and p.get("down") in (1, 2, 3, 4):
            nxt = next((ev for ev in events[ev_ptr:] if ev[0] >= i and ev[1] == half), None)
            try_points = None
            if e.kind == "touchdown":
                scorer_pts = off_pts if e.scorer == "offense" else def_pts
                try_points = scorer_pts - rules.touchdown  # includes inferred tries; may be outside 0-2
            label = "NONE" if nxt is None else (
                {"touchdown": "TD", "field_goal": "FG", "safety": "SAFETY"}[nxt[2]]
                + ("_FOR" if nxt[3] == off else "_AGAINST"))
            rows.append({
                "play_id": p["id"], "period": p["period"], "half": half,
                "seconds_left_half": (sec or 0) + (900 if p["period"] in (1, 3) else 0),
                "offense": off, "defense": dfn, "home_offense": home_off,
                "down": p["down"], "distance": p.get("distance"), "yards_to_goal": p.get("yardsToGoal"),
                "score_margin": pre_margin, "offense_timeouts": p.get("offenseTimeouts"),
                "defense_timeouts": p.get("defenseTimeouts"), "play_type": p.get("playType"),
                "yards_gained": p.get("yardsGained"), "event": e.kind, "next_score": label,
                "penalty_in_text": "penalty" in (p.get("playText") or "").lower(),
                # Net points on this play from the offense's view (including any try), and the
                # try's points on touchdown plays. Used for EPA rewards and the learned try value.
                "play_points": off_pts - def_pts, "try_points": try_points,
            })
        if p["id"] in after:
            last = after[p["id"]]

    # Transition checks over consecutive scrimmage rows of the same offense and half.
    df = pd.DataFrame(rows)
    for a, b in pairwise(rows):
        if a["offense"] != b["offense"] or a["half"] != b["half"] or a["event"] != "none":
            continue
        if a["distance"] and a["yards_gained"] is not None and not a["penalty_in_text"]:
            checks["down_checked"] += 1
            expect = 1 if a["yards_gained"] >= a["distance"] else a["down"] + 1
            checks["down_ok"] += b["down"] == expect
            if a["yards_to_goal"] is not None and b["yards_to_goal"] is not None:
                checks["yards_checked"] += 1
                checks["yards_ok"] += b["yards_to_goal"] == a["yards_to_goal"] - a["yards_gained"]
    for i, p in enumerate(ordered):
        e = classify_play(p, rules)
        if e.kind in ("touchdown", "field_goal"):
            team = p["offense"] if e.scorer == "offense" else p["defense"]
            nxt = next((q for q in ordered[i + 1:] if q.get("playType") not in SCORELESS_TYPES), None)
            if nxt is not None and nxt["period"] in ((1, 2) if p["period"] <= 2 else (3, 4)):
                checks["score_checked"] += 1
                checks["kickoff_after_score_ok"] += nxt.get("playType") in KICK_TYPES and nxt["offense"] == team
    for half_periods in ((1, 2), (3, 4)):
        first = next((q for q in ordered if q["period"] in half_periods and q.get("playType") not in SCORELESS_TYPES), None)
        if first is not None:
            checks["halves"] += 1
            checks["half_starts_with_kickoff"] += first.get("playType") in KICK_TYPES
    return df, checks


def season_states(season: int, tiers: tuple[str, ...] = ("exact",)) -> tuple[pd.DataFrame, dict[str, int]]:
    """States for every game of a season whose P01 scoring tier is in `tiers` (local cache, read-only).
    Exact only by default: EP training needs exactly reconciled next-score labels. Rating already-fit
    EP over plays can also use "events" games. Self-contained so seasons run in parallel processes."""
    import sqlite3

    from cfb.config import REPO_ROOT
    from cfb.evaluation.backtest import latest_facts
    from cfb.ingestion.ledger import RawLedger
    from cfb.state.machine import reconcile_game
    from cfb.state.rules import overtime_rules, scoring_rules

    conn = sqlite3.connect(f"file:{(REPO_ROOT / 'data' / 'ledger.sqlite').as_posix()}?mode=ro", uri=True)
    ledger = RawLedger(REPO_ROOT / "data" / "raw", conn)
    finals = {r["game_id"]: (r["home_points"], r["away_points"]) for r in latest_facts(conn, "game_result")}
    sched = {s["game_id"]: s for s in latest_facts(conn, "game_schedule") if s["season"] == season}
    by_game: dict[int, list] = {}
    cal = ledger.latest_success("/calendar", {"year": season})
    for wk in ledger.load(cal) if cal else []:
        e = ledger.latest_success("/plays", {"year": season, "week": wk["week"], "seasonType": wk["seasonType"]})
        for p in ledger.load(e) if e else []:
            if f"cfbd-game-{p['gameId']}" in sched:
                by_game.setdefault(p["gameId"], []).append(p)
    rules, ot = scoring_rules(season), overtime_rules(season)
    frames, totals = [], dict.fromkeys(("games", "exact_games"), 0)
    for gid, plays in sorted(by_game.items()):
        key = f"cfbd-game-{gid}"
        totals["games"] += 1
        rec = reconcile_game(plays, rules, finals.get(key), ot)
        if rec.tier not in tiers:
            continue
        totals["exact_games"] += rec.tier == "exact"
        df, checks = game_states(plays, rules, rec.score_columns_swapped)
        for k, v in checks.items():
            totals[k] = totals.get(k, 0) + v
        s = sched[key]
        frames.append(df.assign(game_id=key, season=season, week=s["week"], season_type=s["season_type"],
                                start_utc=s["start_utc"], tier=rec.tier))
    conn.close()
    return (pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()), totals
