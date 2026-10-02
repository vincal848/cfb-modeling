"""D05 (games and teams): canonical IDs and versioned schedule/result facts from raw `/games`.

D01 finding 2: a CFBD game record mixes pregame and postgame fields. Each game becomes
two facts with their own availability, so a snapshot can admit a schedule without its
score:

- `game_schedule`: teams, kickoff, site and classification. Reconstructed availability is
  kickoff minus 7 days. No planned model uses schedule information more than a week
  ahead, and postseason or championship pairings are not known much earlier.
- `game_result`: final points and line scores. Reconstructed availability is kickoff plus
  the protocol's `reconstructed_result_available_after_kickoff_hours` (V01).

Plus one `fbs_membership` fact per season, available 30 days before that season's first
calendar week. Provider ratings, win probabilities, attendance and excitement are not
canonicalized: they are postgame or provider-computed (D01 finding 2).

Only the V01 population (games with at least one FBS team that season) is canonicalized.
Versions are append-only: a fact whose normalized payload is unchanged adds no row, and
a corrected payload adds a new version (methodology §2).
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from cfb.ingestion.ledger import RawLedger

SCHEDULE_LEAD = timedelta(days=7)
MEMBERSHIP_LEAD = timedelta(days=30)
EVIDENCE = "reconstructed"


def team_id(cfbd_id: int) -> str:
    return f"cfbd-team-{cfbd_id}"


def game_id(cfbd_id: int) -> str:
    return f"cfbd-game-{cfbd_id}"


def parse_utc(ts: str) -> datetime:
    return datetime.fromisoformat(ts).astimezone(UTC)


def iso(ts: datetime) -> str:
    return ts.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def schedule_fact(g: dict[str, Any]) -> dict[str, Any]:
    return {
        "game_id": game_id(g["id"]),
        "season": g["season"],
        "week": g["week"],
        "season_type": g["seasonType"],
        "start_utc": iso(parse_utc(g["startDate"])),
        "start_time_tbd": bool(g.get("startTimeTBD")),
        "neutral_site": bool(g.get("neutralSite")),
        "conference_game": bool(g.get("conferenceGame")),
        "home_team_id": team_id(g["homeId"]),
        "away_team_id": team_id(g["awayId"]),
        "home_classification": g.get("homeClassification"),
        "away_classification": g.get("awayClassification"),
        "venue_id": g.get("venueId"),
    }


def result_fact(g: dict[str, Any]) -> dict[str, Any] | None:
    """None until the game is completed with both scores; a missing score is never zero."""
    if not g.get("completed") or g.get("homePoints") is None or g.get("awayPoints") is None:
        return None
    return {
        "game_id": game_id(g["id"]),
        "home_points": g["homePoints"],
        "away_points": g["awayPoints"],
        "home_line_scores": g.get("homeLineScores"),
        "away_line_scores": g.get("awayLineScores"),
    }


class FactWriter:
    """Appends source_records versions, skipping payloads identical to the entity's latest."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.latest: dict[tuple[str, str], str] = {}
        for etype, key, h in conn.execute(
            """SELECT entity_type, entity_key, payload_hash FROM source_records r
               WHERE ingested_at = (SELECT max(ingested_at) FROM source_records s
                                    WHERE s.entity_type=r.entity_type AND s.entity_key=r.entity_key)"""
        ):
            self.latest[(etype, key)] = h
        self.added = 0
        self.unchanged = 0

    def write(
        self, request_id: str, ingested_at: str, entity_type: str, entity_key: str,
        payload: dict[str, Any], event_time: datetime | None, available_at: datetime,
    ) -> None:
        body = canonical_json(payload)
        digest = hashlib.sha256(body.encode()).hexdigest()
        if self.latest.get((entity_type, entity_key)) == digest:
            self.unchanged += 1
            return
        if available_at > parse_utc(ingested_at):
            raise ValueError(f"{entity_type} {entity_key} available after it was ingested")
        version_id = hashlib.sha256(f"{request_id}|{entity_type}|{entity_key}|{digest}".encode()).hexdigest()[:32]
        self.conn.execute(
            "INSERT INTO source_records VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (version_id, request_id, entity_type, entity_key,
             iso(event_time) if event_time else None, iso(available_at), ingested_at,
             EVIDENCE, f"cfbd:{request_id}", body, digest),
        )
        self.latest[(entity_type, entity_key)] = digest
        self.added += 1


def _successful(conn: sqlite3.Connection, provider: str, endpoint: str) -> list[tuple]:
    return conn.execute(
        """SELECT request_id, provider, endpoint, parameters_json, retrieved_at, http_status,
                  response_count, suspected_truncation, payload_uri, payload_hash
           FROM raw_requests WHERE provider=? AND endpoint=? AND http_status=200
           ORDER BY retrieved_at""",
        (provider, endpoint),
    ).fetchall()


def canonicalize_games(
    conn: sqlite3.Connection, ledger: RawLedger, result_lag_hours: float,
    log: Callable[[str], None] = print,
) -> dict[str, int]:
    """Canonicalize every cached FBS-membership, calendar and games response, oldest first."""
    from cfb.ingestion.ledger import LedgerEntry

    def load(row: tuple) -> Any:
        return ledger.load(LedgerEntry(*row[:7], bool(row[7]), *row[8:]))

    season_start: dict[int, datetime] = {}
    for row in _successful(conn, ledger.provider, "/calendar"):
        weeks = load(row)
        if weeks:
            season = json.loads(row[3])["year"]
            season_start[int(season)] = min(parse_utc(w["startDate"]) for w in weeks)

    writer = FactWriter(conn)
    fbs: dict[int, set[int]] = {}
    for row in _successful(conn, ledger.provider, "/teams/fbs"):
        season = int(json.loads(row[3])["year"])
        if season not in season_start:
            continue  # no calendar, so no reconstructed availability; leave out rather than guess
        teams = load(row)
        fbs[season] = {t["id"] for t in teams}
        for t in teams:
            conn.execute("INSERT OR IGNORE INTO teams VALUES (?,?)", (team_id(t["id"]), t["school"]))
        writer.write(row[0], row[4], "fbs_membership", str(season),
                     {"season": season, "team_ids": sorted(team_id(i) for i in fbs[season])},
                     season_start[season], season_start[season] - MEMBERSHIP_LEAD)

    lag = timedelta(hours=result_lag_hours)
    games_seen = 0
    for row in _successful(conn, ledger.provider, "/games"):
        for g in load(row):
            members = fbs.get(g["season"])
            if members is None or (g["homeId"] not in members and g["awayId"] not in members):
                continue
            games_seen += 1
            for side in ("home", "away"):
                conn.execute("INSERT OR IGNORE INTO teams VALUES (?,?)",
                             (team_id(g[f"{side}Id"]), g[f"{side}Team"]))
            conn.execute("INSERT OR IGNORE INTO games VALUES (?,?,?,?)",
                         (game_id(g["id"]), g["season"], team_id(g["homeId"]), team_id(g["awayId"])))
            kickoff = parse_utc(g["startDate"])
            writer.write(row[0], row[4], "game_schedule", game_id(g["id"]), schedule_fact(g),
                         kickoff, kickoff - SCHEDULE_LEAD)
            result = result_fact(g)
            if result is not None:
                writer.write(row[0], row[4], "game_result", game_id(g["id"]), result,
                             kickoff, kickoff + lag)
    conn.commit()
    summary = {"games_seen": games_seen, "versions_added": writer.added, "unchanged": writer.unchanged}
    log(f"canonicalized: {summary}")
    return summary
