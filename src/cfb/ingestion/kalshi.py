"""Read-only public Kalshi market data, cached through the raw ledger (provider 'KALSHI').

No authentication and no order endpoints: this module can only read. Pages are chained by
cursor and each page is a ledger entry, so a rerun replays the chain from cache with no calls.

    uv run python -m cfb.ingestion.kalshi   # 2025 CFB game/spread/total markets + game candles
"""

from __future__ import annotations

import re
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from cfb.ingestion.client import RETRYABLE_STATUS, ApiResponse, clean_params, utc_now
from cfb.ingestion.ledger import RawLedger

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
PAGE_LIMIT = 1000
SERIES = ("KXNCAAFGAME", "KXNCAAFSPREAD", "KXNCAAFTOTAL")


class KalshiReader:
    def __init__(self, ledger: RawLedger, *, transport: httpx.BaseTransport | None = None,
                 min_interval: float = 1.0, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], str] = utc_now, max_retries: int = 4) -> None:
        if ledger.provider not in ("KALSHI", "SYNTHETIC"):
            raise ValueError("Kalshi payloads must be recorded as provider 'KALSHI' (or 'SYNTHETIC' in tests)")
        self.ledger = ledger
        self.calls = 0
        self._http = httpx.Client(base_url=BASE_URL, headers={"Accept": "application/json"},
                                  timeout=60.0, transport=transport)
        self._interval, self._sleep, self._clock, self._retries = min_interval, sleep, clock, max_retries
        self._last = 0.0

    def _get(self, path: str, params: dict[str, Any]) -> ApiResponse:
        for attempt in range(self._retries + 1):
            wait = self._interval - (time.monotonic() - self._last)
            if wait > 0:
                self._sleep(wait)
            self._last = time.monotonic()
            self.calls += 1
            r = self._http.get(path, params=clean_params(params))
            if r.status_code in RETRYABLE_STATUS and attempt < self._retries:
                self._sleep(2.0 * 2**attempt)
                continue
            return ApiResponse(r.status_code, r.content, self._clock(), None, attempt + 1)
        raise AssertionError("unreachable")

    def pages(self, path: str, params: dict[str, Any], key: str, fresh: bool = False) -> list[dict]:
        items, cursor = [], None
        while True:
            p = {**params, **({"cursor": cursor} if cursor else {})}
            entry = None if fresh else self.ledger.latest_success(path, p)
            if entry is None:
                resp = self._get(path, p)
                entry = self.ledger.record(path, p, resp, None)
                if resp.status != 200:
                    raise RuntimeError(f"Kalshi {path} {p}: HTTP {resp.status}")
            body = self.ledger.load(entry)
            batch = body.get(key) or []
            items += batch
            cursor = body.get("cursor")
            if not cursor or not batch:
                return items

    def markets(self, series: str) -> list[dict]:
        return self.pages("/historical/markets", {"series_ticker": series, "limit": PAGE_LIMIT}, "markets")

    def candles(self, market: dict, period_minutes: int = 60, start: int | None = None,
                end: int | None = None) -> list[dict]:
        """Candles over the market's life, or over [start, end] (unix seconds) when given."""
        start = start if start is not None else int(parse_ts(market["open_time"]).timestamp())
        end = end if end is not None else int(parse_ts(market["close_time"]).timestamp())
        return self.pages(f"/historical/markets/{market['ticker']}/candlesticks",
                          {"start_ts": start, "end_ts": end, "period_interval": period_minutes},
                          "candlesticks")

    def trades(self, ticker: str) -> list[dict]:
        return self.pages("/historical/trades", {"ticker": ticker, "limit": PAGE_LIMIT}, "trades")

    def trades_between(self, ticker: str, start: int, end: int) -> list[dict]:
        """Trades with start <= created < end (unix seconds), newest first."""
        return self.pages("/historical/trades", {"ticker": ticker, "min_ts": start, "max_ts": end, "limit": PAGE_LIMIT},
                          "trades")


def parse_ts(ts: str) -> datetime:
    return datetime.fromisoformat(ts)


