"""Immutable raw-response store and request ledger (D03/D04).

Payloads are content-addressed by SHA-256 of the exact response bytes, so a
restart or rerun that receives identical data writes no new payload file. Every
retrieval is still logged in `raw_requests`, which keeps a dated history and
preserves corrections: a changed response gets a new hash, and the old payload
is kept.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cfb.ingestion.client import ApiResponse, clean_params


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_params(params: dict[str, Any] | None) -> str:
    return json.dumps(clean_params(params), sort_keys=True, separators=(",", ":"))


def request_key(path: str, params: dict[str, Any] | None) -> str:
    return sha256(f"{path}?{canonical_params(params)}".encode())


def response_count(payload: Any) -> int | None:
    if isinstance(payload, list):
        return len(payload)
    if isinstance(payload, dict):
        return 1
    return None


@dataclass(frozen=True)
class LedgerEntry:
    request_id: str
    provider: str
    endpoint: str
    parameters_json: str
    retrieved_at: str
    http_status: int
    response_count: int | None
    suspected_truncation: bool
    payload_uri: str
    payload_hash: str


class RawLedger:
    """Writes payloads under `root/payloads/` and ledger rows to the contract DB.

    `provider` labels every row. Real CFBD calls use 'CFBD'; fixtures and mocked
    transports must use 'SYNTHETIC' so they can never pass for observations.
    """

    def __init__(self, root: Path, conn: sqlite3.Connection, provider: str = "CFBD") -> None:
        self.root = Path(root)
        self.conn = conn
        self.provider = provider

    def _store_payload(self, body: bytes) -> tuple[str, str]:
        digest = sha256(body)
        rel = Path("payloads") / digest[:2] / f"{digest}.json.gz"
        path = self.root / rel
        if path.exists():
            with gzip.open(path, "rb") as fh:
                if sha256(fh.read()) != digest:
                    raise RuntimeError(f"stored payload {rel} is corrupt")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            with gzip.open(tmp, "wb") as fh:
                fh.write(body)
            tmp.replace(path)
        return rel.as_posix(), digest

    def record(
        self, path: str, params: dict[str, Any] | None, resp: ApiResponse, cap: int | None
    ) -> LedgerEntry:
        uri, digest = self._store_payload(resp.body)
        try:
            count = response_count(resp.json()) if resp.status == 200 else None
        except json.JSONDecodeError:
            count = None
        entry = LedgerEntry(
            request_id=f"{request_key(path, params)[:24]}@{resp.retrieved_at}",
            provider=self.provider,
            endpoint=path,
            parameters_json=canonical_params(params),
            retrieved_at=resp.retrieved_at,
            http_status=resp.status,
            response_count=count,
            suspected_truncation=cap is not None and count is not None and count >= cap,
            payload_uri=uri,
            payload_hash=digest,
        )
        self.conn.execute(
            "INSERT INTO raw_requests VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                entry.request_id, entry.provider, entry.endpoint, entry.parameters_json,
                entry.retrieved_at, entry.http_status, entry.response_count,
                int(entry.suspected_truncation), entry.payload_uri, entry.payload_hash,
            ),
        )
        self.conn.commit()
        return entry

    def latest_success(self, path: str, params: dict[str, Any] | None) -> LedgerEntry | None:
        row = self.conn.execute(
            """SELECT request_id, provider, endpoint, parameters_json, retrieved_at, http_status,
                      response_count, suspected_truncation, payload_uri, payload_hash
               FROM raw_requests
               WHERE provider=? AND endpoint=? AND parameters_json=? AND http_status=200
               ORDER BY retrieved_at DESC LIMIT 1""",
            (self.provider, path, canonical_params(params)),
        ).fetchone()
        if row is None:
            return None
        return LedgerEntry(*row[:7], bool(row[7]), *row[8:])

    def load(self, entry: LedgerEntry) -> Any:
        with gzip.open(self.root / entry.payload_uri, "rb") as fh:
            body = fh.read()
        if sha256(body) != entry.payload_hash:
            raise RuntimeError(f"payload hash mismatch for {entry.request_id}")
        return json.loads(body)
