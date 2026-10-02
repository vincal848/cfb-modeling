"""V01: the registered validation protocol and its chronological folds.

`config/protocol.json` is the registered protocol. Once frozen, its canonical
SHA-256 is recorded in `experiments/protocols/V01-freeze.json`, and loading a
protocol whose hash differs from the freeze record fails. A change after freezing
needs a new protocol version and a docs/deviations.md entry (methodology §11).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from cfb.config import REPO_ROOT, load_config

DEFAULT_PROTOCOL = REPO_ROOT / "config" / "protocol.json"
FREEZE_DIR = REPO_ROOT / "experiments" / "protocols"

# Protocol season roles, in chronological order, and the config.validation key each mirrors.
ROLES = (
    ("warmup", "warmup_seasons"),
    ("development", "development_seasons"),
    ("stack_fit", "stack_fit_seasons"),
    ("calibration", "optional_calibration_seasons"),
    ("test", "untouched_historical_test_seasons"),
)
SCORED_ROLES = ("development", "stack_fit", "calibration", "test")


class ProtocolError(ValueError):
    pass


def protocol_hash(protocol: dict[str, Any]) -> str:
    """SHA-256 of canonical JSON, so line endings and key order do not change the hash."""
    canonical = json.dumps(protocol, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def freeze_path(protocol: dict[str, Any], freeze_dir: Path = FREEZE_DIR) -> Path:
    return freeze_dir / f"{protocol['protocol_id']}-freeze.json"


def validate_protocol(protocol: dict[str, Any], cfg: dict[str, Any]) -> None:
    problems: list[str] = []
    val = cfg["validation"]

    seasons = protocol["seasons"]
    for role, key in ROLES:
        if seasons[role]["seasons"] != val[key]:
            problems.append(f"seasons.{role} {seasons[role]['seasons']} differs from config.validation.{key}")
    if protocol["replay"]["prospective_season"] != val["prospective_season"]:
        problems.append("replay.prospective_season differs from config.validation.prospective_season")
    if protocol["replay"]["historical_class"] not in ("reconstructed", "archived_replay"):
        problems.append("replay.historical_class must state a non-strict class for 2014-2025")

    products = protocol["products"]
    horizons = [products["primary"]["horizon_minutes"], *products["secondary_horizons_minutes"]]
    if sorted(horizons) != sorted(cfg["scope"]["pregame_horizons_minutes"]):
        problems.append("product horizons must match config.scope.pregame_horizons_minutes")
    if products["primary"]["product"] not in cfg["scope"]["forecast_products"]:
        problems.append("products.primary.product is not a configured forecast product")

    metrics = protocol["metrics"]
    if metrics["game_joint"]["primary"] != val["primary_joint_metric"]:
        problems.append("metrics.game_joint.primary differs from config.validation.primary_joint_metric")
    if metrics["winner"]["primary"] != val["primary_winner_metric"]:
        problems.append("metrics.winner.primary differs from config.validation.primary_winner_metric")
    for target in ("margin", "total"):
        if metrics[target]["primary"] != val["primary_margin_total_metric"]:
            problems.append(f"metrics.{target}.primary differs from config.validation.primary_margin_total_metric")
    if metrics["intervals"]["levels"] != val["interval_levels"]:
        problems.append("metrics.intervals.levels differs from config.validation.interval_levels")
    if metrics["promotion_metric"] != "game_joint." + metrics["game_joint"]["primary"]:
        problems.append("promotion_metric must be the registered joint primary metric")

    if protocol["cohorts"]["minimum_size_for_stable_summary"] != val["minimum_cohort_size_for_stable_summary"]:
        problems.append("cohorts.minimum_size_for_stable_summary differs from config.validation")
    mc = protocol["monte_carlo"]
    if mc["root_seed"] != cfg["computation"]["root_seed"]:
        problems.append("monte_carlo.root_seed differs from config.computation.root_seed")
    if mc["draws_per_game"] != cfg["computation"]["initial_independent_game_draws"]:
        problems.append("monte_carlo.draws_per_game differs from config.computation.initial_independent_game_draws")

    if protocol["status"] not in ("draft", "frozen"):
        problems.append("status must be 'draft' or 'frozen'")
    if protocol["status"] == "frozen" and protocol["candidate_results_seen"] is not False:
        problems.append("a protocol cannot be frozen after candidate results were seen")

    if problems:
        raise ProtocolError("; ".join(problems))


def check_freeze(protocol: dict[str, Any], freeze_dir: Path = FREEZE_DIR) -> dict[str, Any] | None:
    """Return the freeze record, or None for a draft. A frozen protocol must match its record."""
    path = freeze_path(protocol, freeze_dir)
    if protocol["status"] == "draft":
        if path.exists():
            raise ProtocolError(f"{path.name} exists but the protocol is marked draft")
        return None
    if not path.exists():
        raise ProtocolError(f"protocol is marked frozen but {path.name} is missing")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record["protocol_sha256"] != protocol_hash(protocol):
        raise ProtocolError(
            "protocol changed after freezing; register a new protocol version and a deviation instead"
        )
    return record


def load_protocol(
    path: Path | str = DEFAULT_PROTOCOL, freeze_dir: Path = FREEZE_DIR, cfg: dict[str, Any] | None = None
) -> dict[str, Any]:
    protocol = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_protocol(protocol, cfg if cfg is not None else load_config())
    check_freeze(protocol, freeze_dir)
    return protocol


def freeze_protocol(
    path: Path | str = DEFAULT_PROTOCOL, freeze_dir: Path = FREEZE_DIR, frozen_at: str | None = None
) -> dict[str, Any]:
    """Mark a validated draft as frozen and write its freeze record. Refuses to refreeze."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    protocol = json.loads(text)
    if protocol["status"] != "draft":
        raise ProtocolError("only a draft protocol can be frozen")
    if protocol["candidate_results_seen"] is not False:
        raise ProtocolError("candidate results were seen; the protocol can no longer be frozen")
    # Edit only the status line so the registered file keeps its layout.
    frozen_text = text.replace('"status": "draft"', '"status": "frozen"', 1)
    protocol = json.loads(frozen_text)
    if protocol["status"] != "frozen":
        raise ProtocolError('could not find the line "status": "draft" to freeze')
    validate_protocol(protocol, load_config())
    record = {
        "protocol_id": protocol["protocol_id"],
        "protocol_version": protocol["protocol_version"],
        "protocol_sha256": protocol_hash(protocol),
        "frozen_at": frozen_at or datetime.now(UTC).isoformat(timespec="seconds"),
        "candidate_results_seen": False,
    }
    out = freeze_path(protocol, freeze_dir)
    if out.exists():
        raise ProtocolError(f"{out.name} already exists")
    out.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frozen_text, encoding="utf-8")
    out.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    return record


