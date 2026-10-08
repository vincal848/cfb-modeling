"""M01: does B02 beat closing prices after Kalshi-style costs? (experiments/protocols/M01-protocol.md)

    uv run python -m cfb.evaluation.m01              # 2022 select, 2023 validate, null check
    uv run python -m cfb.evaluation.m01 --open-test  # 2024-2025, only for markets that passed 2023
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, datetime

import numpy as np
import pandas as pd

from cfb.evaluation.backtest import block_bootstrap, prepare_tasks
from cfb.markets import MARKETS, consensus_lines, model_probabilities, outcomes, trade_pnl
from cfb.models.dynamic import DynamicParams, filter_and_predict, ids_digest

B02 = DynamicParams(q_week=0.25, rho=0.9, s0=8.0, sigma=11.0)
GRID = [(w, t) for w in (0.25, 0.5, 1.0) for t in (0.02, 0.04, 0.06)]
MIN_TRADES = 100
NULL_SEED = 20261007
REPS, BOOT_SEED = 4000, 7


def forecast_frame(conn, ledger, spec, seasons, snapshot_dir) -> pd.DataFrame:
    """One row per scored game in `seasons` with market prices, model probabilities, outcomes."""
    lag = spec["replay"]["reconstructed_result_available_after_kickoff_hours"]
    tasks = sorted(prepare_tasks(conn, spec, seasons, [], snapshot_dir), key=lambda t: t.fold.cutoff)
    folds = [(t.fold.cutoff.isoformat(), ids_digest(t.frame.train["game_id"]), t.frame.target) for t in tasks]
    preds = filter_and_predict(tasks[-1].frame.train, folds, B02, lag)
    rows = []
    for task, (_, gids, means, covs) in zip(tasks, preds, strict=True):
        for gid, m, c in zip(gids, means, covs, strict=True):
            rows.append({"game_id": gid, "season": task.fold.season,
                         "block": f"{task.fold.season}-{task.fold.season_type}-{task.fold.week}",
                         "home_points": task.outcomes[gid][0], "away_points": task.outcomes[gid][1],
                         "mean": m, "cov": c})
    df = pd.DataFrame(rows)
    games = [g for s in seasons for st in ("regular", "postseason")
             for g in ledger.load(ledger.latest_success("/lines", {"year": s, "seasonType": st}))]
    df = df.merge(consensus_lines(games), on="game_id", how="left")
    probs = model_probabilities(np.stack(df["mean"]), np.stack(df["cov"]), df["spread"].to_numpy(),
                                df["total"].to_numpy())
    ys = outcomes(df["home_points"].to_numpy(), df["away_points"].to_numpy(), df["spread"].to_numpy(),
                  df["total"].to_numpy())
    for k in MARKETS:
        df[f"p_{k}_model"], df[f"y_{k}"] = probs[k], ys[k]
    df["p_cover_market"] = np.where(df["spread"].notna(), 0.5, np.nan)
    df["p_over_market"] = np.where(df["total"].notna(), 0.5, np.nan)
    corr = np.corrcoef(df["spread"].dropna(), (df["home_points"] - df["away_points"])[df["spread"].notna()])[0, 1]
    if corr > -0.3:
        raise RuntimeError(f"spread sign check failed (corr {corr:.2f}); CFBD spread is not the home line")
    return df.drop(columns=["mean", "cov"])


def permuted(df: pd.DataFrame) -> pd.DataFrame:
    """Null: model probabilities shuffled across games within each week."""
    rng = np.random.default_rng(NULL_SEED)
    out = df.copy()
    for k in MARKETS:
        col = f"p_{k}_model"
        out[col] = out.groupby("block")[col].transform(lambda s: rng.permutation(s.to_numpy()))
    return out


def evaluate(df: pd.DataFrame, market: str, w: float, t: float) -> dict:
    pnl = pd.Series(trade_pnl(df[f"p_{market}_model"].to_numpy(), df[f"p_{market}_market"].to_numpy(),
                              df[f"y_{market}"].to_numpy(), w, t), index=df.index).dropna()
    if len(pnl) == 0:
        return {"trades": 0}
    mean, lo, hi = block_bootstrap(pnl, df.loc[pnl.index, "block"], REPS, BOOT_SEED)
    return {"trades": len(pnl), "pnl": float(pnl.sum()), "per_trade": mean, "lo": lo, "hi": hi,
            "hit_rate": float((pnl > 0).mean())}


def select_and_validate(df: pd.DataFrame) -> dict[str, dict]:
    out = {}
    for m in MARKETS:
        fit = df[df["season"] == 2022]
        cands = [(evaluate(fit, m, w, t), w, t) for w, t in GRID]
        cands = [c for c in cands if c[0]["trades"] >= MIN_TRADES]
        if not cands:
            out[m] = {"selected": None, "reason": f"no rule with >= {MIN_TRADES} trades in 2022"}
            continue
        sel, w, t = max(cands, key=lambda c: c[0]["per_trade"])
        val = evaluate(df[df["season"] == 2023], m, w, t)
        out[m] = {"selected": {"w": w, "t": t}, "2022": sel, "2023": val,
                  "passed": val["trades"] > 0 and val["lo"] > 0}
    return out


def log_loss(p: pd.Series, y: pd.Series) -> float:
    ok = p.notna() & y.notna()
    p, y = p[ok].clip(1e-6, 1 - 1e-6), y[ok]
    return float(-(y * np.log(p) + (1 - y) * np.log(1 - p)).mean())


GAP_BINS = [-1, -0.15, -0.10, -0.05, -0.02, 0.02, 0.05, 0.10, 0.15, 1]


def logit_fit(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Newton-Raphson logistic regression of y on [1, x]; coefficients and standard errors."""
    x = np.column_stack([np.ones(len(x)), x])
    b = np.zeros(x.shape[1])
    for _ in range(50):
        p = 1 / (1 + np.exp(-x @ b))
        h = x.T @ (x * (p * (1 - p))[:, None])
        b = b + np.linalg.solve(h, x.T @ (y - p))
    return b, np.sqrt(np.diag(np.linalg.inv(h)))


