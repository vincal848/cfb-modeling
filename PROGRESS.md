# Progress

Last updated: 2026-10-01

This file keeps two things separate:

- **Implemented** means the code exists and its contract tests pass.
- **Demonstrated** means forecasting performance was observed out of sample on real data.

**Development evidence only.** B01 baselines and the B02 dynamic model were scored forward on the 2019–2021 development seasons (reconstructed replay, configurations tuned on the same games). No stack-fit, calibration or test season has been scored.

## Status by milestone

| Milestone | Implemented | Demonstrated | Notes |
|---|---|---|---|
| Repo setup | ✅ | n/a | Scaffold, blueprint copy, config/schema loaders, contract tests |
| M0 Source audit | 🟡 | n/a | D01, D02, D03 and V01 done |
| M1 Temporal data foundation | ✅ | n/a | D03–D08 done |
| M2 Forecasting baseline | ✅ | 🟡 development only | B01, B02, B03 done. Champion decision deferred to the stack/test stages per V01 |
| M3 EP and skill players | ✅ | 🟡 development only | P01–P04 done. Remaining P01 work: down/distance-level state transitions are measured, not modeled |
| M4 Transfers and rosters | ✅ | 🟡 development only (null results) | R01–R03 done; roster information does not yet improve team forecasts |
| M5–M7 | ⬜ | ⬜ | In dependency order |
| T1 Tracking / L1 Live | disabled | — | Gated on external data. `tracking_enabled=false`, enforced by config validation |

## Backlog items

| ID | Status | Evidence |
|---|---|---|
| D01 Endpoint contracts | ✅ | Live run: 20/20 endpoints returned 200. See [experiments/m0/d01-findings.md](experiments/m0/d01-findings.md). |
| D02 Season/team coverage | ✅ | Live run 2014–2025: 10,372 FBS games, 0 failed partitions, 585 calls. See [experiments/m0/d02-findings.md](experiments/m0/d02-findings.md). |
| D03 Credentials and request ledger | ✅ | `src/cfb/ingestion/{client,ledger,fetch}.py`, 10 tests on a mocked transport |
| D04 Immutable raw backfill | ✅ | `cfb ingest --family core --season 2014 --end 2025`: all partitions cached, 0 calls, 0 failed, 0 truncated. 3 tests. |
| V01 Folds, estimands, metrics | ✅ | Frozen 2026-10-01T19:57:51Z before any model was fitted; sha256 `5d0f1fc0…`. See [experiments/protocols/V01-protocol.md](experiments/protocols/V01-protocol.md). |
| D05 Canonical games/teams/players | ✅ | Games/teams: 10,372 schedule and 10,371 result facts. Players: 103,372 from 246,248 roster rows (2014–2025); 14,393 players appear on several teams under one athlete ID. Reruns add 0. |
| D06 Roster/portal crosswalk | ✅ | 14,422 portal records (2021–2025): 7,767 verified, 4,604 proposed, 70 ambiguous (never merged), 1,981 unresolved. See [experiments/d06/portal-crosswalk.md](experiments/d06/portal-crosswalk.md). 7 tests. |
| D07 Snapshot builder | ✅ | Sealed, deterministic cutoff snapshots; strict mode admits no reconstructed history. 6 temporal tests. |
| D08 Score and coverage quality checks | ✅ | `cfb quality`: per-game flags for 10,372 games; quarantine per model family. Team-score models lose 1 game; play-derived models 1,187 (11.4%). See [experiments/d08/quality-2014-2025.md](experiments/d08/quality-2014-2025.md). 13 tests. |
| B03 Immutable forecast summaries and forced picks | ✅ | 147 runs, 7,029 forecasts with winner_v1 picks, outcomes and evaluations; rerun inserts 0; 50/50 sampled forecasts replay exactly. 4 replay tests. |
| B02 Dynamic team-only strength | ✅ | Kalman filter, past-only states checked against every fold snapshot; 36-configuration prior/innovation sensitivity reported. See [experiments/b02/b02-development.md](experiments/b02/b02-development.md). |
| P01 State machine (scoring, overtime) | 🟡 | Scoring and overtime reconciliation under a cited rules registry: 78.3% of games exact, 11.7% events-only, 10.0% failed. 46 tests against independent sources (ESPN, recaps). Down/distance/field-position and clock transitions remain. See [experiments/p01/reconciliation-2014-2025.md](experiments/p01/reconciliation-2014-2025.md). |
| P02 College EP and EPA | ✅ | Fold-specific multinomial next-score model, all fits converged. Held-out log loss 1.207 vs 1.407 (yard line only) and 1.477 (class prior); calibrated within 0.12 points per EP decile. See [experiments/p02/ep-development.md](experiments/p02/ep-development.md). 4 tests. |
| P03 Hierarchical opportunity shares | ✅ | Shares (dropbacks, carries, targets) with explicit unknown/unassigned group; totals conserved to 4e-14. Beats a smoothed last-game copy in every category and season (log score 1.55 vs 1.80); separate participation model beats both alternatives. See [experiments/p03/opportunity-development.md](experiments/p03/opportunity-development.md). 9 tests. |
| P04 Skill-player effectiveness and development | ✅ | Per-position development model of EPA per opportunity; matches or beats the position mean in every fitted group and beats last season's raw mean everywhere; new players get the pooled (widest) uncertainty. See [experiments/p04/ability-development.md](experiments/p04/ability-development.md). 6 tests incl. parameter recovery. |
| R01 Roster scenario graph | ✅ | Scenarios with transfers that move players, redistribute shares and keep IDs; paired changes with common random numbers. Projection does not beat last season's team EPA (combined −0.00007, interval includes 0). See [experiments/r01/roster-development.md](experiments/r01/roster-development.md). 3 tests. |
| R02 Destination/adaptation | ✅ | No significant mover-stayer gap in any category; support and censoring reported; explicitly not causal. See [experiments/r02/transfer-development.md](experiments/r02/transfer-development.md). 4 tests. |
| R03 Player-informed team decomposition | ✅ | Forward-residual correction of B02 with raw vs residualized roster features; no out-of-sample gain, so B02 stays the team model. See [experiments/r03/decomposition-development.md](experiments/r03/decomposition-development.md). 3 tests. |
| B01 Elo and margin/total baselines | ✅ | Both beat the trivial model on every primary metric (development). See [experiments/b01/b01-development.md](experiments/b01/b01-development.md). |

