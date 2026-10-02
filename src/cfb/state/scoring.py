"""P01 (scoring core): classify each play's scoring event from CFBD play type and text, and
check it against the play's score change.

CFBD play conventions (checked on 2023 week 5 data):

- `offenseScore`/`defenseScore` on a play are the scores *after* the play, including the
  try that follows a touchdown.
- The try is not a separate play. Its result is in the touchdown play's text:
  "(X KICK)", "PAT MISSED", "PAT BLOCKED", "Two-Point ... Conversion", "... failed".
- On kickoffs and punts, `offense` is the kicking team, so a return touchdown scores for
  the `defense`.
- Play IDs sort in game order.

Point values come from the season's rules (`ScoringRules`), not constants here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ScoringRules:
    touchdown: int
    field_goal: int
    safety: int
    try_kick: int
    try_two_point: int
    defensive_try_return: int


# Play types whose touchdown is scored by the team on defense in CFBD's labelling.
DEFENSIVE_TD_TYPES = {
    "Interception Return Touchdown", "Fumble Return Touchdown", "Punt Return Touchdown",
    "Kickoff Return Touchdown", "Blocked Punt Touchdown", "Blocked Field Goal Touchdown",
    "Missed Field Goal Return Touchdown", "Blocked PAT Touchdown",
}
OFFENSIVE_TD_TYPES = {"Passing Touchdown", "Rushing Touchdown", "Fumble Recovery (Own) Touchdown"}
# Older games label some touchdowns with a non-scoring type and put "for a TD" in the text.
# On these types the touchdown belongs to the team on defense (kicking plays and turnovers).
TEXT_TD_DEFENSE_TYPES = {"Punt", "Blocked Punt", "Kickoff", "Kickoff Return (Offense)", "Fumble Recovery (Opponent)",
                         "Interception", "Pass Interception Return", "Blocked Field Goal", "Missed Field Goal Return"}
_TEXT_TD = re.compile(r"\bfor a (TD|touchdown)\b|\bTOUCHDOWN\b", re.IGNORECASE)
_NULLIFIED = re.compile(r"nullified|NO PLAY", re.IGNORECASE)
# Standalone two-point snaps; CFBD uses these for overtime shootout plays (2024 Georgia-Georgia Tech).
TWO_POINT_PLAY_TYPES = {"Two Point Pass", "Two Point Rush", "Two Point Conversion"}

_KICK_GOOD = re.compile(r"\bKICK\)|PAT GOOD|EXTRA POINT GOOD|\bKICK GOOD", re.IGNORECASE)
_KICK_FAILED = re.compile(r"PAT (MISSED|BLOCKED|FAILED)|KICK (MISSED|BLOCKED|FAILED)|EXTRA POINT (MISSED|BLOCKED)", re.IGNORECASE)
_TWO_FAILED = re.compile(r"(TWO|2)[- ]?(POINT|PT).{0,30}(FAIL|NO GOOD|UNSUCCESSFUL)|CONVERSION FAILED", re.IGNORECASE)
_TWO_GOOD = re.compile(r"(TWO|2)[- ]?(POINT|PT).{0,30}CONVERSION|CONVERSION (GOOD|SUCCESSFUL)", re.IGNORECASE)
_DEF_TRY = re.compile(r"DEFENSIVE (TWO|2)[- ]?(POINT|PT)|(TWO|2)[- ]?(POINT|PT) (RETURN|DEFENSIVE)", re.IGNORECASE)


@dataclass
class ScoringEvent:
    kind: str  # touchdown, field_goal, safety, none, unknown
    scorer: str | None  # "offense" or "defense"
    try_result: str | None = None  # kick_good, kick_failed, two_good, two_failed, defensive_return, none, unparsed
    points: dict[str, int] = field(default_factory=dict)  # "offense"/"defense" -> points
    from_text: bool = False  # touchdown identified from play text under a non-touchdown type


def classify_try(text: str) -> str:
    if _DEF_TRY.search(text):
        return "defensive_return"
    if _TWO_FAILED.search(text):
        return "two_failed"
    if _TWO_GOOD.search(text):
        return "two_good"
    if _KICK_FAILED.search(text):
        return "kick_failed"
    if _KICK_GOOD.search(text):
        return "kick_good"
    return "unparsed"


def classify_play(play: dict[str, Any], rules: ScoringRules) -> ScoringEvent:
    """The scoring event a play records and the points it implies for offense/defense.

    `unparsed` tries are left unresolved: the touchdown counts and the try is unknown, so
    the reconciliation check can report it instead of guessing.
    """
    ptype = play.get("playType") or ""
    text = play.get("playText") or ""
    if ptype == "Field Goal Good":
        return ScoringEvent("field_goal", "offense", points={"offense": rules.field_goal})
    if ptype == "Safety":
        return ScoringEvent("safety", "defense", points={"defense": rules.safety})
    if ptype in OFFENSIVE_TD_TYPES or ptype in DEFENSIVE_TD_TYPES:
        scorer = "defense" if ptype in DEFENSIVE_TD_TYPES else "offense"
        other = "offense" if scorer == "defense" else "defense"
        result = classify_try(text)
        pts = {scorer: rules.touchdown}
        if result == "kick_good":
            pts[scorer] += rules.try_kick
        elif result == "two_good":
            pts[scorer] += rules.try_two_point
        elif result == "defensive_return":
            pts[other] = rules.defensive_try_return
        return ScoringEvent("touchdown", scorer, result, pts)
    if play.get("scoring") and _TEXT_TD.search(text) and not _NULLIFIED.search(text):
        # A touchdown under a non-touchdown play type; the event records that it came from text.
        scorer = "defense" if ptype in TEXT_TD_DEFENSE_TYPES else "offense"
        other = "offense" if scorer == "defense" else "defense"
        result = classify_try(text)
        pts = {scorer: rules.touchdown}
        if result == "kick_good":
            pts[scorer] += rules.try_kick
        elif result == "two_good":
            pts[scorer] += rules.try_two_point
        elif result == "defensive_return":
            pts[other] = rules.defensive_try_return
        return ScoringEvent("touchdown", scorer, result, pts, from_text=True)
    if ptype in TWO_POINT_PLAY_TYPES:
        # A standalone two-point play: the overtime shootout snap (or a try CFBD split out).
        result = classify_try(text)
        if result == "defensive_return":
            return ScoringEvent("two_point_play", "defense", result, {"defense": rules.defensive_try_return})
        good = result == "two_good"
        return ScoringEvent("two_point_play", "offense", result, {"offense": rules.try_two_point} if good else {})
    if play.get("scoring"):
        return ScoringEvent("unknown", None)
    return ScoringEvent("none", None)
