"""D02: season-level coverage matrix for the core families.

The population is games involving an FBS team. FBS membership comes from
`/teams/fbs` for that season, not from per-game classification (which can be
null). Every share has an explicit denominator.

When a request fails, its partition is reported as unavailable, never as zero
coverage.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cfb.ingestion.fetch import Fetcher

SEASON_TYPES = ("regular", "postseason")


def game_scores(game: dict[str, Any]) -> tuple[int, int] | None:
    h, a = game.get("homePoints"), game.get("awayPoints")
    return (h, a) if h is not None and a is not None else None


def reduce_drives(drives: list[dict[str, Any]]) -> dict[int, tuple[int, int, int, int]]:
    """gameId -> (drive count, home final, away final, last period) from the last drive.

    The last drive by `driveNumber` is used rather than the maximum score seen, because a
    single corrupt mid-game score (observed in 2024 CFBD drives) would otherwise mark a
    game whose play-by-play ends at the right score as a mismatch.
    """
    count: dict[int, int] = {}
    last: dict[int, dict[str, Any]] = {}
    for d in drives:
        gid = d["gameId"]
        count[gid] = count.get(gid, 0) + 1
        if gid not in last or (d.get("driveNumber") or 0) >= (last[gid].get("driveNumber") or 0):
            last[gid] = d
    out: dict[int, tuple[int, int, int, int]] = {}
    for gid, d in last.items():
        off, dfn = d.get("endOffenseScore"), d.get("endDefenseScore")
        if off is None or dfn is None or d.get("isHomeOffense") is None:
            home, away = -1, -1  # unknown; never equals a real score
        else:
            home, away = (off, dfn) if d["isHomeOffense"] else (dfn, off)
        out[gid] = (count[gid], home, away, d.get("endPeriod") or 0)
    return out


def classify_drive_mismatch(drive: tuple[int, int, int, int], final: tuple[int, int]) -> str:
    """Why the last drive's score differs from the official final score."""
    _, home, away, period = drive
    if (home, away) == final:
        return "match"
    if period < 4:
        return "pbp_ends_before_q4"
    if home <= final[0] and away <= final[1]:
        return "pbp_short_of_final"
    return "pbp_over_or_mixed"


def reduce_plays(plays: list[dict[str, Any]]) -> dict[int, tuple[int, int, int]]:
    """gameId -> (play count, max home score, max away score) seen on any play."""
    out: dict[int, list[int]] = {}
    for p in plays:
        g = out.setdefault(p["gameId"], [0, 0, 0])
        g[0] += 1
        off, dfn = p.get("offenseScore"), p.get("defenseScore")
        if off is None or dfn is None:
            continue
        if p.get("offense") == p.get("home"):
            home, away = off, dfn
        elif p.get("defense") == p.get("home"):
            home, away = dfn, off
        else:
            continue
        g[1], g[2] = max(g[1], home), max(g[2], away)
    return {k: tuple(v) for k, v in out.items()}


@dataclass
class SeasonInputs:
    season: int
    fbs_ids: set[int]
    games: list[dict[str, Any]]
    lines: list[dict[str, Any]]
    team_stat_ids: set[int] = field(default_factory=set)
    drives: dict[int, tuple[int, int, int, int]] = field(default_factory=dict)
    plays: dict[int, tuple[int, int, int]] = field(default_factory=dict)
    failed_partitions: list[str] = field(default_factory=list)


def _share(n: int, d: int) -> float | None:
    return round(n / d, 4) if d else None


def summarize_season(x: SeasonInputs) -> dict[str, Any]:
    pop = [g for g in x.games if g.get("homeId") in x.fbs_ids or g.get("awayId") in x.fbs_ids]
    scored = [g for g in pop if g.get("completed") and game_scores(g) is not None]
    scored_ids = {g["id"] for g in scored}
    by_id = {g["id"]: g for g in scored}
    lines_by_id = {g["id"]: g.get("lines") or [] for g in x.lines}

    def reconcile(reduced: dict[int, tuple[int, ...]]) -> tuple[int, int]:
        have = [gid for gid in scored_ids if reduced.get(gid, (0,))[0] > 0]
        match = sum(reduced[gid][1:3] == game_scores(by_id[gid]) for gid in have)
        return len(have), match

    n_drv, drv_match = reconcile(x.drives)
    n_ply, ply_match = reconcile(x.plays)
    drive_mismatch = Counter(
        classify_drive_mismatch(x.drives[gid], game_scores(by_id[gid]))
        for gid in scored_ids if x.drives.get(gid, (0,))[0] > 0
    )
    drive_mismatch.pop("match", None)
    with_lines = [gid for gid in scored_ids if lines_by_id.get(gid)]
    books = Counter(len(lines_by_id.get(gid, [])) for gid in scored_ids)

    def any_line(gid: int, key: str) -> bool:
        return any(ln.get(key) is not None for ln in lines_by_id.get(gid, []))

    n = len(scored)
    return {
        "season": x.season,
        "fbs_teams": len(x.fbs_ids),
        "games_fbs_involving": len(pop),
        "postseason_games": sum(g.get("seasonType") == "postseason" for g in pop),
        "fbs_vs_nonfbs": sum((g.get("homeId") in x.fbs_ids) != (g.get("awayId") in x.fbs_ids) for g in pop),
        "null_classification": sum(
            g.get("homeClassification") is None or g.get("awayClassification") is None for g in pop
        ),
        "not_completed_or_unscored": len(pop) - n,
        "start_time_tbd": sum(bool(g.get("startTimeTBD")) for g in pop),
        "scored_games": n,
        "team_stats_share": _share(len(scored_ids & x.team_stat_ids), n),
        "drives_share": _share(n_drv, n),
        "drive_score_match_share": _share(drv_match, n_drv),
        "drive_mismatch_kinds": dict(sorted(drive_mismatch.items())),
        "pbp_ends_before_q4": drive_mismatch.get("pbp_ends_before_q4", 0),
        "plays_share": _share(n_ply, n),
        "play_score_match_share": _share(ply_match, n_ply),
        "lines_share": _share(len(with_lines), n),
        "spread_share": _share(sum(any_line(g, "spread") for g in scored_ids), n),
        "spread_open_share": _share(sum(any_line(g, "spreadOpen") for g in scored_ids), n),
        "moneyline_share": _share(sum(any_line(g, "homeMoneyline") for g in scored_ids), n),
        "books_per_game": dict(sorted(books.items())),
        "failed_partitions": x.failed_partitions,
    }


