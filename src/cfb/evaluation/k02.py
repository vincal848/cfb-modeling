"""K02: Kalshi vs de-vigged sportsbook consensus, 2025 (experiments/protocols/K02-protocol.md)

    uv run python -m cfb.evaluation.k02    # replays the Kalshi cache; makes no network calls
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime

import numpy as np
import pandas as pd
from scipy.special import expit, logit

from cfb.evaluation.backtest import block_bootstrap
from cfb.markets import fee

HOURS = (24, 1)
DS = (0.02, 0.04, 0.06)
MIN_TRADES, FALLBACK_TRADES = 100, 50
MAX_AGE = 12 * 3600
NULL_SEED = 20261007
REPS, BOOT_SEED = 4000, 7


# -- information test ---------------------------------------------------------------------------

def logit_fit(X: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Logistic regression with intercept by Newton-Raphson: (coefficients, standard errors)."""
    X = np.column_stack([np.ones(len(X)), X])
    b = np.zeros(X.shape[1])
    for _ in range(50):
        p = expit(X @ b)
        H = X.T @ (X * (p * (1 - p))[:, None])
        step = np.linalg.solve(H, X.T @ (y - p))
        b += step
        if np.abs(step).max() < 1e-10:
            break
    p = expit(X @ b)
    return b, np.sqrt(np.diag(np.linalg.inv(X.T @ (X * (p * (1 - p))[:, None]))))


def scores(p: np.ndarray, y: np.ndarray) -> dict:
    q = np.clip(p, 1e-6, 1 - 1e-6)
    return {"log_loss": float(-(y * np.log(q) + (1 - y) * np.log(1 - q)).mean()),
            "brier": float(((p - y) ** 2).mean())}


def information(df: pd.DataFrame) -> dict:
    y = df["y"].to_numpy(float)
    X = np.column_stack([logit(df["mid"].clip(0.01, 0.99)), logit(df["book"].clip(0.01, 0.99))])
    b, se = logit_fit(X, y)
    def ci(i):
        return {"coef": float(b[i]), "lo": float(b[i] - 1.96 * se[i]), "hi": float(b[i] + 1.96 * se[i])}

    return {"games": len(df), "intercept": ci(0), "logit_kalshi": ci(1), "logit_book": ci(2),
            "kalshi": scores(df["mid"].to_numpy(), y), "book": scores(df["book"].to_numpy(), y),
            "average": scores((df["mid"] + df["book"]).to_numpy() / 2, y)}


# -- trade rule ---------------------------------------------------------------------------------

def trade_pnl(df: pd.DataFrame, d: float, ref: str = "book") -> pd.Series:
    """P&L of one contract per game on the cheap side (NaN = no trade): home at the ask when the
    reference exceeds the mid by >= d, away at 1 - bid when it falls short by >= d."""
    gap = df[ref] - df["mid"]
    home, away = gap >= d, gap <= -d
    a = np.where(home, df["ask"], 1 - df["bid"])
    won = np.where(home, df["y"], 1 - df["y"])
    return pd.Series(np.where(home | away, won - a - fee(a), np.nan), index=df.index)


def evaluate(df: pd.DataFrame, d: float, ref: str = "book") -> dict:
    pnl = trade_pnl(df, d, ref).dropna()
    if len(pnl) == 0:
        return {"trades": 0}
    mean, lo, hi = block_bootstrap(pnl, df.loc[pnl.index, "block"], REPS, BOOT_SEED)
    return {"trades": len(pnl), "pnl": float(pnl.sum()), "per_trade": mean, "lo": lo, "hi": hi,
            "hit_rate": float((pnl > 0).mean())}


