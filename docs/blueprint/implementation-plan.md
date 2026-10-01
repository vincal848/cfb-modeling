# Practical implementation plan

Version 1.0 — October 1, 2026

## 1. Deliveries and estimates

Build the CFBD core first. Tracking and full participation are separately gated extensions. Estimates below are engineering effort for one experienced implementer, excluding source acquisition and long-running prospective evaluation. They are planning ranges, not delivery promises. Statistical review happens within every milestone.

| Milestone | Effort | Deliverable | Release gate |
|---|---:|---|---|
| M0: Source audit and protocol | 2-4 days | Endpoint/coverage matrix, identity samples, frozen research protocol | Required core fields demonstrated; historical availability classified |
| M1: Temporal data foundation | 4-7 days | Raw adapters, normalized facts, snapshot builder, quality checks | Restartable ingest; no duplicate facts; cutoff tests pass |
| M2: Useful forecasting baseline | 4-7 days | Elo/regression/dynamic margin forecasts, baseline views, forced picks | Full forward evaluation and immutable forecast replay |
| M3: EP and skill players | 6-10 days | State reconstruction, EP/EPA, opportunity/performance/development models | Scoring transitions reconcile; sparse-player uncertainty behaves sensibly |
| M4: Transfers and rosters | 4-7 days | Reviewed crosswalk, paired destination scenarios, roster allocations | Opportunities conserve totals; ambiguous identities excluded or scenario-modeled |
| M5: Joint game forecasts | 6-10 days | Joint-score expert, feature expert, drive simulator | Final score/OT contracts hold; tail and scoring checks documented |
| M6: Stack and audited views | 4-7 days | Forward-trained mixture, coherent summaries, policy decisions | Stack weights past-only; views agree with stored samples |
| M7: Operating release | 3-5 days | Packaging, logs, fallback, scheduled-run instructions, runbooks | Reproducible rehearsal on known and incomplete game batches |
| T1: Tracking extension | 15-35+ days after data access | Tracking normalization, movement/value models, tracking views | External held-out validation and physical plausibility |
| L1: Live extension | 8-15+ days | Received-event replay and live state forecasting | Latency, corrections, outages, and state-transition tests |

The core is roughly 33-57 focused engineering days under these assumptions. Evaluate and revise estimates after M1. A minimal useful baseline ships after M2; sophisticated modules do not block it. Running prospective checks requires elapsed football games and cannot be compressed into implementation time.

## 2. Architecture and software choices

