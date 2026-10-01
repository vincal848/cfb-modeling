"""Ingestion contracts against a mocked transport. All rows are provider='SYNTHETIC'."""

import json

import httpx
import pytest

from cfb.ingestion.client import CFBDClient, CFBDError
from cfb.ingestion.fetch import Fetcher, QuotaGuard, QuotaStop
from cfb.ingestion.ledger import RawLedger

KEY = "test-key-0123456789"
ENDPOINTS = {"/plays/stats": {"documented_cap": 3}, "/games": {"documented_cap": None}}


class FakeApi:
    """Serves queued responses and records requests."""

    def __init__(self, *responses):
        self.queue = list(responses)
        self.requests = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        item = self.queue.pop(0)
        if isinstance(item, Exception):
            raise item
        status, body, headers = item
        return httpx.Response(status, content=json.dumps(body).encode(), headers=headers)


def make(api, db, tmp_path, *, quota=None, remaining=None):
    clock = iter(f"2026-10-01T00:00:{i:02d}.000000Z" for i in range(60))
    client = CFBDClient(
        KEY, transport=httpx.MockTransport(api), sleep=lambda s: None, clock=lambda: next(clock)
    )
    ledger = RawLedger(tmp_path, db, provider="SYNTHETIC")
    guard = QuotaGuard(monthly_quota=quota, stop_fraction=0.8, remaining=remaining)
    return Fetcher(client, ledger, guard, ENDPOINTS)


def test_sends_bearer_auth_and_retries_rate_limit(db, tmp_path):
    api = FakeApi((429, {}, {"Retry-After": "1"}), (200, [{"id": 1}], {"X-CallLimit-Remaining": "99"}))
    f = make(api, db, tmp_path)
    entry, cached = f.fetch("/games", {"year": 2024, "week": 5})
    assert not cached and entry.http_status == 200 and entry.response_count == 1
    assert api.requests[0].headers["Authorization"] == f"Bearer {KEY}"
    assert len(api.requests) == 2
    assert f.guard.remaining == 99


def test_transport_failure_does_not_leak_key(db, tmp_path):
    err = httpx.ConnectError(f"boom with {KEY}")
    f = make(FakeApi(*[err] * 5), db, tmp_path)
    with pytest.raises(CFBDError) as exc:
        f.fetch("/games", {"year": 2024})
    assert KEY not in str(exc.value)


def test_rerun_hits_cache_and_adds_no_payload(db, tmp_path):
    api = FakeApi((200, [{"id": 1}], {}))
    f = make(api, db, tmp_path)
    first, _ = f.fetch("/games", {"year": 2024, "week": 5})
    # Same request with different param order and types is the same request.
    second, cached = f.fetch("/games", {"week": "5", "year": "2024"})
    assert cached and second == first
    assert len(api.requests) == 1
    assert f.ledger.load(first) == [{"id": 1}]


def test_refresh_preserves_corrected_record(db, tmp_path):
    api = FakeApi((200, [{"id": 1, "pts": 21}], {}), (200, [{"id": 1, "pts": 24}], {}))
    f = make(api, db, tmp_path)
    old, _ = f.fetch("/games", {"year": 2024})
    new, _ = f.fetch("/games", {"year": 2024}, refresh=True)
    assert old.payload_hash != new.payload_hash
    assert f.ledger.load(old) == [{"id": 1, "pts": 21}]  # original kept
    assert f.ledger.latest_success("/games", {"year": 2024}) == new
    (n,) = db.execute("SELECT count(*) FROM raw_requests").fetchone()
    assert n == 2


def test_identical_refresh_dedupes_payload_file(db, tmp_path):
    api = FakeApi((200, [{"id": 1}], {}), (200, [{"id": 1}], {}))
    f = make(api, db, tmp_path)
    f.fetch("/games", {"year": 2024})
    f.fetch("/games", {"year": 2024}, refresh=True)
    assert len(list((tmp_path / "payloads").rglob("*.json.gz"))) == 1


def test_response_at_documented_cap_is_flagged(db, tmp_path):
    api = FakeApi((200, [{}, {}, {}], {}), (200, [{}, {}], {}))
    f = make(api, db, tmp_path)
    capped, _ = f.fetch("/plays/stats", {"year": 2024, "week": 1})
    under, _ = f.fetch("/plays/stats", {"year": 2024, "week": 2})
    assert capped.suspected_truncation and not under.suspected_truncation


def test_empty_response_is_not_zero(db, tmp_path):
    f = make(FakeApi((200, [], {})), db, tmp_path)
    entry, _ = f.fetch("/games", {"year": 1850})
    assert entry.response_count == 0 and entry.http_status == 200


def test_quota_guard_stops_bulk_but_not_forecast_calls(db, tmp_path):
    api = FakeApi((200, [], {}))
    f = make(api, db, tmp_path, quota=100, remaining=20)  # 80 used = stop threshold
    with pytest.raises(QuotaStop):
        f.fetch("/games", {"year": 2024}, bulk=True)
    f.fetch("/games", {"year": 2024}, bulk=False)
    assert len(api.requests) == 1


def test_rows_are_labeled_synthetic(db, tmp_path):
    f = make(FakeApi((200, [], {})), db, tmp_path)
    f.fetch("/games", {"year": 2024})
    assert db.execute("SELECT DISTINCT provider FROM raw_requests").fetchall() == [("SYNTHETIC",)]


def test_audit_profiles_fields_and_keeps_errors(db, tmp_path):
    from cfb.ingestion.audit import run_audit

    api = FakeApi(
        (200, [{"id": 1, "x": None}, {"id": 2}], {"X-CallLimit-Remaining": "50"}),
        (400, {"message": "week required"}, {}),
    )
    f = make(api, db, tmp_path)
    f.endpoints = {
        "/games": {"family": "games", "role": "core", "params": {"year": "{year}"}, "documented_cap": None},
        "/plays": {"family": "plays", "role": "core", "params": {"year": "{year}"}, "documented_cap": None},
    }
    report = run_audit(f, {"year": 2024})
    games, plays = report["results"]
    assert games["params"] == {"year": "2024"}
    assert games["fields"]["x"]["null_rate"] == 1.0 and games["fields"]["id"]["null_rate"] == 0.0
    assert plays["http_status"] == 400 and plays["error"] == {"message": "week required"}
    assert report["provider"] == "SYNTHETIC" and report["calls_remaining_after"] == 50
