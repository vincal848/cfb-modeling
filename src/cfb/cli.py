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
