# E02: play-efficiency rating, full coverage

Registered 2026-10-08, after E01 and before any E02 rating was computed. **Trial count: this is
the second market test of the efficiency family on 2022–2023** (E01 was the first; M02 tested B02
alone on the same seasons). Read any 2023 interval with that in mind.

## Why a second trial

E01's efficiency rating predicted margins worse than B02 on the development seasons (MAE 13.87
vs 13.10, before any line was seen). It drew only on exact-tier games, which cover 66–79% of
2021–2023 games, so ratings went stale for a third of a team's games. E01's σ_e also landed
on the edge of its grid (4). Both are build defects, found without looking at the market.

## Changes from E01 (nothing else changes)

1. **Coverage.** Efficiency observations come from `artifacts/plays/states-rating.parquet`: P01
   states for exact- *and* events-tier games (2021: 779, 2022: 803, 2023: 861 games). EP models
   are unchanged: they are still trained on exact-tier states only, from earlier seasons.
2. **σ_e grid** ∈ {2, 3, 4, 6}, again chosen on 2019–2021 blend MAE.

The model, blend, market tests, trade rule, roles, null check and decision rule are all exactly
[E01's](E01-protocol.md).

## Development gate (before the market)

If the full-coverage efficiency rating still predicts 2019–2021 margins worse than B02 alone,
the market results are reported but read as "this efficiency build is not yet a better
model". The next step is then rating design (success rate, pass/rush split, offense/defense
weighting), tuned on development MAE only, never another market look.
