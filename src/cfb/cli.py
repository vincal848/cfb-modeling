"""Command-line entry point. Commands are added as milestones land (see PROGRESS.md)."""

from __future__ import annotations

import typer

from cfb import __version__
from cfb.config import DEFAULT_CONFIG, REPO_ROOT, ConfigError, load_config
from cfb.credentials import SETUP_INSTRUCTIONS, MissingCredentialError, get_api_key, require_api_key
from cfb.db import connect
from cfb.ingestion.audit import run_audit, write_report
from cfb.ingestion.client import CFBDClient
from cfb.ingestion.fetch import Fetcher, QuotaGuard
from cfb.ingestion.ledger import RawLedger

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.callback()
def main() -> None:
    """College football modeling system."""


@app.command()
def doctor() -> None:
    """Check configuration, contract schema, and CFBD credential presence (never prints the key)."""
    ok = True
    typer.echo(f"cfb-modeling {__version__}")

    try:
        cfg = load_config()
        typer.echo(f"[ok]   config valid: {DEFAULT_CONFIG}")
    except (ConfigError, OSError, KeyError) as exc:
        typer.echo(f"[FAIL] config: {exc}")
        ok = False
        cfg = None

    try:
        conn = connect()
        (fk_errors,) = conn.execute("SELECT count(*) FROM pragma_foreign_key_check").fetchone()
        conn.close()
        typer.echo(f"[ok]   contract schema executes (fk violations: {fk_errors})")
    except Exception as exc:  # noqa: BLE001 - report any schema failure
        typer.echo(f"[FAIL] contract schema: {exc}")
        ok = False

    if get_api_key():
        tier = cfg["data"]["subscription_tier_assumption"] if cfg else "?"
        typer.echo(f"[ok]   CFBD_API_KEY present (tier assumption {tier}; entitlement unverified until M0 audit)")
    else:
        typer.echo("[warn] CFBD_API_KEY missing - live ingestion unavailable")
        typer.echo(SETUP_INSTRUCTIONS)

    raise typer.Exit(code=0 if ok else 1)


DATA_DIR = REPO_ROOT / "data"


def open_fetcher() -> Fetcher:
    cfg = load_config()
    try:
        key = require_api_key()
    except MissingCredentialError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=2) from None
    DATA_DIR.mkdir(exist_ok=True)
    guard = QuotaGuard(cfg["data"]["monthly_quota"], cfg["data"]["bulk_backfill_stop_fraction"])
    return Fetcher(
        CFBDClient(key), RawLedger(DATA_DIR / "raw", connect(DATA_DIR / "ledger.sqlite")), guard
    )


@app.command("audit-source")
def audit_source(
    season: int = typer.Option(2024, help="Sample season for the per-endpoint call"),
    week: int = typer.Option(5),
    team: str = typer.Option("Michigan"),
    refresh: bool = typer.Option(False, help="Re-fetch even if a cached response exists"),
) -> None:
    """D01: one authenticated sample call per registered endpoint; writes experiments/m0/."""
    fetcher = open_fetcher()
    report = run_audit(fetcher, {"year": season, "week": week, "team": team}, refresh=refresh)
    jpath, mpath = write_report(report, REPO_ROOT / "experiments" / "m0")
    bad = [r["path"] for r in report["results"] if r["http_status"] != 200]
    typer.echo(f"{len(report['results'])} endpoints audited; non-200: {bad or 'none'}")
    typer.echo(f"calls remaining: {report['calls_remaining_after']}")
    typer.echo(f"wrote {mpath.relative_to(REPO_ROOT)} and {jpath.name}")


@app.command("audit-coverage")
def audit_coverage(
    start: int = typer.Option(2014), end: int = typer.Option(2025),
) -> None:
    """D02: season coverage matrix for core families; cache-first, so reruns are free."""
    from cfb.ingestion import coverage

    fetcher = open_fetcher()
    report = coverage.run_coverage(fetcher, list(range(start, end + 1)), log=typer.echo)
    jpath, mpath = coverage.write_report(report, REPO_ROOT / "experiments" / "m0")
    typer.echo(f"calls remaining: {report['calls_remaining_after']}")
    typer.echo(f"wrote {mpath.relative_to(REPO_ROOT)} and {jpath.name}")


@app.command()
def ingest(
    family: list[str] = typer.Option(..., help="Family name(s), or 'core' for every registered family"),  # noqa: B008
    season: int = typer.Option(..., help="First season"),
    end: int = typer.Option(None, help="Last season (defaults to --season)"),
    refresh: bool = typer.Option(False, help="Re-fetch cached partitions (correction window)"),
) -> None:
    """D04: cache-first raw backfill; restarts make no calls for partitions already retrieved."""
    from cfb.ingestion.backfill import CORE_FAMILIES, FAMILIES, backfill

    families = list(CORE_FAMILIES) if family == ["core"] else family
    unknown = [f for f in families if f not in FAMILIES]
    if unknown:
        typer.echo(f"unknown family {unknown}; choose from {sorted(FAMILIES)} or 'core'", err=True)
        raise typer.Exit(code=2)
    fetcher = open_fetcher()
    failed = truncated = 0
    for s in range(season, (end or season) + 1):
        for f in families:
            r = backfill(fetcher, f, s, refresh=refresh, log=typer.echo)
            failed += len(r.failed)
            truncated += len(r.truncated)
    typer.echo(f"calls remaining: {fetcher.guard.remaining}; failed {failed}; truncated {truncated}")
    raise typer.Exit(code=1 if failed else 0)


def open_store():
    """The local contract database and raw store, without needing the API key."""
    DATA_DIR.mkdir(exist_ok=True)
    conn = connect(DATA_DIR / "ledger.sqlite")
    return conn, RawLedger(DATA_DIR / "raw", conn)


@app.command()
def canonicalize() -> None:
    """D05: canonical teams/games and versioned schedule/result facts from cached /games."""
    from cfb.canonical.games import canonicalize_games
    from cfb.evaluation.protocol import load_protocol

    lag = load_protocol()["replay"]["reconstructed_result_available_after_kickoff_hours"]
    conn, ledger = open_store()
    canonicalize_games(conn, ledger, lag, log=typer.echo)
    for etype, n in conn.execute("SELECT entity_type, count(*) FROM source_records GROUP BY 1"):
        typer.echo(f"  {etype}: {n} versions")


