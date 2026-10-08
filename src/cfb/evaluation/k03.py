"""K03: pooled Kalshi favorite-longshot test across leagues (experiments/protocols/K03-protocol.md).

    uv run python -m cfb.evaluation.k03 --fetch   # markets + entry-window candles into the cache
    uv run python -m cfb.evaluation.k03           # replay from cache (0 calls), write experiments/k03/
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from cfb.evaluation.backtest import block_bootstrap
from cfb.ingestion.kalshi import parse_ts

SERIES = ("KXNFLGAME", "KXNBAGAME", "KXMLBGAME", "KXNHLGAME", "KXNCAAMBGAME", "KXWNBAGAME", "KXNCAAFGAME")
HOURS, CS = (24, 6), (0.85, 0.90, 0.95)
GRID = [(h, c) for h in HOURS for c in CS]
MIN_TRADES, ORDER = 300, 100
SPLIT = pd.Timestamp("2026-01-01", tz="UTC")
START_LAG, WINDOW = timedelta(hours=3), (30, 5)  # start = expected expiration - 3h; candles start-30h..start-5h
SEED, REPS, BOOT_SEED = 20261007, 4000, 7
BUCKETS = [0, 0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 1.0]


def fee(p: np.ndarray) -> np.ndarray:
    """Taker fee per contract with Kalshi's per-order cent rounding at an ORDER-contract order."""
    return np.ceil(ORDER * 0.07 * p * (1 - p) * 100 - 1e-9) / 100 / ORDER


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def events(markets: list[dict]) -> tuple[list[tuple[str, dict, datetime]], dict[str, int]]:
    """(event, first market, start) for settled two-market events with one yes and one no."""
    by: dict[str, list[dict]] = {}
    for m in markets:
        by.setdefault(m["event_ticker"], []).append(m)
    out, drops = [], {"not_two_markets": 0, "not_one_yes_one_no": 0}
    for ev, ms in by.items():
        if len(ms) != 2:
            drops["not_two_markets"] += 1
        elif sorted(m.get("result") for m in ms) != ["no", "yes"]:
            drops["not_one_yes_one_no"] += 1
        else:
            m = min(ms, key=lambda m: m["ticker"])
            out.append((ev, m, parse_ts(m["expected_expiration_time"]) - START_LAG))
    return out, drops


def window(start: datetime) -> tuple[int, int]:
    return int((start - timedelta(hours=WINDOW[0])).timestamp()), int((start - timedelta(hours=WINDOW[1])).timestamp())


def event_row(series: str, ev: str, m: dict, start: datetime, candles: list[dict]) -> dict:
    cs = sorted((int(c["end_period_ts"]), _f(c["yes_bid"].get("close")), _f(c["yes_ask"].get("close")))
                for c in candles)
    row = {"series": series, "event": ev, "start": pd.Timestamp(start), "yes_won": float(m["result"] == "yes")}
    for h in HOURS:
        cut = (start - timedelta(hours=h)).timestamp()
        ok = [c for c in cs if c[0] <= cut and 0 < c[1] < c[2] < 1]
        row[f"bid_{h}"], row[f"ask_{h}"] = (ok[-1][1], ok[-1][2]) if ok else (np.nan, np.nan)
    return row


