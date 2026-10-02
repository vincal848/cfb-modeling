# Progress

Last updated: 2026-10-01

This file keeps two things separate:

- **Implemented** means the code exists and its contract tests pass.
- **Demonstrated** means forecasting performance was observed out of sample on real data.

**Development evidence only.** B01 baselines were scored forward on the 2019–2021 development seasons (reconstructed replay, configurations tuned on the same games). No stack-fit, calibration or test season has been scored.

## Status by milestone

| Milestone | Implemented | Demonstrated | Notes |
|---|---|---|---|
| Repo setup | ✅ | n/a | Scaffold, blueprint copy, config/schema loaders, contract tests |
| M0 Source audit | 🟡 | n/a | D01, D02, D03 and V01 done |
| M1 Temporal data foundation | 🟡 | n/a | D03, D04, D07 done; D05 done for games/teams (players pending D06); D06, D08 remain |
| M2 Forecasting baseline | 🟡 | 🟡 development only | B01 and B03 done; B02 dynamic team model remains |
| M3–M7 | ⬜ | ⬜ | In dependency order after M2 |
| T1 Tracking / L1 Live | disabled | — | Gated on external data. `tracking_enabled=false`, enforced by config validation |

## Backlog items

| ID | Status | Evidence |
|---|---|---|
| D01 Endpoint contracts | ✅ | Live run: 20/20 endpoints returned 200. See [experiments/m0/d01-findings.md](experiments/m0/d01-findings.md). |
| D02 Season/team coverage | ✅ | Live run 2014–2025: 10,372 FBS games, 0 failed partitions, 585 calls. See [experiments/m0/d02-findings.md](experiments/m0/d02-findings.md). |
| D03 Credentials and request ledger | ✅ | `src/cfb/ingestion/{client,ledger,fetch}.py`, 10 tests on a mocked transport |
| D04 Immutable raw backfill | ✅ | `cfb ingest --family core --season 2014 --end 2025`: all partitions cached, 0 calls, 0 failed, 0 truncated. 3 tests. |
| V01 Folds, estimands, metrics | ✅ | Frozen 2026-10-01T19:57:51Z before any model was fitted; sha256 `5d0f1fc0…`. See [experiments/protocols/V01-protocol.md](experiments/protocols/V01-protocol.md). |
| D05 Canonical games/teams/players | 🟡 | Games and teams: 10,372 schedule and 10,371 result facts, 12 FBS lists; rerun adds 0. Players wait for D06. |
| D06 Roster/portal crosswalk | ⬜ | Needed for M3–M4, not for B01 |
| D07 Snapshot builder | ✅ | Sealed, deterministic cutoff snapshots; strict mode admits no reconstructed history. 6 temporal tests. |
| D08 Score and coverage quality checks | ⬜ | Needed before P01; D02 already classifies play-by-play mismatches |
| B03 Immutable forecast summaries and forced picks | ✅ | 147 runs, 7,029 forecasts with winner_v1 picks, outcomes and evaluations; rerun inserts 0; 50/50 sampled forecasts replay exactly. 4 replay tests. |
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
| 2026-10-02 | `uv run pytest` | 77 passed | Synthetic contract rows and mocked transport only |
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

1. B02: dynamic team strength (filtered states, past-only).
2. D06 and D08 before the play-level work in M3.
