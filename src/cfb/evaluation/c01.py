"""C01: S01 and K04 rules restricted to low-attention cohorts (experiments/protocols/C01-protocol.md).

    uv run python -m cfb.evaluation.c01
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from cfb.evaluation.s01 import (
    CELLS,
    DISCOVERY_END,
    cell_bets,
    evaluate_bets,
    games_frame,
    holm,
    permuted,
    trial_count,
)

G5 = {"American Athletic", "Conference USA", "Mid-American", "Mountain West", "Sun Belt"}
COHORTS = ("fcs", "g5_midweek", "early")


def cohort_ids(df: pd.DataFrame, name: str) -> set[str]:
    """Game ids in a cohort (definitions in the protocol)."""
    if name == "fcs":
        m = (df["home_class"] == "fcs") | (df["away_class"] == "fcs")
    elif name == "g5_midweek":
        day = pd.to_datetime(df["date"], utc=True).dt.tz_convert("America/New_York").dt.dayofweek
        m = (df["home_conf"].isin(G5) | df["away_conf"].isin(G5)) & day.between(1, 4)
    elif name == "early":
        m = (df["season_type"] == "regular") & (df["week"] <= 3)
    else:
        raise KeyError(name)
    return set(df.loc[m, "game_id"])


def s01_cohort_cells(df: pd.DataFrame, m_total: int, seasons: tuple[int, int]) -> dict:
    d = df[(df["season"] >= seasons[0]) & (df["season"] <= seasons[1])]
    ids = {c: cohort_ids(d, c) for c in COHORTS}
    res = {}
    for cell in CELLS:
        bets = cell_bets(d, cell)
        for c in COHORTS:
            res[f"{cell}|{c}"] = evaluate_bets(bets[bets["game_id"].isin(ids[c])])
    surv = holm({k: r["p"] for k, r in res.items()}, m_total)
    return {"cells": res, "holm_survivors": [k for k, ok in surv.items() if ok]}


def k04_cohort_cells(frame: pd.DataFrame, cohorts: dict[str, set[str]]) -> dict:
    from cfb.evaluation import k04

    return {name: k04.evaluate(frame[frame["game_id"].isin(ids)]) for name, ids in cohorts.items()}


def terciles(volume: dict[str, float]) -> set[str]:
    cut = np.quantile(list(volume.values()), 1 / 3)
    return {g for g, v in volume.items() if v <= cut}


def render(rep: dict) -> str:
    nan = float("nan")
    lines = [f"# C01 results\n\n**Verdict: {rep['verdict']}**\n",
             f"Ledger family size {rep['m_total']}; protocol sha256 `{rep['protocol_sha256']}`.\n",
             f"Cohort sizes (games with a line, 2014-2023): {rep['cohort_sizes']}\n", "## S01 cells by cohort (discovery)\n",
             "| cell | bets | cover rate | P&L per bet | 95% interval | p |", "|---|---|---|---|---|---|"]
    for k, r in rep["s01"]["cells"].items():
        lines.append(f"| {k} | {r['bets']} | {r.get('cover_rate', nan):.4f} | {r.get('per_bet', nan):+.4f} | "
                     f"[{r.get('lo', nan):+.4f}, {r.get('hi', nan):+.4f}] | {r['p']:.4f} |")
    lines += ["", f"Null (permuted covers): survivors {rep['s01_null']['holm_survivors']}.", "",
              "## K04 rule by cohort (2025)", "", "| cohort | ladder rows | trades |", "|---|---|---|"]
    lines += [f"| {c} | {rep['k04_cohort_games'][c]} | {r['trades']} |" for c, r in rep["k04"].items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    from cfb.canonical.games import game_id
    from cfb.cli import DATA_DIR, REPO_ROOT, open_store
    from cfb.evaluation import k04
    from cfb.evaluation.backtest import latest_facts
    from cfb.evaluation.k04 import lines_of
    from cfb.ingestion.kalshi import KalshiReader, map_events, team_names
    from cfb.ingestion.ledger import RawLedger
    from cfb.markets import consensus_lines

    conn, cfbd = open_store()
    seasons = range(2014, 2026)
    games = [g for y in seasons for st in ("regular", "postseason")
             for g in cfbd.load(cfbd.latest_success("/games", {"year": y, "seasonType": st}))]
    df = games_frame(games, [g for ls in lines_of(cfbd, seasons).values() for g in ls])
    m_total = trial_count(REPO_ROOT / "experiments" / "trials.csv")
    protocol = REPO_ROOT / "experiments" / "protocols" / "C01-protocol.md"
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "m_total": m_total,
           "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
           "cohort_sizes": {c: len(cohort_ids(df[df["season"] <= DISCOVERY_END], c)) for c in COHORTS},
           "s01": s01_cohort_cells(df, m_total, (2014, DISCOVERY_END)),
           "s01_null": s01_cohort_cells(permuted(df), m_total, (2014, DISCOVERY_END))}
    # K04 cohorts on the 2025 ladder frame (cache only)
    reader = KalshiReader(RawLedger(DATA_DIR / "raw", conn, provider="KALSHI"))
    events, _ = k04.load_events(conn, cfbd, reader)
    g25 = {game_id(g["id"]): g for g in lines_of(cfbd, [2025])[2025]}
    spread = consensus_lines(list(g25.values())).set_index("game_id")["spread"].dropna()
    frame, _ = k04.build_frame(events, g25, spread, lambda m, a, b: reader.candles(m, 60, a, b))
    model = k04.fit(k04.train_frame(lines_of(cfbd, range(2014, 2025))), 2023)
    frame["q"] = k04.q_model(model, frame["mu"].to_numpy(), frame["k"].to_numpy())
    d25 = df[df["season"] == 2025]
    cohorts = {c: cohort_ids(d25, c) for c in COHORTS}
    schedules = [s for s in latest_facts(conn, "game_schedule") if s["season"] == 2025]
    game_markets = reader.markets("KXNCAAFGAME")
    ev_game = map_events(game_markets, schedules, team_names(conn, cfbd))
    vol: dict[str, float] = {}
    for m in game_markets:
        gid = ev_game.get(m["event_ticker"])
        if gid:
            vol[gid] = max(vol.get(gid, 0.0), float(m.get("volume_fp") or 0))
    cohorts["low_volume"] = terciles(vol)
    assert reader.calls == 0, "C01 replays from cache"
    rep["k04"] = k04_cohort_cells(frame, cohorts)
    rep["k04_cohort_games"] = {c: int(frame["game_id"].isin(ids).sum()) for c, ids in cohorts.items()}
    surv = rep["s01"]["holm_survivors"]
    rep["verdict"] = ("PIPELINE BROKEN: null produced a survivor" if rep["s01_null"]["holm_survivors"] else
                      "NO EDGE: no cohort cell survives Holm in discovery; 2024-2025 stays sealed" if not surv else
                      "SURVIVORS in discovery: " + ", ".join(surv) + " (2024-2025 not yet opened)")
    out = REPO_ROOT / "experiments" / "c01"
    out.mkdir(parents=True, exist_ok=True)
    (out / "c01-results.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "c01-results.md").write_text(render(rep), encoding="utf-8")
    print(render(rep))


if __name__ == "__main__":
    main()
