"""Forward logger: snapshot open Kalshi CFB ladders and Open-Meteo day-ahead wind into the request ledger.

Read-only and public (no keys for Kalshi or Open-Meteo; CFBD is used only for the schedule and is cache-first).
Run it on a schedule, for example hourly on game days:

    uv run python -m cfb.ingestion.forward

Each run records, as raw ledger rows with `retrieved_at` as the proof of bet-time:
- provider 'KALSHI': every open market of KXNCAAFSPREAD and KXNCAAFTOTAL (the ladders; pick the snapshot nearest
  kickoff - 6h per game when analysing);
- provider 'OPENMETEO': the hourly wind forecast at each outdoor venue whose game kicks off 23-25 h from now
  (the day-ahead forecast W01 needs).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx

from cfb.ingestion.client import ApiResponse, utc_now
from cfb.ingestion.kalshi import KalshiReader
from cfb.ingestion.ledger import RawLedger

LADDER_SERIES = ("KXNCAAFSPREAD", "KXNCAAFTOTAL")
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
DAY_AHEAD = (timedelta(hours=23), timedelta(hours=25))


def select_games(games: list[dict], venues: dict[int, dict], now: datetime) -> list[tuple[dict, dict]]:
    """(game, venue) for games kicking off in the day-ahead window at an outdoor venue with coordinates."""
    out = []
    for g in games:
        start = datetime.fromisoformat(g["startDate"])
        v = venues.get(g.get("venueId"))
        if not g.get("startTimeTBD") and DAY_AHEAD[0] <= start - now <= DAY_AHEAD[1] and v and not v.get("dome") \
                and v.get("latitude") is not None and v.get("longitude") is not None:
            out.append((g, v))
    return out


def record_forecast(ledger: RawLedger, client: httpx.Client, venue: dict) -> None:
    params = {"latitude": round(venue["latitude"], 3), "longitude": round(venue["longitude"], 3),
              "hourly": "wind_speed_10m", "wind_speed_unit": "mph", "forecast_days": 3, "timezone": "UTC"}
    r = client.get(FORECAST_URL, params=params)
    ledger.record("/v1/forecast", params, ApiResponse(r.status_code, r.content, utc_now(), None, 1), None)
    if r.status_code != 200:
        raise RuntimeError(f"Open-Meteo {r.status_code} for venue {venue['id']}")


def snapshot(kalshi: KalshiReader, weather: RawLedger, games: list[dict], venues: dict[int, dict], now: datetime,
             transport: httpx.BaseTransport | None = None) -> dict:
    """One logging pass; returns what was recorded."""
    for series in LADDER_SERIES:
        # ponytail: no ts filters (the API restricts combining them); stores every open market, ~2 pages a series
        kalshi.pages("/markets", {"series_ticker": series, "status": "open", "limit": 1000}, "markets", fresh=True)
    picked = select_games(games, venues, now)
    with httpx.Client(timeout=60, transport=transport) as client:
        for venue in {v["id"]: v for _, v in picked}.values():
            record_forecast(weather, client, venue)
    return {"kalshi_calls": kalshi.calls, "forecast_venues": len({v["id"] for _, v in picked}), "games": len(picked)}


def main() -> None:
    from cfb.cli import DATA_DIR, open_fetcher, open_store

    fetcher = open_fetcher()
    now = datetime.now(UTC)
    entry, _ = fetcher.fetch("/games", {"year": now.year}, refresh=True, bulk=False)
    games = fetcher.ledger.load(entry)
    ventry, _ = fetcher.fetch("/venues", {})
    venues = {v["id"]: v for v in fetcher.ledger.load(ventry)}
    conn, _ = open_store()
    kalshi = KalshiReader(RawLedger(DATA_DIR / "raw", conn, provider="KALSHI"))
    out = snapshot(kalshi, RawLedger(DATA_DIR / "raw", conn, provider="OPENMETEO"), games, venues, now)
    print(f"{now.isoformat(timespec='seconds')} {out}")


if __name__ == "__main__":
    main()
