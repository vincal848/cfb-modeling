"""Q01: maker-side quoting with a conservative fill model (experiments/protocols/Q01-protocol.md).

Fills are an UPPER BOUND: a trade-through proves a better price traded, not that our order was ahead in the queue.

    uv run python -m cfb.evaluation.q01 --fetch   # pre-game tape for the markets the cells can use
    uv run python -m cfb.evaluation.q01           # replay from cache (0 calls), write experiments/q01/
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from cfb.evaluation.backtest import block_bootstrap
from cfb.evaluation.k04 import PLACEBO_KEYS
from cfb.evaluation.s01 import holm
from cfb.markets import consensus_lines

DELTA, LEAD_S, EDGE = 0.03, 6 * 3600, 0.01
MAKER_RATE = 0.0175
AS_MINUTES = (5, 30, 60)
REPS, BOOT_SEED, SEED, ALPHA = 4000, 7, 20261008, 0.05


def maker_fee(p: float) -> float:
    return MAKER_RATE * p * (1 - p)


def cents_down(x: float) -> float:
    return float(np.floor(x * 100 + 1e-9) / 100)


# -- fill model ----------------------------------------------------------------------------------

def tape(trades: list[dict]) -> pd.DataFrame:
    """Ascending trade tape: ts (unix s), yes price, size."""
    t = pd.DataFrame({"ts": [pd.Timestamp(x["created_time"]).timestamp() for x in trades],
                      "yes": [float(x["yes_price_dollars"]) for x in trades],
                      "n": [float(x["count_fp"]) for x in trades]})
    return t.sort_values("ts", kind="stable").reset_index(drop=True)


def first_fill(tp: pd.DataFrame, side: str, price: float, t0: float, t1: float) -> float | None:
    """Time of the first trade in [t0, t1) strictly through a resting bid at `price` on `side` ('yes' or 'no'),
    of at least one contract; None if there is none."""
    inside = tp[(tp["ts"] >= t0) & (tp["ts"] < t1) & (tp["n"] >= 1)]
    hit = inside[inside["yes"] < price - 1e-9] if side == "yes" else inside[inside["yes"] > 1 - price + 1e-9]
    return float(hit["ts"].iloc[0]) if len(hit) else None


def fair_after(tp: pd.DataFrame, ts: float, minutes: int, start: float) -> float:
    """Last YES trade price at or before ts + minutes; NaN if that time is not before kickoff or there is none."""
    t = ts + 60 * minutes
    if t >= start:
        return np.nan
    before = tp[tp["ts"] <= t]
    return float(before["yes"].iloc[-1]) if len(before) else np.nan


def fill_row(game_id: str, block: str, cell: str, side: str, price: float, won: float, tp: pd.DataFrame,
             ts: float, start: float) -> dict:
    """One fill: settlement P&L after the maker fee, and the drift of fair value against the fill."""
    row = {"game_id": game_id, "block": block, "cell": cell, "side": side, "price": price,
           "pnl": won - price - maker_fee(price)}
    for d in AS_MINUTES:
        fair = fair_after(tp, ts, d, start)
        row[f"adv{d}"] = (fair - price) if side == "yes" else ((1 - fair) - price)  # positive = value rose after fill
    return row


# -- cells ---------------------------------------------------------------------------------------

def winner_fills(games: pd.DataFrame, tapes: dict[str, pd.DataFrame], anchor: str, cell: str) -> pd.DataFrame:
    """Q1/Q2: bid a - DELTA on YES and (1 - a) - DELTA on NO of the home market for each game.
    `games` has game_id, block, start, ticker, yes_won, and the anchor column."""
    rows = []
    for g in games.itertuples():
        a, tp, t0 = getattr(g, anchor), tapes.get(g.ticker), g.start - LEAD_S
        if tp is None or not np.isfinite(a):
            continue
        for side, price, won in (("yes", cents_down(a - DELTA), g.yes_won), ("no", cents_down(1 - a - DELTA), 1 - g.yes_won)):
            if not 0.01 <= price <= 0.99:
                continue
            ts = first_fill(tp, side, price, t0, g.start)
            if ts is not None:
                rows.append(fill_row(g.game_id, g.block, cell, side, price, won, tp, ts, g.start))
    return pd.DataFrame(rows)


def ladder_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """Q3 rows where the K04 model value beats the maker cost of joining both bids: YES lo at bid_lo, NO hi at 1 - ask_hi."""
    ok = df[["bid_lo", "ask_hi"]].notna().all(axis=1) & (df["bid_lo"] >= 0.01) & (df["ask_hi"] <= 0.99)
    d = df[ok]
    fees = np.array([maker_fee(a) + maker_fee(1 - b) for a, b in zip(d["bid_lo"], d["ask_hi"])])
    return d[d["q"] - (d["bid_lo"] - d["ask_hi"]) - fees > EDGE]


def ladder_fills(cands: pd.DataFrame, tapes: dict[str, pd.DataFrame], cell: str) -> pd.DataFrame:
    rows = []
    for r in cands.itertuples():
        t0, sgn = r.start - LEAD_S, 1 if r.k > 0 else -1
        s = sgn * r.m  # the ladder team's margin
        won_lo, won_hi = float(s >= abs(r.k)), float(s >= abs(r.k) + 1)
        legs = ((r.lo_ticker, "yes", r.bid_lo, won_lo), (r.hi_ticker, "no", 1 - r.ask_hi, 1 - won_hi))
        for ticker, side, price, won in legs:
            tp = tapes.get(ticker)
            ts = first_fill(tp, side, price, t0, r.start) if tp is not None else None
            if ts is not None:
                rows.append(fill_row(r.game_id, f"{r.block}", cell, side, price, won, tp, ts, r.start) | {"k": r.k})
    return pd.DataFrame(rows)


# -- statistics ----------------------------------------------------------------------------------

def summarize(fills: pd.DataFrame) -> dict:
    if len(fills) < 30:
        return {"fills": len(fills), "p": 1.0, "passed": False}
    mean, lo, hi = block_bootstrap(fills["pnl"], fills["game_id"], REPS, BOOT_SEED)
    s = fills.groupby("game_id")["pnl"].agg(["sum", "size"])
    rng = np.random.Generator(np.random.PCG64(BOOT_SEED))
    pick = rng.integers(0, len(s), size=(REPS, len(s)))
    p = float(((s["sum"].to_numpy()[pick].sum(1) / s["size"].to_numpy()[pick].sum(1)) <= 0).mean())
    out = {"fills": len(fills), "games": int(fills["game_id"].nunique()), "per_fill": mean, "lo": lo, "hi": hi,
           "p": max(p, 1 / REPS), "yes_fills": int((fills["side"] == "yes").sum())}
    for d in AS_MINUTES:
        v = fills.dropna(subset=[f"adv{d}"])
        if len(v) >= 30:
            m, l, h = block_bootstrap(v[f"adv{d}"], v["game_id"], REPS, BOOT_SEED)
            out[f"adv{d}"] = {"n": len(v), "mean": m, "lo": l, "hi": h}
    return out


# -- simulation ----------------------------------------------------------------------------------

def simulate_world(n: int, seed: int, martingale: bool) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    """Games with a known anchor and a pre-game tape. martingale=True: the traded price is a fair martingale and
    the outcome is Bernoulli(final price) (no maker edge exists). False: trades scatter around the true probability
    (mean-reverting noise) and the anchor is the truth (a maker edge exists)."""
    rng = np.random.default_rng(seed)
    games, tapes = [], {}
    for i in range(n):
        p0, start = float(rng.uniform(0.2, 0.8)), 1.0e9
        ts = np.sort(start - LEAD_S + rng.uniform(0, LEAD_S, 60))
        if martingale:
            path = np.clip(p0 + np.cumsum(rng.normal(0, 0.012, 60)), 0.02, 0.98)
            yes, p_final = path, path[-1]
        else:
            yes, p_final = np.clip(p0 + rng.normal(0, 0.04, 60), 0.02, 0.98), p0
        tapes[f"t{i}"] = pd.DataFrame({"ts": ts, "yes": np.round(yes, 2), "n": 5.0})
        games.append({"game_id": f"g{i}", "block": f"w{i % 14}", "start": start, "ticker": f"t{i}",
                      "yes_won": float(rng.uniform() < p_final), "anchor": p0})
    return pd.DataFrame(games), tapes


def permuted_anchor(games: pd.DataFrame, col: str) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    out = games.copy()
    out[col] = out.groupby("block")[col].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


# -- real data -----------------------------------------------------------------------------------

def build_games(conn, cfbd, reader) -> tuple[pd.DataFrame, dict]:
    """One row per mapped 2025 game: home-market ticker and outcome, kickoff, book anchor, Kalshi T-6h mid."""
    from cfb.evaluation.backtest import latest_facts
    from cfb.evaluation.k02 import home_market, quote_at, quotes
    from cfb.evaluation.k04 import lines_of
    from cfb.ingestion.kalshi import map_events, parse_ts, team_names

    names = team_names(conn, cfbd)
    schedules = [s for s in latest_facts(conn, "game_schedule") if s["season"] == 2025]
    sched = {s["game_id"]: s for s in schedules}
    markets = [m for m in reader.markets("KXNCAAFGAME") if m.get("result") in ("yes", "no")]
    book = dict(consensus_lines(lines_of(cfbd, [2025])[2025]).set_index("game_id")["p_win_market"])
    by_event: dict[str, list[dict]] = {}
    for m in markets:
        by_event.setdefault(m["event_ticker"], []).append(m)
    c = {"events": len(by_event), "mapped": 0, "ambiguous_side": 0}
    rows = []
    for ev, gid in map_events(markets, schedules, names).items():
        if gid is None:
            continue
        c["mapped"] += 1
        s = sched[gid]
        hm = home_market(by_event[ev], names, s["home_team_id"], s["away_team_id"])
        if hm is None:
            c["ambiguous_side"] += 1
            continue
        start = parse_ts(s["start_utc"]).timestamp()
        q = quotes(reader.candles(hm))
        bid, ask = quote_at(q, start - LEAD_S) if not q.empty else (np.nan, np.nan)
        rows.append({"game_id": gid, "block": f"{s['season_type']}-{s['week']}", "start": start, "ticker": hm["ticker"],
                     "yes_won": float(hm["result"] == "yes"), "book": book.get(gid, np.nan), "kalshi": (bid + ask) / 2})
    return pd.DataFrame(rows), c


def fetch_tapes(reader, tickers: set[str], starts: dict[str, float]) -> dict[str, pd.DataFrame]:
    out = {}
    for i, t in enumerate(sorted(tickers)):
        s = int(starts[t])
        out[t] = tape(reader.trades_between(t, s - LEAD_S, s))
        if i % 200 == 0:
            print(f"tape {i}/{len(tickers)} ({reader.calls} calls)", flush=True)
    return out


def ladder_frames(conn, cfbd, reader):
    """K04 ladder frames for the real keys and the placebo keys, with the model value q."""
    from cfb.canonical.games import game_id
    from cfb.evaluation import k04
    from cfb.evaluation.k04 import lines_of

    events, _ = k04.load_events(conn, cfbd, reader)
    g25 = {game_id(g["id"]): g for g in lines_of(cfbd, [2025])[2025]}
    spread = consensus_lines(list(g25.values())).set_index("game_id")["spread"].dropna()
    model = k04.fit(k04.train_frame(lines_of(cfbd, range(2014, 2025))), 2023)
    out = {}
    for name, keys in (("real", k04.KEYS), ("placebo", PLACEBO_KEYS)):
        f, _ = k04.build_frame(events, g25, spread, lambda m, a, b: reader.candles(m, 60, a, b), keys)
        f["q"] = k04.q_model(model, f["mu"].to_numpy(), f["k"].to_numpy())
        out[name] = f
    return out


def main(argv: list[str]) -> None:
    from cfb.cli import DATA_DIR, REPO_ROOT, open_store
    from cfb.evaluation.s01 import trial_count
    from cfb.ingestion.kalshi import KalshiReader
    from cfb.ingestion.ledger import RawLedger

    conn, cfbd = open_store()
    fetch = "--fetch" in argv
    reader = KalshiReader(RawLedger(DATA_DIR / "raw", conn, provider="KALSHI"), min_interval=0.25)
    games, counts = build_games(conn, cfbd, reader)
    frames = ladder_frames(conn, cfbd, reader)
    cands = {k: ladder_candidates(f) for k, f in frames.items()}
    need = dict(zip(games["ticker"], games["start"]))
    for c in cands.values():
        for col in ("lo_ticker", "hi_ticker"):
            need |= dict(zip(c[col], c["start"]))
    if fetch:
        fetch_tapes(reader, set(need), need)
        print(f"done: {reader.calls} calls")
        return
    tapes = {t: tape(reader.trades_between(t, int(s) - LEAD_S, int(s))) for t, s in need.items()}
    assert reader.calls == 0, "Q01 analysis must replay from cache; run --fetch first"
    m_total = trial_count(REPO_ROOT / "experiments" / "trials.csv")
    fills = {"Q1": winner_fills(games, tapes, "book", "Q1"), "Q2": winner_fills(games, tapes, "kalshi", "Q2"),
             "Q3": ladder_fills(cands["real"], tapes, "Q3")}
    null = {"Q1": winner_fills(permuted_anchor(games, "book"), tapes, "book", "Q1"),
            "Q2": winner_fills(permuted_anchor(games, "kalshi"), tapes, "kalshi", "Q2"),
            "Q3": ladder_fills(cands["placebo"], tapes, "Q3")}
    real, nul = {k: summarize(v) for k, v in fills.items()}, {k: summarize(v) for k, v in null.items()}
    real_ok, null_ok = holm({k: v["p"] for k, v in real.items()}, m_total), holm({k: v["p"] for k, v in nul.items()}, m_total)
    both = {}
    if len(fills["Q3"]):
        g = fills["Q3"].groupby(["game_id", "k"])["side"].nunique()
        both = {"ladder_rows": len(cands["real"]), "games_with_both_legs": int((g == 2).sum()), "games_with_any_fill": len(g)}
    protocol = REPO_ROOT / "experiments" / "protocols" / "Q01-protocol.md"
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "m_total": m_total, "counts": counts,
           "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(), "games": len(games),
           "real": real, "null": nul, "holm": real_ok, "null_holm": null_ok, "q3_legs": both}
    rep["verdict"] = ("PIPELINE BROKEN: a null cell passed Holm, no claim" if any(null_ok.values()) else
                      "PASS (upper bound, paper-quote forward only): " + ", ".join(k for k, v in real_ok.items() if v)
                      if any(real_ok.values()) else "NO EDGE: no maker cell has a Holm-significant positive P&L per fill")
    out = REPO_ROOT / "experiments" / "q01"
    out.mkdir(parents=True, exist_ok=True)
    (out / "q01-results.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "q01-results.md").write_text(render(rep), encoding="utf-8")
    print(render(rep))


def render(rep: dict) -> str:
    def row(k, s):
        if s["fills"] < 30:
            return f"| {k} | {s['fills']} | - | - | - |"
        adv = "; ".join(f"{d}m {s[f'adv{d}']['mean']:+.4f}" for d in AS_MINUTES if f"adv{d}" in s)
        return f"| {k} | {s['fills']} | {s['per_fill']:+.4f} | [{s['lo']:+.4f}, {s['hi']:+.4f}] | {adv} |"

    head = ["| cell | fills | P&L per fill | 95% interval | fair-value drift after fill |", "|---|---|---|---|---|"]
    lines = [f"# Q01 results\n\n**Verdict: {rep['verdict']}**\n",
             (f"Upper bound: queue position is ignored. Ledger family size {rep['m_total']}; protocol sha256 "
              f"`{rep['protocol_sha256']}`. Games with a home market and a kickoff: {rep['games']} ({rep['counts']}).\n"),
             "## Real", "", *head, *[row(k, s) for k, s in rep["real"].items()], "",
             "## Null (anchors permuted within week; Q3 on neighbouring cells 4, 8)", "", *head,
             *[row(k, s) for k, s in rep["null"].items()], "", f"Q3 leg pairing: {rep['q3_legs']}", ""]
    return "\n".join(lines)


if __name__ == "__main__":
    main(sys.argv[1:])