## Completed work

### Setup

- Created `D:\cfb-modeling` with the blueprint layout from implementation-plan §2.
- Copied the blueprint verbatim to `docs/blueprint/`.
- Spec-sync tests allow the working config to differ from the blueprint **only** by deviations logged in [docs/deviations.md](docs/deviations.md).
- `cfb.config` enforces these invariants:
  - gated extensions are off;
  - missing values are not zeros;
  - strict replay is the default;
  - validation cohorts are disjoint and chronological;
  - no stored credentials;
  - the winner policy uses unrounded probabilities.
- `cfb.credentials` reads `CFBD_API_KEY` from the environment or a `.env` file, and redacts the key everywhere.
- `cfb doctor` checks the config, the schema, and that the key is present.

### DEV-001 applied

- Tier 3→4 and `monthly_quota` null→125000, verified with `GET /info`.

### D03: CFBD client and request ledger

The client:

- uses bearer authentication;
- retries on 429 and 5xx with exponential backoff, honoring `Retry-After`;
- never includes the key in error text;
- reads `X-CallLimit-Remaining` after each call.

The raw store:

- addresses payloads by the SHA-256 of their exact bytes and writes them under `data/raw/payloads/` (git-ignored);
- logs every retrieval as a `raw_requests` row in `data/ledger.sqlite`.

Behavior on reruns and refreshes:

- a rerun hits the cache and makes no call;
- a refresh that receives identical data adds no payload file;
- a refresh that receives corrected data adds a new version and keeps the old one.

Other checks:

- `suspected_truncation` is set when a response reaches its documented cap;
- an empty response is recorded as 0 rows, never treated as a zero value.

The quota guard:

- stops *bulk* calls at 80% of the monthly quota;
- leaves the remaining 20% for forecast-critical calls.

Labeling: rows from mocked transports use `provider='SYNTHETIC'`. Live rows use `'CFBD'`.