# -- Kalshi event -> CFBD game ---------------------------------------------------------------

TITLE = re.compile(r"^(?P<away>.+?) (?:at|vs\.?) (?P<home>.+?) Winner\?$")
EVENT_DATE = re.compile(r"-(\d{2}[A-Z]{3}\d{2})")


def norm(name: str) -> str:
    n = name.lower().replace("&", "and").replace("state", "st")
    n = re.sub(r"\((fl|oh)\)", r"\1", n)
    return re.sub(r"[^a-z0-9]", "", n)


def event_code(event_ticker: str) -> str:
    """KXNCAAFSPREAD-26JAN19MIAIND -> 26JAN19MIAIND, the key shared across a game's series."""
    return event_ticker.split("-", 1)[1]


def event_date(event_ticker: str) -> datetime:
    """Kalshi event tickers carry the game's local date, e.g. KXNCAAFGAME-26JAN08MIAMISS."""
    return datetime.strptime(EVENT_DATE.search(event_ticker).group(1), "%y%b%d").replace(tzinfo=UTC)


def team_names(conn, cfbd_ledger: RawLedger) -> dict[str, set[str]]:
    """team_id -> normalized names: the contract DB's display name plus CFBD /teams school,
    abbreviation and alternate names (cached 2024 payload)."""
    out: dict[str, set[str]] = {}
    for tid, name in conn.execute("SELECT team_id, display_name FROM teams"):
        out.setdefault(tid, set()).add(norm(name))
    entry = cfbd_ledger.latest_success("/teams", {"year": 2024})
    for t in cfbd_ledger.load(entry) if entry else []:
        names = [t["school"], t.get("abbreviation") or "", *(t.get("alternateNames") or [])]
        out.setdefault(f"cfbd-team-{t['id']}", set()).update(norm(n) for n in names if n)
    return out


def map_events(markets: list[dict], schedules: list[dict], names: dict[str, set[str]]) -> dict[str, str | None]:
    """Game-winner event_ticker -> CFBD game_id (None when unmatched). Spread and total
    events share the game event's code (the part after the series), see `event_code`. `names` maps team_id to every
    normalized name CFBD knows for it. A match needs both teams and a kickoff within a day
    of the ticker date; ambiguous matches are left unmatched, never guessed."""
    by_pair: dict[tuple[str, str], list[dict]] = {}
    lookup: dict[str, set[str]] = {}
    for tid, ns in names.items():
        for n in ns:
            lookup.setdefault(n, set()).add(tid)
    for s in schedules:
        by_pair.setdefault((s["away_team_id"], s["home_team_id"]), []).append(s)
    out: dict[str, str | None] = {}
    for m in markets:
        ev = m["event_ticker"]
        if ev in out:
            continue
        t = TITLE.match(m["title"])
        out[ev] = None
        if not t:
            continue
        day = event_date(ev)
        hits = []
        for a in lookup.get(norm(t["away"]), ()):
            for h in lookup.get(norm(t["home"]), ()):
                for pair in ((a, h), (h, a)):  # neutral sites may list either side first
                    hits += [s for s in by_pair.get(pair, [])
                             if abs(parse_ts(s["start_utc"]) - day) <= timedelta(days=1, hours=12)]
        ids = {s["game_id"] for s in hits}
        out[ev] = ids.pop() if len(ids) == 1 else None
    return out


def main(argv: list[str]) -> None:
    from cfb.cli import DATA_DIR, open_store

    conn, _ = open_store()
    reader = KalshiReader(RawLedger(DATA_DIR / "raw", conn, provider="KALSHI"))
    games = []
    for series in SERIES:
        ms = reader.markets(series)
        print(f"{series}: {len(ms)} markets ({reader.calls} calls so far)", flush=True)
        if series == "KXNCAAFGAME":
            games = ms
    for i, m in enumerate(games):
        reader.candles(m)
        if i % 200 == 0:
            print(f"candles {i}/{len(games)} ({reader.calls} calls)", flush=True)
    print(f"done: {reader.calls} calls")


if __name__ == "__main__":
    main(sys.argv[1:])
