"""M02: does B02 minus the opener predict the open->close move, and pay at the opener?
(experiments/protocols/M02-protocol.md)

    uv run python -m cfb.evaluation.m02
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from statistics import median

import numpy as np
import pandas as pd

from cfb.canonical.games import game_id
from cfb.evaluation.backtest import block_bootstrap, prepare_tasks
from cfb.evaluation.m01 import B02, MIN_TRADES, NULL_SEED, REPS
from cfb.markets import HALF_SPREAD, fee
from cfb.models.dynamic import filter_and_predict, ids_digest

GRID = (1.0, 2.0, 3.0, 4.0)
BOOT_SEED = 7


def open_close_lines(games: list[dict]) -> pd.DataFrame:
    """Median open and close home spread over providers having both; also the Bovada-opener count."""
    rows = []
    for g in games:
        both = [ln for ln in g.get("lines") or [] if ln.get("spread") is not None and ln.get("spreadOpen") is not None]
        if both:
            rows.append({"game_id": game_id(g["id"]), "open": median(ln["spreadOpen"] for ln in both),
                         "close": median(ln["spread"] for ln in both),
                         "bovada": any(ln.get("provider") == "Bovada" for ln in both)})
    return pd.DataFrame(rows, columns=["game_id", "open", "close", "bovada"])


def margin_frame(conn, ledger, spec, seasons, snapshot_dir) -> pd.DataFrame:
    """One row per scored game: B02 margin, result margin, open/close spread (same pass as m01.forecast_frame)."""
    lag = spec["replay"]["reconstructed_result_available_after_kickoff_hours"]
    tasks = sorted(prepare_tasks(conn, spec, seasons, [], snapshot_dir), key=lambda t: t.fold.cutoff)
    folds = [(t.fold.cutoff.isoformat(), ids_digest(t.frame.train["game_id"]), t.frame.target) for t in tasks]
    preds = filter_and_predict(tasks[-1].frame.train, folds, B02, lag)
    rows = []
    for task, (_, gids, means, _covs) in zip(tasks, preds, strict=True):
        for gid, m in zip(gids, means, strict=True):
            h, a = task.outcomes[gid]
            rows.append({"game_id": gid, "season": task.fold.season, "margin": m[0] - m[1], "result": h - a,
                         "block": f"{task.fold.season}-{task.fold.season_type}-{task.fold.week}"})
    games = [g for s in seasons for st in ("regular", "postseason")
             for g in ledger.load(ledger.latest_success("/lines", {"year": s, "seasonType": st}))]
    df = pd.DataFrame(rows).merge(open_close_lines(games), on="game_id", how="left")
    df["gap"] = -df["margin"] - df["open"]
    return df


def permuted(df: pd.DataFrame) -> pd.DataFrame:
    """Null: B02 margin shuffled across games within each week."""
    rng = np.random.default_rng(NULL_SEED)
    out = df.copy()
    out["margin"] = out.groupby("block")["margin"].transform(lambda s: rng.permutation(s.to_numpy()))
    out["gap"] = -out["margin"] - out["open"]
    return out


def slope(df: pd.DataFrame) -> dict:
    """OLS of move = close - open on gap; week-block bootstrap interval for the slope."""
    d = df.dropna(subset=["gap", "open", "close"])
    return slope_xy(d["gap"].to_numpy(), (d["close"] - d["open"]).to_numpy(), d["block"].to_numpy())


def slope_xy(x: np.ndarray, y: np.ndarray, blocks: np.ndarray) -> dict:
    """OLS slope of y on x with a week-block bootstrap interval."""
    ok = np.isfinite(x) & np.isfinite(y)
    x, y, blocks = x[ok], y[ok], blocks[ok]
    cols = pd.DataFrame({"n": 1.0, "x": x, "y": y, "xx": x * x, "xy": x * y}).groupby(blocks).sum()
    s = cols.to_numpy()

    def b(t):
        n, sx, sy, sxx, sxy = t.sum(axis=0)
        return (sxy - sx * sy / n) / (sxx - sx * sx / n)

    rng = np.random.Generator(np.random.PCG64(BOOT_SEED))
    pick = rng.integers(0, len(s), size=(REPS, len(s)))
    boots = np.array([b(s[p]) for p in pick])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    return {"n": len(x), "slope": float(b(s)), "lo": float(lo), "hi": float(hi)}


def evaluate(df: pd.DataFrame, g: float) -> dict:
    """Bet B02's side at the opener when |gap| >= g; P&L, CLV, share of closes moving our way."""
    d = df.dropna(subset=["gap", "open", "close"])
    d = d[(d["gap"].abs() >= g) & (d["result"] + d["open"] != 0)]
    if d.empty:
        return {"trades": 0}
    home = (d["gap"] < 0).to_numpy()
    cover = np.where(home, d["result"] + d["open"] > 0, d["result"] + d["open"] < 0).astype(float)
    price = 0.5 + HALF_SPREAD
    pnl = pd.Series(cover - price - fee(price), index=d.index)
    clv = np.where(home, d["open"] - d["close"], d["close"] - d["open"])
    mean, lo, hi = block_bootstrap(pnl, d["block"], REPS, BOOT_SEED)
    return {"trades": len(d), "per_trade": mean, "lo": lo, "hi": hi, "hit_rate": float(cover.mean()),
            "clv": float(clv.mean()), "clv_share": float((clv > 0).mean())}


