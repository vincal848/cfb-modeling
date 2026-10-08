"""T01: away underdogs that crossed exactly one time zone, late season (experiments/protocols/T01-protocol.md).

    uv run python -m cfb.evaluation.t01    # power gate first; opens covers only if the gate passes
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pandas as pd

from cfb.evaluation.k04 import lines_of
from cfb.evaluation.s01 import DISCOVERY_END, evaluate_bets, games_frame, permuted

NEEDED, WEEK_FROM, ALPHA, M_TOTAL = 2240, 9, 0.05, 16


def utc_offset(tz: str, when: pd.Timestamp) -> float:
    return when.tz_convert(ZoneInfo(tz)).utcoffset().total_seconds() / 3600


def cell(df: pd.DataFrame, team_tz: dict[int, str]) -> tuple[pd.DataFrame, dict]:
    """Late-season non-neutral games with an away underdog, plus the shift in hours; drops are counted."""
    d = df[(df["season_type"] == "regular") & (df["week"] >= WEEK_FROM) & ~df["neutral"] & (df["spread"] < 0)].copy()
    c = {"candidates": len(d)}
    d = d[d["home"].isin(team_tz) & d["away"].isin(team_tz)]
    c["with_both_time_zones"] = len(d)
    when = pd.to_datetime(d["date"], utc=True)
    d["shift"] = [abs(utc_offset(team_tz[h], t) - utc_offset(team_tz[a], t)) for h, a, t in zip(d["home"], d["away"], when)]
    return d[d["shift"] == 1.0], c


def bets(d: pd.DataFrame) -> pd.DataFrame:
    """The away underdog covers = the home team does not."""
    out = pd.DataFrame({"game_id": d["game_id"], "block": d["block"], "season": d["season"], "win": 1 - d["home_cover"]})
    return out.dropna(subset=["win"])


def main() -> None:
    from cfb.cli import REPO_ROOT, open_store

    _, cfbd = open_store()
    seasons = range(2014, 2026)
    games = [g for y in seasons for st in ("regular", "postseason")
             for g in cfbd.load(cfbd.latest_success("/games", {"year": y, "seasonType": st}))]
    df = games_frame(games, [g for ls in lines_of(cfbd, seasons).values() for g in ls])
    team_tz = {t["id"]: t["location"]["timezone"] for t in cfbd.load(cfbd.latest_success("/teams", {"year": 2024}))
               if (t.get("location") or {}).get("timezone")}
    cellg, counts = cell(df, team_tz)
    disc = cellg[cellg["season"] <= DISCOVERY_END]
    protocol = REPO_ROOT / "experiments" / "protocols" / "T01-protocol.md"
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
           "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(), "counts": counts,
           "cell_games_all": len(cellg), "cell_games_discovery": len(disc), "needed": NEEDED}
    if len(disc) < NEEDED:
        rep["verdict"] = "UNDERPOWERED, NOT RUN: fewer cell games than the gate requires; no cover outcome opened"
    else:
        r = evaluate_bets(bets(disc))
        pcell, _ = cell(permuted(df), team_tz)
        null = evaluate_bets(bets(pcell[pcell["season"] <= DISCOVERY_END]))
        rep |= {"discovery": r, "null": null}
        rep["verdict"] = ("PIPELINE BROKEN: null passed" if null["p"] < ALPHA / M_TOTAL else
                          "NO EDGE in discovery; 2024-2025 stays sealed" if r["p"] >= ALPHA / M_TOTAL else
                          "DISCOVERY PASSED: open 2024-2025 once")
    out = REPO_ROOT / "experiments" / "t01"
    out.mkdir(parents=True, exist_ok=True)
    (out / "t01-results.json").write_text(json.dumps(rep, indent=1, default=str))
    print(json.dumps(rep, indent=1, default=str))


if __name__ == "__main__":
    main()
