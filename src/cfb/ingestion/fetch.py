"""Cache-first fetching with the quota guard from implementation-plan §4."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cfb.config import REPO_ROOT
from cfb.ingestion.client import CFBDClient
from cfb.ingestion.ledger import LedgerEntry, RawLedger

ENDPOINTS_FILE = REPO_ROOT / "config" / "endpoints.json"


class QuotaStop(RuntimeError):
    pass


def load_endpoints(path: Path = ENDPOINTS_FILE) -> dict[str, dict[str, Any]]:
    spec = json.loads(Path(path).read_text(encoding="utf-8"))
    return {e["path"]: e for e in spec["endpoints"]}


@dataclass
class QuotaGuard:
    """Stops bulk work once used calls reach `stop_fraction` of the verified monthly quota.

    Forecast-critical calls pass `bulk=False` and may use the reserve.
    """

    monthly_quota: int | None
    stop_fraction: float
    remaining: int | None = None

    def check(self, *, bulk: bool) -> None:
        if not bulk or self.monthly_quota is None or self.remaining is None:
            return
        used = self.monthly_quota - self.remaining
        if used >= self.stop_fraction * self.monthly_quota:
            raise QuotaStop(
                f"bulk ingestion stopped: {used}/{self.monthly_quota} calls used "
                f"(stop at {self.stop_fraction:.0%})"
            )

    def observe(self, remaining: int | None) -> None:
        if remaining is not None:
            self.remaining = remaining


class Fetcher:
    def __init__(
        self,
        client: CFBDClient,
        ledger: RawLedger,
        guard: QuotaGuard,
        endpoints: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.client = client
        self.ledger = ledger
        self.guard = guard
        self.endpoints = endpoints if endpoints is not None else load_endpoints()

    def fetch(
        self, path: str, params: dict[str, Any] | None = None, *, refresh: bool = False, bulk: bool = True
    ) -> tuple[LedgerEntry, bool]:
        """Return (ledger entry, from_cache). Re-fetches only when `refresh` is set."""
        if not refresh:
            cached = self.ledger.latest_success(path, params)
            if cached is not None:
                return cached, True
        self.guard.check(bulk=bulk)
        resp = self.client.get(path, params)
        self.guard.observe(resp.calls_remaining)
        cap = self.endpoints.get(path, {}).get("documented_cap")
        return self.ledger.record(path, params, resp, cap), False
