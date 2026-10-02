"""V01 protocol registration, freeze enforcement, and folds on SYNTHETIC games (fabricated)."""

import copy
import json
from datetime import UTC, datetime

import pytest

from cfb.config import load_config
from cfb.evaluation.protocol import (
    DEFAULT_PROTOCOL,
    ProtocolError,
    build_folds,
    check_freeze,
    freeze_protocol,
    load_protocol,
    protocol_hash,
    validate_protocol,
)

DRAFT_TEXT = DEFAULT_PROTOCOL.read_text(encoding="utf-8").replace('"status": "frozen"', '"status": "draft"', 1)


@pytest.fixture
def protocol():
    """The registered protocol as a draft (the shipped file is frozen)."""
    return json.loads(DRAFT_TEXT)


@pytest.fixture
def cfg():
    return load_config()


def test_shipped_protocol_is_frozen_and_matches_its_record():
    spec = load_protocol()
    assert spec["status"] == "frozen" and spec["candidate_results_seen"] is False


@pytest.mark.parametrize(
    "path, value",
    [
        (("seasons", "test", "seasons"), [2023, 2024, 2025]),  # disagrees with config cohorts
        (("metrics", "game_joint", "primary"), "log_score"),
        (("metrics", "winner", "primary"), "brier"),
        (("metrics", "promotion_metric"), "winner.log_loss"),
        (("products", "primary", "horizon_minutes"), 720),
        (("replay", "historical_class"), "strict"),
        (("monte_carlo", "root_seed"), 1),
        (("status",), "final"),
    ],
)
def test_protocol_must_agree_with_config(protocol, cfg, path, value):
    bad = copy.deepcopy(protocol)
    node = bad
    for k in path[:-1]:
        node = node[k]
    node[path[-1]] = value
    with pytest.raises(ProtocolError):
        validate_protocol(bad, cfg)


def test_hash_ignores_key_order_and_line_endings(protocol):
    reordered = json.loads(json.dumps(protocol, sort_keys=True).replace("\n", "\r\n"))
    assert protocol_hash(reordered) == protocol_hash(protocol)


@pytest.fixture
def draft(tmp_path):
    path = tmp_path / "protocol.json"
    path.write_text(DRAFT_TEXT, encoding="utf-8")
    return path, tmp_path / "freeze"


def test_freeze_then_load_and_reject_later_edits(draft):
    path, freeze_dir = draft
    record = freeze_protocol(path, freeze_dir, frozen_at="2026-10-01T00:00:00+00:00")
    frozen = load_protocol(path, freeze_dir)
    assert frozen["status"] == "frozen" and record["protocol_sha256"] == protocol_hash(frozen)
    assert path.read_text(encoding="utf-8").count("\n\n") > 0  # layout preserved

    with pytest.raises(ProtocolError, match="only a draft"):
        freeze_protocol(path, freeze_dir)

    edited = json.loads(path.read_text(encoding="utf-8"))
    edited["comparison"]["replicates"] = 1000
    path.write_text(json.dumps(edited), encoding="utf-8")
    with pytest.raises(ProtocolError, match="changed after freezing"):
        load_protocol(path, freeze_dir)


def test_frozen_without_record_and_draft_with_record_are_rejected(protocol, draft):
    _, freeze_dir = draft
    frozen = dict(protocol, status="frozen")
    with pytest.raises(ProtocolError, match="missing"):
        check_freeze(frozen, freeze_dir)
    freeze_dir.mkdir()
    (freeze_dir / "V01-freeze.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ProtocolError, match="marked draft"):
        check_freeze(protocol, freeze_dir)


def test_cannot_freeze_after_results_seen(draft):
    path, freeze_dir = draft
    seen = json.loads(path.read_text(encoding="utf-8"))
    seen["candidate_results_seen"] = True
    path.write_text(json.dumps(seen), encoding="utf-8")
    with pytest.raises(ProtocolError, match="results were seen"):
        freeze_protocol(path, freeze_dir)
    assert not (freeze_dir / "V01-freeze.json").exists()


def game(gid, season, stype, week, start, tbd=False):
    return {"id": gid, "season": season, "seasonType": stype, "week": week,
            "startDate": start, "startTimeTBD": tbd}


def test_folds_are_weekly_with_earliest_cutoff_minus_horizon(protocol):
    games = [
        game(3, 2019, "regular", 2, "2019-09-07T16:00:00.000Z"),
        game(1, 2019, "regular", 1, "2019-08-31T23:30:00.000Z"),
        game(2, 2019, "regular", 1, "2019-08-29T23:00:00.000Z", tbd=True),
        game(4, 2019, "postseason", 1, "2019-12-20T19:00:00.000Z"),
    ]
    folds = build_folds(protocol, 2019, games, horizon_minutes=1440)
    assert [(f.season_type, f.week) for f in folds] == [("regular", 1), ("regular", 2), ("postseason", 1)]
    wk1 = folds[0]
    assert wk1.role == "development" and wk1.game_ids == (1, 2) and wk1.tbd_game_ids == (2,)
    assert wk1.cutoff == datetime(2019, 8, 28, 23, 0, tzinfo=UTC)


def test_warmup_seasons_have_no_folds_and_wrong_season_rejected(protocol):
    assert build_folds(protocol, 2016, [game(1, 2016, "regular", 1, "2016-09-03T16:00:00Z")], 1440) == []
    with pytest.raises(ProtocolError):
        build_folds(protocol, 2024, [game(1, 2023, "regular", 1, "2023-09-02T16:00:00Z")], 1440)