def season_role(protocol: dict[str, Any], season: int) -> str | None:
    for role, _ in ROLES:
        if season in protocol["seasons"][role]["seasons"]:
            return role
    return None


def parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone(UTC)


@dataclass(frozen=True)
class Fold:
    season: int
    season_type: str
    week: int
    role: str
    cutoff: datetime  # earliest game cutoff in the fold; parameters are fit on data available by then
    game_ids: tuple[int, ...]
    tbd_game_ids: tuple[int, ...]


def build_folds(
    protocol: dict[str, Any], season: int, games: list[dict[str, Any]], horizon_minutes: int
) -> list[Fold]:
    """One fold per (seasonType, week) among the given games, in kickoff order.

    `games` should already be restricted to the scored population. Warm-up seasons
    have no folds because they are never scored.
    """
    role = season_role(protocol, season)
    if role not in SCORED_ROLES:
        return []
    horizon = timedelta(minutes=horizon_minutes)
    batches: dict[tuple[str, int], list[dict[str, Any]]] = {}
    for g in games:
        if g["season"] != season:
            raise ProtocolError(f"game {g['id']} belongs to season {g['season']}, not {season}")
        batches.setdefault((g["seasonType"], g["week"]), []).append(g)
    folds = []
    for (stype, week), batch in batches.items():
        cutoff = min(parse_utc(g["startDate"]) for g in batch) - horizon
        folds.append(Fold(
            season, stype, week, role, cutoff,
            tuple(sorted(g["id"] for g in batch)),
            tuple(sorted(g["id"] for g in batch if g.get("startTimeTBD"))),
        ))
    return sorted(folds, key=lambda f: (f.cutoff, f.season_type, f.week))
