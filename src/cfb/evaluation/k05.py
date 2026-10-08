"""K05 power gate: settled events per Kalshi derivative family (experiments/protocols/K05-protocol.md).
Counts market metadata only (public, read-only live /markets); no price is read.

    uv run python -m cfb.evaluation.k05
"""

from __future__ import annotations

import json
import time

import httpx

BASE = "https://api.elections.kalshi.com/trade-api/v2"
FAMILIES = ("KXNCAAFTOTAL", "KXNCAAF1HTOTAL", "KXNCAAF2HTOTAL", "KXNCAAFTEAMTOTAL", "KXNCAAF1HSPREAD")
NEEDED = 620


def settled_events(markets: list[dict]) -> set[str]:
    return {m["event_ticker"].split("-", 1)[1] for m in markets
            if m.get("status") in ("finalized", "settled") and m.get("result") in ("yes", "no")}


def fetch(series: str, client: httpx.Client) -> list[dict]:
    out, cursor = [], None
    while True:
        j = client.get(f"{BASE}/markets", params={"series_ticker": series, "limit": 1000, **({"cursor": cursor} if cursor else {})}).json()
        out += j.get("markets", [])
        cursor = j.get("cursor")
        if not cursor or not j.get("markets"):
            return out
        time.sleep(0.3)


def gate(events: dict[str, set[str]]) -> dict:
    full = events["KXNCAAFTOTAL"]
    both_halves = full & events["KXNCAAF1HTOTAL"] & events["KXNCAAF2HTOTAL"]
    best = {"1H+full": len(full & events["KXNCAAF1HTOTAL"]), "1H+2H+full": len(both_halves),
            "team total+full": len(full & events["KXNCAAFTEAMTOTAL"])}
    return {"events": {k: len(v) for k, v in events.items()}, "overlap": best, "needed": NEEDED,
            "verdict": "UNDERPOWERED, NOT RUN" if max(best.values()) < NEEDED else "POWERED"}


def main() -> None:
    from cfb.cli import REPO_ROOT

    with httpx.Client(timeout=60) as c:
        rep = gate({s: settled_events(fetch(s, c)) for s in FAMILIES})
    out = REPO_ROOT / "experiments" / "k05"
    out.mkdir(parents=True, exist_ok=True)
    (out / "k05-sizing.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
