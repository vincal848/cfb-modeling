"""D05 (players) and D06: canonical players, roster memberships, and the portal crosswalk.

Players use CFBD athlete IDs (`cfbd-athlete-<id>`), which persist across teams, so a
transfer keeps one identity. Each roster row is a versioned `roster_entry` fact,
reconstructed as available at that season's first calendar week.

Portal records carry no athlete ID (D01 finding 5). Each becomes a versioned
`portal_entry` fact (reconstructed availability: its `transferDate`, which is an event
time, not publication evidence) and an identity link with one status:

- `verified`: exactly one player with the same normalized name on the origin team's
  roster the season before, and that same athlete ID on the named destination's roster
  in the portal season. Two independent records agree.
- `proposed`: exactly one origin-roster match without destination confirmation, or a
  unique match by one of two weaker rules: the exact name on the origin roster in the
  portal season itself, or the same last name with one first name a prefix (3+ letters)
  of the other (Sam/Samuel, Mitch/Mitchell). Weaker rules never give `verified`.
- `ambiguous`: more than one candidate under the first rule that finds any. No player
  is assigned; these are never merged automatically.
- `unresolved`: no origin-roster match. No player is assigned.

Links and transfer events are derived from the facts and rebuilt deterministically on
each run, so a change to these rules never leaves stale statuses behind.

Transfer events: `entry` for every record; `commitment` when a destination is named;
`enrollment` only when the destination roster confirms the player. A named destination
is not treated as enrollment, and portal entry is not treated as departure.
"""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from cfb.canonical.games import FactWriter, iso, parse_utc
from cfb.ingestion.ledger import LedgerEntry, RawLedger

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def player_id(athlete_id: str | int) -> str:
    return f"cfbd-athlete-{athlete_id}"


