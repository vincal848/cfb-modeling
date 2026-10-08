"""W01 power gate: how many outdoor, windy games with a closing total have a bet-time forecast archive?
(experiments/protocols/W01-protocol.md). Counts only; no total is compared with any wind figure.

    uv run python -m cfb.evaluation.w01
"""

from __future__ import annotations

import json

SEASONS, WIND_MPH, NEEDED = (2024, 2025), 15.0, 860
WEEKS = {"regular": range(1, 16), "postseason": (1,)}


def windy_counts(weather: list[dict], totals: set[int]) -> dict:
    """Outdoor games with wind >= WIND_MPH that have a closing total (`totals` = CFBD game ids)."""
    outdoor = [w for w in weather if w.get("gameIndoors") is False and w.get("windSpeed") is not None]
    windy = [w for w in outdoor if w["windSpeed"] >= WIND_MPH]
    return {"outdoor_with_wind": len(outdoor), "windy": len(windy), "windy_with_total": sum(w["id"] in totals for w in windy)}


def main() -> None:
    from cfb.cli import REPO_ROOT, open_fetcher
    from cfb.evaluation.k04 import lines_of

    fetcher = open_fetcher()
    rows = {}
    for year in SEASONS:
        weather = []
        for st, weeks in WEEKS.items():
            for wk in weeks:
                entry, _ = fetcher.fetch("/games/weather", {"year": year, "week": wk, "seasonType": st})
                weather += fetcher.ledger.load(entry) or []
        lines = lines_of(fetcher.ledger, [year])[year]
        totals = {g["id"] for g in lines if any(ln.get("overUnder") is not None for ln in g.get("lines") or [])}
        rows[year] = {"games_with_weather": len(weather), **windy_counts(weather, totals)}
    n = sum(r["windy_with_total"] for r in rows.values())
    rep = {"counts": rows, "windy_with_total": n, "needed": NEEDED, "wind_mph": WIND_MPH,
           "verdict": "UNDERPOWERED, NOT RUN" if n < NEEDED else "POWERED: proceed to the totals test"}
    out = REPO_ROOT / "experiments" / "w01"
    out.mkdir(parents=True, exist_ok=True)
    (out / "w01-sizing.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
