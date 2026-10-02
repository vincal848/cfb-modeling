"""B01: forward evaluation of the baselines on the V01 development seasons.

The grid below was fixed before any B01 result was computed. Each model keeps its
configuration with the lowest mean development energy score; because that choice is
made on the same games, the selected scores are optimistic and are reported as
development results, never as test results. Stack-fit, calibration and test seasons
are not touched here.
"""

from __future__ import annotations

import itertools
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from cfb.evaluation.backtest import Config, block_bootstrap, mean_scores

# Pass 2 (2026-10-02). Pass 1 (commit 7aa513e) selected grid-edge values: ridge penalty 2
# (smallest tried), Elo hfa 50 (smallest) and carryover 0.75 (largest), and ridge intervals
# were too narrow. This grid widens around those edges and adds a ridge covariance scale.
# It was fixed before pass 2 ran, and no further pass is planned.
GRID_PASS = 2
GRID: dict[str, dict[str, list[float]]] = {
    "hfa_only": {"half_life_days": [365.0]},
    "elo": {"k": [25.0, 30.0, 35.0], "hfa": [20.0, 35.0, 50.0], "carryover": [0.75, 0.85, 0.95]},
    "ridge": {"half_life_days": [180.0, 240.0, 300.0, 360.0], "penalty": [0.25, 0.5, 1.0, 2.0, 3.0],
              "cov_scale": [1.0, 1.1, 1.2]},
}
CHAMPION_MODEL = "ridge"  # config.models.initial_champion: regularized past-only baseline
TRIVIAL_MODEL = "hfa_only"


def grid_configs() -> list[Config]:
    out = []
    for model, params in GRID.items():
        keys = sorted(params)
        for values in itertools.product(*(params[k] for k in keys)):
            out.append(Config(model, tuple(zip(keys, values, strict=True))))
    return out


def select(df: pd.DataFrame) -> dict[str, str]:
    """Best configuration label per model by mean energy score."""
    means = df.groupby(["model", "config"])["energy_score"].mean()
    return {m: means.loc[m].idxmin() for m in means.index.get_level_values(0).unique()}