@app.command()
def players() -> None:
    """D05/D06: canonical players and roster memberships; portal identity crosswalk."""
    from cfb.canonical.players import canonicalize_rosters, crosswalk_portal

    conn, ledger = open_store()
    canonicalize_rosters(conn, ledger, log=typer.echo)
    crosswalk_portal(conn, ledger, log=typer.echo)
    rows = conn.execute(
        """SELECT CAST(substr(source_player_key, 1, 4) AS INTEGER) AS season, status, count(*)
           FROM player_identity_links GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()
    by: dict[int, dict[str, int]] = {}
    for season, status, n in rows:
        by.setdefault(season, {})[status] = n
    statuses = ["verified", "proposed", "ambiguous", "unresolved"]
    lines = ["# D06 portal identity crosswalk", "",
             ("Each portal record is matched by exact normalized name to the origin team's roster the season "
              "before. `verified` also requires the same athlete ID on the named destination's roster in the "
              "portal season; `ambiguous` (several same-name players) and `unresolved` records get no player."), "",
             "| Portal season | Records | " + " | ".join(statuses) + " | Verified share |",
             "|---|---|" + "---|" * (len(statuses) + 1)]
    for season, c in sorted(by.items()):
        total = sum(c.values())
        lines.append(f"| {season} | {total} | " + " | ".join(str(c.get(s, 0)) for s in statuses)
                     + f" | {c.get('verified', 0) / total:.1%} |")
    moved = conn.execute(
        """SELECT count(*) FROM (SELECT player_id FROM roster_memberships GROUP BY player_id
           HAVING count(DISTINCT team_id) > 1)""").fetchone()[0]
    players_n = conn.execute("SELECT count(*) FROM players").fetchone()[0]
    lines += ["", (f"Canonical players: {players_n:,}. Players listed on more than one team across seasons, "
                   f"under one athlete ID: {moved:,}.")]
    out = REPO_ROOT / "experiments" / "d06"
    out.mkdir(parents=True, exist_ok=True)
    (out / "portal-crosswalk.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines[4:]))


@app.command("reconcile-plays")
def reconcile_plays(start: int = typer.Option(2014), end: int = typer.Option(2025),
                    workers: int = typer.Option(0, help="Worker processes (0 = CPU count - 1)")) -> None:
    """P01: play-by-play scoring reconciliation per game under the cited rules registry."""
    import json
    from collections import Counter

    import pandas as pd

    from cfb.evaluation.backtest import parallel_map
    from cfb.state.machine import reconcile_season

    seasons = list(range(start, end + 1))
    df = pd.DataFrame([r for rows in parallel_map(reconcile_season, seasons, workers or None) for r in rows])
    out = REPO_ROOT / "artifacts" / "quality"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "play_reconciliation.parquet", index=False)

    tiers = ["exact", "events", "failed"]
    lines = ["# P01 play-by-play scoring reconciliation", "",
             ("Every population game's CFBD plays are walked in game order under the season's rules from "
              "`config/rules_registry.json`. **exact**: every score change is explained and the walk ends at the "
              "official final. **events**: the classified scoring events sum to the official final (undescribed "
              "tries 0-2 points; failed tries may have been returned for 2), but some per-play changes are "
              "unexplained. **failed**: neither. Only exact games are fit for transition-level models (P02)."), "",
             "| Season | Games | Exact | Events | Failed | Exact share | Swapped columns | OT games |",
             "|---|---|---|---|---|---|---|---|"]
    for season, g in df.groupby("season"):
        c = g["tier"].value_counts()
        lines.append(f"| {season} | {len(g)} | " + " | ".join(str(int(c.get(t, 0))) for t in tiers)
                     + f" | {c.get('exact', 0) / len(g):.1%} | {int(g['score_columns_swapped'].sum())} | "
                     f"{int((g['overtime_periods'] > 0).sum())} |")
    c = df["tier"].value_counts()
    lines.append(f"| All | {len(df)} | " + " | ".join(str(int(c.get(t, 0))) for t in tiers)
                 + f" | {c.get('exact', 0) / len(df):.1%} | {int(df['score_columns_swapped'].sum())} | "
                 f"{int((df['overtime_periods'] > 0).sum())} |")
    issues = Counter()
    for s in df["issues"]:
        issues.update({k: 1 for k in json.loads(s)})
    lines += ["", "## Games with each issue", "", "| Issue | Games |", "|---|---|"]
    lines += [f"| `{k}` | {n} |" for k, n in issues.most_common()]
    lines += ["", "## Provider conventions handled (games affected)", "",
              f"- Touchdowns found from text under non-touchdown play types: {int((df['text_touchdowns'] > 0).sum())}",
              f"- Stale rows skipped: {int((df['stale_rows'] > 0).sum())}",
              f"- Try points recorded on the next play: {int((df['split_tries'] > 0).sum())}",
              f"- Try results inferred from the score change: {int((df['inferred_tries'] > 0).sum())}",
              f"- Score columns swapped for the whole game: {int(df['score_columns_swapped'].sum())}"]
    rep = REPO_ROOT / "experiments" / "p01"
    rep.mkdir(parents=True, exist_ok=True)
    (rep / f"reconciliation-{start}-{end}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines[4:]))


@app.command()
def ep(workers: int = typer.Option(0, help="Worker processes (0 = the EP default)")) -> None:
    """P02: fold-specific EP models on the development seasons; calibration and held-out scores."""
    import pandas as pd

    from cfb.evaluation import p02
    from cfb.evaluation.backtest import block_bootstrap, parallel_map
    from cfb.evaluation.protocol import load_protocol
    from cfb.state.table import LABELS

    spec = load_protocol()
    seasons = spec["seasons"]["development"]["seasons"]
    first = spec["seasons"]["warmup"]["seasons"][0]
    states = REPO_ROOT / "artifacts" / "plays" / "states.parquet"
    n = workers or p02.EP_WORKERS
    selection = parallel_map(p02.run_job, p02.plan_selection(states, seasons, first), n)
    chosen = p02.choose(selection, seasons)
    final = parallel_map(p02.run_job, p02.plan_final(states, chosen, first), n)
    by = {(r["job"].eval_season, r["job"].kind): r for r in final}
    full = pd.concat([by[(s, "full")]["frame"] for s in seasons], ignore_index=True)
    yard = pd.concat([by[(s, "yardline")]["frame"] for s in seasons], ignore_index=True)
    full["yardline_log_loss"] = yard["log_loss"].to_numpy()
    out = REPO_ROOT / "artifacts" / "plays"
    full.to_parquet(out / "ep-development.parquet", index=False)

    reps, seed = spec["comparison"]["replicates"], spec["monte_carlo"]["root_seed"]
    blocks = full["season"].astype(str) + "-" + full["season_type"] + "-" + full["week"].astype(str)
    lines = ["# P02 expected points: development results", "",
             (f"Reconstructed evaluation on development seasons {seasons}. Each season's EP model is fit only on "
              f"earlier seasons ({first} onward), with its penalty chosen on the season before it. States are P01 "
              "exact-tier regulation scrimmage plays. Next-score log loss is per play; lower is better."), "",
             "## Folds", "", "| Season | Train plays | Penalty (full / yardline) | Learned try value | Converged |",
             "|---|---|---|---|---|"]
    for s in seasons:
        f, y = by[(s, "full")], by[(s, "yardline")]
        lines.append(f"| {s} | {f['train_rows']:,} | {f['job'].penalty:g} / {y['job'].penalty:g} | "
                     f"{f['try_value']:.3f} | {f['converged'] and y['converged']} |")
    lines += ["", "## Held-out next-score log loss", "", "| Season | Plays | Class prior | Yard line only | Full |",
              "|---|---|---|---|---|"]
    for s, g in full.groupby("season"):
        lines.append(f"| {s} | {len(g):,} | {g['prior_log_loss'].mean():.4f} | {g['yardline_log_loss'].mean():.4f} | "
                     f"{g['log_loss'].mean():.4f} |")
    lines.append(f"| All | {len(full):,} | {full['prior_log_loss'].mean():.4f} | "
                 f"{full['yardline_log_loss'].mean():.4f} | {full['log_loss'].mean():.4f} |")
    lines += ["", "Paired differences (per play, week-block bootstrap, 95% interval):", ""]
    for name, base in (("yard line only", "yardline_log_loss"), ("class prior", "prior_log_loss")):
        m, lo, hi = block_bootstrap(full["log_loss"] - full[base], blocks, reps, seed)
        lines.append(f"- Full minus {name}: {m:+.4f} [{lo:+.4f}, {hi:+.4f}]")

    full["ep_decile"] = pd.qcut(full["ep"], 10, labels=False, duplicates="drop")
    lines += ["", "## Calibration: EP versus realized next-score points (deciles of EP)", "",
              "| Decile | Plays | Mean EP | Mean realized | Difference |", "|---|---|---|---|---|"]
    for d, g in full.groupby("ep_decile"):
        lines.append(f"| {int(d) + 1} | {len(g):,} | {g['ep'].mean():+.3f} | {g['realized'].mean():+.3f} | "
                     f"{g['realized'].mean() - g['ep'].mean():+.3f} |")
    lines += ["", "## Calibration by outcome", "", "| Next score | Mean predicted | Observed |", "|---|---|---|"]
    for lab in LABELS:
        lines.append(f"| {lab} | {full[f'p_{lab}'].mean():.4f} | {(full['next_score'] == lab).mean():.4f} |")
    lines += ["", "## EP at 1st and 10, start of game, tied (by fold)", "",
              "| Yards to goal | " + " | ".join(str(s) for s in seasons) + " |", "|---|" + "---|" * len(seasons)]
    for ytg in (5, 15, 25, 35, 50, 65, 75, 85, 95):
        lines.append(f"| {ytg} | " + " | ".join(f"{by[(s, 'full')]['ep_by_yardline'][ytg]:+.2f}" for s in seasons) + " |")
    kinds = {"pass": full["play_type"].str.contains("Pass|Sack|Interception", regex=True),
             "rush": full["play_type"].str.contains("Rush", regex=True)}
    lines += ["", "## EPA sanity", "", f"- Mean EPA over all plays: {full['epa'].mean():+.4f}"]
    lines += [f"- Mean EPA, {k} plays: {full.loc[m, 'epa'].mean():+.4f} ({int(m.sum()):,} plays)" for k, m in kinds.items()]
    rep = REPO_ROOT / "experiments" / "p02"
    rep.mkdir(parents=True, exist_ok=True)
    (rep / "ep-development.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines))


@app.command()
def opportunity() -> None:
    """P03: opportunity-share forecasts scored on the development seasons (one process)."""
    import pandas as pd

    from cfb.evaluation import p03
    from cfb.evaluation.protocol import load_protocol

    spec = load_protocol()
    seasons = spec["seasons"]["development"]["seasons"]
    conn, ledger = open_store()
    series = {s: p03.season_series(conn, ledger, s) for s in seasons}
    rows = []
    for params in [None, *p03.grid()]:
        for s in seasons:
            rows += [dict(r, config=p03.label(params)) for r in p03.evaluate(series[s], params, s)]
    df = pd.DataFrame(rows)
    summary = p03.summarize(df)
    best = summary.drop(index="last_game").index[0]
    chosen = df[df["config"].isin([best, "last_game"])]
    lines = ["# P03 opportunity shares: development results", "",
             (f"Seasons {seasons}, reconstructed. Each team-game-category share forecast uses only earlier games "
              "of the season, the previous season and the season's roster. Log score is per opportunity "
              "(lower is better); new players and unassigned opportunities count against the UNKNOWN group. "
              "The configuration was selected on these games, so its scores are optimistic."), "",
             f"Selected: `{best}`", "",
             "| Model | Category | Team-games | Opportunities | Log score | Participation log loss | Max conservation error |",
             "|---|---|---|---|---|---|---|"]
    for (cfg, cat), g in chosen.groupby(["config", "category"]):
        lines.append(f"| {'last game' if cfg == 'last_game' else 'shares'} | {cat} | {len(g):,} | "
                     f"{int(g['opportunities'].sum()):,} | {g['log_score_sum'].sum() / g['opportunities'].sum():.4f} | "
                     f"{g['participation_loss_sum'].sum() / max(g['candidates'].sum(), 1):.4f} | "
                     f"{g['conservation_error'].max():.2e} |")
    lines += ["", "By season (log score, all categories):", "", "| Season | Shares | Last game |", "|---|---|---|"]
    for s in seasons:
        sub = chosen[chosen["season"] == s]
        vals = {c: g["log_score_sum"].sum() / g["opportunities"].sum() for c, g in sub.groupby("config")}
        lines.append(f"| {s} | {vals[best]:.4f} | {vals['last_game']:.4f} |")
    # Participation: separate two-part model versus deriving it from shares.
    import itertools

    part = {}
    for hl, st in itertools.product(*p03.PARTICIPATION_GRID.values()):
        part[(hl, st)] = pd.DataFrame([r for s in seasons for r in p03.evaluate_participation(series[s], s, hl, st)])
    base = pd.DataFrame([r for s in seasons for r in p03.evaluate_participation(series[s], s, None, None)])
    best_part = min(part, key=lambda k: part[k]["loss_sum"].sum() / part[k]["players"].sum())
    derived = chosen[chosen["config"] == best]
    lines += ["", "## Participation: P(at least one opportunity), log loss over known players", "",
              (f"Separate participation model selected: half-life {best_part[0]:g} games, prior strength "
               f"{best_part[1]:g}. 'From shares' is 1 - (1 - share)^N, which assumes independent opportunities."), "",
              "| Category | Last-game indicator | From shares | Participation model |", "|---|---|---|---|"]
    for cat in sorted(base["category"].unique()):
        b, m = base[base["category"] == cat], part[best_part][part[best_part]["category"] == cat]
        d = derived[derived["category"] == cat]
        lines.append(f"| {cat} | {b['loss_sum'].sum() / b['players'].sum():.4f} | "
                     f"{d['participation_loss_sum'].sum() / d['candidates'].sum():.4f} | "
                     f"{m['loss_sum'].sum() / m['players'].sum():.4f} |")
    lines += ["", "## Grid (pooled log score)", "", "| Configuration | Log score | Participation log loss |",
              "|---|---|---|"]
    lines += [f"| `{i}` | {r.log_score:.4f} | {r.participation_log_loss:.4f} |" for i, r in summary.iterrows()]
    out = REPO_ROOT / "experiments" / "p03"
    out.mkdir(parents=True, exist_ok=True)
    (out / "opportunity-development.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines[:16]))


@app.command()
def ability() -> None:
    """P04: held-forward skill-player effectiveness on the development seasons (one process)."""
    import pandas as pd

    from cfb.evaluation import p04
    from cfb.evaluation.protocol import load_protocol

    spec = load_protocol()
    seasons = spec["seasons"]["development"]["seasons"]
    first_ep = spec["seasons"]["warmup"]["seasons"][0]
    conn, ledger = open_store()
    states = pd.read_parquet(REPO_ROOT / "artifacts" / "plays" / "states.parquet")
    stats_seasons = list(range(2015, max(seasons) + 1))
    stats = p04.load_play_stats(conn, ledger, stats_seasons)
    pos = p04.positions(ledger, stats_seasons)
    results, params_rows = [], []
    for s in seasons:
        model = p04.fold_ep_model(states, s, first_ep, REPO_ROOT / "artifacts" / "models", log=typer.echo)
        epa = p04.play_epa(states[states["season"].between(2015, s)], model)
        rows, sigma2 = p04.player_seasons(stats[stats["season"] <= s], epa, pos)
        for cat, sub in rows.groupby("category"):
            out, fits = p04.evaluate_category(sub, s, sigma2[cat])
            results.append(out.assign(category=cat))
            params_rows += [dict(f, season=s, category=cat, sigma=sigma2[cat] ** 0.5) for f in fits]
        typer.echo(f"  season {s} done")
    df = pd.concat(results, ignore_index=True)
    df.to_parquet(REPO_ROOT / "artifacts" / "plays" / "ability-development.parquet", index=False)

    def wavg(x, w):
        return float((x * w).sum() / w.sum())

    lines = ["# P04 skill-player effectiveness: development results", "",
             (f"Seasons {seasons}, reconstructed. Each season's player EPA per opportunity is predicted from earlier "
              "seasons only, with EPA from the EP model fit before that season. Scores are per player-season, "
              "weighted by opportunities; lower is better. Only P01 exact-tier games contribute EPA."), "",
             "## Fitted parameters by fold and position group", "",
             ("Each position group with at least 100 training player-seasons, 1,000 opportunities and a median of 5 "
              "opportunities per player-season gets its own development model; other groups (one-off trick plays, "
              "rare roles) are predicted by their training mean."), "",
             ("| Season | Category | Group | Training player-seasons | Persistence rho | Prior sd tau | "
              "Season innovation sd | Play sd sigma | Converged |"),
             "|---|---|---|---|---|---|---|---|---|"]
    for r in params_rows:
        if r["fitted"]:
            lines.append(f"| {r['season']} | {r['category']} | {r['group']} | {r['player_seasons']:,} | {r['rho']:.3f} | "
                         f"{r['tau']:.4f} | {r['q_sd']:.4f} | {r['sigma']:.3f} | {r['converged']} |")
        else:
            lines.append(f"| {r['season']} | {r['category']} | {r['group']} | {r['player_seasons']:,} | "
                         "mean only | | | | |")
    lines += ["", "## Held-forward scores", "",
              ("| Category | Player-seasons | Opportunities | Log score: model | group mean | last season raw | "
               "MSE: model | group mean | last season raw | 80% coverage |"), "|---|---|---|---|---|---|---|---|---|---|"]
    for cat, g in df.groupby("category"):
        w = g["n"]
        lines.append(
            f"| {cat} | {len(g):,} | {int(w.sum()):,} | {wavg(g['ls_model'], w):.4f} | {wavg(g['ls_group'], w):.4f} | "
            f"{wavg(g['ls_last'], w):.4f} | {wavg((g['y'] - g['model_mean']) ** 2, w):.5f} | "
            f"{wavg((g['y'] - g['group_mean']) ** 2, w):.5f} | {wavg((g['y'] - g['last_raw']) ** 2, w):.5f} | "
            f"{wavg(g['covered80'].astype(float), w):.1%} |")
    lines += ["", "## By position group (MSE weighted by opportunities)", "",
              "| Category | Group | Player-seasons | Opportunities | MSE: model | group mean | last season raw |",
              "|---|---|---|---|---|---|---|"]
    for (cat, grp), g in df.groupby(["category", "group"]):
        w = g["n"]
        lines.append(f"| {cat} | {grp} | {len(g):,} | {int(w.sum()):,} | {wavg((g['y'] - g['model_mean']) ** 2, w):.5f} | "
                     f"{wavg((g['y'] - g['group_mean']) ** 2, w):.5f} | {wavg((g['y'] - g['last_raw']) ** 2, w):.5f} |")
    lines += ["", "## New versus returning players (model)", "",
              "| Category | Group | Player-seasons | Mean predictive sd | 80% coverage |", "|---|---|---|---|---|"]
    for (cat, hist), g in df.groupby(["category", "has_history"]):
        lines.append(f"| {cat} | {'returning' if hist else 'new'} | {len(g):,} | {g['model_var'].pow(0.5).mean():.4f} | "
                     f"{wavg(g['covered80'].astype(float), g['n']):.1%} |")
    out = REPO_ROOT / "experiments" / "p04"
    out.mkdir(parents=True, exist_ok=True)
    (out / "ability-development.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines))


@app.command("roster-eval")
def roster_eval() -> None:
    """R01: preseason roster projection versus last season's team offense (one process)."""
    from collections import defaultdict

    import pandas as pd

    from cfb.evaluation import p04, r01
    from cfb.evaluation.backtest import latest_facts
    from cfb.evaluation.protocol import load_protocol

    spec = load_protocol()
    seasons = spec["seasons"]["development"]["seasons"]
    first_ep = spec["seasons"]["warmup"]["seasons"][0]
    conn, ledger = open_store()
    states = pd.read_parquet(REPO_ROOT / "artifacts" / "plays" / "states.parquet")
    stat_seasons = list(range(2015, max(seasons) + 1))
    pos = p04.positions(ledger, stat_seasons)
    rosters: dict[int, dict[str, set[str]]] = {}
    for s in stat_seasons:
        e = ledger.latest_success("/roster", {"year": s})
        teams = defaultdict(set)
        for r in ledger.load(e) if e else []:
            if r.get("id") is not None:
                teams[r["team"]].add(str(r["id"]))
        rosters[s] = dict(teams)
    rows_raw = []
    for sch in latest_facts(conn, "game_schedule"):
        if sch["season"] in stat_seasons:
            e = ledger.latest_success("/plays/stats", {"gameId": int(sch["game_id"].split("-")[-1])})
            for r in ledger.load(e) if e else []:
                cat = p04.STAT_CATEGORY.get(r.get("statType"))
                if cat and r.get("athleteId") is not None:
                    rows_raw.append((str(r["playId"]), str(r["athleteId"]), cat, int(r["season"]), r["team"]))
    stats = pd.DataFrame(rows_raw, columns=["play_id", "athlete_id", "category", "season", "team"]).drop_duplicates(
        ["play_id", "athlete_id", "category"])

    tests = []
    for s in seasons:
        model = p04.fold_ep_model(states, s, first_ep, REPO_ROOT / "artifacts" / "models", log=typer.echo)
        st = states[states["season"].between(2015, s)]
        epa = p04.play_epa(st, model)
        rows, sigma2 = p04.player_seasons(stats[stats["season"] <= s].drop(columns="team"), epa, pos)
        offense = r01.team_offense(st, epa)
        data = r01.season_dataset(rows, stats[stats["season"] <= s], rosters, pos, sigma2, offense, s)
        tests.append(r01.calibrated_predictions(data, s))
        typer.echo(f"  season {s}: {int((data['season'] == s).sum())} teams")
    df = pd.concat(tests, ignore_index=True)
    df.to_parquet(REPO_ROOT / "artifacts" / "plays" / "roster-development.parquet", index=False)

    reps, seed = spec["comparison"]["replicates"], spec["monte_carlo"]["root_seed"]
    lines = ["# R01 roster projection: development results", "",
             (f"Seasons {seasons}, reconstructed. Target: each team's offensive EPA per play (P01 exact-tier games). "
              "Predictors are past-only and linearly calibrated on 2017 through the season before. 'roster' is the "
              "preseason roster-scenario strength (P03 shares x P04 abilities); 'naive' is last season's team EPA "
              "per play, which ignores roster turnover."), "",
             "| Season | Teams | MSE naive | MSE roster | MSE both | Corr naive | Corr roster |",
             "|---|---|---|---|---|---|---|"]
    for s, g in df.groupby("season"):
        mse = {k: float(((g["realized"] - g[f"pred_{k}"]) ** 2).mean()) for k in r01.PREDICTORS}
        lines.append(f"| {s} | {len(g)} | {mse['naive']:.5f} | {mse['roster']:.5f} | {mse['both']:.5f} | "
                     f"{g['naive'].corr(g['realized']):.3f} | {g['roster'].corr(g['realized']):.3f} |")
    mse_all = {k: float(((df["realized"] - df[f"pred_{k}"]) ** 2).mean()) for k in r01.PREDICTORS}
    lines.append(f"| All | {len(df)} | {mse_all['naive']:.5f} | {mse_all['roster']:.5f} | {mse_all['both']:.5f} | "
                 f"{df['naive'].corr(df['realized']):.3f} | {df['roster'].corr(df['realized']):.3f} |")
    lines += ["", "Paired squared-error differences (bootstrap over teams, 95% interval):", ""]
    sq = {k: (df["realized"] - df[f"pred_{k}"]) ** 2 for k in r01.PREDICTORS}
    for a, b in (("both", "naive"), ("roster", "naive")):
        m, lo, hi = r01.team_bootstrap(sq[a] - sq[b], df["team"], reps, seed)
        lines.append(f"- {a} minus {b}: {m:+.6f} [{lo:+.6f}, {hi:+.6f}]")
    lines += ["", "Calibration coefficients fit on earlier seasons (intercept, slopes):", ""]
    for s, g in df.groupby("season"):
        lines.append(f"- {s}: naive {g['coef_naive'].iloc[0]}, roster {g['coef_roster'].iloc[0]}, "
                     f"both {g['coef_both'].iloc[0]}")
    out = REPO_ROOT / "experiments" / "r01"
    out.mkdir(parents=True, exist_ok=True)
    (out / "roster-development.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines))


@app.command("transfer-eval")
def transfer_eval() -> None:
    """R02: mover-versus-stayer adaptation, support and censoring (descriptive, not causal)."""
    from collections import defaultdict

    import numpy as np
    import pandas as pd

    from cfb.evaluation import p04, r02
    from cfb.evaluation.backtest import latest_facts
    from cfb.evaluation.protocol import load_protocol

    spec = load_protocol()
    seasons = spec["seasons"]["development"]["seasons"]
    conn, ledger = open_store()
    pred = pd.read_parquet(REPO_ROOT / "artifacts" / "plays" / "ability-development.parquet")
    stat_seasons = list(range(min(seasons) - 1, max(seasons) + 1))
    rows = []
    for sch in latest_facts(conn, "game_schedule"):
        if sch["season"] in stat_seasons:
            e = ledger.latest_success("/plays/stats", {"gameId": int(sch["game_id"].split("-")[-1])})
            for r in ledger.load(e) if e else []:
                if p04.STAT_CATEGORY.get(r.get("statType")) and r.get("athleteId") is not None:
                    rows.append((str(r["athleteId"]), int(r["season"]), r["team"], str(r["playId"])))
    stats = pd.DataFrame(rows, columns=["athlete_id", "season", "team", "play_id"]).drop_duplicates()
    rosters: dict[int, dict[str, set[str]]] = {}
    for s in seasons:
        e = ledger.latest_success("/roster", {"year": s})
        teams = defaultdict(set)
        for r in ledger.load(e) if e else []:
            if r.get("id") is not None:
                teams[r["team"]].add(str(r["id"]))
        rosters[s] = dict(teams)
    tiers = r02.team_tiers(ledger, stat_seasons)
    d = r02.adaptation_table(pred, r02.main_team(stats), tiers)
    d.to_parquet(REPO_ROOT / "artifacts" / "plays" / "transfer-development.parquet", index=False)
    reps, seed = 2000, spec["monte_carlo"]["root_seed"]

    lines = ["# R02 destination and adaptation: development results", "",
             (f"Seasons {seasons}, reconstructed. **Descriptive, not causal**: players choose to move, so these gaps "
              "are associations conditional on the P04 forecast, not effects of transferring. Residual = actual "
              "season EPA per opportunity minus the P04 forecast from history before that season; gaps are movers "
              "minus stayers, weighted by opportunities, with a bootstrap over players. Players without history are "
              "excluded (no pre-move forecast)."), "",
             "## Adaptation gap by category and position", "",
             "| Category | Group | Movers | Stayers | Mover opportunities | Gap (EPA/opportunity) | 95% interval |",
             "|---|---|---|---|---|---|---|"]
    for (cat, grp), g in d.groupby(["category", "group"]):
        mv, st = g[g["mover"]], g[~g["mover"]]
        if len(mv) < 5 or len(st) < 5:
            continue
        gap, lo, hi = r02.weighted_gap(mv, st, reps, seed)
        flag = " (thin)" if len(mv) < r02.MIN_SUPPORT else ""
        lines.append(f"| {cat} | {grp} | {len(mv)}{flag} | {len(st)} | {int(mv['n'].sum()):,} | {gap:+.3f} | "
                     f"[{lo:+.3f}, {hi:+.3f}] |")
    lines += ["", "## Support by move direction (player-seasons with opportunities, all categories)", "",
              "| Direction | Player-season-categories | Opportunities | Mean residual | Support |", "|---|---|---|---|---|"]
    for direction, g in d.groupby("direction"):
        lines.append(f"| {direction} | {len(g):,} | {int(g['n'].sum()):,} | "
                     f"{np.average(g['residual'], weights=g['n']):+.3f} | "
                     f"{'thin: no comparison claimed' if len(g) < r02.MIN_SUPPORT else 'adequate'} |")
    lines += ["", "## Censoring: appearance the next season", "",
              ("Of players with opportunities in the previous season, the share with any opportunity this season. "
               "'Not on a roster' covers graduation, the draft, leaving the sport and missing roster coverage; "
               "these are distinct exits CFBD does not separate. Non-appearance is never scored as zero ability."), "",
              "| Season | Group | Appeared | Total | Share |", "|---|---|---|---|---|"]
    for s in seasons:
        for key, (hit, tot) in r02.appearance(stats, rosters, s).items():
            lines.append(f"| {s} | {key} | {hit:,} | {tot:,} | {hit / tot:.1%} |" if tot else f"| {s} | {key} | 0 | 0 | n/a |")
    out = REPO_ROOT / "experiments" / "r02"
    out.mkdir(parents=True, exist_ok=True)
    (out / "transfer-development.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines))


@app.command("decomposition-eval")
def decomposition_eval() -> None:
    """R03: forward-residual roster correction of B02 forecasts, with a double-counting ablation."""
    import json

    import pandas as pd

    from cfb.evaluation import r03
    from cfb.evaluation.backtest import block_bootstrap, latest_facts
    from cfb.evaluation.protocol import load_protocol

    spec = load_protocol()
    conn, _ = open_store()
    b02_report = json.loads((REPO_ROOT / "experiments" / "b02" / "b02-development.json").read_text(encoding="utf-8"))
    chosen = b02_report["selected"]["dynamic"]
    b02 = pd.read_parquet(REPO_ROOT / "artifacts" / "backtests" / "b02-development.parquet")
    b02 = b02[b02["config"] == chosen]
    names = dict(conn.execute("SELECT team_id, display_name FROM teams").fetchall())
    sched = {s["game_id"]: (names[s["home_team_id"]], names[s["away_team_id"]]) for s in latest_facts(conn, "game_schedule")}
    feats = r03.team_features(pd.read_parquet(REPO_ROOT / "artifacts" / "plays" / "roster-development.parquet"))
    games = r03.game_table(b02, sched, feats)
    seasons = sorted(games["season"].unique())
    df = pd.concat([r03.forward_correction(games, s) for s in seasons[1:]], ignore_index=True)

    reps, seed = spec["comparison"]["replicates"], spec["monte_carlo"]["root_seed"]
    blocks = df["season"].astype(str) + "-" + df["season_type"] + "-" + df["week"].astype(str)
    lines = ["# R03 player-informed team decomposition: development results", "",
             (f"Forward-residual correction of B02 (`{chosen}`) margin forecasts by the difference in the two teams' "
              "preseason roster offense features (R01). Fit on earlier development seasons, applied to the next "
              "(2019 -> 2020, 2019-2020 -> 2021). Reconstructed. Lower is better; differences are corrected minus "
              "B02, week-block bootstrap. Games where a team lacks a roster feature get no correction."), "",
             "| Feature | Test season | Games | Fitted beta | In-sample MSE gain | Margin MSE change | Margin CRPS change |",
             "|---|---|---|---|---|---|---|"]
    for k in r03.FEATURES:
        for s, g in df.groupby("season"):
            lines.append(f"| {k} | {s} | {len(g)} | {g[f'beta_{k}'].iloc[0]:+.2f} | {g[f'train_gain_{k}'].iloc[0]:+.3f} | "
                         f"{(g[f'sq_{k}'] - g['sq_base']).mean():+.3f} | {(g[f'crps_{k}'] - g['crps_base']).mean():+.4f} |")
    lines += ["", "Pooled over test seasons (95% interval):", ""]
    for k in r03.FEATURES:
        m, lo, hi = block_bootstrap(df[f"crps_{k}"] - df["crps_base"], blocks, reps, seed)
        lines.append(f"- {k}: margin CRPS change {m:+.4f} [{lo:+.4f}, {hi:+.4f}]")
    covered = float((games["raw_diff"] != 0).mean())
    lines += ["", f"Games with a roster feature for both teams: {covered:.1%}."]
    out = REPO_ROOT / "experiments" / "r03"
    out.mkdir(parents=True, exist_ok=True)
    (out / "decomposition-development.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines))


@app.command("build-states")
def build_states(start: int = typer.Option(2014), end: int = typer.Option(2025),
                 workers: int = typer.Option(0, help="Worker processes (0 = CPU count - 1)")) -> None:
    """P01: per-play preplay states and next-score labels for exact-tier games."""
    import pandas as pd

    from cfb.evaluation.backtest import parallel_map
    from cfb.state.table import LABELS, season_states

    results = parallel_map(season_states, list(range(start, end + 1)), workers or None)
    df = pd.concat([r[0] for r in results if len(r[0])], ignore_index=True)
    out = REPO_ROOT / "artifacts" / "plays"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "states.parquet", index=False)

    def rate(t: dict, ok: str, n: str) -> str:
        return f"{t[ok] / t[n]:.1%}" if t.get(n) else "n/a"

    lines = ["# P01 preplay states and transition checks", "",
             ("Scrimmage plays in regulation of games whose scoring reconciles exactly. Transition checks compare "
              "consecutive scrimmage rows of one possession (plays with a penalty in the text are not checked for "
              "down and yards). They describe CFBD's consistency; no play is dropped for failing one."), "",
             ("| Season | Exact games | Plays | Down carries | Yards carry | Clock order | Kickoff after score | "
              "Half opens with kickoff |"), "|---|---|---|---|---|---|---|---|"]
    for season, (frame, t) in zip(range(start, end + 1), results, strict=True):
        lines.append(f"| {season} | {t['exact_games']} | {len(frame)} | {rate(t, 'down_ok', 'down_checked')} | "
                     f"{rate(t, 'yards_ok', 'yards_checked')} | {rate(t, 'clock_ok', 'clock_checked')} | "
                     f"{rate(t, 'kickoff_after_score_ok', 'score_checked')} | "
                     f"{rate(t, 'half_starts_with_kickoff', 'halves')} |")
    shares = df["next_score"].value_counts(normalize=True)
    lines += ["", "## Next-score labels (all seasons)", "", "| Label | Share |", "|---|---|"]
    lines += [f"| {lab} | {shares.get(lab, 0):.1%} |" for lab in LABELS]
    rep = REPO_ROOT / "experiments" / "p01"
    rep.mkdir(parents=True, exist_ok=True)
    (rep / f"state-checks-{start}-{end}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines[4:]))
    typer.echo(f"{len(df):,} states written to artifacts/plays/states.parquet")


@app.command()
def quality(start: int = typer.Option(2014), end: int = typer.Option(2025)) -> None:
    """D08: per-game score/coverage flags and quarantine per model family (cached data only)."""
    from collections import Counter

    from cfb.canonical.games import game_id
    from cfb.canonical.quality import FAMILIES, assess

    conn, ledger = open_store()
    df = assess(conn, ledger, list(range(start, end + 1)))
    out = REPO_ROOT / "artifacts" / "quality"
    out.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out / "game_quality.parquet", index=False)

    fams = list(FAMILIES)
    lines = ["# D08 game quality flags", "",
             f"Population games {start}-{end}: {len(df)}. Flags come from canonical results, cached "
             "drives and team stats. A game is quarantined for a model family if it has any of that "
             "family's flags: " + "; ".join(f"`{f}`: {', '.join(FAMILIES[f])}" for f in fams) + ".", "",
             "| Season | Games | " + " | ".join(f"Quarantined: {f}" for f in fams) + " |",
             "|---|---|" + "---|" * len(fams)]
    for season, g in df.groupby("season"):
        lines.append(f"| {season} | {len(g)} | " + " | ".join(str(int(g[f'quarantine_{f}'].sum())) for f in fams) + " |")
    lines.append(f"| All | {len(df)} | " + " | ".join(str(int(df[f'quarantine_{f}'].sum())) for f in fams) + " |")
    counts = Counter(f for fl in df["flags"] for f in fl)
    lines += ["", "## Flag counts (a game can have several)", "", "| Flag | Games |", "|---|---|"]
    lines += [f"| `{f}` | {n} |" for f, n in counts.most_common()]
    checks = {401634301: "2024 California-UC Davis (D02: play-by-play stops in Q3)",
              401636616: "2024 Tulane-Kansas State (D02: corrupt mid-game drive score)",
              401628468: "2024 Ohio State-Western Michigan (D02: TD drive +8, final 56-0)"}
    lines += ["", "## Spot checks from D02", "", "| Game | Flags | Team-score | Play-derived |", "|---|---|---|---|"]
    by_id = df.set_index("game_id")
    for cid, label in checks.items():
        if game_id(cid) in by_id.index:
            r = by_id.loc[game_id(cid)]
            lines.append(f"| {label} | {', '.join(r['flags']) or 'none'} | "
                         f"{'quarantined' if r['quarantine_team_score'] else 'kept'} | "
                         f"{'quarantined' if r['quarantine_play_derived'] else 'kept'} |")
    report = REPO_ROOT / "experiments" / "d08"
    report.mkdir(parents=True, exist_ok=True)
    (report / f"quality-{start}-{end}.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo("\n".join(lines[4:4 + len(df["season"].unique()) + 3]))
    typer.echo(f"wrote experiments/d08/quality-{start}-{end}.md and artifacts/quality/game_quality.parquet")


@app.command("build-snapshot")
def build_snapshot_cmd(
    cutoff: str = typer.Option(..., help="UTC cutoff, e.g. 2019-09-06T16:00:00Z"),
    mode: str = typer.Option("strict", help="strict or reconstructed"),
) -> None:
    """D07: build (or return) the sealed snapshot for a cutoff."""
    from datetime import datetime

    from cfb.snapshots.builder import build_snapshot

    conn, _ = open_store()
    snap = build_snapshot(conn, datetime.fromisoformat(cutoff), mode, REPO_ROOT / "artifacts" / "snapshots")
    typer.echo(f"{snap.snapshot_id} {snap.cutoff} {snap.mode}: {len(snap.record_version_ids)} facts")


@app.command()
def backtest(
    stage: str = typer.Option("b01", help="Backtest stage (b01 or b02)"),
    workers: int = typer.Option(0, help="Worker processes (0 = CPU count - 1)"),
) -> None:
    """B01: forward evaluation of the baselines on the development seasons only."""
    import time

    from cfb.evaluation import b01
    from cfb.evaluation.backtest import latest_facts, prepare_tasks, run_tasks, to_frame
    from cfb.evaluation.cohorts import label_cohorts
    from cfb.evaluation.protocol import load_protocol

    if stage not in ("b01", "b02"):
        typer.echo(f"unknown stage {stage!r}", err=True)
        raise typer.Exit(code=2)
    spec = load_protocol()
    seasons = spec["seasons"]["development"]["seasons"]
    conn, ledger = open_store()
    if stage == "b02":
        _backtest_b02(spec, seasons, conn, ledger, workers)
        return
    configs = b01.grid_configs()
    typer.echo(f"{len(configs)} configurations x development seasons {seasons}")
    t0 = time.perf_counter()
    tasks = prepare_tasks(conn, spec, seasons, configs, REPO_ROOT / "artifacts" / "snapshots", log=typer.echo)
    t1 = time.perf_counter()
    df = run_tasks(tasks, workers or None)
    t2 = time.perf_counter()
    typer.echo(f"snapshots {t1 - t0:.1f}s; fit+simulate+score {t2 - t1:.1f}s; {len(df)} game forecasts")

    art = REPO_ROOT / "artifacts" / "backtests"
    art.mkdir(parents=True, exist_ok=True)
    df.to_parquet(art / "b01-development.parquet", index=False)

    results = {r["game_id"]: r for r in latest_facts(conn, "game_result")}
    sched = [s for s in latest_facts(conn, "game_schedule") if s["season"] in seasons]
    games = to_frame(sched, results).rename(columns={"hp": "home_points", "ap": "away_points"})
    cohorts = label_cohorts(games, ledger)
    rep = b01.report(df, cohorts, spec)
    j, m = b01.write(rep, REPO_ROOT / "experiments" / "b01")
    typer.echo(f"selected: {rep['selected']}")
    typer.echo(f"wrote {m.relative_to(REPO_ROOT)} and {j.name}")


def _backtest_b02(spec, seasons, conn, ledger, workers) -> None:
    import time

    import pandas as pd

    from cfb.evaluation import b01, b02
    from cfb.evaluation.backtest import latest_facts, prepare_tasks, to_frame
    from cfb.evaluation.cohorts import label_cohorts

    lag = spec["replay"]["reconstructed_result_available_after_kickoff_hours"]
    t0 = time.perf_counter()
    tasks = prepare_tasks(conn, spec, seasons, [], REPO_ROOT / "artifacts" / "snapshots", log=typer.echo)
    t1 = time.perf_counter()
    df = b02.run_grid(tasks, lag, workers or None)
    t2 = time.perf_counter()
    typer.echo(f"{len(b02.grid_configs())} configurations; snapshots {t1 - t0:.1f}s; "
               f"filter+simulate+score {t2 - t1:.1f}s; {len(df)} game forecasts")
    art = REPO_ROOT / "artifacts" / "backtests"
    art.mkdir(parents=True, exist_ok=True)
    df.to_parquet(art / "b02-development.parquet", index=False)
    b01_rows = pd.read_parquet(art / "b01-development.parquet")
    combined = pd.concat([b01_rows, df], ignore_index=True)

    results = {r["game_id"]: r for r in latest_facts(conn, "game_result")}
    sched = [s for s in latest_facts(conn, "game_schedule") if s["season"] in seasons]
    games = to_frame(sched, results).rename(columns={"hp": "home_points", "ap": "away_points"})
    rep = b01.report(combined, label_cohorts(games, ledger), spec, stage="B02", grid_pass=1,
                     pairs=b02.PAIRS, sensitivity_pairs=b02.SENSITIVITY_PAIRS)
    j, m = b01.write(rep, REPO_ROOT / "experiments" / "b02")
    typer.echo(f"selected: {rep['selected']}")
    typer.echo(f"wrote {m.relative_to(REPO_ROOT)} and {j.name}")


@app.command("record-forecasts")
def record_forecasts(
    stage: str = typer.Option("b01", help="Stage whose selected models to record (b01)"),
    workers: int = typer.Option(0, help="Worker processes (0 = CPU count - 1)"),
    replay_sample: int = typer.Option(50, help="Stored forecasts to replay-check afterwards"),
) -> None:
    """B03: immutable forecast, winner-pick, outcome and evaluation records for the
    development seasons. Rerunning records nothing new."""
    import json
    import random

    from cfb.evaluation.backtest import Config, prepare_tasks
    from cfb.evaluation.protocol import load_protocol
    from cfb.operations.records import lock_hash, record_runs, replay_check

    if stage != "b01":
        typer.echo(f"unknown stage {stage!r}", err=True)
        raise typer.Exit(code=2)
    spec = load_protocol()
    report = json.loads((REPO_ROOT / "experiments" / "b01" / "b01-development.json").read_text(encoding="utf-8"))
    configs = [Config.from_label(label) for label in report["selected"].values()]
    seasons = spec["seasons"]["development"]["seasons"]
    conn, _ = open_store()
    tasks = prepare_tasks(conn, spec, seasons, configs, REPO_ROOT / "artifacts" / "snapshots", log=typer.echo)
    art = REPO_ROOT / "artifacts"
    summary = record_runs(conn, tasks, configs, stage="B01", dep_lock=lock_hash(REPO_ROOT / "uv.lock"),
                          artifact_dir=art, evaluation_class=spec["replay"]["historical_class"],
                          workers=workers or None)
    typer.echo(f"runs: {summary}")
    for table in ("model_runs", "forecast_summaries", "decision_records", "outcome_versions", "evaluation_results"):
        typer.echo(f"  {table}: {conn.execute(f'SELECT count(*) FROM {table}').fetchone()[0]} rows")

    rows = conn.execute("SELECT forecast_id, model_version FROM forecast_summaries JOIN model_runs USING(run_id)").fetchall()
    sample = random.Random(spec["monte_carlo"]["root_seed"]).sample(rows, min(replay_sample, len(rows)))
    ok = sum(replay_check(conn, art, fid, spec["monte_carlo"]["root_seed"], spec["protocol_version"],
                          mv.split(":")[1].split("|")[0], spec["monte_carlo"]["draws_per_game"])
             for fid, mv in sample)
    typer.echo(f"replay check: {ok}/{len(sample)} forecasts reproduce their samples hash and winner pick")
    raise typer.Exit(code=0 if ok == len(sample) else 1)


@app.command()
def protocol(
    freeze: bool = typer.Option(False, help="Freeze the draft protocol (irreversible for this version)"),
) -> None:
    """V01: validate config/protocol.json and count folds and scored games from cached CFBD data."""
    import sqlite3

    from cfb.evaluation import protocol as proto
    from cfb.ingestion.coverage import game_scores

    try:
        if freeze:
            record = proto.freeze_protocol()
            typer.echo(f"froze {record['protocol_id']} sha256={record['protocol_sha256']}")
        spec = proto.load_protocol()
    except proto.ProtocolError as exc:
        typer.echo(f"[FAIL] protocol: {exc}", err=True)
        raise typer.Exit(code=1) from None
    typer.echo(f"{spec['protocol_id']} v{spec['protocol_version']}: {spec['status']}, "
               f"sha256={proto.protocol_hash(spec)[:16]}")

    ledger_path = DATA_DIR / "ledger.sqlite"
    if not ledger_path.exists():
        typer.echo("no cached CFBD data; run `cfb audit-coverage` for fold counts")
        return
    conn = sqlite3.connect(f"file:{ledger_path.as_posix()}?mode=ro", uri=True)
    ledger = RawLedger(DATA_DIR / "raw", conn)
    horizon = spec["products"]["primary"]["horizon_minutes"]
    typer.echo(f"primary horizon {horizon} min; replay class {spec['replay']['historical_class']}")
    typer.echo("season  role         folds  scored games  TBD kickoffs")
    for role, _ in proto.ROLES:
        for season in spec["seasons"][role]["seasons"]:
            entries = [ledger.latest_success(p, q) for p, q in [("/teams/fbs", {"year": season})] + [
                ("/games", {"year": season, "seasonType": st}) for st in ("regular", "postseason")]]
            if any(e is None for e in entries):
                typer.echo(f"{season}    {role:<12} not cached")
                continue
            fbs = {t["id"] for t in ledger.load(entries[0])}
            games = [g for e in entries[1:] for g in ledger.load(e)
                     if (g.get("homeId") in fbs or g.get("awayId") in fbs)
                     and g.get("completed") and game_scores(g) is not None]
            folds = proto.build_folds(spec, season, games, horizon)
            n_games = sum(len(f.game_ids) for f in folds) if folds else len(games)
            n_tbd = sum(len(f.tbd_game_ids) for f in folds)
            label = "-" if role not in proto.SCORED_ROLES else str(len(folds))
            typer.echo(f"{season}    {role:<12} {label:>5}  {n_games:>12}  {n_tbd:>12}")


if __name__ == "__main__":
    app()
