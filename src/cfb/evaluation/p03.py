"""P03: opportunity-share evaluation on the V01 development seasons.

For every team-game-category in a development season, shares are forecast from earlier
games of the season, the previous season and the season's roster, then scored on the
game's realized allocation: per-opportunity log score (new players and unassigned
opportunities count against the UNKNOWN group) and participation log loss for candidates.

The grid is fixed before results; selection on the same development games makes the
selected scores optimistic, as in B01. Runs in one process.
"""

from __future__ import annotations

import itertools
import json
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from cfb.ingestion.ledger import LedgerEntry, RawLedger
from cfb.models.opportunity import (
    CATEGORIES,
    UNKNOWN,
    ShareParams,
    forecast_shares,
    log_score,
    player_counts,
    team_totals,
)

# Pass 2. Pass 1 (half-life 2/4/8, prior weight 0.25/0.5/1, alpha 0.1/0.5, kappa 1/3) selected
# the shortest half-life, smallest alpha and largest kappa, and lost to copying last game on
# share log score (1.555 vs 1.503). This grid widens past those edges once; no further pass.
GRID = {"half_life_games": [0.5, 1.0, 2.0], "prior_season_weight": [0.1, 0.25, 0.5],
        "alpha": [0.01, 0.03, 0.1], "kappa": [3.0, 6.0, 12.0]}
LAST_GAME_UNKNOWN_FLOOR = 0.02  # baseline: unknown share when copying the previous game
PARTICIPATION_GRID = {"half_life_games": [1.0, 2.0, 4.0], "strength": [1.0, 3.0]}
KNOWN_PLAYER_FLOOR = 0.005  # baseline: share for a known player absent from the previous game


def _load(ledger: RawLedger, row: tuple) -> Any:
    return ledger.load(LedgerEntry(*row[:7], bool(row[7]), *row[8:]))


@dataclass
class TeamSeries:
    """One team's games in a season (kickoff order) for one category."""

    games: list[str]
    counts: list[dict[str, int]]  # attributed per athlete
    unassigned: list[int]
    totals: list[int]
    prior_shares: dict[str, float]  # last-season shares of this season's roster players


def season_series(conn: sqlite3.Connection, ledger: RawLedger, season: int) -> dict[tuple[str, str], TeamSeries]:
    """(team, category) -> TeamSeries for every FBS-population game of `season`."""
    from cfb.evaluation.backtest import latest_facts

    sched = sorted((s for s in latest_facts(conn, "game_schedule") if s["season"] == season),
                   key=lambda s: (s["start_utc"], s["game_id"]))
    ids = [int(s["game_id"].split("-")[-1]) for s in sched]
    stats, plays = [], []
    for gid in ids:
        e = ledger.latest_success("/plays/stats", {"gameId": gid})
        if e is not None and e.http_status == 200:
            stats.extend(ledger.load(e))
    cal = ledger.latest_success("/calendar", {"year": season})
    for wk in ledger.load(cal) if cal else []:
        e = ledger.latest_success("/plays", {"year": season, "week": wk["week"], "seasonType": wk["seasonType"]})
        plays.extend(p for p in (ledger.load(e) if e else []) if p["gameId"] in set(ids))
    if not stats:
        return {}
    counts = player_counts(pd.DataFrame(stats))
    totals = team_totals(pd.DataFrame(plays))
    have_stats = set(pd.DataFrame(stats)["gameId"])

    prior = _prior_shares(conn, ledger, season)
    roster = defaultdict(set)
    e = ledger.latest_success("/roster", {"year": season})
    for r in ledger.load(e) if e else []:
        if r.get("id") is not None:
            roster[r["team"]].add(str(r["id"]))

    cnt = defaultdict(lambda: defaultdict(dict))
    for r in counts.itertuples(index=False):
        cnt[(r.team, r.category)][r.game_id][str(r.athlete_id)] = int(r.n)
    tot = {(r.game_id, r.team, r.category): int(r.total) for r in totals.itertuples(index=False)}
    out: dict[tuple[str, str], TeamSeries] = {}
    order = {gid: i for i, gid in enumerate(ids)}
    teams = {t for (_, t, _) in tot}
    for team in teams:
        for cat in CATEGORIES:
            games = sorted({g for (g, t, c) in tot if t == team and c == cat and g in have_stats}, key=order.get)
            series = TeamSeries([], [], [], [], {a: s for a, s in prior.get(cat, {}).items() if a in roster[team]})
            for g in games:
                attributed = cnt[(team, cat)].get(g, {})
                total = max(tot[(g, team, cat)], sum(attributed.values()))
                series.games.append(f"cfbd-game-{g}")
                series.counts.append(attributed)
                series.unassigned.append(total - sum(attributed.values()))
                series.totals.append(total)
            if games:
                out[(team, cat)] = series
    return out


def _prior_shares(conn, ledger, season: int) -> dict[str, dict[str, float]]:
    """category -> athlete -> share of his team's attributed opportunities last season."""
    prev = season_series_counts(conn, ledger, season - 1)
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for (team, cat), by_athlete in prev.items():
        total = sum(by_athlete.values())
        for aid, n in by_athlete.items():
            out[cat][aid] = max(out[cat].get(aid, 0.0), n / total)
    return out