def select_and_validate(frames: dict[int, pd.DataFrame]) -> dict:
    grid = [(h, d, evaluate(f[f["fit"]], d)) for h, f in frames.items() for d in DS]
    for floor in (MIN_TRADES, FALLBACK_TRADES):
        cands = [c for c in grid if c[2]["trades"] >= floor]
        if cands:
            break
    else:
        return {"selected": None, "reason": f"no rule with >= {FALLBACK_TRADES} trades in weeks 1-7"}
    h, d, fit = max(cands, key=lambda c: c[2]["per_trade"])
    val_df = frames[h][~frames[h]["fit"]]
    val = evaluate(val_df, d)
    return {"selected": {"h": h, "d": d, "min_trades_used": floor}, "fit": fit, "validation": val,
            "passed": val["trades"] > 0 and val["lo"] > 0, "lookahead_ref": evaluate(val_df, d, "ref"),
            "lookahead_slope": move_slope(val_df), "fit_grid": {f"h{g[0]}_d{g[1]}": g[2] for g in grid}}


def move_slope(df: pd.DataFrame) -> float | None:
    """OLS slope of the later Kalshi move (ref - mid) on (book - mid)."""
    x, y = (df["book"] - df["mid"]).to_numpy(), (df["ref"] - df["mid"]).to_numpy()
    ok = np.isfinite(x) & np.isfinite(y)
    return float(np.polyfit(x[ok], y[ok], 1)[0]) if ok.sum() > 2 else None


def permuted(frames: dict[int, pd.DataFrame]) -> dict[int, pd.DataFrame]:
    """Null: book probabilities shuffled across games within each week."""
    rng = np.random.default_rng(NULL_SEED)
    out = {}
    for h, f in frames.items():
        f = f.copy()
        f["book"] = f.groupby("block")["book"].transform(lambda s: rng.permutation(s.to_numpy()))
        out[h] = f
    return out


# -- data ---------------------------------------------------------------------------------------

def price(q: dict | None) -> float:
    """A candle price field as a probability. Accepts dollar strings or integer cents."""
    if not q:
        return np.nan
    v = q.get("close_dollars", q.get("close"))
    try:
        v = float(v)
    except (TypeError, ValueError):
        return np.nan
    v = v / 100 if v > 1 else v
    return v if 0 < v < 1 else np.nan


def quotes(candles: list[dict]) -> pd.DataFrame:
    """Candles with a valid two-sided quote, by end time."""
    rows = [(c["end_period_ts"], price(c.get("yes_bid")), price(c.get("yes_ask"))) for c in candles]
    q = pd.DataFrame(rows, columns=["ts", "bid", "ask"])
    return q[q["bid"] < q["ask"]].sort_values("ts").reset_index(drop=True)


def quote_at(q: pd.DataFrame, t: float) -> tuple[float, float]:
    """(bid, ask) of the last valid candle ending at or before t and at most MAX_AGE stale."""
    i = q["ts"].searchsorted(t, side="right") - 1
    if i < 0 or t - q["ts"].iloc[i] > MAX_AGE:
        return np.nan, np.nan
    return float(q["bid"].iloc[i]), float(q["ask"].iloc[i])


def home_market(pair: list[dict], names: dict[str, set[str]], home: str, away: str) -> dict | None:
    """The market whose team is the home side, or None when the pair is ambiguous."""
    from cfb.ingestion.kalshi import norm

    hits = [m for m in pair if norm(m["yes_sub_title"]) in names[home] and norm(m["yes_sub_title"]) not in names[away]]
    others = [m for m in pair if m not in hits and norm(m["yes_sub_title"]) in names[away]]
    return hits[0] if len(hits) == 1 and len(others) == 1 else None


