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


if __name__ == "__main__":
    app()
