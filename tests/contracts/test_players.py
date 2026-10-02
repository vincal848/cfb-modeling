"""D05 players and D06 portal crosswalk on SYNTHETIC CFBD-shaped records (fabricated)."""

import json

import pytest

from cfb.canonical.players import (
    canonicalize_rosters,
    crosswalk_portal,
    match_portal,
    normalize_name,
)
from cfb.ingestion.client import ApiResponse
from cfb.ingestion.ledger import RawLedger


def test_name_normalization():
    assert normalize_name("D'Andre", "Swift Jr.") == "dandre swift"
    assert normalize_name("José", "Núñez III") == "jose nunez"
    assert normalize_name("A.J.", "Green") == "aj green"


def roster(*rows):
    out = {}
    for team, first, last, aid in rows:
        out.setdefault((team, normalize_name(first, last)), []).append(aid)
    return out


def rec(first="Sam", last="Lee", origin="Alpha", dest="Beta"):
    return {"season": 2024, "firstName": first, "lastName": last, "origin": origin, "destination": dest,
            "transferDate": "2024-01-03T00:00:00.000Z", "position": "WR"}


def test_destination_roster_corroboration_verifies():
    status, pid, ev = match_portal(rec(), roster(("Alpha", "Sam", "Lee", "7")), {"7": "Beta"})
    assert (status, pid) == ("verified", "cfbd-athlete-7") and "corroboration" in ev


def test_unique_origin_match_without_destination_is_only_proposed():
    assert match_portal(rec(dest=None), roster(("Alpha", "Sam", "Lee", "7")), {})[:2] == ("proposed", "cfbd-athlete-7")
    # Destination named but the player is on a different roster: still only proposed.
    assert match_portal(rec(), roster(("Alpha", "Sam", "Lee", "7")), {"7": "Gamma"})[0] == "proposed"


def test_same_name_collision_is_ambiguous_and_never_merged():
    status, pid, ev = match_portal(rec(), roster(("Alpha", "Sam", "Lee", "7"), ("Alpha", "Sam", "Lee", "8")),
                                   {"7": "Beta"})
    assert status == "ambiguous" and pid is None and len(ev["candidates"]) == 2


def test_same_name_on_another_team_is_not_a_candidate():
    assert match_portal(rec(), roster(("Delta", "Sam", "Lee", "7")), {"7": "Beta"})[:2] == ("unresolved", None)


@pytest.fixture
def db_with_data(db, tmp_path):
    ledger = RawLedger(tmp_path / "raw", db, provider="SYNTHETIC")
    bodies = [
        ("/calendar", {"year": 2023}, [{"week": 1, "seasonType": "regular", "startDate": "2023-08-26T07:00:00.000Z"}]),
        ("/calendar", {"year": 2024}, [{"week": 1, "seasonType": "regular", "startDate": "2024-08-24T07:00:00.000Z"}]),
        ("/roster", {"year": 2023}, [
            {"id": "7", "firstName": "Sam", "lastName": "Lee", "team": "Alpha", "position": "WR"},
            {"id": "8", "firstName": "Pat", "lastName": "Kim", "team": "Alpha", "position": "QB"},
            {"id": "9", "firstName": "Pat", "lastName": "Kim", "team": "Alpha", "position": "LB"}]),
        ("/roster", {"year": 2024}, [
            {"id": "7", "firstName": "Sam", "lastName": "Lee", "team": "Beta", "position": "WR"},
            {"id": "9", "firstName": "Pat", "lastName": "Kim", "team": "Alpha", "position": "LB"}]),
        ("/player/portal", {"year": 2024}, [rec(), rec("Pat", "Kim", dest="Beta"), rec("Nobody", "Here")]),
    ]
    for n, (path, params, body) in enumerate(bodies):
        ledger.record(path, params, ApiResponse(200, json.dumps(body).encode(),
                                                f"2026-10-01T00:00:{n:02d}.000000Z", None, 1), None)
    return db, ledger


def test_end_to_end_identity_survives_transfer_and_rerun_adds_nothing(db_with_data):
    db, ledger = db_with_data
    canonicalize_rosters(db, ledger, log=lambda s: None)
    summary = crosswalk_portal(db, ledger, log=lambda s: None)
    assert (summary["verified"], summary["ambiguous"], summary["unresolved"]) == (1, 1, 1)
    teams = [t for (t,) in db.execute("SELECT t.display_name FROM roster_memberships m JOIN teams t USING(team_id) "
                                      "WHERE player_id='cfbd-athlete-7' ORDER BY valid_from")]
    assert teams == ["Alpha", "Beta"]  # one identity across the transfer
    events = {e for (e,) in db.execute("SELECT event_type FROM transfer_events WHERE player_id='cfbd-athlete-7'")}
    assert events == {"entry", "commitment", "enrollment"}
    assert db.execute("SELECT count(*) FROM transfer_events WHERE event_type='enrollment'").fetchone()[0] == 1
    # The ambiguous Pat Kim is linked to no player.
    assert db.execute("SELECT player_id FROM player_identity_links WHERE status='ambiguous'").fetchone() == (None,)

    before = [db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
              for t in ("source_records", "player_identity_links", "transfer_events", "roster_memberships")]
    canonicalize_rosters(db, ledger, log=lambda s: None)
    crosswalk_portal(db, ledger, log=lambda s: None)
    after = [db.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
             for t in ("source_records", "player_identity_links", "transfer_events", "roster_memberships")]
    assert before == after


def test_weaker_rules_propose_but_never_verify():
    # Nickname prefix: Sam on the portal, Samuel on the roster; destination confirms, still only proposed.
    status, pid, ev = match_portal(rec(), roster(("Alpha", "Samuel", "Lee", "7")), {"7": "Beta"})
    assert (status, pid, ev["method"]) == ("proposed", "cfbd-athlete-7", "first_name_prefix_prior_season_roster")
    # Different first names that are not prefixes (Julian/Julio) stay unresolved.
    assert match_portal(rec("Julian", "Humphrey"), roster(("Alpha", "Julio", "Humphrey", "5")), {})[0] == "unresolved"
    # Two prefix-compatible candidates: ambiguous, no player.
    two = roster(("Alpha", "Samuel", "Lee", "7"), ("Alpha", "Sammy", "Lee", "8"))
    assert match_portal(rec(), two, {})[:2] == ("ambiguous", None)
    # Exact name only on the portal-season origin roster: proposed.
    same = roster(("Alpha", "Sam", "Lee", "9"))
    assert match_portal(rec(), {}, {"9": "Beta"}, same)[:2] == ("proposed", "cfbd-athlete-9")
