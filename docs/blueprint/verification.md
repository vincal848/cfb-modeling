# Package verification

Performed October 1, 2026 using local Python and an in-memory SQLite database.

27 checks passed.

- Configuration and model contracts parse as JSON
- Historical validation cohorts are disjoint and ordered
- Unverified extensions disabled by default
- No credential value stored in configuration
- Decision contract agrees with policy configuration
- All principal model stages have a contract
- SQLite schema executes with foreign keys enabled
- Strict snapshot rejects future availability
- Strict snapshot rejects unknown availability
- Source corrections cannot overwrite an existing version
- Sealed snapshot cannot acquire new facts
- Sealed snapshot cutoff cannot change
- Model training cannot extend past snapshot cutoff
- Winner view uses unrounded probability
- Exact probability tie has deterministic canonical-ID choice
- Inconsistent winner probability sums rejected
- Forecast cannot be overwritten
- Recorded winner choice cannot contradict forecast policy
- Evaluation cannot attach another game outcome
- Forecast/decision/evaluation views execute
- Foreign-key integrity check passes
- Local link exists: README.md -> methodology.md
- Local link exists: README.md -> implementation-plan.md
- Local link exists: README.md -> statistical-review.md
- Local link exists: README.md -> config.json
- Local link exists: README.md -> schema.sql
- Local link exists: README.md -> model-contracts.json

These checks cover configuration consistency, executable schema constraints, synthetic cutoff/decision cases, and local links. They do not fit models, authenticate CFBD access, verify provider completeness, validate NCAA rules, reconcile actual sample artifacts, or demonstrate forecast calibration/accuracy.
