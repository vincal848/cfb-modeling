"""D04 backfill against a mocked transport. All rows are provider='SYNTHETIC'."""

import json

import httpx
import pytest

from cfb.ingestion.backfill import backfill
from cfb.ingestion.client import CFBDClient
from cfb.ingestion.fetch import Fetcher, QuotaGuard
from cfb.ingestion.ledger import RawLedger

CALENDAR = [{"week": 1, "seasonType": "regular"}, {"week": 2, "seasonType": "regular"},
            {"week": 1, "seasonType": "postseason"}]


class Api:
    """Answers by path; `bodies` can be swapped to simulate a provider correction."""

    def __init__(self):
        self.calls = []
        self.bodies = {"/calendar": CALENDAR, "/drives": [{"gameId": 1}], "/games": [{"id": 1}]}

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.calls.append((request.url.path, dict(request.url.params)))
        body = self.bodies[request.url.path]
        return httpx.Response(200, content=json.dumps(body).encode(), headers={"X-CallLimit-Remaining": "500"})


@pytest.fixture
def setup(db, tmp_path):
    api = Api()
    clock = iter(f"2026-10-01T00:{i // 60:02d}:{i % 60:02d}.000000Z" for i in range(600))
    client = CFBDClient("k" * 20, transport=httpx.MockTransport(api), sleep=lambda s: None,
                        clock=lambda: next(clock))
    fetcher = Fetcher(client, RawLedger(tmp_path, db, provider="SYNTHETIC"),
                      QuotaGuard(1000, 0.8), {"/drives": {"documented_cap": None}})
    return api, fetcher, db, tmp_path


def payload_files(root):
    return sorted(p.name for p in (root / "payloads").rglob("*.json.gz"))


def test_week_family_partitions_from_calendar_and_rerun_is_free(setup):
    api, fetcher, db, root = setup
    r = backfill(fetcher, "drives", 2024, log=lambda s: None)
    assert r.partitions == 3 and r.fetched == 3 and not r.failed
    assert [c for c in api.calls if c[0] == "/drives"][2][1] == {
        "year": "2024", "week": "1", "seasonType": "postseason"}
    rows, files, calls = db.execute("SELECT count(*) FROM raw_requests").fetchone()[0], payload_files(root), len(api.calls)

    again = backfill(fetcher, "drives", 2024, log=lambda s: None)
    assert again.fetched == 0 and again.cached == 3
    assert len(api.calls) == calls  # no requests on restart
    assert db.execute("SELECT count(*) FROM raw_requests").fetchone()[0] == rows
    assert payload_files(root) == files


def test_refresh_keeps_identical_payloads_single_and_preserves_corrections(setup):
    api, fetcher, db, root = setup
    backfill(fetcher, "games", 2024, log=lambda s: None)
    files = payload_files(root)
    backfill(fetcher, "games", 2024, refresh=True, log=lambda s: None)
    assert payload_files(root) == files  # same bytes, no new payload

    api.bodies["/games"] = [{"id": 1, "homePoints": 21}]  # provider correction
    backfill(fetcher, "games", 2024, refresh=True, log=lambda s: None)
    assert len(payload_files(root)) == len(files) + 1  # old version kept
    hashes = {h for (h,) in db.execute("SELECT DISTINCT payload_hash FROM raw_requests WHERE endpoint='/games'")}
    assert len(hashes) == 2


def test_unknown_family_rejected(setup):
    _, fetcher, *_ = setup
    with pytest.raises(ValueError):
        backfill(fetcher, "weather", 2024)