def frame(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df["block"] = df["start"].dt.strftime("%G-W%V")
    df["split"] = np.where(df["start"] < SPLIT, "select", "validate")
    return df


def rule_pnl(df: pd.DataFrame, h: int, c: float) -> pd.Series:
    """Per-contract P&L of buying the side priced >= c at its ask (traded events only)."""
    bid, ask = df[f"bid_{h}"], df[f"ask_{h}"]
    yes = ask >= c
    no = ~yes & ((1 - bid) >= c)
    price = np.where(yes, ask, 1 - bid)
    won = np.where(yes, df["yes_won"], 1 - df["yes_won"])
    pnl = pd.Series(won - price - fee(price), index=df.index)
    return pnl[(yes | no) & bid.notna()]


def evaluate(df: pd.DataFrame, h: int, c: float) -> dict:
    pnl = rule_pnl(df, h, c)
    if len(pnl) == 0:
        return {"trades": 0}
    mean, lo, hi = block_bootstrap(pnl, df.loc[pnl.index, "block"], REPS, BOOT_SEED)
    return {"trades": len(pnl), "per_trade": mean, "lo": lo, "hi": hi, "hit_rate": float((pnl > 0).mean())}


def select_and_validate(df: pd.DataFrame) -> dict:
    sel, val = df[df["split"] == "select"], df[df["split"] == "validate"]
    cands = [(evaluate(sel, h, c), (h, c)) for h, c in GRID]
    grid = {f"h{h}_c{c}": r for r, (h, c) in cands}
    cands = [x for x in cands if x[0]["trades"] >= MIN_TRADES]
    if not cands:
        return {"selected": None, "passed": False, "select_grid": grid}
    best, (h, c) = max(cands, key=lambda x: x[0]["per_trade"])
    v = evaluate(val, h, c)
    by_league = {s: evaluate(g, h, c) for s, g in val.groupby("series")}
    return {"selected": {"hours": h, "c": c}, "select": best, "validate": v, "passed": v["trades"] > 0 and v["lo"] > 0,
            "validate_by_league": by_league, "select_grid": grid}


def permuted(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    out = df.copy()
    out["yes_won"] = out.groupby("block")["yes_won"].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


def calibration(df: pd.DataFrame, h: int) -> list[dict]:
    """Mid price vs win rate of the analyzed (alphabetically first) market of each event."""
    mid = (df[f"bid_{h}"] + df[f"ask_{h}"]) / 2
    g = pd.DataFrame({"mid": mid, "y": df["yes_won"]}).dropna()
    g["bucket"] = pd.cut(g["mid"], BUCKETS, include_lowest=True)
    return [{"bucket": str(b), "n": len(x), "mean_mid": float(x["mid"].mean()), "win_rate": float(x["y"].mean())}
            for b, x in g.groupby("bucket", observed=True)]


def mlb_start_agreement(df: pd.DataFrame) -> float | None:
    """Share of MLB events whose ticker start time (e.g. 26AUG062140, US Eastern) is within 15 min of ours."""
    et, hits, n = ZoneInfo("America/New_York"), 0, 0
    for ev, start in df.loc[df["series"] == "KXMLBGAME", ["event", "start"]].itertuples(index=False):
        try:
            t = datetime.strptime(ev.split("-")[1][:11], "%y%b%d%H%M").replace(tzinfo=et)
        except ValueError:
            continue
        n += 1
        hits += abs(t - start.to_pydatetime()) <= timedelta(minutes=15)
    return hits / n if n else None


def render(rep: dict) -> str:
    r = rep["real"]
    lines = [f"# K03 results\n\n**Verdict: {rep['verdict']}**\n",
             f"Protocol sha256 `{rep['protocol_sha256']}`; generated {rep['generated_at']}; Kalshi calls {rep['calls']}.",
             f"Events per series: {rep['events']}. Dropped: {rep['drops']}. MLB start-time agreement: {rep['mlb_start_agreement']}.\n"]
    if r["selected"]:
        lines += [f"## Selected rule (select split): {r['selected']}\n",
                  "| split | trades | per trade | 95% interval | hit rate |", "|---|---|---|---|---|"]
        for k in ("select", "validate"):
            x = r[k]
            lines.append(f"| {k} | {x['trades']} | {x['per_trade']:+.4f} | [{x['lo']:+.4f}, {x['hi']:+.4f}] | {x['hit_rate']:.3f} |")
        lines += ["\nValidation by league (descriptive):\n", "| series | trades | per trade | 95% interval |", "|---|---|---|---|"]
        for s, x in r["validate_by_league"].items():
            lines.append(f"| {s} | {x['trades']} | {x.get('per_trade', float('nan')):+.4f} | "
                         f"[{x.get('lo', float('nan')):+.4f}, {x.get('hi', float('nan')):+.4f}] |")
    lines += ["\n## Select-split grid\n", "| rule | trades | per trade | 95% interval |", "|---|---|---|---|"]
    for k, x in r["select_grid"].items():
        lines.append(f"| {k} | {x['trades']} | {x.get('per_trade', float('nan')):+.4f} | "
                     f"[{x.get('lo', float('nan')):+.4f}, {x.get('hi', float('nan')):+.4f}] |")
    n = rep["null"]
    lines.append(f"\n## Null (outcomes shuffled within week)\n\nSelected {n['selected']}, validate "
                 f"{n.get('validate')}, passed={n['passed']}.\n")
    for h, rows in rep["calibration"].items():
        lines += [f"## Calibration, {h} before start (all events, YES side)\n", "| bucket | n | mean mid | win rate |",
                  "|---|---|---|---|"] + [f"| {x['bucket']} | {x['n']} | {x['mean_mid']:.3f} | {x['win_rate']:.3f} |"
                                          for x in rows] + [""]
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    from cfb.cli import DATA_DIR, REPO_ROOT, open_store
    from cfb.ingestion.kalshi import KalshiReader
    from cfb.ingestion.ledger import RawLedger

    conn, _ = open_store()
    fetch = "--fetch" in argv
    reader = KalshiReader(RawLedger(DATA_DIR / "raw", conn, provider="KALSHI"), min_interval=0.2)
    rows, counts, drops = [], {}, {"not_two_markets": 0, "not_one_yes_one_no": 0}
    for series in SERIES:
        evs, d = events(reader.markets(series))
        counts[series] = len(evs)
        drops = {k: drops[k] + d[k] for k in drops}
        for i, (ev, m, start) in enumerate(evs):
            rows.append(event_row(series, ev, m, start, reader.candles(m, 60, *window(start))))
            if fetch and i % 500 == 0:
                print(f"{series} {i}/{len(evs)} ({reader.calls} calls)", flush=True)
    if fetch:
        print(f"done: {reader.calls} calls")
        return
    assert reader.calls == 0, "K03 analysis must replay from cache; run --fetch first"
    df = frame(rows)
    real, null = select_and_validate(df), select_and_validate(permuted(df))
    protocol = REPO_ROOT / "experiments" / "protocols" / "K03-protocol.md"
    verdict = ("NULL CHECK FAILED: pipeline broken, no claim" if null["passed"] else
               "PASS: paper-trade forward (not a trading signal yet)" if real["passed"] else
               "NO EDGE: validation interval lower bound is not > 0")
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "verdict": verdict,
           "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(), "calls": reader.calls,
           "events": counts, "drops": drops, "mlb_start_agreement": mlb_start_agreement(df),
           "real": real, "null": null, "calibration": {f"{h}h": calibration(df, h) for h in HOURS}}
    out = REPO_ROOT / "experiments" / "k03"
    out.mkdir(parents=True, exist_ok=True)
    (out / "k03-results.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "k03-results.md").write_text(render(rep), encoding="utf-8")
    print(render(rep))


if __name__ == "__main__":
    main(sys.argv[1:])
