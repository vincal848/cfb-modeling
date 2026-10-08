"""K04: key-number mass in Kalshi CFB spread ladders (experiments/protocols/K04-protocol.md).

    uv run python -m cfb.evaluation.k04 --gate    # CFBD-only model check; stops here if it fails
    uv run python -m cfb.evaluation.k04 --fetch   # ladder candles for the usable rungs into the cache
    uv run python -m cfb.evaluation.k04           # replay from cache (0 calls), write experiments/k04/
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from scipy.stats import norm

from cfb.evaluation.backtest import block_bootstrap
from cfb.evaluation.k03 import fee

KEYS = (3, -3, 7, -7)  # signed home-minus-away margins
H_GRID = (0.5, 1.0, 2.0, 3.0)
EDGE, LEAD = 0.01, timedelta(hours=6)
WINDOW = (30, 5)  # candle hours before start
REPS, BOOT_SEED, SEED = 4000, 7, 20261008
MIN_TRADES = 200  # below this a non-pass is "underpowered"
MARGINS = np.arange(-80, 81)


# -- model ---------------------------------------------------------------------------------------

def kernel_q(mu_tr: np.ndarray, m_tr: np.ndarray, h: float, mu: np.ndarray, k: np.ndarray) -> np.ndarray:
    """P(m = k | mu): Nadaraya-Watson over training games, Gaussian weights in the expected margin."""
    w = np.exp(-((mu[:, None] - mu_tr[None, :]) ** 2) / (2 * h * h))
    return (w * (m_tr[None, :] == k[:, None])).sum(1) / w.sum(1)


def gaussian_q(mu: np.ndarray | float, k: np.ndarray, sd: float) -> np.ndarray:
    return norm.cdf((k + 0.5 - mu) / sd) - norm.cdf((k - 0.5 - mu) / sd)


def key_loss(q_of, mu: np.ndarray, m: np.ndarray) -> float:
    """Mean Bernoulli log loss of P(m = k) over the four key events and all games."""
    out = []
    for k in KEYS:
        q = np.clip(q_of(mu, np.full(len(mu), k)), 1e-4, 1 - 1e-4)
        y = (m == k).astype(float)
        out.append(-(y * np.log(q) + (1 - y) * np.log(1 - q)).mean())
    return float(np.mean(out))


def fit(train: pd.DataFrame, tune_from: int) -> dict:
    """Pick h on seasons >= `tune_from` using earlier ones, benchmark against a Gaussian, refit on all.
    `train` has season, mu, m. Returns the model and the gate result."""
    a, b = train[train["season"] < tune_from], train[train["season"] >= tune_from]
    mu_a, m_a, mu_b, m_b = a["mu"].to_numpy(), a["m"].to_numpy(), b["mu"].to_numpy(), b["m"].to_numpy()
    loss = {h: key_loss(lambda mu, k, h=h: kernel_q(mu_a, m_a, h, mu, k), mu_b, m_b) for h in H_GRID}
    h = min(loss, key=loss.get)
    sd = float((m_a - mu_a).std())
    gauss = key_loss(lambda mu, k: gaussian_q(mu, k, sd), mu_b, m_b)
    return {"h": h, "sd": sd, "kernel_loss": loss, "gaussian_loss": gauss, "gate_passed": loss[h] < gauss,
            "mu": train["mu"].to_numpy(), "m": train["m"].to_numpy()}


def q_model(model: dict, mu: np.ndarray, k: np.ndarray) -> np.ndarray:
    return kernel_q(model["mu"], model["m"], model["h"], mu, k)


# -- trades --------------------------------------------------------------------------------------

def trades(df: pd.DataFrame) -> pd.DataFrame:
    """Rows of `df` (game_id, block, q, bid_hi, ask_lo, hit) that the rule takes, with their P&L."""
    ok = df["ask_lo"].notna() & df["bid_hi"].notna() & (df["ask_lo"] > df["bid_hi"])
    cost = df["ask_lo"] - df["bid_hi"]
    fees = fee(df["ask_lo"].to_numpy()) + fee((1 - df["bid_hi"]).to_numpy())
    take = ok & (df["q"] - cost - fees > EDGE)
    out = df[take].copy()
    out["pnl"] = out["hit"].astype(float) - cost[take] - fees[take]
    return out


def evaluate(df: pd.DataFrame) -> dict:
    t = trades(df)
    if t.empty:
        return {"trades": 0, "games": 0, "passed": False, "underpowered": True}
    mean, lo, hi = block_bootstrap(t["pnl"], t["game_id"], REPS, BOOT_SEED)
    return {"trades": len(t), "games": int(t["game_id"].nunique()), "per_trade": mean, "lo": lo, "hi": hi,
            "hit_rate": float(t["hit"].mean()), "sd": float(t["pnl"].std()), "passed": lo > 0,
            "underpowered": len(t) < MIN_TRADES}


def permuted(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    out = df.copy()
    out["q"] = out.groupby("block")["q"].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


# -- simulation (signal-free and planted-signal ladders) -------------------------------------------

def spiked_pmf(mu: float, sd: float, boost: float) -> np.ndarray:
    """pmf of the home margin over MARGINS: Gaussian mass with the |k| in {3, 7} cells multiplied by `boost`."""
    p = gaussian_q(mu, MARGINS, sd)
    p = np.where(np.isin(np.abs(MARGINS), (3, 7)), p * boost, p)
    return p / p.sum()


def simulate(n_train: int, n_test: int, market_boost: float, true_boost: float, seed: int, sd: float = 13.0):
    """(train frame, test ladder frame). Truth has `true_boost` on the key cells, the market quotes a pmf with
    `market_boost` (equal = efficient market; 1 vs larger = a smooth market, key mass planted)."""
    rng = np.random.default_rng(seed)

    def games(n):
        mu = np.round(rng.normal(0, 10, n) * 2) / 2
        return mu, np.array([rng.choice(MARGINS, p=spiked_pmf(u, sd, true_boost)) for u in mu])

    mu_tr, m_tr = games(n_train)
    train = pd.DataFrame({"season": np.where(np.arange(n_train) < n_train * 0.7, 2020, 2024), "mu": mu_tr, "m": m_tr})
    mu, m = games(n_test)
    rows = []
    for i in range(n_test):
        pm = spiked_pmf(mu[i], sd, market_boost)
        for k in KEYS:
            sgn = 1 if k > 0 else -1
            mid_lo, mid_hi = (pm[sgn * MARGINS >= abs(k) + d].sum() for d in (0, 1))
            rows.append({"game_id": f"g{i}", "block": f"w{i % 14}", "k": k, "mu": mu[i],
                         "ask_lo": min(mid_lo + 0.01, 0.99), "bid_hi": max(mid_hi - 0.01, 0.01), "hit": bool(m[i] == k)})
    return train, pd.DataFrame(rows)


def run_sim(market_boost: float, true_boost: float, seed: int, n_train=4000, n_test=1500) -> dict:
    train, test = simulate(n_train, n_test, market_boost, true_boost, seed)
    model = fit(train, 2024)
    test["q"] = q_model(model, test["mu"].to_numpy(), test["k"].to_numpy())
    return {"gate_passed": model["gate_passed"], "real": evaluate(test), "placebo": evaluate(permuted(test))}


# -- real data -----------------------------------------------------------------------------------

def train_frame(lines_by_season: dict[int, list[dict]]) -> pd.DataFrame:
    """Season, mu (= -consensus closing spread) and home-minus-away margin of every scored game with a line."""
    from cfb.markets import consensus_lines

    rows = []
    for season, games in lines_by_season.items():
        cl = consensus_lines(games).set_index("game_id")["spread"].dropna()
        for g in games:
            gid = f"cfbd-game-{g['id']}"
            if gid in cl.index and g.get("homeScore") is not None and g.get("awayScore") is not None:
                rows.append({"season": season, "game_id": gid, "mu": -float(cl[gid]),
                             "m": int(g["homeScore"]) - int(g["awayScore"])})
    return pd.DataFrame(rows)


def team_markets(spread_markets: list[dict], names: dict[str, set[str]], home: str, away: str) -> dict:
    """{(side, strike): market} for one event's rungs; a rung whose team is ambiguous is skipped."""
    from cfb.ingestion.kalshi import norm as nrm

    out = {}
    for m in spread_markets:
        team = nrm(m["yes_sub_title"].rsplit(" wins by over", 1)[0])
        in_home, in_away = team in names[home], team in names[away]
        side = "home" if in_home and not in_away else "away" if in_away and not in_home else None
        if side and m.get("floor_strike") is not None:
            out[(side, float(m["floor_strike"]))] = m
    return out


