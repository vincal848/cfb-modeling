"""D04: resumable raw backfill by family and season (implementation-plan §5 `cfb ingest`).

Each family maps to one endpoint and a partitioning scheme. Requests are cache-first,
so a restarted or repeated backfill makes no calls and adds no payloads for partitions
already retrieved. `refresh=True` re-fetches; identical bytes add no payload file and
corrected bytes add a new version beside the old one (RawLedger).

Requests run sequentially on purpose: they share one monthly quota and the provider's
rate limits, so parallel calls would only add 429 retries.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from typing import Any

from cfb.ingestion.fetch import Fetcher

SEASON_TYPES = ("regular", "postseason")

# family -> (endpoint, partition scheme). "week" partitions come from that season's /calendar.
FAMILIES: dict[str, tuple[str, str]] = {
    "teams_fbs": ("/teams/fbs", "season"),
    "calendar": ("/calendar", "season"),
    "games": ("/games", "season_type"),
    "lines": ("/lines", "season_type"),
    "team_game_stats": ("/games/teams", "week"),
    "drives": ("/drives", "week"),
    "plays": ("/plays", "week"),
    # Player families (D06). /roster accepts a season without a team and returns every team.
    "rosters": ("/roster", "season"),
    "portal": ("/player/portal", "season"),
    "recruiting": ("/recruiting/players", "season"),
    # Player-attributed play stats (P03/P04): athlete IDs per play, joinable to EPA by playId.
    "player_play_stats": ("/plays/stats", "game"),
}
CORE_FAMILIES = ("teams_fbs", "calendar", "games", "lines", "team_game_stats", "drives", "plays")


def partitions(fetcher: Fetcher, family: str, season: int, *, refresh: bool = False) -> Iterator[dict[str, Any]]:
    _, scheme = FAMILIES[family]
    if scheme == "season":
        yield {"year": season}
    elif scheme == "season_type":
        for st in SEASON_TYPES:
            yield {"year": season, "seasonType": st}
    elif scheme == "week":
        entry, _ = fetcher.fetch("/calendar", {"year": season}, refresh=refresh)
        if entry.http_status != 200:
            raise RuntimeError(f"/calendar {season} unavailable (HTTP {entry.http_status})")
        for wk in fetcher.ledger.load(entry):
            yield {"year": season, "week": wk["week"], "seasonType": wk["seasonType"]}
    elif scheme == "game":
        # One partition per completed game with an FBS team (V01 population). Per-game
        # requests stay far below the endpoint's 2,000-row cap (about 190 rows per game).
        fbs_entry, _ = fetcher.fetch("/teams/fbs", {"year": season}, refresh=refresh)
        fbs = {t["id"] for t in fetcher.ledger.load(fbs_entry)} if fbs_entry.http_status == 200 else set()
        if not fbs:
            raise RuntimeError(f"/teams/fbs {season} unavailable")
        for st in SEASON_TYPES:
            entry, _ = fetcher.fetch("/games", {"year": season, "seasonType": st}, refresh=refresh)
            if entry.http_status != 200:
                raise RuntimeError(f"/games {season} {st} unavailable (HTTP {entry.http_status})")
            for g in fetcher.ledger.load(entry):
                if g.get("completed") and (g.get("homeId") in fbs or g.get("awayId") in fbs):
                    yield {"gameId": g["id"]}
    else:
        raise ValueError(f"unknown partition scheme {scheme!r}")


@dataclass
class BackfillReport:
    family: str
    season: int
    partitions: int = 0
    fetched: int = 0
    cached: int = 0
    failed: list[str] = field(default_factory=list)
    truncated: list[str] = field(default_factory=list)


def backfill(
    fetcher: Fetcher, family: str, season: int, *, refresh: bool = False,
    log: Callable[[str], None] = print,
) -> BackfillReport:
    if family not in FAMILIES:
        raise ValueError(f"unknown family {family!r}; choose from {sorted(FAMILIES)}")
    path, _ = FAMILIES[family]
    report = BackfillReport(family, season)
    for params in partitions(fetcher, family, season, refresh=refresh):
        entry, cached = fetcher.fetch(path, params, refresh=refresh, bulk=True)
        report.partitions += 1
        report.cached += cached
        report.fetched += not cached
        label = f"{path} {params}"
        if entry.http_status != 200:
            report.failed.append(f"{label} -> {entry.http_status}")
        if entry.suspected_truncation:
            report.truncated.append(label)
    log(f"{family} {season}: {report.partitions} partitions, {report.fetched} fetched, "
        f"{report.cached} cached, {len(report.failed)} failed, {len(report.truncated)} truncated")
    return report
