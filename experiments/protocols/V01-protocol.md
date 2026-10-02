# V01: registered validation protocol

The machine-readable protocol is [config/protocol.json](../../config/protocol.json). This page explains it. If the two disagree, the JSON wins.

Status: **frozen** 2026-10-01T19:57:51Z, SHA-256 `5d0f1fc06c369118f2e460a4f506590072e545760b68b5e4abbac5fbe1468d6e` ([V01-freeze.json](V01-freeze.json)). Since then, `load_protocol` fails if the file changes, and a change needs a new protocol version plus a [deviation](../../docs/deviations.md) entry.

No candidate results existed at freezing: no model had been fitted. D02 looked at coverage counts for every season, including the test seasons, but not at any forecast or outcome relationship.

## What is unchanged from the blueprint

The season splits, primary metrics, interval levels, horizons, draw count, seed and minimum cohort size all equal the blueprint defaults in `config/config.json`. `validate_protocol` checks this, so the protocol cannot drift from the config. D02 found no reason to move the splits, so **no deviation is logged**.

| Role | Seasons | Use |
|---|---|---|
| Warm-up | 2014–2018 | Fit only; never scored |
| Development | 2019–2021 | Weekly outer folds scored; model and hyperparameter selection |
| Stack fit | 2022 | Held-forward expert forecasts fit the mixture weights |
| Calibration | 2023 | Fits coherent calibration if enabled; otherwise scores the frozen stack as a validation season and may halt promotion, but nothing is refit |
| Test | 2024–2025 | Opened once, after every compared model is frozen; archived after |
| Prospective | 2026 | From the first real implementation forecast |

## Choices the blueprint leaves open, registered here

1. **Replay class.** Every 2014–2025 evaluation is *reconstructed*. CFBD history was first retrieved in 2026, so there is no publication evidence for strict replay. A game result is treated as available 6 hours after kickoff. Every reported score carries its replay class.
2. **Folds.** One fold per calendar week (`season`, `seasonType`, `week`) from `/calendar`. The postseason is one fold per season, because CFBD's postseason week 1 runs from mid-December to January.
   - A game's cutoff is its scheduled kickoff minus the horizon.
   - A fold's parameters are fit on data available by the fold's earliest game cutoff.
   - Filtered team states may add results available by each game's own cutoff, so a Saturday forecast can use Thursday's result.
   - Every stage refits at least at each season's first fold.
3. **Primary product and horizon.** Football-only game forecasts at 24 hours. The 7-day and 60-minute horizons are reported separately and never pooled. Historically, 24h and 60m may coincide because no timestamped intra-week information exists.
4. **Promotion metric.** Mean energy score on (home points, away points). Lower is better. A model without paired score samples (e.g. a margin-only Elo) is scored on winner log loss and margin/total CRPS but cannot compete on the promotion metric. B01's initial champion must therefore emit paired final-score samples.
5. **Paired comparison.** Per-game differences (challenger minus champion) on identical games, horizon and replay class. Week-block bootstrap with 4,000 replicates and a 95% percentile interval. Superiority requires the interval's upper bound to be below 0. Sensitivity: three-week and season-half blocks.
   Simulations may run in parallel across games and folds. Each game's draws depend only on a seed derived from the protocol version, model, game and horizon, so results are identical for any worker count or order.
6. **One primary test comparison.** On 2024–2025, final stack versus initial champion. Any other test comparison is secondary and carries no superiority claim. No improvement means the simpler champion stays.
7. **Cohorts** reported with every evaluation: early season (either team has played fewer than 3 games), FBS vs non-FBS, postseason, neutral site, 2020, play-by-play unreconciled, missing team stats, no line. Cohorts under 100 games show counts and uncertainty only.
8. **Market benchmarks** (D01 and D02 findings).
   - The historical spread benchmark (2014–2025) and the opening-spread benchmark (2021–2025) are reconstructed, of unknown timing, never pooled with each other, and descriptive only.
   - The market-informed product is evaluated prospectively only.
9. **Outcomes and play-derived exclusions.** The official `/games` score is always the outcome. Games whose play-by-play does not reconcile (D02 finding 2) are excluded from training play-derived models only.

## Not yet registered

These must be added to `config/protocol.json` **before any of their results are seen**, under a new protocol version:

- the `transfer_heavy` cohort, which needs a portal coverage audit first;
- short-history modules (transfers, enriched 2025+ fields), each with its own seasons, folds and metrics;
- player-level metrics (opportunity, conditional performance, development).

## Commands

```text
uv run cfb protocol            # validate and show folds/games per season (cached data, no API calls)
uv run cfb protocol --freeze   # freeze the draft; refuses if results were seen or already frozen
```