def entry_quote(candles: list[dict], t: float) -> tuple[float, float]:
    from cfb.evaluation.k02 import quotes

    q = quotes(candles)
    i = q["ts"].searchsorted(t, side="right") - 1
    return (float(q["bid"].iloc[i]), float(q["ask"].iloc[i])) if i >= 0 else (np.nan, np.nan)


def load_events(conn, cfbd, reader):
    """Mapped 2025 spread events as (game_id, schedule row, rungs), with the drop counts."""
    from cfb.evaluation.backtest import latest_facts
    from cfb.ingestion.kalshi import event_code, map_events, team_names

    names = team_names(conn, cfbd)
    schedules = [s for s in latest_facts(conn, "game_schedule") if s["season"] == 2025]
    sched = {s["game_id"]: s for s in schedules}
    ev_game = map_events(reader.markets("KXNCAAFGAME"), schedules, names)
    code_game = {event_code(e): g for e, g in ev_game.items() if g}
    by_event: dict[str, list[dict]] = {}
    for m in reader.markets("KXNCAAFSPREAD"):
        by_event.setdefault(event_code(m["event_ticker"]), []).append(m)
    drops = {"spread_events": len(by_event), "unmapped": 0}
    out = []
    for code, ms in by_event.items():
        gid = code_game.get(code)
        if gid is None:
            drops["unmapped"] += 1
            continue
        s = sched[gid]
        out.append((gid, s, team_markets(ms, names, s["home_team_id"], s["away_team_id"])))
    return out, drops


