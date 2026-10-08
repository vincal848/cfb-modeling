# E01: play-efficiency rating vs the opener protocol

Registered 2026-10-08, before any efficiency rating was computed. Idea 1 of
[the CFB modeling report](../../reports/College%20football%20modeling%20vs%20betting%20lines.md).
Question: does a past-only, opponent-adjusted EPA/play rating, blended with B02, carry
information the opening line lacks? We test two things: does it predict the open-to-close move
(closing-line value), and does betting it at the opener pay after costs?

## Model (no market input anywhere)

1. **EPA.** Each play's EPA in season s comes from the P02 EP model fit on seasons 2014..s−1
   (`p04.fold_ep_model`), so 2015 is the first season with EPA. Plays: P01 exact-tier
   regulation scrimmage states (`artifacts/plays/states.parquet`). Games without such plays
   contribute no efficiency observation; B02 still sees their score.
2. **Garbage time.** Drop plays where |score margin| exceeds 28 (Q1), 24 (Q2), 21 (Q3) or 16 (Q4).
   These are SP+'s published thresholds, used as is, not tuned.
3. **Per-game observation.** For each offense, EPA/play over the kept plays (≥ 20 plays, otherwise
   no observation). This is mapped to points-like units: 27 + 70·EPA/play, for both home and away.
4. **Opponent adjustment and dynamics.** The same Kalman filter as B02 (`TeamFilter`: offense,
   defense, home field, non-FBS group effects; q_week = 0.25, rho = 0.9, s0 = 8), run on the
   efficiency observations. The observation noise σ_e ∈ {4, 6, 8, 11} is the only tuned
   parameter. Results are admitted 6 hours after kickoff, and predictions are made at each V01
   fold cutoff, so only past information is used.
5. **Blend.** On the development seasons 2019–2021 only, fit OLS:
   result margin = a + b1·(B02 margin) + b2·(efficiency margin). Pick σ_e by the blend's MAE on
   the same seasons. Report MAE for B02 alone, efficiency alone and the blend. **No line is
   used in any fitting or selection.**

## Market tests (same harness as M02)

Lines: the median open and close home spread over providers that have both (`m02.open_close_lines`).
With m = the blended margin and gap = −m − open:

- **CLV slope:** OLS of (close − open) on gap; b > 0 means the model anticipates the move.
- **Encompassing (opener):** OLS of (result + open) on (m + open); c > 0 means information beyond the opener.
- **Encompassing (close):** OLS of (result + close) on (m + close); expected ≈ 0 (Fair & Oster).
- **Trade rule:** M02's rule unchanged: bet the model's side at the opener when |gap| ≥ g,
  g ∈ {1, 2, 3, 4}; price 0.51, fee 0.07·p(1−p).

| Season | Use |
|---|---|
| 2019–2021 | Fit the blend and σ_e (no lines) |
| 2022 | Select g (≥ 100 trades) |
| 2023 | Validate once. Week-block bootstrap, 4,000 reps, seed 7, 95% intervals for the P&L and all three slopes |
| 2024–2025 | Sealed |

## Null check

The blended margin shuffled across games within each week (seed 20261007, `m02.permuted`).
Its 2023 rule must not pass and its slopes must be ≈ 0.

## Decision

E01 passes if the 2023 trade rule's interval lower bound is > 0, or if the 2023 CLV-slope
and opener-encompassing intervals both exclude 0 on the positive side. Either outcome is
evidence of information beyond the opener. Anything else: the efficiency channel, as built
here, adds nothing the opener lacks.
