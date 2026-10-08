"""Load config/config.json and enforce the invariants the blueprint depends on.

Thresholds in the config are proposed defaults (docs/blueprint/statistical-review.md),
not tuned values. Changing one is a specification change: log it in docs/deviations.md.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = REPO_ROOT / "config" / "config.json"
# CFB_DATA_DIR lets a git worktree share one data dir (and one request ledger) with the main clone.
DATA_DIR = Path(os.environ.get("CFB_DATA_DIR") or REPO_ROOT / "data")

# Extensions that need external data or later milestones. They stay off until
# coverage and rights are demonstrated (blueprint README, "What is ready to build").
GATED_EXTENSIONS = (
    "tracking_enabled",
    "portal_entry_prediction_enabled",
    "live_enabled",
    "individual_ol_defense_enabled",
)

VALIDATION_COHORTS = (
    "warmup_seasons",
    "development_seasons",
    "stack_fit_seasons",
    "optional_calibration_seasons",
    "untouched_historical_test_seasons",
)


class ConfigError(ValueError):
    pass


def load_config(path: Path | str = DEFAULT_CONFIG) -> dict[str, Any]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict[str, Any]) -> None:
    problems: list[str] = []

    data = cfg["data"]
    if data.get("missing_values_are_zero") is not False:
        problems.append("data.missing_values_are_zero must be false")
    if data.get("raw_immutable") is not True:
        problems.append("data.raw_immutable must be true")
    if data.get("default_replay_mode") != "strict":
        problems.append("data.default_replay_mode must be 'strict'")
    for key, value in data.items():
        if "key" in key.lower() and key != "credential_environment_variable" and value:
            problems.append(f"data.{key} looks like a stored credential")

    models = cfg["models"]
    for flag in GATED_EXTENSIONS:
        if models.get(flag) is not False:
            problems.append(f"models.{flag} must stay false until its data gate passes")

    # Cohorts must be disjoint and strictly chronological, ending before the prospective season.
    val = cfg["validation"]
    previous_max = None
    seen: set[int] = set()
    for name in VALIDATION_COHORTS:
        seasons = val[name]
        if not seasons:
            continue
        if seen & set(seasons):
            problems.append(f"validation.{name} overlaps an earlier cohort")
        if previous_max is not None and min(seasons) <= previous_max:
            problems.append(f"validation.{name} is not after the preceding cohort")
        seen |= set(seasons)
        previous_max = max(seasons)
    if previous_max is not None and val["prospective_season"] <= previous_max:
        problems.append("validation.prospective_season must follow all historical cohorts")

    winner = cfg["policies"]["winner"]
    if winner.get("use_unrounded_probability") is not True:
        problems.append("policies.winner.use_unrounded_probability must be true")

    if problems:
        raise ConfigError("; ".join(problems))
