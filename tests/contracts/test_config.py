import copy
import json

import pytest

from cfb.config import DEFAULT_CONFIG, REPO_ROOT, ConfigError, load_config, validate_config


def test_shipped_config_is_valid():
    load_config()


def test_model_contracts_parse_and_cover_principal_stages():
    contracts = json.loads((REPO_ROOT / "docs/blueprint/model-contracts.json").read_text())
    names = {s["name"] for s in contracts["stages"]}
    assert {"snapshot", "teams", "game_experts", "stack", "decisions"} <= names
    tracking = next(s for s in contracts["stages"] if s["name"] == "tracking")
    assert tracking["enabled_by_default"] is False


@pytest.fixture
def cfg():
    return json.loads(DEFAULT_CONFIG.read_text())


@pytest.mark.parametrize(
    "path, value",
    [
        (("models", "tracking_enabled"), True),
        (("models", "live_enabled"), True),
        (("data", "missing_values_are_zero"), True),
        (("data", "default_replay_mode"), "reconstructed"),
        (("policies", "winner", "use_unrounded_probability"), False),
        (("validation", "stack_fit_seasons"), [2021]),  # overlaps development
        (("validation", "prospective_season"), 2025),  # inside the test cohort
        (("data", "api_key"), "abc123"),
    ],
)
def test_invariant_violations_rejected(cfg, path, value):
    bad = copy.deepcopy(cfg)
    node = bad
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    with pytest.raises(ConfigError):
        validate_config(bad)
