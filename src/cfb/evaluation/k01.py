"""K01: does a favorite-buying rule on Kalshi KXNCAAFGAME make money after fees?
(experiments/protocols/K01-protocol.md)

    uv run python -m cfb.evaluation.k01            # cached data only, 0 calls
    uv run python -m cfb.evaluation.k01 --trades   # also fetch trades for <= 80 sampled events
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from cfb.evaluation.backtest import block_bootstrap

HOURS = (24, 3, 1)
GRID = [(h, c, v) for h in HOURS for c in (0.60, 0.70, 0.80, 0.90) for v in ("taker", "maker")]
MIN_TRADES = 100
SPLIT = pd.Timestamp("2025-11-01", tz="UTC")
START = pd.Timestamp("2025-08-01", tz="UTC")
SEED = 20261007
REPS, BOOT_SEED = 4000, 7
TRADE_SAMPLE = 80
PROTOCOL = Path(__file__).resolve().parents[3] / "experiments" / "protocols" / "K01-protocol.md"


def _f(x) -> float:
    try:
        return float(x)
    except (TypeError, ValueError):
        return np.nan


def _ts(x) -> pd.Timestamp:
    if isinstance(x, str) and not x.isdigit():
        return pd.Timestamp(x).tz_convert("UTC")
    return pd.Timestamp(int(x), unit="s", tz="UTC")


def event_frame(markets: list[dict], candles: dict[str, list[dict]], kickoffs: dict[str, tuple[pd.Timestamp, bool]]) -> pd.DataFrame:
    """One row per event (alphabetically first ticker): bid_h/ask_h at each entry hour, outcome, volume."""
    first = {}
    for m in sorted(markets, key=lambda m: m["ticker"]):
        first.setdefault(m["event_ticker"], m)
    rows = []
    for ev, m in first.items():
        if m.get("result") not in ("yes", "no") or ev not in kickoffs:
            continue
        ko, matched = kickoffs[ev]
        cs = sorted(((_ts(c["end_period_ts"]), _f(c["yes_bid"]["close"]), _f(c["yes_ask"]["close"]))
                     for c in candles.get(m["ticker"], [])), key=lambda c: c[0])
        row = {"event": ev, "ticker": m["ticker"], "kickoff": ko, "matched": matched,
               "yes_won": float(m["result"] == "yes"), "volume": _f(m.get("volume_fp"))}
        for h in HOURS:
            ok = [c for c in cs if c[0] <= ko - timedelta(hours=h) and c[1] == c[1] and c[2] == c[2]]
            row[f"bid_{h}"], row[f"ask_{h}"] = (ok[-1][1], ok[-1][2]) if ok else (np.nan, np.nan)
        rows.append(row)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df[df["kickoff"] >= START].reset_index(drop=True)
    df["block"] = df["kickoff"].dt.strftime("%G-W%V")
    df["split"] = np.where(df["kickoff"] < SPLIT, "select", "validate")
    return df


def rule_pnl(df: pd.DataFrame, h: int, c: float, variant: str) -> pd.Series:
    """P&L per contract for each traded event (index = df index of trades only)."""
    bid, ask = df[f"bid_{h}"], df[f"ask_{h}"]
    yes = ask >= c
    no = ~yes & ((1 - bid) >= c)
    side_win = np.where(yes, df["yes_won"], 1 - df["yes_won"])
    if variant == "taker":
        price, rate = np.where(yes, ask, 1 - bid), 0.07
    else:
        price, rate = np.where(yes, bid, 1 - ask) + 0.01, 0.0175
    pnl = pd.Series(side_win - price - rate * price * (1 - price), index=df.index)
    return pnl[(yes | no) & bid.notna() & ask.notna()]


def evaluate(df: pd.DataFrame, h: int, c: float, variant: str) -> dict:
    pnl = rule_pnl(df, h, c, variant)
    if len(pnl) == 0:
        return {"trades": 0}
    mean, lo, hi = block_bootstrap(pnl, df.loc[pnl.index, "block"], REPS, BOOT_SEED)
    return {"trades": len(pnl), "total": float(pnl.sum()), "per_trade": mean, "lo": lo, "hi": hi,
            "hit_rate": float((pnl > 0).mean())}


def select_and_validate(df: pd.DataFrame) -> dict:
    sel_df, val_df = df[df["split"] == "select"], df[df["split"] == "validate"]
    cands = [(evaluate(sel_df, *g), g) for g in GRID]
    cands = [c for c in cands if c[0]["trades"] >= MIN_TRADES]
    if not cands:
        return {"selected": None, "passed": False, "reason": f"no rule with >= {MIN_TRADES} select trades"}
    sel, (h, c, v) = max(cands, key=lambda c: c[0]["per_trade"])
    val = evaluate(val_df, h, c, v)
    return {"selected": {"hours": h, "c": c, "variant": v}, "select": sel, "validate": val,
            "passed": val["trades"] > 0 and val["lo"] > 0}


def permuted(df: pd.DataFrame) -> pd.DataFrame:
    """Null: outcomes shuffled across events within each week."""
    rng = np.random.default_rng(SEED)
    out = df.copy()
    out["yes_won"] = out.groupby("block")["yes_won"].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


def calibration(df: pd.DataFrame) -> list[dict]:
    rows = []
    for h in HOURS:
        mid = (df[f"bid_{h}"] + df[f"ask_{h}"]) / 2
        g = pd.DataFrame({"mid": mid, "y": df["yes_won"]}).dropna()
        g["bucket"] = np.minimum((g["mid"] * 10).astype(int), 9) / 10
        for b, x in g.groupby("bucket"):
            rows.append({"hours": h, "bucket": f"{b:.1f}-{b + 0.1:.1f}", "n": len(x),
                         "mean_mid": float(x["mid"].mean()), "win_rate": float(x["y"].mean())})
    return rows


def spreads(df: pd.DataFrame) -> dict:
    s = (df["ask_3"] - df["bid_3"]).where(df["volume"].notna())
    d = pd.DataFrame({"spread": s, "volume": df["volume"]}).dropna()
    if d.empty:
        return {"median": None, "deciles": []}
    d["decile"] = pd.qcut(d["volume"].rank(method="first"), min(10, len(d)), labels=False)
    return {"median": float(d["spread"].median()),
            "deciles": [{"decile": int(k), "n": len(x), "median_volume": float(x["volume"].median()),
                         "median_spread": float(x["spread"].median())} for k, x in d.groupby("decile")]}


def taker_breakdown(trades: list[dict], yes_won: float) -> pd.DataFrame:
    """Per trade: taker side, taker price, count, taker gross P&L per contract (maker = -taker)."""
    rows = []
    for t in trades:
        yp = _f(t.get("yes_price_dollars", t.get("yes_price")))
        if "yes_price_dollars" not in t and not np.isnan(yp):
            yp /= 100
        side, n = t.get("taker_side"), _f(t.get("count_fp", t.get("count")))
        if np.isnan(yp) or side not in ("yes", "no") or np.isnan(n):
            continue
        price = yp if side == "yes" else 1 - yp
        win = yes_won if side == "yes" else 1 - yes_won
        rows.append({"price": price, "n": n, "pnl": win - price})
    return pd.DataFrame(rows)


def trades_summary(frames: list[pd.DataFrame]) -> list[dict]:
    if not frames:
        return []
    d = pd.concat(frames)
    d["bucket"] = np.minimum((d["price"] * 10).astype(int), 9) / 10
    return [{"taker_price": f"{b:.1f}-{b + 0.1:.1f}", "contracts": float(x["n"].sum()),
             "taker_pnl_per_contract": float((x["pnl"] * x["n"]).sum() / x["n"].sum())}
            for b, x in d.groupby("bucket")]


def render(rep: dict) -> str:
    def row(r):
        return (f"{r['trades']} trades, {r['per_trade']:+.4f}/trade [{r['lo']:+.4f}, {r['hi']:+.4f}], "
                f"hit {r['hit_rate']:.2f}") if r.get("trades") else "no trades"

    real, null = rep["real"], rep["null"]
    if rep.get("null_failed"):
        head = "NULL CHECK FAILED: pipeline broken, no result reported."
    elif real["passed"]:
        head = "PASS: validation interval lower bound > 0 (null did not pass)."
    else:
        head = "NO EDGE: validation interval lower bound is not > 0."
    out = [f"# K01 results\n\n**Verdict: {head}**\n", f"Protocol sha256 `{rep['protocol_sha256']}`; generated {rep['generated_at']}.\n",
           (f"Events {rep['events']} (matched to CFBD {rep['matched']}, rate {rep['match_rate']:.3f}; "
            f"unmatched use expiry - 3.5h). Calls: {rep['calls']}.\n"), "## Selected rule\n"]
    if real["selected"]:
        out += [f"`{real['selected']}`\n", f"- select (Aug-Oct): {row(real['select'])}",
                f"- validate (Nov-Jan): {row(real['validate'])}\n"]
    else:
        out.append(real["reason"] + "\n")
    out += ["## Null (outcomes shuffled within week)\n"]
    out.append(f"`{null['selected']}` validate: {row(null['validate'])}, passed={null['passed']}\n" if null["selected"] else null["reason"] + "\n")
    out += ["## All rules, validation split (maker = assumed fills, upper bound)\n", "| hours | c | variant | select | validate |", "|---|---|---|---|---|"]
    out += [f"| {h} | {c} | {v} | {row(s)} | {row(x)} |" for (h, c, v), s, x in rep["grid"]]
    out += ["", "## Calibration (mid vs outcome)\n", "| hours | bucket | n | mean mid | win rate |", "|---|---|---|---|---|"]
    out += [f"| {r['hours']} | {r['bucket']} | {r['n']} | {r['mean_mid']:.3f} | {r['win_rate']:.3f} |" for r in rep["calibration"]]
    sp = rep["spread"]
    out += ["", f"## Bid-ask spread at 3h (median {sp['median']})\n", "| volume decile | n | median volume | median spread |", "|---|---|---|---|"]
    out += [f"| {r['decile']} | {r['n']} | {r['median_volume']:.0f} | {r['median_spread']:.3f} |" for r in sp["deciles"]]
    if rep["taker_by_price"]:
        out += ["", f"## Taker gross P&L per contract ({rep['trade_events']} sampled events)\n", "| taker price | contracts | pnl/contract |", "|---|---|---|"]
        out += [f"| {r['taker_price']} | {r['contracts']:.0f} | {r['taker_pnl_per_contract']:+.4f} |" for r in rep["taker_by_price"]]
    return "\n".join(out) + "\n"


def run(df: pd.DataFrame) -> dict:
    sel_df, val_df = df[df["split"] == "select"], df[df["split"] == "validate"]
    real, null = select_and_validate(df), select_and_validate(permuted(df))
    return {"real": real, "null": null, "null_failed": bool(null["passed"]),
            "grid": [(g, evaluate(sel_df, *g), evaluate(val_df, *g)) for g in GRID],
            "calibration": calibration(df), "spread": spreads(df)}


def main(argv: list[str]) -> None:
    from cfb.cli import DATA_DIR, REPO_ROOT, open_store
    from cfb.evaluation.backtest import latest_facts
    from cfb.ingestion.kalshi import KalshiReader, map_events, parse_ts, team_names
    from cfb.ingestion.ledger import RawLedger

    conn, cfbd = open_store()
    r = KalshiReader(RawLedger(DATA_DIR / "raw", conn, provider="KALSHI"))
    markets = r.markets("KXNCAAFGAME")
    schedules = [s for s in latest_facts(conn, "game_schedule") if s["season"] == 2025]
    start = {s["game_id"]: pd.Timestamp(s["start_utc"]).tz_convert("UTC") for s in schedules}
    mapped = map_events(markets, schedules, team_names(conn, cfbd))
    exp = {m["event_ticker"]: parse_ts(m["expected_expiration_time"]) for m in markets if m.get("expected_expiration_time")}
    kick = {ev: (start[g], True) if g else (pd.Timestamp(exp[ev]).tz_convert("UTC") - timedelta(hours=3.5), False)
            for ev, g in mapped.items() if g or ev in exp}
    candles = {m["ticker"]: r.candles(m) for m in markets}
    df = event_frame(markets, candles, kick)
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "protocol": "K01",
           "protocol_sha256": hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
           "events": len(df), "matched": int(df["matched"].sum()), "match_rate": float(df["matched"].mean()),
           "markets": len(markets), "taker_by_price": [], "trade_events": 0, **run(df)}
    if "--trades" in argv:
        sample = df.sample(min(TRADE_SAMPLE, len(df)), random_state=SEED)
        frames = [taker_breakdown(r.trades(t), y) for t, y in zip(sample["ticker"], sample["yes_won"], strict=True)]
        rep["taker_by_price"], rep["trade_events"] = trades_summary([f for f in frames if len(f)]), len(sample)
    rep["calls"] = r.calls
    out = REPO_ROOT / "experiments" / "k01"
    out.mkdir(parents=True, exist_ok=True)
    (out / "k01-results.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "k01-results.md").write_text(render(rep))
    print(render(rep))


if __name__ == "__main__":
    main(sys.argv[1:])
