# College football modeling blueprint

Prepared October 1, 2026. Version 1.0.

This package defines the methodology and implementation sequence for player development, transfers, roster composition, dynamic team strength, game forecasts, and an optional tracking extension. It is a specification, not a trained forecasting system. No subscription requests, production deployment, or model fitting have been performed.

Read in this order:

1. [Methodology](methodology.md): estimands, models, uncertainty, validation, and decisions.
2. [Implementation plan](implementation-plan.md): architecture, milestones, acceptance criteria, and operating procedures.
3. [Statistical review](statistical-review.md): design audit, remaining limitations, and release gates.
4. [Configuration](config.json): proposed defaults, disabled extensions, and validation policy.
5. [Database schema](schema.sql): executable SQLite prototype of the audit and forecast contracts.
6. [Model contracts](model-contracts.json): required stage inputs and outputs.

The SQLite schema is intentionally a small executable contract prototype. Store large raw, play, frame, and sample datasets in Parquet. The production warehouse described in the plan uses DuckDB; migrate the SQL constraints and views deliberately rather than treating SQLite SQL as a DuckDB migration. The schema does not implement training or ingestion.

## What is ready to build

The CFBD core includes temporal ingestion, football-only baselines, skill-player opportunity and performance, roster scenarios, dynamic team strength, joint game distributions, views, and deterministic decisions. Tier 3 is the current working assumption. Verify account entitlements and endpoint behavior during the first milestone.

Complete on-field participation, injury availability, route charting, and frame-level tracking are external-data dependencies. Keep those extensions disabled until their coverage and rights are established. An increase in CFBD tier should be justified by observed call usage, not assumed tracking availability.

## First delivery

Implement milestones M0-M2 before adding sophisticated player or tracking models. The first useful release is a reproducible pregame winner/margin/total baseline with cutoff-aware features, immutable forecasts, measured uncertainty, and a simple decision policy. Do not wait for tracking to ship the core.

## Verification of this package

The accompanying local verification record states the checks actually performed. These checks validate specification consistency and executable schema behavior; they do not validate forecasting accuracy. All numeric thresholds in the configuration are proposed engineering or research defaults, not empirically optimized values.

Primary sources and links are included in the methodology. Research-derived ideas are distinguished from design choices and from unverified data capabilities.
