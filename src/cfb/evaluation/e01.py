"""E01: past-only play-efficiency rating blended with B02, tested against the opener
(experiments/protocols/E01-protocol.md).

    uv run python -m cfb.evaluation.e01
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from cfb.evaluation import m02
from cfb.evaluation.backtest import prepare_tasks
from cfb.evaluation.m01 import B02
from cfb.models.dynamic import DynamicParams, filter_and_predict, ids_digest

SIGMAS = (4.0, 6.0, 8.0, 11.0)
BASE, SCALE, MIN_PLAYS = 27.0, 70.0, 20
GARBAGE = {1: 28, 2: 24, 3: 21, 4: 16}  # SP+ thresholds: |margin| above this in the quarter = garbage
DEV, EVAL = (2019, 2020, 2021), (2022, 2023)
FIRST_EPA = 2015


def kept(states: pd.DataFrame) -> pd.Series:
    limit = states["period"].map(GARBAGE)
    return limit.notna() & (states["score_margin"].abs() <= limit)


def game_efficiency(states: pd.DataFrame, epa: pd.DataFrame, team_ids: dict[str, str]) -> pd.DataFrame:
    """Per game and offense: EPA/play over non-garbage plays (only offenses with >= MIN_PLAYS)."""
    s = states.assign(play_id=states["play_id"].astype(str)).merge(epa[["play_id", "epa"]], on="play_id")
    s = s[kept(s)]
    g = s.groupby(["game_id", "offense"])["epa"].agg(["mean", "size"]).reset_index()
    g = g[g["size"] >= MIN_PLAYS]
    g["team"] = g["offense"].map(team_ids)
    return g[["game_id", "team", "mean"]].rename(columns={"mean": "epa_pp"})


def efficiency_history(train: pd.DataFrame, eff: pd.DataFrame) -> pd.DataFrame:
    """B02-shaped history with hp/ap replaced by points-like efficiency; games lacking either side dropped."""
    e = eff.set_index(["game_id", "team"])["epa_pp"]
    h = train.copy()
    h["hp"] = [e.get((g, t), np.nan) for g, t in zip(h["game_id"], h["home"], strict=True)]
    h["ap"] = [e.get((g, t), np.nan) for g, t in zip(h["game_id"], h["away"], strict=True)]
    h = h.dropna(subset=["hp", "ap"])
    h[["hp", "ap"]] = BASE + SCALE * h[["hp", "ap"]]
    return h.reset_index(drop=True)


def admitted(history: pd.DataFrame, cutoff, lag_hours: float) -> list[str]:
    cut = pd.Timestamp(cutoff)
    cut = cut.tz_convert(None) if cut.tzinfo else cut
    return list(history.loc[history["start"] + pd.Timedelta(hours=lag_hours) <= cut, "game_id"])


def predict_margins(tasks, history: pd.DataFrame, params: DynamicParams, lag: float, digests=None) -> dict[str, float]:
    folds = [(t.fold.cutoff.isoformat(),
              digests[i] if digests else ids_digest(admitted(history, t.fold.cutoff, lag)), t.frame.target)
             for i, t in enumerate(tasks)]
    out = {}
    for _, gids, means, _ in filter_and_predict(history, folds, params, lag):
        out.update({g: m[0] - m[1] for g, m in zip(gids, means, strict=True)})
    return out


def blend_fit(dev: pd.DataFrame) -> np.ndarray:
    x = np.column_stack([np.ones(len(dev)), dev["b02"], dev["eff"]])
    return np.linalg.lstsq(x, dev["result"].to_numpy(), rcond=None)[0]


def mae(a, b) -> float:
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def market_tests(df: pd.DataFrame) -> dict:
    out = {}
    for s in EVAL:
        d = df[df["season"] == s].dropna(subset=["open", "close"])
        b = d["block"].to_numpy()
        out[str(s)] = {"clv_slope": m02.slope(d),
                       "encompass_open": m02.slope_xy((d["margin"] + d["open"]).to_numpy(),
                                                      (d["result"] + d["open"]).to_numpy(), b),
                       "encompass_close": m02.slope_xy((d["margin"] + d["close"]).to_numpy(),
                                                       (d["result"] + d["close"]).to_numpy(), b)}
    return out


def run_market(df: pd.DataFrame) -> dict:
    sv, tests = m02.select_and_validate(df), market_tests(df)
    t23 = tests["2023"]
    slopes_pass = t23["clv_slope"]["lo"] > 0 and t23["encompass_open"]["lo"] > 0
    return {"trade": sv, "tests": tests, "passed": bool(sv.get("passed")) or slopes_pass}


def render(rep: dict, tag: str = "E01") -> str:
    L = [f"# {tag} results\n\n**Verdict: {rep['verdict']}**\n",
         f"Protocol sha256 `{rep['protocol_sha256']}`; generated {rep['generated_at']}. Reconstructed replay.",
         (f"Selected σ_e = {rep['sigma']:g}; blend = {rep['blend'][0]:+.2f} + {rep['blend'][1]:.3f}·B02 + "
          f"{rep['blend'][2]:.3f}·efficiency.\n"),
         "## Margin error (no market input)\n", "| Seasons | Games | B02 | Efficiency | Blend | Opener | Close |",
         "|---|---|---|---|---|---|---|"]
    for k, r in rep["mae"].items():
        L.append(f"| {k} | {r['games']} | {r['b02']:.2f} | {r['eff']:.2f} | {r['blend']:.2f} | "
                 f"{r.get('open', float('nan')):.2f} | {r.get('close', float('nan')):.2f} |")
    L += ["\nσ_e selection on 2019–2021 (blend MAE): " + ", ".join(f"{k}: {v:.3f}" for k, v in rep["sigma_grid"].items()),
          "\n## Market tests (95% week-block intervals)\n",
          "| Run | Season | CLV slope | Encompassing vs opener | Encompassing vs close |", "|---|---|---|---|---|"]
    f = lambda x: f"{x['slope']:+.3f} [{x['lo']:+.3f}, {x['hi']:+.3f}]"
    for run in ("real", "null"):
        for s, t in rep[run]["tests"].items():
            L.append(f"| {run} | {s} | {f(t['clv_slope'])} | {f(t['encompass_open'])} | {f(t['encompass_close'])} |")
    L += ["\n## Trade rule at the opener (M02 harness)\n", "| Run | g | Season | Trades | Per trade | Interval | CLV | Close our way |",
          "|---|---|---|---|---|---|---|---|"]
    for run in ("real", "null"):
        t = rep[run]["trade"]
        for s in ("2022", "2023"):
            if t.get("selected"):
                x = t[s]
                L.append(f"| {run} | {t['selected']['g']:g} | {s} | {x['trades']} | {x['per_trade']:+.4f} | "
                         f"[{x['lo']:+.4f}, {x['hi']:+.4f}] | {x['clv']:+.2f} | {x['clv_share']:.1%} |")
    return "\n".join(L) + "\n"


def main(states_file: str = "states.parquet", sigmas: tuple[float, ...] = SIGMAS, tag: str = "E01") -> None:
    from cfb.cli import REPO_ROOT, open_store
    from cfb.evaluation import p04
    from cfb.evaluation.protocol import load_protocol

    spec = load_protocol()
    conn, ledger = open_store()
    lag = spec["replay"]["reconstructed_result_available_after_kickoff_hours"]
    seasons = [*DEV, *EVAL]
    tasks = sorted(prepare_tasks(conn, spec, seasons, [], REPO_ROOT / "artifacts" / "snapshots"),
                   key=lambda t: t.fold.cutoff)
    train = tasks[-1].frame.train

    # B02 margins (identical pass to M01/M02).
    b02 = predict_margins(tasks, train, B02, lag, [ids_digest(t.frame.train["game_id"]) for t in tasks])

    # Past-only EPA per season, then per-game efficiency.
    ep_states = pd.read_parquet(REPO_ROOT / "artifacts" / "plays" / "states.parquet")  # EP training: exact tier
    states = pd.read_parquet(REPO_ROOT / "artifacts" / "plays" / states_file)
    team_ids = {n: t for t, n in conn.execute("SELECT team_id, display_name FROM teams")}
    eff = []
    for s in range(FIRST_EPA, max(seasons) + 1):
        model = p04.fold_ep_model(ep_states, s, 2014, REPO_ROOT / "artifacts" / "models")
        st = states[states["season"] == s]
        eff.append(game_efficiency(st, p04.play_epa(st, model), team_ids))
    eff = pd.concat(eff, ignore_index=True)
    hist = efficiency_history(train[train["season"] >= FIRST_EPA], eff)

    rows = [{"game_id": g, "season": t.fold.season, "result": t.outcomes[g][0] - t.outcomes[g][1],
             "block": f"{t.fold.season}-{t.fold.season_type}-{t.fold.week}"} for t in tasks for g in t.fold.game_ids]
    base = pd.DataFrame(rows)
    base["b02"] = base["game_id"].map(b02)
    grid, preds = {}, {}
    for sig in sigmas:
        p = DynamicParams(q_week=B02.q_week, rho=B02.rho, s0=B02.s0, sigma=sig)
        preds[sig] = base["game_id"].map(predict_margins(tasks, hist, p, lag))
        d = base.assign(eff=preds[sig])
        dev = d[d["season"].isin(DEV)]
        coef = blend_fit(dev)
        grid[f"{sig:g}"] = mae(coef[0] + coef[1] * dev["b02"] + coef[2] * dev["eff"], dev["result"])
    sigma = min(sigmas, key=lambda s: grid[f"{s:g}"])
    df = base.assign(eff=preds[sigma])
    coef = blend_fit(df[df["season"].isin(DEV)])
    df["margin"] = coef[0] + coef[1] * df["b02"] + coef[2] * df["eff"]
    dev = df[df["season"].isin(DEV)]
    eff_only = np.linalg.lstsq(np.column_stack([np.ones(len(dev)), dev["eff"]]), dev["result"].to_numpy(), rcond=None)[0]

    games = [g for s in seasons for st in ("regular", "postseason")
             for g in ledger.load(ledger.latest_success("/lines", {"year": s, "seasonType": st}))]
    df = df.merge(m02.open_close_lines(games), on="game_id", how="left")
    df["gap"] = -df["margin"] - df["open"]

    err = {}
    for k, ss in (("2019-2021", DEV), ("2022", (2022,)), ("2023", (2023,))):
        d = df[df["season"].isin(ss)]
        r = {"games": len(d), "b02": mae(d["b02"], d["result"]),
             "eff": mae(eff_only[0] + eff_only[1] * d["eff"], d["result"]), "blend": mae(d["margin"], d["result"])}
        if k != "2019-2021":
            w = d.dropna(subset=["open", "close"])
            r |= {"open": mae(-w["open"], w["result"]), "close": mae(-w["close"], w["result"]),
                  "blend_lined": mae(w["margin"], w["result"])}
        err[k] = r

    real, null = run_market(df), run_market(m02.permuted(df))
    protocol = Path(REPO_ROOT) / "experiments" / "protocols" / f"{tag}-protocol.md"
    verdict = ("NULL CHECK FAILED: pipeline broken, no claim" if null["passed"] else
               "PASS: efficiency carries information beyond the opener" if real["passed"] else
               "NO EDGE: the efficiency blend adds nothing the opener lacks")
    rep = {"generated_at": datetime.now(UTC).isoformat(timespec="seconds"), "verdict": verdict,
           "protocol_sha256": hashlib.sha256(protocol.read_bytes()).hexdigest(), "sigma": sigma,
           "sigma_grid": grid, "blend": [float(c) for c in coef], "mae": err, "real": real, "null": null}
    out = REPO_ROOT / "experiments" / tag.lower()
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{tag.lower()}-results.json").write_text(json.dumps(rep, indent=1, default=float))
    (out / f"{tag.lower()}-results.md").write_text(render(rep, tag), encoding="utf-8")
    print(rep["verdict"])


if __name__ == "__main__":
    main()