def build_frame(events, games2025: dict, spread: pd.Series, candles_of) -> tuple[pd.DataFrame, dict]:
    from cfb.ingestion.kalshi import parse_ts

    rows, c = [], {"mapped": len(events), "no_result_or_spread": 0, "no_rungs": 0}
    for gid, s, rungs in events:
        g = games2025.get(gid)
        if g is None or gid not in spread.index or g.get("homeScore") is None:
            c["no_result_or_spread"] += 1
            continue
        start = parse_ts(s["start_utc"])
        t = (start - LEAD).timestamp()
        w = (int((start - timedelta(hours=WINDOW[0])).timestamp()), int((start - timedelta(hours=WINDOW[1])).timestamp()))
        m = int(g["homeScore"]) - int(g["awayScore"])
        got = False
        for k in KEYS:
            side = "home" if k > 0 else "away"
            lo, hi = rungs.get((side, abs(k) - 0.5)), rungs.get((side, abs(k) + 0.5))
            if lo is None or hi is None:
                continue
            got = True
            rows.append({"game_id": gid, "block": f"{s['season_type']}-{s['week']}", "k": k, "mu": -float(spread[gid]),
                         "ask_lo": entry_quote(candles_of(lo, *w), t)[1], "bid_hi": entry_quote(candles_of(hi, *w), t)[0],
                         "hit": m == k})
        c["no_rungs"] += not got
    return pd.DataFrame(rows), c


def lines_of(cfbd, seasons) -> dict[int, list[dict]]:
    return {y: [g for st in ("regular", "postseason")
                for g in cfbd.load(cfbd.latest_success("/lines", {"year": y, "seasonType": st}))] for y in seasons}