### D01: endpoint audit

- `cfb audit-source` makes one sample call per endpoint in `config/endpoints.json`.
- It writes `experiments/m0/endpoint-audit-<season>.{md,json}`.

### D02: coverage matrix

- `cfb audit-coverage --start 2014 --end 2025` writes `experiments/m0/coverage-<start>-<end>.{md,json}`. Reruns read from the cache and make no calls.
- Drive reconciliation uses the last drive's end score, not the maximum seen, and classifies each mismatch (ends before Q4, short of final, over or mixed).

### D04–D07: data foundation for B01

- `cfb ingest` backfills by family and season, cache-first. API calls stay sequential: they share one quota and rate limit.
- `cfb canonicalize` turns raw `/games` into append-only `source_records`: a schedule fact (available kickoff − 7 days) and a separate result fact (available kickoff + 6 hours, per V01), plus per-season FBS lists. Only the V01 population is canonicalized. Provider Elo and win probabilities are dropped.
- `cfb build-snapshot` seals the latest version of each fact available at a cutoff. Each forecast's own target game is read as of that game's cutoff, because a postseason fold spans several weeks.

### B01: baselines (development seasons only)

- Models: trivial home-advantage-only, recomputed margin Elo with a decayed total, and the ridge champion (team offense/defense, non-FBS group effect, time decay). Each emits 20,000 paired integer final scores per game; tied draws are redrawn.
- Parallel: snapshots are built in the main process; each fold is one worker task over all 39 configurations. Seeds are per game, so results are identical for any worker count (tested). Workers use one BLAS thread each. Full run: about 40 s on 19 workers.
- `cfb backtest --stage b01` writes [experiments/b01/b01-development.md](experiments/b01/b01-development.md); per-game rows go to `artifacts/backtests/` (git-ignored).

### B03: immutable forecast records

- `cfb record-forecasts` fits the three selected B01 models per development fold (in parallel), writes hashed artifacts (per-game normal parameters, paired score samples), and inserts `model_runs`, `forecast_summaries`, `decision_records` (winner_v1 forced pick), `outcome_versions` and `evaluation_results`.
- IDs are content-derived, so rerunning records nothing new. The schema's triggers reject edits, deletes and picks that contradict the stored probability.
- Replay: a stored forecast's parameters and derived seed regenerate the identical samples hash, probability and pick.
- Storage: samples are about 69 KB per forecast (483 MB for the 7,029 development forecasts) because random draws barely compress. Since replay regenerates them exactly, storing only parameters and seeds is an option before the stack and test seasons multiply the run count.

### B02: dynamic team strength

- `cfb backtest --stage b02`: Kalman filter on paired final scores (league level, home advantage, non-FBS group effects, team offense/defense). Weekly random-walk drift, off-season shrinkage by rho with innovation (1 − rho²)·s0², filtered never smoothed.
- One forward pass per configuration, run in parallel. Before each fold's predictions the filter must have absorbed exactly that fold's snapshot results (checked by digest), so every prediction is past-only.
- Predictions use only the state entries a game loads on; a test checks them against the full-state computation for same-week, next-week, new-season and new-team cases.
- 36 configurations, fixed before running; about 3.5 minutes on 19 workers.

## B02 findings (development, reconstructed, tuned on the same games)

1. **Best development energy score so far**: dynamic 10.391, ridge 10.462, Elo 10.799, trivial 12.645.
2. **Versus the ridge champion the gain is small and not robust**: −0.072, with the 95% interval below 0 for week blocks (−0.141 to −0.009) but not for three-week or season-half blocks. Margin CRPS improves (−0.124, interval below 0); winner log loss and total CRPS do not differ. Excluding 2020: −0.097 (interval below 0). Under V01 this is development evidence only; promotion is decided later on held-out seasons.
3. **Clearly better than Elo and the trivial model** on every primary metric and block choice.
4. **Intervals are slightly wide** (margin 53.4 / 82.1 / 96.1%, total 53.9 / 81.5 / 95.3% at nominal 50 / 80 / 95%). The selected observation noise, sigma = 11, is the smallest value in the grid, so it is probably a little high.
5. **The tuning surface is flat**: the selected configuration (q_week 0.25, rho 0.9, s0 8, sigma 11) sits at grid edges, but the second best (q_week 1, rho 0.75, s0 5, sigma 11) is 0.005 worse and interior on drift and carryover. No second pass was run: the gap to ridge is small enough that more tuning on these seasons could manufacture a win. A better fix is to estimate sigma from past innovations rather than tune it.