def gap_table(p_model: pd.Series, p_market: pd.Series, y: pd.Series) -> pd.DataFrame:
    """Mean model, market and realized rate by model-minus-market gap: who does reality side with?"""
    d = pd.DataFrame({"model": p_model, "market": p_market, "actual": y}).dropna()
    return d.groupby(pd.cut(d.model - d.market, GAP_BINS), observed=True).agg(
        games=("actual", "size"), model=("model", "mean"), market=("market", "mean"), actual=("actual", "mean"))


def main(argv: list[str]) -> None:
    from cfb.cli import REPO_ROOT, open_store
    from cfb.evaluation.protocol import load_protocol

    spec = load_protocol()
    conn, ledger = open_store()
    snaps, out_dir = REPO_ROOT / "artifacts" / "snapshots", REPO_ROOT / "experiments" / "m01"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).isoformat(timespec="seconds")

    if "--open-test" in argv:
        dev = json.loads((out_dir / "m01-validation.json").read_text())
        passed = [m for m, r in dev["real"].items() if r.get("passed")]
        if not passed:
            sys.exit("no market passed 2023; the protocol keeps 2024-2025 closed")
        df = forecast_frame(conn, ledger, spec, [2024, 2025], snaps)
        res = {m: evaluate(df, m, **dev["real"][m]["selected"]) for m in passed}
        for r in res.values():
            r["passed"] = r["trades"] > 0 and r["lo"] > 0
        (out_dir / "m01-test.json").write_text(json.dumps({"generated_at": stamp, "test": res}, indent=1))
        print(json.dumps(res, indent=1))
        return

    df = forecast_frame(conn, ledger, spec, [2022, 2023], snaps)
    win_ok = df["p_win_market"].notna()
    report = {
        "generated_at": stamp, "protocol": "M01", "games": len(df),
        "with_spread": int(df["spread"].notna().sum()), "with_moneyline": int(win_ok.sum()),
        "win_log_loss": {"model": log_loss(df.loc[win_ok, "p_win_model"], df.loc[win_ok, "y_win"]),
                         "market": log_loss(df.loc[win_ok, "p_win_market"], df.loc[win_ok, "y_win"])},
        "real": select_and_validate(df),
        "null": select_and_validate(permuted(df)),
    }
    if any(r.get("passed") for r in report["null"].values()):
        report["null_failed"] = True
    (out_dir / "m01-validation.json").write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main(sys.argv[1:])
