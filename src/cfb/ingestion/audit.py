"""D01: one authenticated sample per registered endpoint, summarized for the M0 audit.

Field null rates come from a single sample partition. They show whether the fields
exist and are populated, not how complete the coverage is across seasons (that is D02).
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cfb.ingestion.fetch import Fetcher


def fill(params: dict[str, str], sample: dict[str, Any]) -> dict[str, Any]:
    return {k: (v.format(**sample) if isinstance(v, str) else v) for k, v in params.items()}


def field_profile(payload: Any) -> dict[str, dict[str, Any]]:
    """Per top-level field: share of records where it is missing or null, and observed types."""
    records = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    records = [r for r in records if isinstance(r, dict)]
    if not records:
        return {}
    keys = sorted({k for r in records for k in r})
    profile = {}
    for k in keys:
        values = [r.get(k) for r in records]
        types = Counter(type(v).__name__ for v in values if v is not None)
        profile[k] = {
            "null_rate": round(sum(v is None for v in values) / len(values), 4),
            "types": sorted(types),
        }
    return profile


def run_audit(fetcher: Fetcher, sample: dict[str, Any], *, refresh: bool = False) -> dict[str, Any]:
    results = []
    for path, spec in fetcher.endpoints.items():
        params = fill(spec["params"], sample)
        entry, cached = fetcher.fetch(path, params, refresh=refresh, bulk=False)
        payload = fetcher.ledger.load(entry)
        row: dict[str, Any] = {
            "path": path,
            "family": spec["family"],
            "role": spec["role"],
            "params": params,
            "http_status": entry.http_status,
            "response_count": entry.response_count,
            "documented_cap": spec.get("documented_cap"),
            "suspected_truncation": entry.suspected_truncation,
            "from_cache": cached,
            "request_id": entry.request_id,
            "payload_hash": entry.payload_hash,
        }
        if entry.http_status == 200:
            row["fields"] = field_profile(payload)
        else:
            row["error"] = payload if isinstance(payload, (dict, str)) else str(payload)[:500]
        results.append(row)
    return {
        "audit": "D01_endpoint_contracts",
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "provider": fetcher.ledger.provider,
        "sample": sample,
        "calls_remaining_after": fetcher.guard.remaining,
        "results": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        f"# D01 endpoint audit ({report['provider']})",
        "",
        (
            f"Generated {report['generated_at']}. "
            f"Sample partition: `{json.dumps(report['sample'])}`. "
            f"Calls remaining after the run: {report['calls_remaining_after']}."
        ),
        "",
        (
            "Each endpoint got one sample call. Null rates come from that one partition "
            "and do not measure coverage across seasons (that is D02)."
        ),
        "",
        "| Endpoint | Role | Status | Rows | Cap | Truncation? | Fields | Fields mostly null (>50%) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        fields = r.get("fields", {})
        sparse = [k for k, v in fields.items() if v["null_rate"] > 0.5]
        lines.append(
            f"| `{r['path']}` | {r['role']} | {r['http_status']} | {r['response_count']} | "
            f"{r['documented_cap'] or ''} | {'**yes**' if r['suspected_truncation'] else 'no'} | "
            f"{len(fields)} | {', '.join(f'`{s}`' for s in sparse) or '—'} |"
        )
    errors = [r for r in report["results"] if r["http_status"] != 200]
    if errors:
        lines += ["", "## Non-200 responses", ""]
        for r in errors:
            lines.append(f"- `{r['path']}` {r['http_status']}: `{json.dumps(r.get('error'))[:300]}`")
    return "\n".join(lines) + "\n"


def write_report(report: dict[str, Any], out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"endpoint-audit-{report['sample']['year']}"
    jpath, mpath = out_dir / f"{stem}.json", out_dir / f"{stem}.md"
    jpath.write_text(json.dumps(report, indent=2), encoding="utf-8")
    mpath.write_text(render_markdown(report), encoding="utf-8")
    return jpath, mpath
