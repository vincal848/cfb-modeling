"""Thin CFBD REST client: bearer auth, bounded retries, key redaction.

It does no caching or storage itself; see ledger.py and fetch.py.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self

import httpx

from cfb.credentials import redact

BASE_URL = "https://api.collegefootballdata.com"
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass(frozen=True)
class ApiResponse:
    status: int
    body: bytes
    retrieved_at: str
    calls_remaining: int | None
    attempts: int

    def json(self) -> Any:
        return json.loads(self.body) if self.body else None


class CFBDError(RuntimeError):
    pass


def clean_params(params: dict[str, Any] | None) -> dict[str, str]:
    """Drop unset values and stringify, so equal requests have equal parameters."""
    out = {}
    for k, v in (params or {}).items():
        if v is None:
            continue
        out[k] = str(v).lower() if isinstance(v, bool) else str(v)
    return dict(sorted(out.items()))


class CFBDClient:
    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = BASE_URL,
        transport: httpx.BaseTransport | None = None,
        max_retries: int = 4,
        backoff_seconds: float = 1.0,
        timeout: float = 60.0,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], str] = utc_now,
    ) -> None:
        self._key = api_key
        self._max_retries = max_retries
        self._backoff = backoff_seconds
        self._sleep = sleep
        self._clock = clock
        self._http = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _delay(self, attempt: int, response: httpx.Response | None) -> float:
        if response is not None:
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                return float(retry_after)
        return self._backoff * 2**attempt

    def get(self, path: str, params: dict[str, Any] | None = None) -> ApiResponse:
        query = clean_params(params)
        for attempt in range(self._max_retries + 1):
            last = attempt == self._max_retries
            try:
                r = self._http.get(path, params=query)
            except httpx.TransportError as exc:
                if last:
                    raise CFBDError(redact(f"{path}: {type(exc).__name__}: {exc}", self._key)) from None
                self._sleep(self._delay(attempt, None))
                continue
            if r.status_code in RETRYABLE_STATUS and not last:
                self._sleep(self._delay(attempt, r))
                continue
            remaining = r.headers.get("X-CallLimit-Remaining")
            return ApiResponse(
                status=r.status_code,
                body=r.content,
                retrieved_at=self._clock(),
                calls_remaining=int(remaining) if remaining and remaining.isdigit() else None,
                attempts=attempt + 1,
            )
        raise AssertionError("unreachable")
