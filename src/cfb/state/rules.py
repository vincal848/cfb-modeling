"""Season rules from the cited registry (config/rules_registry.json; see
docs/rules/ncaa-rules-registry.md for sources and unverified items).

Only fields the state machine uses are exposed. A required field that the registry
leaves null raises rather than falling back to a remembered value.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from cfb.config import REPO_ROOT
from cfb.state.scoring import ScoringRules

REGISTRY = REPO_ROOT / "config" / "rules_registry.json"


@dataclass(frozen=True)
class OvertimeRules:
    mandatory_two_point_from: int  # overtime number from which a TD's try must be a two-point play
    shootout_from: int | None  # overtime number from which each possession is one two-point play


@cache
def _registry(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _season(season: int, path: Path) -> dict:
    seasons = _registry(str(path))["seasons"]
    if str(season) not in seasons:
        raise KeyError(f"no rules registered for {season}")
    return seasons[str(season)]


def _require(d: dict, key: str, season: int):
    if d.get(key) is None:
        raise ValueError(f"rules registry has no verified value for {key} in {season}")
    return d[key]


def scoring_rules(season: int, path: Path = REGISTRY) -> ScoringRules:
    s = _season(season, path)["scoring"]
    return ScoringRules(
        touchdown=_require(s, "touchdown", season), field_goal=_require(s, "field_goal", season),
        safety=_require(s, "safety", season), try_kick=_require(s, "pat_kick", season),
        try_two_point=_require(s, "two_point_try", season),
        defensive_try_return=_require(s, "defensive_return_on_try", season),
    )


def overtime_rules(season: int, path: Path = REGISTRY) -> OvertimeRules:
    o = _season(season, path)["overtime"]
    return OvertimeRules(_require(o, "mandatory_two_point_from_overtime_period", season),
                         o.get("two_point_shootout_from_overtime_period"))