## D08 findings (drive-level checks, all 2014–2025 population games)

1. **The official result is missing for 1 game**, so team-score models lose 1 game.
2. **Play-derived models lose 1,187 games (11.4%)**, more from 2021 on (123–261 per season vs 25–62 before).
3. **Most score changes between drives are real, not errors.** 3,189 games have a single valid score between drive records, after punts, interceptions and fumbles: return touchdowns that CFBD does not credit to a drive. These are warnings, not quarantines; the first version of the check counted them as defects and quarantined 37% of games.
4. **CFBD numbers drives out of game order in 110 games**, mostly 2021+. Checks now order drives by period and clock; misnumbering alone is a warning.
5. **957 games still have a score decrease between or within drives** (for example a touchdown drive ending at 38 and the next drive starting at 31 at the same clock time). Drive records cannot tell which is right, so these stay quarantined for play models. This is conservative; P01's play-level reconciliation supersedes these drive proxies.
6. The three D02 spot-check games are kept for team-score models and quarantined for play models.

## D06 findings (portal crosswalk, 2021–2025)

1. **`/roster` returns every team for a season in one call**, so rosters for 2014–2025 cost 12 calls (35 calls with portal and recruiting).
2. **Verified share rises over time**: 32% of 2021 portal records to 64% of 2025. Verified needs a unique exact-name match on the origin's prior-season roster and the same athlete ID on the named destination's roster.
3. **70 records are ambiguous** (same-name players on one roster) and get no player.
4. **1,981 stay unresolved**. A diagnosis of the first pass: about half have no similar name on the origin roster (roster coverage gaps), 371 come from schools with no roster data (mostly Division II), and nickname variants were the next largest group. Two weaker rules (exact name on the portal-season roster; first-name prefix such as Sam/Samuel) then moved 215 records to proposed. They can never produce verified. Different first names that are not prefixes (Julian/Julio) stay unresolved.
5. **A named destination is a commitment, not an enrollment.** Enrollment events exist only for verified links (7,767).

### Rules registry (P01 prerequisite)

- [config/rules_registry.json](config/rules_registry.json) and [docs/rules/ncaa-rules-registry.md](docs/rules/ncaa-rules-registry.md): scoring, overtime, clock, kickoff and halftime rules for 2014–2025, each citing its source. 13 sources, 12 primary (NCAA rulebooks and rule-change documents; several read from third-party copies because ncaapublications.com links are broken).
- Overtime: two-point try mandatory from OT3 in 2014–2020 and from OT2 from 2021; single two-point plays from OT5 in 2019–2020 and from OT3 from 2021. Point values unchanged 2014–2025.
- Unverified items (2015, 2020 and 2022 rulebooks not opened; 2024 clock restart after the Two-Minute Timeout) are null in the JSON and listed in the .md. The loader raises on a null it needs rather than falling back.
- [docs/rules/fixture-candidates.md](docs/rules/fixture-candidates.md): 24 real games with an independent source per scoring situation.

## P01 findings (play-level scoring, all 2014–2025 population games)

1. **78.3% of games reconcile exactly** (every score change explained, ending at the official final); 11.7% only at the events tier; 10.0% fail. Exact share is 82–85% through 2020 and 66–79% from 2021. Only exact games should feed transition-level models (P02).
2. **CFBD conventions handled explicitly, never silently**: scores on plays are after the play and include the try; administrative rows carry stale scores (skipped); 932 games have transient stale rows; 1,005 games have touchdowns under non-touchdown play types (found from text); try results come from text or, in 955 games, from the score change; 7 games record the try on the next play.
3. **11 games have the offense/defense score columns swapped for the whole game** (e.g. 2022 Florida State–LSU); the swapped reading is used only when it explains strictly more.
4. **Overtime is unreliable in CFBD**: some games put every overtime in period 5 (overtime number then inferred from possessions), some lack plays for scoreless overtimes (2019 Virginia Tech–North Carolina: 5 inferred, 6 real), and 2021 Illinois–Penn State lacks all seven shootout periods (reported as failed).
5. **Defensive two-point returns are recorded only in the score**; the try text says the kick was blocked. These reconcile at the events tier, not exactly.
6. **Fixtures**: 20 games extracted to `tests/fixtures/football/`; official finals, scorers, return touchdowns, safeties, nullified touchdowns, failed tries, overtime counts and the mandatory two-point periods all match ESPN or written recaps.