def _get(fetcher: Fetcher, path: str, params: dict[str, Any], failed: list[str]) -> list[Any] | None:
    entry, _ = fetcher.fetch(path, params, bulk=True)
    if entry.http_status != 200:
        failed.append(f"{path} {json.dumps(params, sort_keys=True)} -> {entry.http_status}")
        return None
    return fetcher.ledger.load(entry)


def collect_season(fetcher: Fetcher, season: int, log=print) -> SeasonInputs:
    failed: list[str] = []
    fbs = _get(fetcher, "/teams/fbs", {"year": season}, failed) or []
    calendar = _get(fetcher, "/calendar", {"year": season}, failed) or []
    games: list[dict[str, Any]] = []
    lines: list[dict[str, Any]] = []
    for st in SEASON_TYPES:
        games += _get(fetcher, "/games", {"year": season, "seasonType": st}, failed) or []
        lines += _get(fetcher, "/lines", {"year": season, "seasonType": st}, failed) or []
    x = SeasonInputs(season, {t["id"] for t in fbs}, games, lines, failed_partitions=failed)
    for wk in calendar:
        p = {"year": season, "week": wk["week"], "seasonType": wk["seasonType"]}
        ts = _get(fetcher, "/games/teams", p, failed)
        x.team_stat_ids |= {g["id"] for g in ts or []}
        x.drives.update(reduce_drives(_get(fetcher, "/drives", p, failed) or []))
        x.plays.update(reduce_plays(_get(fetcher, "/plays", p, failed) or []))
        log(f"  {season} {wk['seasonType']} wk{wk['week']} (remaining {fetcher.guard.remaining})")
    return x


COLUMNS = [
    ("season", "Season"), ("games_fbs_involving", "FBS games"), ("scored_games", "Scored"),
    ("not_completed_or_unscored", "Unscored"), ("team_stats_share", "Team stats"),
    ("drives_share", "Drives"), ("drive_score_match_share", "Drive=final"),
    ("pbp_ends_before_q4", "PBP ends <Q4"),
    ("plays_share", "Plays"), ("play_score_match_share", "Play=final"),
    ("lines_share", "Lines"), ("spread_open_share", "Open spread"),
    ("moneyline_share", "Moneyline"), ("start_time_tbd", "TBD kick"),
]


def render_markdown(report: dict[str, Any]) -> str:
    def fmt(v: Any) -> str:
        if v is None:
            return "n/a"
        return f"{v:.1%}" if isinstance(v, float) else str(v)

    out = [
        f"# D02 coverage matrix ({report['provider']})",
        "",
        (f"Generated {report['generated_at']}. Population: games with at least one team in "
        "that season's `/teams/fbs`. Shares are over scored games (completed, both scores "
        "present) unless the column says otherwise. 'Drive=final' and 'Play=final' are "
        "computed over games that have drives or plays respectively. 'Drive=final' uses the "
        "last drive's end score; 'Play=final' uses the maximum score on any play, so a single "
        "corrupt play score counts as a mismatch there. Drives and plays come from the same "
        "play-by-play feed, so they are not independent checks."),
        "",
        "| " + " | ".join(h for _, h in COLUMNS) + " |",
        "|" + "---|" * len(COLUMNS),
    ]
    for s in report["seasons"]:
        out.append("| " + " | ".join(fmt(s[k]) for k, _ in COLUMNS) + " |")
    failed = [f for s in report["seasons"] for f in s["failed_partitions"]]
    out += ["", f"Failed partitions (reported unavailable, not zero): {len(failed)}"]
    out += [f"- `{f}`" for f in failed]
    return "\n".join(out) + "\n"


def run_coverage(fetcher: Fetcher, seasons: list[int], log=print) -> dict[str, Any]:
    rows = []
    for s in seasons:
        log(f"season {s}")
        rows.append(summarize_season(collect_season(fetcher, s, log)))
    return {
        "audit": "D02_coverage_matrix",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider": fetcher.ledger.provider,
        "calls_remaining_after": fetcher.guard.remaining,
        "seasons": rows,
    }


def write_report(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    years = [s["season"] for s in report["seasons"]]
    stem = f"coverage-{min(years)}-{max(years)}"
    jpath, mpath = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    jpath.write_text(json.dumps(report, indent=2), encoding="utf-8")
    mpath.write_text(render_markdown(report), encoding="utf-8")
    return jpath, mpath