def build(markets, candles_of, schedules, results, book, names) -> tuple[dict[int, pd.DataFrame], dict]:
    """Per-h frames (one row per usable game) and the drop counts."""
    from cfb.ingestion.kalshi import map_events, parse_ts

    ev_game = map_events(markets, schedules, names)
    sched = {s["game_id"]: s for s in schedules}
    by_event: dict[str, list[dict]] = {}
    for m in markets:
        by_event.setdefault(m["event_ticker"], []).append(m)
    c = {"events": len(by_event), "mapped": 0, "ambiguous_side": 0, "no_book": 0, "no_result": 0, "no_candles": 0}
    rows: dict[int, list[dict]] = {h: [] for h in HOURS}
    for ev, gid in ev_game.items():
        if gid is None:
            continue
        c["mapped"] += 1
        s = sched[gid]
        m = home_market(by_event[ev], names, s["home_team_id"], s["away_team_id"])
        if m is None:
            c["ambiguous_side"] += 1
            continue
        pb = book.get(gid, np.nan)
        r = results.get(gid)
        if np.isnan(pb):
            c["no_book"] += 1
            continue
        if r is None or r["home_points"] == r["away_points"]:
            c["no_result"] += 1
            continue
        q = quotes(candles_of(m))
        if q.empty:
            c["no_candles"] += 1
            continue
        k = parse_ts(s["start_utc"]).timestamp()
        for h in HOURS:
            bid, ask = quote_at(q, k - h * 3600)
            rb, ra = quote_at(q, k - (3600 if h > 1 else 0))
            ref = (rb + ra) / 2
            rows[h].append({"game_id": gid, "block": f"{s['season_type']}-{s['week']}",
                            "fit": s["season_type"] == "regular" and s["week"] <= 7,
                            "y": float(r["home_points"] > r["away_points"]), "book": pb,
                            "bid": bid, "ask": ask, "mid": (bid + ask) / 2, "ref": ref})
    frames = {h: pd.DataFrame(v).dropna(subset=["mid"]).reset_index(drop=True) for h, v in rows.items()}
    return frames, c


def spread_dist(frames: dict[int, pd.DataFrame]) -> dict:
    out = {}
    for h, f in frames.items():
        s = f["ask"] - f["bid"]
        out[f"h{h}"] = {"n": len(s), "mean": float(s.mean()), **{f"p{q}": float(s.quantile(q / 100)) for q in (10, 25, 50, 75, 90)}}
    return out


# -- report -------------------------------------------------------------------------------------

def fmt(r: dict) -> str:
    if not r.get("trades"):
        return "no trades"
    return f"{r['trades']} trades, {r['per_trade']:+.4f} per trade [{r['lo']:+.4f}, {r['hi']:+.4f}], hit {r['hit_rate']:.1%}"