def select_and_validate(df: pd.DataFrame) -> dict:
    fit = df[df["season"] == 2022]
    cands = [(evaluate(fit, g), g) for g in GRID]
    cands = [c for c in cands if c[0]["trades"] >= MIN_TRADES]
    if not cands:
        return {"selected": None, "reason": f"no rule with >= {MIN_TRADES} trades in 2022"}
    sel, g = max(cands, key=lambda c: c[0]["per_trade"])
    val = evaluate(df[df["season"] == 2023], g)
    return {"selected": {"g": g}, "2022": sel, "2023": val, "slope_2022": slope(fit),
            "slope_2023": slope(df[df["season"] == 2023]), "passed": val["trades"] > 0 and val["lo"] > 0}


def render(r: dict, sha: str) -> str:
    real, null = r["real"], r["null"]
    if real.get("selected") is None:
        verdict = f"**Verdict: no rule selected ({real['reason']}). Do not trade.**"
    elif real["passed"]:
        verdict = "**Verdict: the opener rule passed 2023. This is one look; the sealed seasons are still closed.**"
    else:
        verdict = "**Verdict: the opener rule did not pass 2023. B02 does not beat the opener after costs.**"
    lines = ["# M02: results (2022 select, 2023 validate)\n",
             (f"Protocol: [M02](../protocols/M02-protocol.md), sha256 `{sha}`. Run {r['generated_at'][:10]}. "
              "Raw output: `m02-validation.json`."),
             (f"{r['games']} games; {r['with_open']} with an open and close from the same books "
              f"(2022: {r['coverage']['2022']}, 2023: {r['coverage']['2023']}; "
              f"Bovada among them: {r['bovada']['2022']} / {r['bovada']['2023']}). "
              "**Evaluation class: reconstructed.**\n"), verdict + "\n"]
    if real.get("selected"):
        lines += [("Per trade is dollars per $1 contract at the opener after the 1c half-spread and the fee. "
                   "Interval is a week-block bootstrap, 95%. CLV is in points.\n"),
                  "| Run | g | Season | Trades | Per trade | Interval | CLV | Close moved our way | Slope [interval] |",
                  "|---|---|---|---|---|---|---|---|---|"]
        for name, x in (("Real", real), ("Null", null)):
            if x.get("selected") is None:
                continue
            for yr in ("2022", "2023"):
                v, s = x[yr], x[f"slope_{yr}"]
                lines.append(f"| {name} | {x['selected']['g']:g} | {yr} | {v['trades']} | {v['per_trade']:+.4f} | "
                             f"[{v['lo']:+.4f}, {v['hi']:+.4f}] | {v['clv']:+.2f} | {v['clv_share']:.1%} | "
                             f"{s['slope']:+.3f} [{s['lo']:+.3f}, {s['hi']:+.3f}] |")
        lines.append("")
    lines.append("Null check (B02 margin shuffled within week): "
                 + ("**PASSED, pipeline broken, discard.**" if null.get("passed") else "did not pass, as required."))
    return "\n".join(lines) + "\n"


def main() -> None:
    from cfb.cli import REPO_ROOT, open_store
    from cfb.evaluation.protocol import load_protocol

    spec = load_protocol()
    conn, ledger = open_store()
    out_dir = REPO_ROOT / "experiments" / "m02"
    out_dir.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256((REPO_ROOT / "experiments" / "protocols" / "M02-protocol.md").read_bytes()).hexdigest()
    df = margin_frame(conn, ledger, spec, [2022, 2023], REPO_ROOT / "artifacts" / "snapshots")
    ok = df.dropna(subset=["open"])
    report = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "protocol": "M02",
              "protocol_sha256": sha, "games": len(df), "with_open": len(ok),
              "coverage": {str(s): int((ok["season"] == s).sum()) for s in (2022, 2023)},
              "bovada": {str(s): int(ok.loc[ok["season"] == s, "bovada"].sum()) for s in (2022, 2023)},
              "real": select_and_validate(df), "null": select_and_validate(permuted(df))}
    (out_dir / "m02-validation.json").write_text(json.dumps(report, indent=1))
    (out_dir / "m02-results.md").write_text(render(report, sha))
    print(render(report, sha))


if __name__ == "__main__":
    main()
