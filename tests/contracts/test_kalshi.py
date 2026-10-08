"""Kalshi reader on a mocked transport and event mapping on fabricated games. provider='SYNTHETIC'."""

import json

import httpx
import pytest

from cfb.ingestion.kalshi import KalshiReader, event_code, map_events, norm
from cfb.ingestion.ledger import RawLedger


def reader(db, tmp_path, pages):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        assert "authorization" not in {k.lower() for k in request.headers}
        body = pages[request.url.params.get("cursor", "")]
        return httpx.Response(200, content=json.dumps(body).encode())

    r = KalshiReader(RawLedger(tmp_path, db, provider="SYNTHETIC"),
                     transport=httpx.MockTransport(handler), min_interval=0, sleep=lambda s: None)
    return r, seen


def test_pages_follow_cursor_then_replay_from_cache(db, tmp_path):
    pages = {"": {"markets": [{"ticker": "A"}], "cursor": "c1"},
             "c1": {"markets": [{"ticker": "B"}], "cursor": ""}}
    r, seen = reader(db, tmp_path, pages)
    assert [m["ticker"] for m in r.markets("KXNCAAFGAME")] == ["A", "B"]
    assert r.calls == 2 and seen[1]["cursor"] == "c1"
    r2, seen2 = reader(db, tmp_path, pages)
    assert [m["ticker"] for m in r2.markets("KXNCAAFGAME")] == ["A", "B"]
    assert r2.calls == 0 and seen2 == []


def test_reader_refuses_cfbd_provider(db, tmp_path):
    with pytest.raises(ValueError):
        KalshiReader(RawLedger(tmp_path, db, provider="CFBD"))


def test_map_events_needs_both_teams_and_date():
    names = {"t1": {norm("Miami")}, "t2": {norm("Ole Miss")}, "t3": {norm("Miami (OH)")}}
    sched = [{"game_id": "g1", "away_team_id": "t1", "home_team_id": "t2", "start_utc": "2026-01-09T00:30:00Z"},
             {"game_id": "g2", "away_team_id": "t3", "home_team_id": "t2", "start_utc": "2025-09-06T16:00:00Z"}]
    mk = [{"event_ticker": "KXNCAAFGAME-26JAN08MIAMISS", "title": "Miami at Ole Miss Winner?"},
          {"event_ticker": "KXNCAAFGAME-25OCT01MIAMISS", "title": "Miami at Ole Miss Winner?"},  # wrong date
          {"event_ticker": "KXNCAAFGAME-25SEP06M-OHMISS", "title": "Miami (OH) at Ole Miss Winner?"},
          {"event_ticker": "KXNCAAFGAME-25SEP06XXMISS", "title": "Nobody at Ole Miss Winner?"}]
    got = map_events(mk, sched, names)
    assert got == {"KXNCAAFGAME-26JAN08MIAMISS": "g1", "KXNCAAFGAME-25OCT01MIAMISS": None,
                   "KXNCAAFGAME-25SEP06M-OHMISS": "g2", "KXNCAAFGAME-25SEP06XXMISS": None}
    assert event_code("KXNCAAFSPREAD-26JAN19MIAIND") == "26JAN19MIAIND"