def normalize_name(first: str | None, last: str | None) -> str:
    """Lowercase ASCII, punctuation removed, generational suffixes dropped."""
    text = f"{first or ''} {last or ''}"
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"[^a-z ]+", " ", text.replace("'", "").replace(".", ""))
    return " ".join(w for w in text.split() if w not in SUFFIXES)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class TeamNames:
    """Roster and portal records name teams; map names to canonical team IDs. A name not in
    the canonical teams table (e.g. a Division II school) gets a name-based ID."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.by_name = {name: tid for tid, name in conn.execute("SELECT team_id, display_name FROM teams")}

    def get(self, name: str | None) -> str | None:
        if not name:
            return None
        if name not in self.by_name:
            tid = f"cfbd-teamname-{_slug(name)}"
            self.conn.execute("INSERT OR IGNORE INTO teams VALUES (?,?)", (tid, name))
            self.by_name[name] = tid
        return self.by_name[name]


def _requests(conn: sqlite3.Connection, provider: str, endpoint: str) -> list[tuple]:
    return conn.execute(
        """SELECT request_id, provider, endpoint, parameters_json, retrieved_at, http_status,
                  response_count, suspected_truncation, payload_uri, payload_hash
           FROM raw_requests WHERE provider=? AND endpoint=? AND http_status=200 ORDER BY retrieved_at""",
        (provider, endpoint)).fetchall()


def _season_starts(conn: sqlite3.Connection, ledger: RawLedger) -> dict[int, Any]:
    out = {}
    for row in _requests(conn, ledger.provider, "/calendar"):
        weeks = ledger.load(LedgerEntry(*row[:7], bool(row[7]), *row[8:]))
        if weeks:
            out[int(json.loads(row[3])["year"])] = min(parse_utc(w["startDate"]) for w in weeks)
    return out


def canonicalize_rosters(conn: sqlite3.Connection, ledger: RawLedger, log: Callable[[str], None] = print) -> dict:
    starts = _season_starts(conn, ledger)
    writer, teams = FactWriter(conn), TeamNames(conn)
    memberships = 0
    for row in _requests(conn, ledger.provider, "/roster"):
        params = json.loads(row[3])
        season = int(params["year"])
        if season not in starts:
            continue
        for r in ledger.load(LedgerEntry(*row[:7], bool(row[7]), *row[8:])):
            if r.get("id") is None:
                continue
            pid, tid = player_id(r["id"]), teams.get(r["team"])
            name = f"{r.get('firstName') or ''} {r.get('lastName') or ''}".strip()
            conn.execute("INSERT OR IGNORE INTO players VALUES (?,?)", (pid, name or pid))
            payload = {"player_id": pid, "team_id": tid, "season": season, "first_name": r.get("firstName"),
                       "last_name": r.get("lastName"), "position": r.get("position"), "jersey": r.get("jersey"),
                       "class_year": r.get("year"), "recruit_ids": r.get("recruitIds") or []}
            vid = writer.write(row[0], row[4], "roster_entry", f"{pid}|{season}|{tid}", payload,
                               starts[season], starts[season])
            cur = conn.execute("INSERT OR IGNORE INTO roster_memberships VALUES (?,?,?,?,?,?,?)",
                               (f"mem-{vid}", pid, tid, iso(starts[season]), None, "listed", vid))
            memberships += cur.rowcount
    conn.commit()
    summary = {"roster_versions_added": writer.added, "unchanged": writer.unchanged, "memberships_added": memberships}
    log(f"rosters: {summary}")
    return summary


def _prefix_compatible(a: str, b: str) -> bool:
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 3 and long_.startswith(short)


def match_portal(record: dict[str, Any], origin_roster: dict[tuple[str, str], list[str]],
                 dest_roster: dict[str, str],
                 origin_same_season: dict[tuple[str, str], list[str]] | None = None,
                 ) -> tuple[str, str | None, dict[str, Any]]:
    """(status, player_id or None, evidence) for one portal record.

    `origin_roster` maps (team name, normalized name) to athlete IDs on rosters the season
    before the portal season; `origin_same_season` is the same for the portal season;
    `dest_roster` maps athlete ID to team name in the portal season. Rules are tried in
    order and the first rule that finds any candidate decides.
    """
    name = normalize_name(record.get("firstName"), record.get("lastName"))
    origin = record.get("origin")
    evidence: dict[str, Any] = {"normalized_name": name, "origin": origin}

    def decide(cands: list[str], method: str, can_verify: bool):
        evidence.update(method=method, candidates=[player_id(c) for c in cands])
        if len(cands) > 1:
            return "ambiguous", None, evidence
        athlete = cands[0]
        evidence["destination_roster_team"] = dest_roster.get(athlete)
        dest = record.get("destination")
        if can_verify and dest and dest_roster.get(athlete) == dest:
            evidence["corroboration"] = "same athlete ID on destination roster in portal season"
            return "verified", player_id(athlete), evidence
        return "proposed", player_id(athlete), evidence

    if cands := origin_roster.get((origin, name), []):
        return decide(cands, "exact_name_prior_season_roster", True)
    if origin_same_season and (cands := origin_same_season.get((origin, name), [])):
        return decide(cands, "exact_name_portal_season_roster", False)
    parts = name.split()
    if len(parts) >= 2:
        first, last = parts[0], " ".join(parts[1:])
        cands = sorted({a for (team, n), ids in origin_roster.items() if team == origin
                        and n.split()[1:] == last.split() and n.split()
                        and _prefix_compatible(n.split()[0], first) for a in ids})
        if cands:
            return decide(cands, "first_name_prefix_prior_season_roster", False)
    evidence.update(method="none", candidates=[])
    return "unresolved", None, evidence


def crosswalk_portal(conn: sqlite3.Connection, ledger: RawLedger, log: Callable[[str], None] = print) -> dict:
    rosters: dict[int, list[dict]] = {}
    for row in _requests(conn, ledger.provider, "/roster"):
        rosters[int(json.loads(row[3])["year"])] = ledger.load(LedgerEntry(*row[:7], bool(row[7]), *row[8:]))
    writer, teams = FactWriter(conn), TeamNames(conn)
    counts: dict[str, int] = defaultdict(int)
    conn.execute("DELETE FROM transfer_events")  # derived: rebuilt below
    conn.execute("DELETE FROM player_identity_links")
    for row in _requests(conn, ledger.provider, "/player/portal"):
        season = int(json.loads(row[3])["year"])
        origin_roster: dict[tuple[str, str], list[str]] = defaultdict(list)
        for r in rosters.get(season - 1, []):
            if r.get("id") is not None:
                origin_roster[(r["team"], normalize_name(r.get("firstName"), r.get("lastName")))].append(str(r["id"]))
        dest_roster = {str(r["id"]): r["team"] for r in rosters.get(season, []) if r.get("id") is not None}
        same_season: dict[tuple[str, str], list[str]] = defaultdict(list)
        for r in rosters.get(season, []):
            if r.get("id") is not None:
                same_season[(r["team"], normalize_name(r.get("firstName"), r.get("lastName")))].append(str(r["id"]))
        for rec in ledger.load(LedgerEntry(*row[:7], bool(row[7]), *row[8:])):
            key = "|".join(str(rec.get(k)) for k in ("season", "firstName", "lastName", "origin", "transferDate"))
            when = parse_utc(rec["transferDate"]) if rec.get("transferDate") else None
            available = when or parse_utc(row[4])  # no event time: known only when retrieved
            vid = writer.write(row[0], row[4], "portal_entry", key, rec, when, available)
            status, pid, evidence = match_portal(rec, origin_roster, dest_roster, same_season)
            counts[status] += 1
            link_id = "link-" + hashlib.sha256(key.encode()).hexdigest()[:24]
            conn.execute("INSERT OR IGNORE INTO player_identity_links VALUES (?,?,?,?,?,?)",
                         (link_id, key, pid, status, json.dumps(evidence, sort_keys=True), vid))
            origin, dest = teams.get(rec.get("origin")), teams.get(rec.get("destination"))
            events = ["entry"] + (["commitment"] if dest else []) + (["enrollment"] if status == "verified" else [])
            for ev in events:
                conn.execute("INSERT OR IGNORE INTO transfer_events VALUES (?,?,?,?,?,?,?)",
                             (f"xfer-{ev}-{link_id[5:]}", pid, origin, dest if ev != "entry" else None,
                              ev, link_id, vid))
    conn.commit()
    summary = {"portal_versions_added": writer.added, **dict(counts)}
    log(f"portal crosswalk: {summary}")
    return summary