Python handles typed ingestion, features, models, and orchestration. Parquet stores raw-normalized play/frame/sample datasets; JSON preserves original API responses. DuckDB provides analytical queries and snapshot materialization. Use one Bayesian engine initially, preferably Stan for the specified hierarchical models, and a regularized regression implementation for baselines. Add CatBoost after the linear expert is evaluated. Pin versions after platform compatibility checks. [DuckDB Python](https://duckdb.org/docs/stable/clients/python/overview), [Stan time series](https://mc-stan.org/docs/stan-users-guide/time-series.html), [CatBoost objectives](https://catboost.ai/docs/en/concepts/loss-functions-regression).

Use simple local jobs and a run ledger first. Add a hosted scheduler, serving database, or distributed computation only after measured need. No infrastructure purchase is necessary to validate a sample-season pipeline. A lightweight local dashboard should consume read-only summaries; API keys never enter the dashboard or browser.

SQLite schema.sql is an executable audit-contract prototype, not the warehouse implementation. It allows review of keys, time checks, forecast constraints, and deterministic views before large datasets exist. Keep query responsibilities separate from large-file storage.

Proposed repository structure:

```text
cfb-modeling/
  pyproject.toml
  dependency-lock-file
  config/
  src/cfb/
    ingestion/          # source adapters, request ledger, retries
    canonical/          # IDs, memberships, transfers, typed schemas
    snapshots/          # temporal joins, provenance, feature snapshots
    state/              # possession, scoring, clock, season rules
    features/           # past-only transforms
    models/             # EP, players, rosters, teams, experts, tracking
    stacking/           # forward distributions, weights, calibration
    decisions/          # deterministic policies
    evaluation/         # folds, metrics, paired comparisons, ablations
    views/              # summary interfaces and dashboard queries
    operations/         # job ledger, fallback, release manifests
  tests/
    contracts/
    transitions/
    temporal/
    numerical/
    replay/
  data/                 # local development only; ignored in version control
  artifacts/            # fitted models and hashed distribution manifests
  experiments/          # registered protocols and evaluation results
  docs/
```

The repository and commands below are planned interfaces; this blueprint does not claim to have implemented them.

## 3. Work backlog

| ID | Task | Depends on | Acceptance criterion |
|---|---|---|---|
| D01 | Register endpoint contracts and entitlements | none | Small authenticated sample per core endpoint; cap/filter behavior recorded |
| D02 | Audit season/team coverage | D01 | Matrix of counts, missingness, and exclusions; no empty-to-zero conversion |
| D03 | Implement credential handling and request ledger | D01 | Key read from secret/environment; redacted logs; request hash/retries |
| D04 | Implement immutable raw backfill | D03 | Restart rerun adds no duplicate payloads; corrected records preserved |
| D05 | Canonicalize games/teams/players | D04 | IDs survive roster moves; unresolved names remain unresolved |
| D06 | Build roster/portal crosswalk review | D05 | Evidence/status recorded; collision fixtures reject ambiguous merges |
| D07 | Add temporal version and snapshot builder | D04-D05 | Future facts excluded; manifest hashes deterministic |
| D08 | Add score and coverage quality checks | D05,D07 | Known incomplete games correctly quarantined per model |
| V01 | Register folds, estimands, and primary metrics | D02 | Protocol frozen before candidate results; replay class stated |
| B01 | Recompute Elo and margin/total regressions | D07,V01 | Forward forecasts beat trivial sanity cases; full scores reported |
| B02 | Add dynamic team-only strength | B01 | Past-only filtered states; prior/innovation sensitivity reported |
| B03 | Store immutable forecast summaries and forced picks | B01 | One forecast per run/game/horizon; identical replay choice |
| P01 | Implement possession/clock/scoring state machine | D08 | Turnovers, penalties, scoring, half-end, and OT cases reconcile |
| P02 | Fit fold-specific college EP and EPA | P01,V01 | Calibration and held-game scores; no reward double counting |
| P03 | Fit hierarchical opportunity shares | D06,P01 | Team category totals conserved; unknown group retained |
| P04 | Fit skill-player effectiveness/development | P02,P03 | Held-forward player scores; new players receive pooled uncertainty |
| R01 | Build roster scenario graph | P03,P04 | Transfers redistribute opportunities; canonical IDs preserved |
| R02 | Fit destination-context/adaptation models | R01 | Destination support/censoring documented; no causal claim |
| R03 | Add player-informed team decomposition | R01,B02 | Joint or forward-residual fit; ablation detects double counting |
| G01 | Implement joint statistical final-score expert | B02 | Nonnegative integer scores; tie/OT convention declared |
| G02 | Fit feature distribution expert | G01,R03 | Residual dependence learned past-only; broad coverage reported |
| G03 | Implement drive outcome/duration/field-position models | P01,R03 | Possession coupling and elapsed time coherent |
| G04 | Implement season-aware drive simulation | G03 | Regulation and overtime checks; scoring tails and returns tested |
| S01 | Generate forward distributions from eligible experts | G01-G04 | Entire upstream chain respects each cutoff |
| S02 | Fit constrained distribution mixture | S01 | Weights sum to one; primary scoring result versus champion |
| S03 | Optional coherent calibration | S02 | Winner adjustment reflected in joint scores; other scores rechecked |
| U01 | Implement game/player/transfer/evaluation views | B03,R02,S02 | Every display identifies cutoff/model/snapshot; no independent rounded decision |
| Q01 | Run paired comparisons and ablations | S02,U01 | Metric deltas, uncertainty, cohort counts, exclusions |
| O01 | Package release and fallback | Q01 | Rehearsal handles missing source, invalid data, and numerical failure |
| O02 | Start prospective immutable logging | B03 | Forecast stored before game; outcome appended later |
| T01 | Acquire and audit external participation/tracking | none | Coverage, ID links, permitted use, timestamps demonstrated |
| T02 | Normalize tracking and constant-velocity baseline | T01 | Direction/frame checks; no future-frame predictors |
| T03 | Fit step-and-turn and within-play value | T02,P02 | Held-game/player performance and physical checks |
| T04 | Test incremental game/player value of tracking | T03,Q01 | Missing tracking uses core; ablation supports integration |
| L01 | Add received-event live adapter and replay | P01,O01 | Uses receipt time; duplicate/corrected events handled |
| L02 | Evaluate live forecasting by state and latency | L01,G04 | Proper scores by game phase; outage recovery demonstrated |

Responsibility roles: engineering owns ingestion/contracts/operations; statistical modeling owns likelihoods/priors/validation; domain review owns state semantics and roster interpretation. One implementer can occupy all roles, but the gates remain distinct. This plan does not create agents or assign human collaborators.

## 4. API request budget and refresh policy

Tier 3 is the existing subscription assumption; verify actual account access and usage before backfill. The documented tier currently offers GraphQL and increased limits. [CFBD tiers](https://collegefootballdata.com/api-tiers). REST is sufficient for the first core release; do not add GraphQL solely because it is available.

Measure calls on a representative season and extrapolate by endpoint: `estimated_calls=sum(number_of_supported_partitions * expected_refreshes)`. Budget using measured partition sizes, retries, and correction windows. Keep a 20% reserve, stop bulk backfill at 80% of the verified monthly quota, and preserve capacity for current-season forecasts. These are operating defaults, not provider limits.

Cache completed historical seasons. Recheck recent completed games during a configurable correction window. During the season, refresh schedules/rosters/portal on a daily research cadence; fetch results after relevant games finish; capture market/weather snapshots at actual required horizons. Live polling frequency is set only after observing source latency, cost, and endpoint semantics. A scheduled job that runs late records actual availability and lead time instead of claiming an earlier cutoff.

No recurring automation has been installed by this package. Implement scheduling as part of O01 when the pipeline exists.

## 5. Planned command interfaces

```text
cfb audit-source --season 2025
cfb ingest --family games --season 2025
cfb ingest --family plays --season 2025
cfb build-snapshot --cutoff <UTC timestamp> --mode strict
cfb backtest --protocol config/protocol.json
cfb train --stage team --snapshot <id>
cfb forecast --snapshot <id> --horizon 24h --product football_only
cfb decide --forecast <id> --policy winner_v1
cfb evaluate --forecast-batch <id>
cfb serve-views --read-only
```

Each command reads configuration and writes an immutable run ledger with inputs, outputs, software version, warnings, and status. Exiting successfully must mean the specified contract passed, not merely that a process finished.

## 6. Quality and research tests

Focus tests on decisions that can materially change forecasts: future-data exclusion, temporal membership, identity collisions, endpoint truncation, scoring/possession transitions, opportunity conservation, overtime, score support, probability sums, handicap signs, pushes, and deterministic replay. Do not write tests asserting the same formula copied from its implementation.

Maintain manually checked football fixtures containing a turnover return TD, safety, penalty-nullified play, halftime possession change, missed/blocked conversion, and overtime examples by rule regime. Use source records and independently reconciled expected states. Source acquisition for rules is a specific prerequisite before implementing each regime; do not invent detailed NCAA rule changes from memory.

Use simulation-based parameter recovery for hierarchical models on synthetic data with known effects. For Bayesian computation start with four chains, target R-hat below 1.01, at least 400 bulk/tail effective samples for decision-relevant summaries, and zero unresolved divergences. Adjust sample counts for model size and tail quantities; these are diagnostic defaults. Compare priors, centered/noncentered parameterizations, and missingness assumptions.

Sensitivity suite: exclude 2020; vary history decay; compare FBS-only versus retained FCS training; vary transfer adaptation priors; vary opportunity scenarios; compare corrected versus archived data where both exist; vary uncertainty propagation approximation.

## 7. Forecast operating procedure

1. Read verified source quota and select required updates.
2. Ingest/cache raw responses and record retrieval times.
3. Validate coverage and materialize the cutoff snapshot.
4. Update past-only player, roster, and team states using the release manifest.
5. Generate eligible expert distributions using matched shared scenario draws.
6. Apply frozen mixture/calibration and derive summaries from final-score samples.
7. Apply deterministic policies to unrounded estimates; attach quality/reason codes.
8. Store immutable artifacts and publish read-only views.
9. After completion, append outcome version and evaluate; never rewrite the prediction.

A late arrival is applied to a new forecast revision, not retroactively inserted into an old cutoff. Repeated run retries reuse the same run key and input hash. Corrected outcomes create evaluation revisions while preserving previous evaluations.

## 8. Failure and fallback rules

| Failure | Response |
|---|---|
| Source timeout or quota | Use only sufficiently fresh evidenced cached facts; otherwise label unavailable |
| Missing player/transfer evidence | Run the validated team-only expert with wider modeled uncertainty where supported |
| Missing tracking | Use the CFBD-only model; retain the game |
| Invalid scoring/state reconstruction | Exclude affected simulator input; statistical score expert can continue if its inputs pass |
| Bayesian diagnostics fail | Keep the previously validated release; do not promote failed estimates |
| No validated expert eligible | Withhold forecast and recommendation; do not invent a distribution |
| Missing market odds or settlement mismatch | Publish winner forecast; market action UNAVAILABLE |
| Marginal source correction | Create a new snapshot/revision and explicitly identify the changed inputs |

Fallback may preserve a forced pick only when a valid forecast exists. An unavailable forecast cannot honestly produce a model-derived deterministic pick. Store fallback model and reason codes in all views.

## 9. Dashboard specification

Game screen: cutoff/horizon, winner probability, forced pick, recommendation, interval display, paired score distribution, model disagreement, scenarios, missing-data flags, and last successful refresh. Player screen: role-specific opportunity/performance, development, evidence and rank uncertainty. Transfer screen: destination feasibility, competition, paired team change, probability of improvement, assumptions. Team screen: components and state uncertainty. Evaluation screen: scores, coverage, calibration, cohorts, benchmark deltas, and audit classification.

All screens read immutable summaries. Include a historical snapshot selector; do not join a past forecast to today's roster or line. A historical forecast remains accessible when the champion model changes.

## 10. Definition of completion

The core is implemented when a new game batch can move from authenticated source ingestion to immutable cutoff snapshots, validated forecasts, coherent uncertainty, deterministic choices, views, and postgame evaluations with no manual data patching. It is statistically reviewed when the temporal audit, computational diagnostics, predictive checks, comparative scores, and limitations are documented. Accuracy superiority and transfer/market utility require observed out-of-sample evidence; implementation alone does not satisfy those claims.
