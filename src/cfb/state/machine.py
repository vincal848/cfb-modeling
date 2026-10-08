"""P01: play-by-play scoring reconciliation per game.

Walks a game's plays in ID order (game order), derives each play's (home, away) score
change from CFBD's after-play scores, and compares it with the points the play's scoring
event implies under that season's rules. A game reconciles when every play's change is
explained and the score after the last play equals the official final.

Two CFBD conventions found on 2023 data shape the walk:

- Administrative rows (timeouts, period ends, penalty-only rows) often carry the score
  from before a preceding touchdown, so they are skipped for score tracking.
- A touchdown play sometimes shows only the touchdown's points, with the try's points on
  the next score-bearing play. That split is accepted when the next change is exactly a
  legal try for the same team, and counted in `split_tries`.

Overtime (from config/rules_registry.json via cfb.state.rules): CFBD does not number
overtime periods reliably (2024 Georgia-Georgia Tech's eight overtimes are all period 5),
so the overtime number is inferred from possessions, two per overtime. A possession ends
on an offense change, a score or field-goal attempt, a two-point play, a turnover, or a
failed fourth down. Then:

- `ot_kick_try_in_mandatory_period`: a touchdown followed by a kick in an overtime where
  the season's rules require a two-point try.
- `ot_shootout_violation`: a touchdown or field goal in an overtime where the rules allow
  only single two-point plays.

Further provider defects, each counted, never silently fixed:

- `text_touchdowns`: touchdowns under non-touchdown play types, found from the text.
- `stale_rows`: a row whose score dips below the previous row and is restored by the next
  row (seen on kickoffs that carry a penalty) is skipped.
- `score_columns_swapped`: in some games CFBD's offense/defense score columns are swapped
  on every row (2022 Florida State-LSU). Both readings are tried; the swapped one is used
  only when it explains strictly more, and is recorded.
- Defensive two-point returns usually appear only in the score; the try text says the
  kick was blocked. The events tier therefore allows each failed try 0 or 2 points for
  the other team.

Overtime numbers come from period numbers when CFBD spreads overtime over several
periods, and from possession counting only when all overtime plays sit in period 5.

Plays are sorted by period, then ID: in some games the IDs of later overtime periods sort
before earlier ones (2021 Illinois-Penn State).

Plays are never repaired. Unexplained changes are recorded per play so that P02 can drop
the affected games or transitions, and so that the D08 drive-level proxies can be
replaced by play-level evidence.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from cfb.state.rules import OvertimeRules
from cfb.state.scoring import ScoringRules, classify_play

POSSESSION_ENDING_TYPES = {
    "Field Goal Good", "Field Goal Missed", "Blocked Field Goal", "Blocked Field Goal Touchdown",
    "Missed Field Goal Return", "Missed Field Goal Return Touchdown", "Interception", "Pass Interception Return",
    "Interception Return Touchdown", "Fumble Recovery (Opponent)", "Fumble Return Touchdown",
    "Passing Touchdown", "Rushing Touchdown", "Two Point Pass", "Two Point Rush", "Two Point Conversion", "Safety",
}

SCORELESS_TYPES = {"Timeout", "End Period", "End of Half", "End of Game", "End of Regulation",
                   "Penalty", "Uncategorized"}


@dataclass
class GameReconciliation:
    game_id: int
    plays: int
    final_from_plays: tuple[int, int] | None
    official_final: tuple[int, int] | None
    issues: Counter = field(default_factory=Counter)
    inferred_tries: int = 0
    split_tries: int = 0
    overtime_periods: int = 0
    text_touchdowns: int = 0
    stale_rows: int = 0
    score_columns_swapped: bool = False
    failed_tries: list[int] = field(default_factory=lambda: [0, 0])  # per scoring team
    event_points: list[int] = field(default_factory=lambda: [0, 0])  # home, away from events
    unparsed_tries: list[int] = field(default_factory=lambda: [0, 0])  # per scoring team

    @property
    def reconciles(self) -> bool:
        """Exact tier: every score change explained and the walk ends at the official final."""
        return (not self.issues and self.final_from_plays is not None
                and self.final_from_plays == self.official_final)

    @property
    def events_reconcile(self) -> bool:
        """Events tier: the classified scoring events sum to the official final, allowing each
        undescribed try 0-2 points, even if some per-play transitions are unexplained."""
        if self.official_final is None:
            return False
        return all(0 <= self.official_final[i] - self.event_points[i]
                   <= 2 * self.unparsed_tries[i] + 2 * self.failed_tries[1 - i] for i in (0, 1))

    @property
    def tier(self) -> str:
        return "exact" if self.reconciles else "events" if self.events_reconcile else "failed"


def _home_away(play: dict[str, Any], swapped: bool = False) -> tuple[int, int] | None:
    o, d = play.get("offenseScore"), play.get("defenseScore")
    if swapped:
        o, d = d, o
    if o is None or d is None:
        return None
    if play.get("offense") == play.get("home"):
        return (o, d)
    if play.get("defense") == play.get("home"):
        return (d, o)
    return None


def _touchdown_only(delta, event, home_is_offense, rules: ScoringRules) -> bool:
    scorer_home = (event.scorer == "offense") == home_is_offense
    return (delta[0] if scorer_home else delta[1]) == rules.touchdown and (delta[1] if scorer_home else delta[0]) == 0


def _ends_possession(play: dict[str, Any]) -> bool:
    if play.get("playType") in POSSESSION_ENDING_TYPES:
        return True
    down, dist, gained = play.get("down"), play.get("distance"), play.get("yardsGained")
    return down == 4 and dist is not None and gained is not None and gained < dist


def _rank(rec: GameReconciliation) -> tuple[int, int]:
    return ({"exact": 2, "events": 1, "failed": 0}[rec.tier], -sum(rec.issues.values()))


def reconcile_game(plays: list[dict[str, Any]], rules: ScoringRules,
                   official_final: tuple[int, int] | None,
                   overtime: OvertimeRules | None = None) -> GameReconciliation:
    """Reconcile under the normal score-column reading, and under the swapped reading only
    if the normal one is not exact; keep the swapped result only if it is strictly better."""
    normal = _reconcile(plays, rules, official_final, overtime, swapped=False)
    if normal.tier == "exact":
        return normal
    swapped = _reconcile(plays, rules, official_final, overtime, swapped=True)
    if _rank(swapped) > _rank(normal):
        swapped.score_columns_swapped = True
        return swapped
    return normal


def _drop_stale(rows: list[tuple[dict, tuple[int, int]]]) -> tuple[list[tuple[dict, tuple[int, int]]], int]:
    out, dropped, prev = [], 0, (0, 0)
    for i, (p, s) in enumerate(rows):
        nxt = rows[i + 1][1] if i + 1 < len(rows) else None
        if (s[0] < prev[0] or s[1] < prev[1]) and nxt == prev:
            dropped += 1
            continue
        out.append((p, s))
        prev = s
    return out, dropped


def _reconcile(plays, rules, official_final, overtime, *, swapped: bool) -> GameReconciliation:
    ordered = sorted(plays, key=lambda p: (p.get("period") or 0, int(p["id"])))
    rec = GameReconciliation(ordered[0]["gameId"] if ordered else -1, len(ordered), None, official_final)
    if not ordered:
        rec.issues["no_plays"] += 1
        return rec
    rows = []
    for p in ordered:
        if p.get("playType") in SCORELESS_TYPES:
            continue
        score = _home_away(p, swapped)
        if score is None:
            rec.issues["score_or_team_missing"] += 1
            continue
        rows.append((p, score))
    rows, rec.stale_rows = _drop_stale(rows)
    numbered_ot = max((p.get("period") or 0 for p, _ in rows), default=0) > 5

    prev = (0, 0)
    pending_try: tuple[int, set[int]] | None = None  # (scorer index, legal try deltas)
    ot_possession, ot_prev = -1, None  # overtime possession index and previous OT play
    for p, score in rows:
        ot_number = None
        if (p.get("period") or 0) >= 5:
            if numbered_ot:
                ot_number = p["period"] - 4
            else:
                if ot_prev is None or p.get("offense") != ot_prev.get("offense") or _ends_possession(ot_prev):
                    ot_possession += 1
                ot_prev = p
                ot_number = ot_possession // 2 + 1
        delta = (score[0] - prev[0], score[1] - prev[1])
        event = classify_play(p, rules)
        home_is_offense = p.get("offense") == p.get("home")
        expected = [0, 0]
        for side, pts in event.points.items():
            home_side = (side == "offense") == home_is_offense
            expected[0 if home_side else 1] += pts
        expected = tuple(expected)
        for i in (0, 1):
            rec.event_points[i] += expected[i]
        scorer_idx = 0 if (event.scorer == "offense") == home_is_offense else 1
        if event.kind == "touchdown" and event.try_result == "unparsed":
            rec.unparsed_tries[scorer_idx] += 1
        if event.kind == "touchdown" and event.try_result in ("kick_failed", "two_failed"):
            rec.failed_tries[scorer_idx] += 1
        rec.text_touchdowns += event.from_text
        if overtime is not None and ot_number is not None:
            shootout = overtime.shootout_from is not None and ot_number >= overtime.shootout_from
            if shootout and event.kind in ("touchdown", "field_goal"):
                rec.issues["ot_shootout_violation"] += 1
            elif (not shootout and ot_number >= overtime.mandatory_two_point_from
                  and event.kind == "touchdown" and event.try_result in ("kick_good", "kick_failed")):
                rec.issues["ot_kick_try_in_mandatory_period"] += 1
            rec.overtime_periods = max(rec.overtime_periods, ot_number)

        if pending_try is not None and event.kind == "none" and delta != (0, 0):
            scorer, legal = pending_try
            pending_try = None
            if delta[1 - scorer] == 0 and delta[scorer] in legal:
                rec.split_tries += 1
                prev = score
                continue
        pending_try = None

        if event.kind == "unknown":
            rec.issues["scoring_flag_without_known_event"] += 1
        elif event.kind == "touchdown" and event.try_result == "unparsed":
            # The text does not describe the try; accept the delta if it is a TD plus a
            # legal try result for the scorer, and count the inference.
            scorer_home = (event.scorer == "offense") == home_is_offense
            got = delta[0] if scorer_home else delta[1]
            other = delta[1] if scorer_home else delta[0]
            legal = {rules.touchdown, rules.touchdown + rules.try_kick, rules.touchdown + rules.try_two_point}
            if got in legal and other in (0, rules.defensive_try_return):
                rec.inferred_tries += 1
            else:
                rec.issues["touchdown_try_unexplained"] += 1
        elif delta != expected:
            if event.kind == "none":
                if min(delta) < 0:
                    rec.issues["score_decrease"] += 1
                else:
                    rec.issues["score_change_on_non_scoring_play"] += 1
            elif delta == (0, 0):
                rec.issues["scoring_play_without_score_change"] += 1
            elif event.kind == "touchdown" and _touchdown_only(delta, event, home_is_offense, rules):
                scorer = 0 if (event.scorer == "offense") == home_is_offense else 1
                legal = {rules.try_kick, rules.try_two_point}
                pending_try = (scorer, legal)  # the try's points may appear on the next play
            else:
                rec.issues[f"{event.kind}_points_mismatch"] += 1
        prev = score
    rec.final_from_plays = prev
    if official_final is not None and prev != official_final:
        rec.issues["final_mismatch"] += 1
    return rec


def reconcile_season(season: int) -> list[dict[str, Any]]:
    """Reconcile every population game of one season from the local cache (read-only).
    Self-contained so seasons can run in parallel worker processes."""
    import sqlite3

    from cfb.config import DATA_DIR
    from cfb.evaluation.backtest import latest_facts
    from cfb.ingestion.ledger import RawLedger
    from cfb.state.rules import overtime_rules, scoring_rules

    conn = sqlite3.connect(f"file:{(DATA_DIR / 'ledger.sqlite').as_posix()}?mode=ro", uri=True)
    ledger = RawLedger(DATA_DIR / "raw", conn)
    finals = {r["game_id"]: (r["home_points"], r["away_points"]) for r in latest_facts(conn, "game_result")}
    pop = {s["game_id"] for s in latest_facts(conn, "game_schedule") if s["season"] == season}
    by_game: dict[int, list] = {}
    cal = ledger.latest_success("/calendar", {"year": season})
    for wk in ledger.load(cal) if cal else []:
        e = ledger.latest_success("/plays", {"year": season, "week": wk["week"], "seasonType": wk["seasonType"]})
        for p in ledger.load(e) if e else []:
            if f"cfbd-game-{p['gameId']}" in pop:
                by_game.setdefault(p["gameId"], []).append(p)
    rules, ot = scoring_rules(season), overtime_rules(season)
    rows = []
    for gid in sorted(int(g.split("-")[-1]) for g in pop):
        key = f"cfbd-game-{gid}"
        rec = reconcile_game(by_game.get(gid, []), rules, finals.get(key), ot)
        rows.append({"game_id": key, "season": season, "plays": rec.plays, "tier": rec.tier,
                     "issues": json_issues(rec.issues), "overtime_periods": rec.overtime_periods,
                     "score_columns_swapped": rec.score_columns_swapped, "stale_rows": rec.stale_rows,
                     "text_touchdowns": rec.text_touchdowns, "split_tries": rec.split_tries,
                     "inferred_tries": rec.inferred_tries})
    conn.close()
    return rows


def json_issues(issues: Counter) -> str:
    import json

    return json.dumps(dict(sorted(issues.items())))
