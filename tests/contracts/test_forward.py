"""Forward logger on mocked transports (fabricated data): who gets a forecast, and that every run is logged fresh."""

import json
from datetime import UTC, datetime

import httpx

from cfb.ingestion.forward import select_games, snapshot
from cfb.ingestion.kalshi import KalshiReader
from cfb.ingestion.ledger import RawLedger

NOW = datetime(2026, 10, 10, 12, 0, tzinfo=UTC)
VENUES = {1: {"id": 1, "latitude": 40.0, "longitude": -83.0, "dome": False},
          2: {"id": 2, "latitude": 33.0, "longitude": -97.0, "dome": True},
          3: {"id": 3, "latitude": None, "longitude": None, "dome": False}}


def game(venue, hours, tbd=False):
    start = datetime(2026, 10, 10, 12, 0, tzinfo=UTC).timestamp() + hours * 3600
    return {"id": venue * 100 + hours, "venueId": venue, "startTBD": tbd, "startTimeTBD": tbd,
            "startDate": datetime.fromtimestamp(start, UTC).isoformat().replace("+00:00", "Z")}


def test_only_outdoor_day_ahead_games_with_coordinates_are_selected():
    games = [game(1, 24), game(1, 30), game(1, 10), game(2, 24), game(3, 24), game(1, 24, tbd=True), game(9, 24)]
    assert [g["id"] for g, _ in select_games(games, VENUES, NOW)] == [124]


def test_snapshot_logs_ladders_and_forecasts_every_run(db, tmp_path):
    def kalshi(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=json.dumps({"markets": [{"ticker": "A"}], "cursor": ""}).encode())

    def meteo(request: httpx.Request) -> httpx.Response:
        assert request.url.params["wind_speed_unit"] == "mph"
        return httpx.Response(200, content=json.dumps({"hourly": {"wind_speed_10m": [5.0]}}).encode())

    def run():
        k = KalshiReader(RawLedger(tmp_path, db, provider="SYNTHETIC"), transport=httpx.MockTransport(kalshi),
                         min_interval=0, sleep=lambda s: None)
        return snapshot(k, RawLedger(tmp_path, db, provider="SYNTHETIC"), [game(1, 24), game(1, 24)], VENUES, NOW,
                        transport=httpx.MockTransport(meteo))

    assert run() == {"kalshi_calls": 2, "forecast_venues": 1, "games": 2}
    run()  # a second run must not be served from the cache
    n = lambda path: db.execute("select count(*) from raw_requests where endpoint=?", (path,)).fetchone()[0]
    assert n("/markets") == 4 and n("/v1/forecast") == 2
