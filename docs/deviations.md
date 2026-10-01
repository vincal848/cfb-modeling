# Deviations from the blueprint

The blueprint in [docs/blueprint/](blueprint/README.md) is the working specification. Every change to its methodology, config defaults, schema, validation splits, or release gates is recorded here before the change is merged.

Each entry gives:

- what changed;
- why, with the statistical justification;
- what evidence prompted it (for example a coverage-audit result);
- whether it was made before any candidate results were seen. This matters for the protocol freeze in methodology §11.

Validation splits may change only after the M0 coverage audit and before any candidate results are inspected.

| ID | Date | Area | Change | Statistical justification | Evidence | Pre-results? |
|---|---|---|---|---|---|---|
| DEV-001 | 2026-10-01 | config.data | Set `subscription_tier_assumption` 3→4 and `monthly_quota` null→125000 | No statistical effect. It corrects an operating assumption so the 80% backfill stop uses the verified quota. The quota pool is shared with `cbb`, so the budget must subtract observed non-CFB usage. | `GET /info`: patronLevel 4, monthlyLimit 125000, sharedPool true | Yes |

## Implementation choices within the spec

These choices are not deviations. They are decisions the blueprint leaves open.

- **Repo location and tooling:** `D:\cfb-modeling`, uv + hatchling, matching the user's other projects.
- **Contract database:** the blueprint's SQLite schema is used as-is for audit/forecast records. A DuckDB migration (plan §2) is deferred until the analytical warehouse is needed in M1. Large data goes to Parquet.
- **HTTP client:** the CFBD REST API is called directly with httpx rather than through the generated `cfbd` client. This gives exact control over the request ledger, payload hashing, and cap and truncation detection (methodology §2).