def render(rep: dict) -> str:
    f = rep["fit"]

    def fmt(x):
        if not x["trades"]:
            return "no trades"
        return (f"{x['trades']} trades in {x['games']} games, {x['per_trade']:+.4f} per trade "
                f"[{x['lo']:+.4f}, {x['hi']:+.4f}], hit {x['hit_rate']:.3f}")

    lines = [f"# K04 results\n\n**Verdict: {rep['verdict']}**\n",
             f"Protocol sha256 `{rep['protocol_sha256']}`; generated {rep['generated_at']}; Kalshi calls {rep['calls']}.\n",
             "## Model gate (CFBD only)\n",
             f"{rep['train_games']} training games, 2014-2024. Held-out (2023-24) key-number log loss by bandwidth: "
             f"{f['kernel_loss']}; chosen h={f['h']}. Gaussian benchmark {f['gaussian_loss']:.5f}. "
             f"Gate passed: {f['gate_passed']}.\n"]
    if rep.get("counts"):
        r, p = rep["real"], rep["placebo"]
        lines += [f"Data: {rep['counts']}\n", f"## 2025 test\n\n{fmt(r)}\n",
                  f"Underpowered (< {MIN_TRADES} trades): {r['underpowered']}; per-trade sd {r.get('sd')}.\n",
                  f"Placebo (q permuted within week): {fmt(p)}; passed={p['passed']}.\n",
                  "| key | trades | per trade | hit rate |", "|---|---|---|---|"]
        lines += [f"| {k} | {v['trades']} | {v['per_trade']:+.4f} | {v['hit']:.3f} |" for k, v in rep["by_key"].items()]
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> None:
    from cfb.canonical.games import game_id
    from cfb.cli import DATA_DIR, REPO_ROOT, open_store
    from cfb.ingestion.kalshi import KalshiReader
    from cfb.ingestion.ledger import RawLedger
    from cfb.markets import consensus_lines

    conn, cfbd = open_store()
    train = train_frame(lines_of(cfbd, range(2014, 2025)))
    model = fit(train, 2023)
    protocol = REPO_ROOT / "experiments" / "protocols" / "K04-protocol.md"
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "calls": 0,
           "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
           "fit": {k: v for k, v in model.items() if k not in ("mu", "m")}, "train_games": len(train)}
    out = REPO_ROOT / "experiments" / "k04"
    out.mkdir(parents=True, exist_ok=True)
    if "--gate" in argv or not model["gate_passed"]:
        rep["verdict"] = ("GATE PASSED: kernel beats the Gaussian on key numbers; proceed to --fetch" if model["gate_passed"]
                          else "NO EDGE (no structure to price): the kernel does not beat the Gaussian on key "
                               "numbers; Kalshi prices not touched")
        print(render(rep))
        if not model["gate_passed"]:
            (out / "k04-results.json").write_text(json.dumps(rep, indent=1, default=str))
            (out / "k04-results.md").write_text(render(rep), encoding="utf-8")
        return
    reader = KalshiReader(RawLedger(DATA_DIR / "raw", conn, provider="KALSHI"), min_interval=0.25)
    events, drops = load_events(conn, cfbd, reader)
    games25 = {game_id(g["id"]): g for g in lines_of(cfbd, [2025])[2025]}
    spread = consensus_lines(list(games25.values())).set_index("game_id")["spread"].dropna()
    df, c = build_frame(events, games25, spread, lambda m, a, b: reader.candles(m, 60, a, b))
    if "--fetch" in argv:
        print(f"done: {reader.calls} calls")
        return
    assert reader.calls == 0, "K04 analysis must replay from cache; run --fetch first"
    df["q"] = q_model(model, df["mu"].to_numpy(), df["k"].to_numpy())
    real, placebo, t = evaluate(df), evaluate(permuted(df)), trades(df)
    rep |= {"counts": {**drops, **c, "ladder_rows": len(df)}, "real": real, "placebo": placebo,
            "by_key": {int(k): {"trades": len(g), "per_trade": float(g["pnl"].mean()), "hit": float(g["hit"].mean())}
                       for k, g in t.groupby("k")}}
    rep["verdict"] = ("PIPELINE BROKEN: placebo passed, no claim" if placebo["passed"] else
                      "PASS: eligible for the one-time 2026 holdout" if real["passed"] else
                      f"UNDERPOWERED, not a pass: fewer than {MIN_TRADES} trades" if real["underpowered"] else
                      "NO EDGE: 2025 interval lower bound is not > 0")
    (out / "k04-results.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "k04-results.md").write_text(render(rep), encoding="utf-8")
    print(render(rep))


if __name__ == "__main__":
    main(sys.argv[1:])
