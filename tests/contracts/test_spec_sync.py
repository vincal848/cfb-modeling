"""The working copies must match the blueprint except for deviations logged in docs/deviations.md.

When a deliberate change is made, record it in docs/deviations.md (with its
statistical justification) and add it to LOGGED_CONFIG_DEVIATIONS below.
"""

import json

from cfb.config import REPO_ROOT

# (path, blueprint value, working value, deviation ID)
LOGGED_CONFIG_DEVIATIONS = [
    (("data", "subscription_tier_assumption"), 3, 4, "DEV-001"),
    (("data", "monthly_quota"), None, 125000, "DEV-001"),
]


def _flatten(node, prefix=()):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _flatten(v, prefix + (k,))
    else:
        yield prefix, node


def test_schema_matches_blueprint():
    pkg = (REPO_ROOT / "src/cfb/db/schema.sql").read_bytes()
    spec = (REPO_ROOT / "docs/blueprint/schema.sql").read_bytes()
    assert pkg == spec


def test_config_differs_from_blueprint_only_by_logged_deviations():
    spec = dict(_flatten(json.loads((REPO_ROOT / "docs/blueprint/config.json").read_text())))
    working = dict(_flatten(json.loads((REPO_ROOT / "config/config.json").read_text())))
    assert spec.keys() == working.keys()
    diffs = {k: (spec[k], working[k]) for k in spec if spec[k] != working[k]}
    expected = {path: (old, new) for path, old, new, _ in LOGGED_CONFIG_DEVIATIONS}
    assert diffs == expected


def test_every_logged_deviation_is_documented():
    log = (REPO_ROOT / "docs/deviations.md").read_text(encoding="utf-8")
    for *_, dev_id in LOGGED_CONFIG_DEVIATIONS:
        assert f"| {dev_id} |" in log