def season_series_counts(conn, ledger, season: int) -> dict[tuple[str, str], dict[str, int]]:
    from cfb.evaluation.backtest import latest_facts

    ids = [int(s["game_id"].split("-")[-1]) for s in latest_facts(conn, "game_schedule") if s["season"] == season]
    stats = []
    for gid in ids:
        e = ledger.latest_success("/plays/stats", {"gameId": gid})
        if e is not None and e.http_status == 200:
            stats.extend(ledger.load(e))
    if not stats:
        return {}
    out: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for r in player_counts(pd.DataFrame(stats)).itertuples(index=False):
        out[(r.team, r.category)][str(r.athlete_id)] += int(r.n)
    return out


def candidates(history: list[dict[str, int]], prior: dict[str, float]) -> set[str]:
    """Players known before the game: earlier opportunities this season, or a prior-season
    share and a place on this season's roster. Fixed before the game and the same for every
    model, so all models are scored over the same outcomes."""
    return {a for game in history for a in game} | set(prior)


def on_partition(shares: dict[str, float], known: set[str], floor: float) -> dict[str, float]:
    """Give every known player at least `floor` (taken proportionally from the rest), so a
    model cannot gain by leaving a known player inside UNKNOWN."""
    out = dict(shares)
    missing = [a for a in known if a not in out]
    if missing:
        take = floor * len(missing)
        out = {k: v * (1 - take) for k, v in out.items()}
        out.update(dict.fromkeys(missing, floor))
    return out


def last_game_shares(history: list[dict[str, int]], unassigned: list[int], prior: dict[str, float]) -> dict[str, float]:
    """Baseline: copy the previous game's allocation (prior-season shares before game 1).
    The evaluation then gives known players absent from that game a small floor."""
    if history:
        base = {a: float(n) for a, n in history[-1].items()}
        base_unknown = float(unassigned[-1])
    else:
        base, base_unknown = dict(prior), 0.0
    total = sum(base.values()) + base_unknown
    shares = {a: v / total for a, v in base.items()} if total else {}
    unknown = (base_unknown / total if total else 1.0)
    unknown = max(unknown, LAST_GAME_UNKNOWN_FLOOR)
    scale = (1 - unknown) / max(sum(shares.values()), 1e-12) if shares else 0.0
    out = {a: s * scale for a, s in shares.items()}
    out[UNKNOWN] = unknown if shares else 1.0
    return out


def evaluate(series: dict[tuple[str, str], TeamSeries], params: ShareParams | None, season: int) -> list[dict]:
    rows = []
    for (team, cat), s in series.items():
        for i, game in enumerate(s.games):
            hist, un = s.counts[:i], s.unassigned[:i]
            known = candidates(hist, s.prior_shares)
            shares = (forecast_shares(hist, un, s.prior_shares, params) if params is not None
                      else on_partition(last_game_shares(hist, un, s.prior_shares), known, KNOWN_PLAYER_FLOOR))
            # Scored over known players plus UNKNOWN (new players and unassigned): the same
            # outcomes for every model.
            loss, n = log_score(shares, s.counts[i], s.unassigned[i])
            total = s.totals[i]
            p_any_loss, p_any_n = 0.0, 0
            for aid in known:
                sh = shares[aid]
                p = min(max(1 - (1 - sh) ** total, 1e-9), 1 - 1e-9)
                got = s.counts[i].get(aid, 0) > 0
                p_any_loss -= np.log(p if got else 1 - p)
                p_any_n += 1
            rows.append({"season": season, "team": team, "category": cat, "game_id": game, "opportunities": n,
                         "log_score_sum": loss, "participation_loss_sum": p_any_loss, "candidates": p_any_n,
                         "conservation_error": abs(sum(sh * total for sh in shares.values()) - total)})
    return rows


def grid() -> list[ShareParams]:
    keys = sorted(GRID)
    return [ShareParams(**dict(zip(keys, v, strict=True))) for v in itertools.product(*(GRID[k] for k in keys))]


def label(p: ShareParams | None) -> str:
    if p is None:
        return "last_game"
    return (f"shares|half_life={p.half_life_games:g}|prior_w={p.prior_season_weight:g}|"
            f"alpha={p.alpha:g}|kappa={p.kappa:g}")


def summarize(rows: pd.DataFrame) -> pd.DataFrame:
    g = rows.groupby("config")
    return pd.DataFrame({
        "opportunities": g["opportunities"].sum(),
        "log_score": g["log_score_sum"].sum() / g["opportunities"].sum(),
        "participation_log_loss": g["participation_loss_sum"].sum() / g["candidates"].sum(),
        "max_conservation_error": g["conservation_error"].max(),
    }).sort_values("log_score")


def to_json(obj) -> str:
    return json.dumps(obj, default=float)


def evaluate_participation(series: dict, season: int, half_life: float | None, strength: float | None) -> list[dict]:
    """Participation log loss over known players. `half_life=None` is the baseline: the
    player's indicator in the previous game, clipped to [0.05, 0.95]."""
    from cfb.models.opportunity import participation_probs

    rows = []
    for (team, cat), s in series.items():
        for i in range(len(s.games)):
            hist = s.counts[:i]
            known = candidates(hist, s.prior_shares)
            if not known:
                continue
            if half_life is None:
                last = hist[-1] if hist else {}
                probs = {a: 0.95 if last.get(a, 0) > 0 else 0.05 for a in known}
            else:
                probs = participation_probs(hist, s.prior_shares, known, half_life, strength)
            loss = 0.0
            for a, p in probs.items():
                p = min(max(p, 1e-9), 1 - 1e-9)
                loss -= np.log(p if s.counts[i].get(a, 0) > 0 else 1 - p)
            rows.append({"season": season, "category": cat, "players": len(probs), "loss_sum": loss})
    return rows