def blocks(df: pd.DataFrame, kind: str) -> pd.Series:
    """Bootstrap block per game. The postseason is its own block, except that it joins the
    late half in season-half blocks."""
    post = df["season_type"] == "postseason"
    if kind == "week":
        key = "w" + df["week"].astype(str)
    elif kind == "three_week":
        key = "t" + ((df["week"] - 1) // 3).astype(str)
    elif kind == "season_half":
        key = (df["week"] > 7).map({True: "late", False: "early"})
    else:
        raise ValueError(kind)
    key = key.where(~post, "late" if kind == "season_half" else "post")
    return df["season"].astype(str) + "-" + key


def paired(df: pd.DataFrame, a: str, b: str, metric: str, kind: str, reps: int, seed: int) -> dict[str, Any]:
    x = df[df["config"] == a].set_index("game_id")
    y = df[df["config"] == b].set_index("game_id")
    common = x.index.intersection(y.index)
    x, y = x.loc[common], y.loc[common]
    mean, lo, hi = block_bootstrap(x[metric] - y[metric], blocks(x, kind), reps, seed)
    return {"challenger": a, "baseline": b, "metric": metric, "blocks": kind, "games": len(common),
            "mean_difference": mean, "ci95": [lo, hi], "challenger_better": hi < 0}


def report(df: pd.DataFrame, cohorts: pd.DataFrame, protocol: dict[str, Any]) -> dict[str, Any]:
    chosen = select(df)
    sel = df[df["config"].isin(chosen.values())]
    reps = protocol["comparison"]["replicates"]
    seed = protocol["monte_carlo"]["root_seed"]
    champ, elo, triv = chosen[CHAMPION_MODEL], chosen["elo"], chosen[TRIVIAL_MODEL]

    comparisons = []
    for a, b in ((champ, triv), (elo, triv), (champ, elo)):
        for kind in ("week", "three_week", "season_half"):
            comparisons.append(paired(sel, a, b, "energy_score", kind, reps, seed))
        for metric in ("winner_log_loss", "margin_crps", "total_crps"):
            comparisons.append(paired(sel, a, b, metric, "week", reps, seed))
    no2020 = sel[sel["season"] != 2020]
    for a, b in ((champ, triv), (champ, elo)):
        c = paired(no2020, a, b, "energy_score", "week", reps, seed)
        c["sensitivity"] = "exclude 2020"
        comparisons.append(c)

    merged = sel.merge(cohorts, on="game_id")
    cohort_rows = []
    for name in cohorts.columns.drop("game_id"):
        sub = merged[merged[name]]
        if sub.empty:  # still reported: V01 lists every cohort for every evaluation
            cohort_rows += [{"cohort": name, "config": cfg, "games": 0, "energy_score": None,
                             "winner_log_loss": None, "margin_crps": None} for cfg in chosen.values()]
            continue
        for cfg, g in sub.groupby("config"):
            cohort_rows.append({"cohort": name, "config": cfg, "games": len(g),
                                "energy_score": g["energy_score"].mean(),
                                "winner_log_loss": g["winner_log_loss"].mean(),
                                "margin_crps": g["margin_crps"].mean()})

    grid = df.groupby(["model", "config"])["energy_score"].mean().reset_index()
    return {
        "stage": "B01",
        "grid_pass": GRID_PASS,
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "protocol_id": protocol["protocol_id"], "protocol_version": protocol["protocol_version"],
        "evaluation_class": protocol["replay"]["historical_class"],
        "role": "development", "seasons": sorted(int(s) for s in df["season"].unique()),
        "horizon_minutes": int(df["horizon_minutes"].iloc[0]),
        "draws_per_game": protocol["monte_carlo"]["draws_per_game"],
        "selected": chosen,
        "overall": mean_scores(sel, ["config"]).reset_index().to_dict("records"),
        "by_season": mean_scores(sel, ["config", "season"]).reset_index().to_dict("records"),
        "comparisons": comparisons,
        "cohorts": cohort_rows,
        "grid": grid.to_dict("records"),
    }


def render(rep: dict[str, Any]) -> str:
    def f(x: float | None, d: int = 3) -> str:
        return "n/a" if x is None else f"{x:.{d}f}"

    sel = rep["selected"]
    names = {v: k for k, v in sel.items()}
    lines = [
        "# B01 baselines: development results",
        "",
        (f"Generated {rep['generated_at']}. Protocol {rep['protocol_id']} v{rep['protocol_version']} "
         f"(frozen). **Evaluation class: {rep['evaluation_class']}.** Seasons {rep['seasons']} "
         f"(development role only), horizon {rep['horizon_minutes']} minutes, "
         f"{rep['draws_per_game']:,} draws per game. Lower is better for every score."),
        "",
        ("Each model's configuration was selected on these same games, so these scores are "
         "optimistic. They are development evidence, not test results."),
        "",
        (f"Tuning pass {rep['grid_pass']}. Pass 1 (commit 7aa513e) selected values at the edges of "
         "its grid, so pass 2 widened the grid once; no further pass is planned."),
        "",
        "## Selected configurations",
        "",
    ]
    lines += [f"- **{m}**: `{c}`" for m, c in sel.items()]
    lines += ["", "## Overall", "",
              ("| Model | Games | Energy score | Winner log loss | Brier | Margin CRPS | Total CRPS "
               "| Margin MAE | Total MAE |"),
              "|---|---|---|---|---|---|---|---|---|"]
    for r in rep["overall"]:
        lines.append(f"| {names[r['config']]} | {r['games']} | {f(r['energy_score'])} | {f(r['winner_log_loss'])} | "
                     f"{f(r['winner_brier'])} | {f(r['margin_crps'])} | {f(r['total_crps'])} | "
                     f"{f(r['margin_abs_error'], 2)} | {f(r['total_abs_error'], 2)} |")
    lines += ["", "Interval coverage (nominal 50 / 80 / 95%):", "",
              "| Model | Margin coverage | Margin width | Total coverage | Total width |", "|---|---|---|---|---|"]
    def cov(r: dict, t: str) -> str:
        return " / ".join(f"{r[f'{t}_{lv}_covered']:.1%}" for lv in (50, 80, 95))

    def wid(r: dict, t: str) -> str:
        return " / ".join(f"{r[f'{t}_{lv}_width']:.1f}" for lv in (50, 80, 95))

    for r in rep["overall"]:
        lines.append(f"| {names[r['config']]} | {cov(r, 'margin')} | {wid(r, 'margin')} | "
                     f"{cov(r, 'total')} | {wid(r, 'total')} |")
    lines += ["", "## By season (energy score)", "", "| Model | " + " | ".join(str(s) for s in rep["seasons"]) + " |",
              "|---|" + "---|" * len(rep["seasons"])]
    for cfg in sel.values():
        vals = {r["season"]: r["energy_score"] for r in rep["by_season"] if r["config"] == cfg}
        lines.append(f"| {names[cfg]} | " + " | ".join(f(vals[s]) for s in rep["seasons"]) + " |")
    lines += ["", "## Paired comparisons", "",
              ("Challenger minus baseline, per game, on identical games; week-block bootstrap unless "
               "noted. Negative favors the challenger. 'Better' means the whole 95% interval is below 0 "
               "(V01 rule)."), "",
              "| Challenger | Baseline | Metric | Blocks | Games | Mean diff | 95% interval | Better |",
              "|---|---|---|---|---|---|---|---|"]
    for c in rep["comparisons"]:
        blk = c["blocks"] + (f", {c['sensitivity']}" if "sensitivity" in c else "")
        lines.append(f"| {names[c['challenger']]} | {names[c['baseline']]} | {c['metric']} | {blk} | {c['games']} | "
                     f"{c['mean_difference']:+.4f} | [{c['ci95'][0]:+.4f}, {c['ci95'][1]:+.4f}] | "
                     f"{'yes' if c['challenger_better'] else 'no'} |")
    lines += ["", "## Cohorts (energy score; cohorts under 100 games are descriptive only)", "",
              "| Cohort | Games | " + " | ".join(sel) + " |", "|---|---|" + "---|" * len(sel)]
    by = {}
    for r in rep["cohorts"]:
        by.setdefault(r["cohort"], {})[names[r["config"]]] = r
    for cohort, rows in by.items():
        n = next(iter(rows.values()))["games"]
        lines.append(f"| {cohort} | {n} | " + " | ".join(f(rows[m]["energy_score"]) for m in sel) + " |")
    lines += ["", "## Tuning grid (mean development energy score)", "", "| Model | Configuration | Energy score |",
              "|---|---|---|"]
    for r in sorted(rep["grid"], key=lambda r: (r["model"], r["energy_score"])):
        lines.append(f"| {r['model']} | `{r['config']}` | {f(r['energy_score'], 4)} |")
    return "\n".join(lines) + "\n"


def write(rep: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    j, m = out_dir / "b01-development.json", out_dir / "b01-development.md"
    j.write_text(json.dumps(rep, indent=1, default=float), encoding="utf-8")
    m.write_text(render(rep), encoding="utf-8")
    return j, m