def markdown(rep: dict) -> str:
    real, null = rep["real"], rep["null"]
    sel = real.get("selected")
    if sel is None:
        verdict = f"NO RULE SELECTED: {real['reason']}."
    elif rep.get("null_failed"):
        verdict = "PIPELINE BROKEN: the permuted-book null passed validation. No result is reported."
    elif real["passed"]:
        verdict = f"PASS: h={sel['h']}, d={sel['d']} validated with a lower bound above 0. Check the look-ahead section before believing it."
    else:
        verdict = f"NO EDGE: h={sel['h']}, d={sel['d']} did not validate (lower bound not above 0)."
    L = ["# K02 results", "", f"**Verdict: {verdict}**", "",
         f"Protocol sha256 `{rep['protocol_sha256']}`; generated {rep['generated_at']}; Kalshi network calls: {rep['kalshi_calls']}.", "",
         "## Data", "", "| Count | n |", "|---|---|"]
    L += [f"| {k} | {v} |" for k, v in rep["counts"].items()]
    L += ["", f"Match rate (events mapped to a CFBD game): {rep['match_rate']:.1%}.", "", "## Information test", "",
          "| h | games | coef logit(Kalshi) | coef logit(book) | log loss Kalshi | log loss book | Brier Kalshi | Brier book |",
          "|---|---|---|---|---|---|---|---|"]
    for h, i in rep["information"].items():
        k, b = i["logit_kalshi"], i["logit_book"]
        L.append(f"| {h} | {i['games']} | {k['coef']:.3f} [{k['lo']:.3f}, {k['hi']:.3f}] | {b['coef']:.3f} [{b['lo']:.3f}, {b['hi']:.3f}] "
                 f"| {i['kalshi']['log_loss']:.4f} | {i['book']['log_loss']:.4f} | {i['kalshi']['brier']:.4f} | {i['book']['brier']:.4f} |")
    L += ["", "## Bid-ask spread at entry", "", "| h | n | mean | p10 | p25 | median | p75 | p90 |", "|---|---|---|---|---|---|---|---|"]
    for h, s in rep["spread"].items():
        L.append(f"| {h} | {s['n']} | " + " | ".join(f"{s[k]:.3f}" for k in ("mean", "p10", "p25", "p50", "p75", "p90")) + " |")
    for name, r in (("Real", real), ("Null (book permuted within week)", null)):
        L += ["", f"## {name}: selection (weeks 1-7) and validation (week 8 on)", ""]
        if r.get("selected") is None:
            L.append(r["reason"])
            continue
        L += [f"Selected h={r['selected']['h']}, d={r['selected']['d']} (floor {r['selected']['min_trades_used']} trades).", "",
              f"- Fit: {fmt(r['fit'])}", f"- Validation: {fmt(r['validation'])}", f"- Passed: {r['passed']}", "",
              "| rule | fit result |", "|---|---|"]
        L += [f"| {k} | {fmt(v)} |" for k, v in r["fit_grid"].items()]
    if sel:
        L += ["", "## Look-ahead check", "",
              f"Same rule with the later Kalshi mid as the reference: {fmt(real['lookahead_ref'])}.",
              f"Slope of the Kalshi move on (book - entry mid): {real['lookahead_slope']}."]
    return "\n".join(L) + "\n"


def main() -> None:
    from cfb.cli import DATA_DIR, REPO_ROOT, open_store
    from cfb.evaluation.backtest import latest_facts
    from cfb.ingestion.kalshi import KalshiReader, team_names
    from cfb.ingestion.ledger import RawLedger
    from cfb.markets import consensus_lines

    conn, cfbd = open_store()
    reader = KalshiReader(RawLedger(DATA_DIR / "raw", conn, provider="KALSHI"))
    markets = reader.markets("KXNCAAFGAME")
    markets = [m for m in markets if m.get("result") in ("yes", "no")]
    schedules = [s for s in latest_facts(conn, "game_schedule") if s["season"] == 2025]
    results = {r["game_id"]: r for r in latest_facts(conn, "game_result")}
    games = [g for st in ("regular", "postseason")
             for g in cfbd.load(cfbd.latest_success("/lines", {"year": 2025, "seasonType": st}))]
    book = dict(consensus_lines(games).set_index("game_id")["p_win_market"])
    frames, counts = build(markets, reader.candles, schedules, results, book, team_names(conn, cfbd))
    assert reader.calls == 0, "K02 must replay from cache"

    real = select_and_validate(frames)
    null = select_and_validate(permuted(frames))
    protocol = REPO_ROOT / "experiments" / "protocols" / "K02-protocol.md"
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "protocol": "K02",
           "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(), "kalshi_calls": reader.calls,
           "counts": {**counts, **{f"games_with_quote_h{h}": len(f) for h, f in frames.items()}},
           "match_rate": counts["mapped"] / counts["events"],
           "information": {f"h{h}": information(f) for h, f in frames.items()},
           "spread": spread_dist(frames), "real": real, "null": null}
    if null.get("passed"):
        rep["null_failed"] = True
    out = REPO_ROOT / "experiments" / "k02"
    out.mkdir(parents=True, exist_ok=True)
    (out / "k02-results.json").write_text(json.dumps(rep, indent=1))
    (out / "k02-results.md").write_text(markdown(rep))
    print(markdown(rep))


if __name__ == "__main__":
    main()
