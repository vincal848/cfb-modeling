"""S01: structural-bias sweep on CFB closing lines (experiments/protocols/S01-protocol.md).

    uv run python -m cfb.evaluation.s01 --discover   # 2014-2023, Holm over the trial ledger; writes experiments/s01/
    uv run python -m cfb.evaluation.s01 --confirm    # opens 2024-2025 once, only for Holm survivors
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from cfb.evaluation.backtest import block_bootstrap
from cfb.markets import fee

PRICE = 0.51  # 0.50 + 0.01 half-spread, as M01
REPS, BOOT_SEED, SEED, ALPHA = 4000, 7, 20261008, 0.05
DISCOVERY_END = 2023
CELLS = ("C1_home_field", "C2_big_fav", "C3_two_ats_losses")


# -- data ----------------------------------------------------------------------------------------

def games_frame(games: list[dict], lines: list[dict]) -> pd.DataFrame:
    """One row per game with a consensus spread and a score: home_cover is 1/0, NaN on a push."""
    from cfb.markets import consensus_lines

    cl = consensus_lines(lines).set_index("game_id")["spread"].dropna()
    rows = []
    for g in games:
        gid = f"cfbd-game-{g['id']}"
        if gid in cl.index and g.get("homePoints") is not None and g.get("awayPoints") is not None:
            m = g["homePoints"] - g["awayPoints"]
            rows.append({"game_id": gid, "season": g["season"], "week": g["week"], "date": g["startDate"],
                         "season_type": g["seasonType"],
                         "home": g["homeId"], "away": g["awayId"], "neutral": bool(g.get("neutralSite")),
                         "spread": float(cl[gid]), "m": m,
                         "home_cover": float(m + cl[gid] > 0) if m + cl[gid] != 0 else np.nan})
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df["block"] = df["season"].astype(str) + "-" + df["week"].astype(str)
    return df


def team_ats(df: pd.DataFrame) -> pd.DataFrame:
    """Per game, whether the home / away team failed to cover each of its previous two lined games that season."""
    long = pd.concat([
        pd.DataFrame({"game_id": df["game_id"], "season": df["season"], "date": df["date"], "team": df["home"],
                      "cover": df["home_cover"]}),
        pd.DataFrame({"game_id": df["game_id"], "season": df["season"], "date": df["date"], "team": df["away"],
                      "cover": 1 - df["home_cover"]})]).sort_values(["team", "season", "date"])
    g = long.groupby(["team", "season"])["cover"]
    long["two_losses"] = (g.shift(1) == 0) & (g.shift(2) == 0)
    side = {"home": df[["game_id", "home"]].rename(columns={"home": "team"}),
            "away": df[["game_id", "away"]].rename(columns={"away": "team"})}
    out = df[["game_id"]].copy()
    for s, keys in side.items():
        out[f"{s}_two_losses"] = keys.merge(long[["game_id", "team", "two_losses"]], on=["game_id", "team"],
                                            how="left")["two_losses"].fillna(False).to_numpy()
    return out


def cell_bets(df: pd.DataFrame, cell: str) -> pd.DataFrame:
    """Bets of one cell: game_id, block, win (1/0). Pushes are dropped."""
    if cell == "C1_home_field":
        sel = df[(df["season"] >= 2021) & ~df["neutral"]]
        return _bets(sel, 1 - sel["home_cover"])
    if cell == "C2_big_fav":
        sel = df[df["spread"].abs() >= 21]
        dog_is_home = sel["spread"] > 0
        return _bets(sel, np.where(dog_is_home, sel["home_cover"], 1 - sel["home_cover"]))
    if cell == "C3_two_ats_losses":
        t = team_ats(df).set_index("game_id").loc[df["game_id"]]
        h, a = t["home_two_losses"].to_numpy(), t["away_two_losses"].to_numpy()
        one = h ^ a  # both qualifying -> opposite sides of one game, dropped
        sel = df[one]
        return _bets(sel, np.where(h[one], sel["home_cover"], 1 - sel["home_cover"]))
    raise KeyError(cell)


def _bets(sel: pd.DataFrame, win) -> pd.DataFrame:
    out = pd.DataFrame({"game_id": sel["game_id"].to_numpy(), "block": sel["block"].to_numpy(),
                        "season": sel["season"].to_numpy(), "win": np.asarray(win, dtype=float)})
    return out.dropna(subset=["win"])


# -- statistics ----------------------------------------------------------------------------------

def evaluate_bets(bets: pd.DataFrame) -> dict:
    if len(bets) < 30:
        return {"bets": len(bets), "p": 1.0}
    pnl = pd.Series(bets["win"].to_numpy() - PRICE - fee(np.array(PRICE)), index=bets.index)
    mean, lo, hi = block_bootstrap(pnl, bets["block"], REPS, BOOT_SEED)
    rng = np.random.Generator(np.random.PCG64(BOOT_SEED))
    s, c = pnl.groupby(bets["block"]).sum().to_numpy(), pnl.groupby(bets["block"]).size().to_numpy()
    pick = rng.integers(0, len(s), size=(REPS, len(s)))
    p = float(((s[pick].sum(1) / c[pick].sum(1)) <= 0).mean())
    return {"bets": len(bets), "cover_rate": float(bets["win"].mean()), "per_bet": mean, "lo": lo, "hi": hi,
            "p": max(p, 1 / REPS)}


def holm(pvals: dict[str, float], m_total: int, alpha: float = ALPHA) -> dict[str, bool]:
    """Holm step-down over a family of m_total tests; the m_total - len(pvals) tests not run count as p = 1."""
    out, ok = {}, True
    for i, (k, p) in enumerate(sorted(pvals.items(), key=lambda kv: kv[1])):
        ok = ok and p <= alpha / (m_total - i)
        out[k] = ok
    return out


def trial_count(path) -> int:
    with open(path, encoding="utf-8", newline="") as fh:
        return sum(int(r["tests"]) for r in csv.DictReader(fh))


def run(df: pd.DataFrame, m_total: int, seasons: tuple[int, int]) -> dict:
    d = df[(df["season"] >= seasons[0]) & (df["season"] <= seasons[1])]
    res = {c: evaluate_bets(cell_bets(d, c)) for c in CELLS}
    surv = holm({c: r["p"] for c, r in res.items()}, m_total)
    return {"cells": res, "holm_survivors": [c for c, ok in surv.items() if ok]}


def permuted(df: pd.DataFrame) -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    out = df.copy()
    out["home_cover"] = out.groupby("block")["home_cover"].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


# -- Wong teaser check ---------------------------------------------------------------------------

def teaser_legs(df: pd.DataFrame) -> dict:
    """Leg win rates of 6-point teaser legs through 3 and 7 (favorite -7.5/-8.5, underdog +1.5/+2.5)."""
    mf = np.where(df["spread"] < 0, df["m"], -df["m"])  # margin from the favorite's side
    s = df["spread"].abs()
    legs = {"fav -7.5 to -1.5": (s == 7.5) & (mf >= 2), "fav -8.5 to -2.5": (s == 8.5) & (mf >= 3),
            "dog +1.5 to +7.5": (s == 1.5) & (mf <= 7), "dog +2.5 to +8.5": (s == 2.5) & (mf <= 8)}
    n = {"fav -7.5 to -1.5": (s == 7.5), "fav -8.5 to -2.5": (s == 8.5), "dog +1.5 to +7.5": (s == 1.5),
         "dog +2.5 to +8.5": (s == 2.5)}
    out = {k: {"n": int(n[k].sum()), "win_rate": float(legs[k].sum() / max(n[k].sum(), 1))} for k in legs}
    tot = sum(n[k].sum() for k in legs)
    out["pooled"] = {"n": int(tot), "win_rate": float(sum(legs[k].sum() for k in legs) / max(tot, 1)),
                     "break_even": float(np.sqrt(120 / 220))}
    return out


def render(rep: dict) -> str:
    lines = [f"# S01 results\n\n**Verdict: {rep['verdict']}**\n",
             f"Protocol sha256 `{rep['protocol_sha256']}`; generated {rep['generated_at']}; ledger family size {rep['m_total']}.\n",
             "## Discovery, 2014-2023 (C1 2021-2023)\n", "| cell | bets | cover rate | P&L per bet | 95% interval | p | Holm survivor |",
             "|---|---|---|---|---|---|---|"]
    for c, r in rep["discovery"]["cells"].items():
        lines.append(f"| {c} | {r['bets']} | {r.get('cover_rate', float('nan')):.4f} | {r.get('per_bet', float('nan')):+.4f} | "
                     f"[{r.get('lo', float('nan')):+.4f}, {r.get('hi', float('nan')):+.4f}] | {r['p']:.4f} | "
                     f"{c in rep['discovery']['holm_survivors']} |")
    lines += ["", f"Null (cover outcomes permuted within week): survivors {rep['null']['holm_survivors']}.", ""]
    if "confirm" in rep:
        lines += ["## Confirmation, 2024-2025 (opened once)", "", json.dumps(rep["confirm"], indent=1), ""]
    lines += ["## Wong-teaser check (2014-2025)", "", "| leg | games | win rate |", "|---|---|---|"]
    lines += [f"| {k} | {v['n']} | {v['win_rate']:.4f} |" for k, v in rep["teaser"].items()]
    lines.append(f"\nBreak-even per leg for a two-team 6-point teaser at -120: {rep['teaser']['pooled']['break_even']:.4f}.")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> None:
    from cfb.cli import REPO_ROOT, open_store
    from cfb.evaluation.k04 import lines_of

    _, cfbd = open_store()
    seasons = range(2014, 2026)
    games = [g for y in seasons for st in ("regular", "postseason")
             for g in cfbd.load(cfbd.latest_success("/games", {"year": y, "seasonType": st}))]
    lines = [g for ls in lines_of(cfbd, seasons).values() for g in ls]
    df = games_frame(games, lines)
    m_total = trial_count(REPO_ROOT / "experiments" / "trials.csv")
    protocol = REPO_ROOT / "experiments" / "protocols" / "S01-protocol.md"
    out = REPO_ROOT / "experiments" / "s01"
    out.mkdir(parents=True, exist_ok=True)
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "m_total": m_total, "games": len(df),
           "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(),
           "discovery": run(df, m_total, (2014, DISCOVERY_END)),
           "null": run(permuted(df), m_total, (2014, DISCOVERY_END)), "teaser": teaser_legs(df)}
    surv = rep["discovery"]["holm_survivors"]
    if rep["null"]["holm_survivors"]:
        rep["verdict"] = "PIPELINE BROKEN: the permuted null produced a Holm survivor, no claim"
    elif "--confirm" in argv and surv:
        rep["confirm"] = {c: evaluate_bets(cell_bets(df[df["season"] > DISCOVERY_END], c)) for c in surv}
        rep["verdict"] = "CONFIRMATION OPENED once for: " + ", ".join(surv)
    else:
        rep["verdict"] = ("NO EDGE: no cell survives Holm in discovery; 2024-2025 stays sealed" if not surv
                          else "SURVIVORS in discovery: " + ", ".join(surv) + " (run --confirm)")
    (out / "s01-results.json").write_text(json.dumps(rep, indent=1, default=str))
    (out / "s01-results.md").write_text(render(rep), encoding="utf-8")
    print(render(rep))


if __name__ == "__main__":
    main(sys.argv[1:])