### P01 states and P02 expected points

- `cfb build-states`: 1,214,836 regulation scrimmage states from exact-tier games, with next-score labels, pre-play margin (from CFBD scores, so inferred tries count), net points per play and try points. Down, yard-line, clock, kickoff-after-score and half-start consistency is reported in [experiments/p01/state-checks-2014-2025.md](experiments/p01/state-checks-2014-2025.md).
- `cfb ep`: for each development season, penalty chosen on the season before (past-only), then refit on all earlier seasons and scored on the season. Runs in one process with one math thread by default (`cfb` now sets OMP/OPENBLAS/MKL threads to 1 unless the caller sets them).

## P02 findings (development, reconstructed)

1. **The full model beats both baselines on every held-out season**: next-score log loss 1.207 vs 1.407 for yard line only (difference −0.200, 95% interval −0.206 to −0.193) and 1.477 for the class prior.
2. **Calibrated**: realized next-score points are within 0.12 of mean EP in every decile; each outcome's predicted rate is within 0.004 of its observed rate.
3. **EP at 1st and 10** runs from −0.5 (own 5) to +5.0 (opponent's 5), nearly identical across folds. The learned try value is 0.96 points per touchdown.
4. **EPA sanity**: mean EPA ≈ 0 overall; passes +0.042, rushes +0.028.
5. **Numerical**: an unpenalized fit does not converge (rare outcomes such as safeties let coefficients grow without bound), so the penalty grid starts at 1e-6. The selected penalty is that floor in every fold; all six final fits converged. An earlier run with a 500-iteration cap and a run including a penalty of 0 did not converge; their log loss differed from the final run by less than 0.001.

## P03 findings (development 2019–2021, reconstructed, tuned on the same games)

1. **Data**: CFBD `/plays/stats` per game (5,844 games, 2015–2021, none truncated) gives athlete IDs per play. CFBD credits no receiver on about 29% of team targets; those, and new players, go to the explicit UNKNOWN group (realized unknown share: targets 0.32, carries 0.12, dropbacks 0.08).
2. **The first evaluation was unfair**: it charged every player a model did not list to one shared UNKNOWN bucket, which rewarded leaving known players out. Copying last game's split looked better (1.503 vs 1.555). All models are now scored over the same outcomes: every player known before the game plus UNKNOWN, with the baseline smoothed (known players absent last game get a 0.005 floor).
3. **Scored fairly, the share model wins in every category and season**: per-opportunity log score 1.55 vs 1.80 for the smoothed last-game copy (carries 1.77 vs 2.01, dropbacks 0.72 vs 0.89, targets 2.20 vs 2.52). Expected counts conserve team totals exactly.
4. **Participation needs its own model.** Deriving P(any opportunity) from shares assumes independent opportunities and badly overstates backups (dropbacks log loss 1.34). A separate past-only beta-binomial participation model (methodology §4's two-part design) wins in every category: carries 0.45, dropbacks 0.39, targets 0.50.
5. **Tuning**: two grid passes for shares (the second widened past pass-1 edges and selected the same configuration: half-life 2 games, prior weight 0.5, alpha 0.1, kappa 3). The participation model's selected settings (half-life 4, strength 1) are at grid edges; not tuned further.

## P04 findings (development 2019–2021, reconstructed)

1. **EPA comes from fold EP models** fit before each season (saved in `artifacts/models/`), joined to player play stats by play ID. Only P01 exact-tier games contribute.
2. **Parameters must be per position (methodology §4: mu[p], rho[p]).** A shared fit per category let rare, extreme passers (wide receivers on trick plays, usually one attempt) inflate the quarterback prior spread to 0.53 EPA per dropback and persistence to 0.91; that model predicted quarterbacks worse than their position mean. Fitting each position group separately gives a plausible QB spread of 0.14 and persistence of 0.80–0.83.
3. **A group gets its own dynamics only with a real role** (at least 100 training player-seasons, 1,000 opportunities and a median of 5 opportunities per player-season). This leaves QB passing, RB/WR/TE receiving and QB/RB rushing; other groups use their training mean. A count-only rule let wide-receiver passing (one-attempt seasons) through and gave a degenerate fit.
4. **Results**: the model matches or beats the position mean in every fitted group (QB passing MSE 0.0541 vs 0.0549, RB rushing 0.0433 vs 0.0445, WR receiving 0.1718 vs 0.1725) and beats last season's raw mean everywhere (e.g. QB passing 0.150). Gains over the mean are small: season EPA per opportunity is noisy, so strong shrinkage toward the position mean is mostly right.
5. **Uncertainty**: new players get the pooled prior (widest intervals); 80% intervals cover 77–81%. Some persistence estimates sit at their bounds (RB receiving 1.0, TE receiving near 0), so the data identify them weakly.

## M4 findings (development 2019–2021, reconstructed)

1. **R01: the roster projection does not beat last season's team offense.** Preseason strength = P03 game-1 shares × P04 abilities (QB passing, rushing), weighted by last season's pass rate. Alone it predicts team offensive EPA per play worse than last season's value (MSE 0.0101 vs 0.0087); combined it adds nothing significant (−0.00007, 95% interval −0.0004 to +0.0003), though its calibrated weight is stable and positive (0.32–0.46). Correlation with the outcome falls from 0.49 (2019) to 0.27–0.28 (2020–2021). Checked: every starting quarterback (150+ dropbacks) is on his preseason roster and 78–85% had prior-season dropbacks, so this is not a coverage bug. The projection covers only quarterbacks and running backs; line, defense and scheme are absent.
2. **R02: players who change teams perform about as forecast.** No mover-stayer gap in EPA per opportunity is significant in any category (e.g. QB passing −0.004, interval −0.063 to +0.046). Support is adequate for P5↔G5, P5→P5, G5→G5 and G5→FCS moves; other directions are flagged thin. Movers appear the next season 72–83% of the time, stayers 70–84%. Returning players beat their P04 forecast by about +0.06 on average whether they moved or not: survivors are better than forecast, a calibration point for P04.
3. **R03: no roster correction is promoted.** Correcting B02 margins by the roster-feature difference helped in 2020 and hurt in 2021; pooled margin CRPS +0.023 (raw) and +0.016 (residualized), intervals including 0. The raw feature, which overlaps with results B02 already absorbed, did worse than the residualized one, consistent with partial double counting. B02 remains the team model (V01: keep the simpler champion).

## B01 findings (development, reconstructed, tuned on the same games)

Two tuning passes. Pass 1 (commit 7aa513e) selected grid-edge values and gave ridge intervals that were too narrow, so pass 2 widened the grid once and added a ridge covariance scale. No further pass.

1. **Both baselines beat the trivial model** on energy score, winner log loss and margin/total CRPS, for every bootstrap block choice and without 2020.
2. **Ridge beats Elo on energy score**: −0.34, 95% interval −0.48 to −0.20 (ridge 10.46, Elo 10.80, trivial 12.65).
3. **Ridge interval coverage is now close to nominal**: margin 50.3 / 78.9 / 94.4%, total 52.0 / 79.3 / 94.2% at 50 / 80 / 95%. This comes from a tuned variance scale of 1.2, which is the top of the grid; B02 should model forecast variance directly instead.
4. **Selected**: ridge penalty 1, half-life 180 days, covariance scale 1.2; Elo K 30, home advantage 35, carryover 0.75. Elo's values are inside the grid.
5. **Cohorts**: no cohort reverses the ordering. `missing_team_stats` has 0 games and `no_line` has 8 (descriptive only).

## D02 findings (real CFBD data, 2014–2025)

Full detail is in [experiments/m0/d02-findings.md](experiments/m0/d02-findings.md).

1. **Opening lines and moneylines exist only from 2021.** Before that, the market benchmark is one spread of unknown timing. V01 must state the seasons each benchmark covers.
2. **Play-by-play disagrees with the official final score in 244 games (about 2.4%).**
   - 9 end before Q4, 147 are short of the final, 88 are over or mixed.
   - 2021 is the worst season (92.6% match).
   - The official score is the outcome of record. D08 must quarantine these games from play-derived models only.
3. **Mid-game drive scores can be corrupt** even when the final drive is right. P01 must validate score changes drive by drive.
4. **Drives and plays share one feed**, so they do not cross-check each other.
5. **2020 is short** (568 games). FBS membership grows from 128 to 136. Books per game varies by era.

## D01 findings (real CFBD data, one sample partition)

Full detail is in [experiments/m0/d01-findings.md](experiments/m0/d01-findings.md).

1. **Historical lines have no observation timestamp.**
   - Historical CFBD lines can only be a *reconstructed* market benchmark of unknown timing.
   - The market-informed product needs our own prospective timestamped captures.
   - Football-only is unaffected.
2. **`/games` mixes schedule and result fields.**
   - D05 must split each game into a schedule fact and a result fact, each with its own `available_at`.
   - Provider pregame Elo is comparison-only.
3. **`/games` returns all divisions.**
   - Week 5 of 2024 had 270 games, of which 56 involve FBS.
   - The population filter must handle null classifications (5 games).
4. **`/games/weather` is realized weather.**
   - It is not usable as a pregame predictor and stays comparison-only.
5. **Portal records have no athlete ID.**
   - The D06 crosswalk is required.
   - `transferDate` is an event time, not publication evidence.
6. **Roster→recruit links are partial.** 92 of 139 rows have them.
7. **The `/plays/stats` cap is not approached** with team-week partitions (87 rows against a cap of 2,000).

None of these require a spec deviation. Each is a case the blueprint already anticipates, now confirmed with data.

## Validation results

| Date | Check | Result | Data |
|---|---|---|---|
| 2026-10-02 | `uv run pytest` | 201 passed | Synthetic contract rows and mocked transport only |
| 2026-10-01 | `uv run ruff check` | Clean | — |
| 2026-10-01 | `uv run cfb doctor` | All ok, key present | — |
| 2026-10-01 | `uv run cfb audit-source --season 2024` | 20/20 endpoints returned 200, none truncated, 19 calls used | **Real CFBD** |
| 2026-10-01 | `uv run cfb audit-coverage --start 2014 --end 2025` | 12 seasons, 0 failed partitions, 0 suspected truncation, 585 calls used | **Real CFBD** |

These checks validate contracts, endpoint access and season coverage. They do not validate forecast accuracy.

## CFBD account (verified 2026-10-01 via `GET /info`)

| Field | Value |
|---|---|
| Tier | Tier 4 (the blueprint assumed Tier 3; see DEV-001) |
| Monthly limit | 125,000 calls. 124,981 remained after D01; 124,348 after D02. |
| Quota resets | 2026-11-01 00:00 UTC |
| Shared pool | Yes, with `cbb`. Any basketball usage on this key counts against the same quota. |
| Features | adjustedMetrics, weather, scoreboard, livePlayByPlay, graphQl |

- The 80% bulk stop is about 100,000 calls per month.
- The higher-tier features don't change the build order. Weather and adjusted metrics stay non-predictive unless timing is evidenced, and REST is enough.

## Blockers

- None.
- Note: terminals opened before the key was set won't see it. Open a new terminal.

## Next executable step

1. Optional B02 refinement: estimate the observation noise from past one-step innovations instead of tuning it (B02 finding 5).
2. M5: joint score experts (G01 joint-score, G02 feature expert, G03–G04 drive simulator).
3. Player play stats exist for 2015–2021 only; stack-fit and test seasons need 2022–2025 (about 3,600 more calls) before those stages.
3. P01: possession/clock/scoring state machine, which needs hand-checked football fixtures and a sourced rules registry.
