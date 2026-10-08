# M01: results (2022 select, 2023 validate)

Protocol: [M01](../protocols/M01-protocol.md). Run 2026-10-07. Raw output: `m01-validation.json`.
1,806 games; 1,799 with a closing spread, 1,500 with a moneyline. **Evaluation class: reconstructed.**

**Verdict: no market passed. 2024–2025 stays closed. Do not trade B02.**

Winner log loss on games with a moneyline: B02 0.573, closing market 0.550. The market is better.

Per trade is dollars per $1 contract after the 1c half-spread and the 0.07·p(1−p) fee.
The interval is a week-block bootstrap, 95%.

| Market | Rule (w, t) | 2022 trades / per trade | 2023 trades / per trade | 2023 interval | Passed |
|---|---|---|---|---|---|
| Win | 0.5, 0.04 | 120 / +0.007 | 120 / −0.018 | [−0.069, +0.042] | no |
| Cover | 1.0, 0.06 | 354 / −0.061 | 372 / −0.019 | [−0.069, +0.039] | no |
| Over | 1.0, 0.04 | 450 / −0.034 | 465 / −0.011 | [−0.031, +0.011] | no |

Null check (model probabilities shuffled within week): no market passed, as required. The
real model's 2023 results are no better than the shuffled null's, so the pipeline does
not invent edges, and B02 adds no information beyond the closing price.

## Who does reality side with? (2022–2023, winner market)

Games grouped by B02 minus market (`m01.gap_table`). In every bucket the realized rate tracks
the market, not B02. A logistic fit of the outcome on logit(market) and logit(B02) gives the
market 0.95 and B02 0.05 [−0.20, 0.31]. B02's disagreement carries no information. Spread
and total markets look the same (B02 coefficients −0.14 [−0.33, 0.06] and −0.06 [−0.28, 0.16]).

| B02 − market | Games | B02 | Market | Actual |
|---|---|---|---|---|
| ≤ −0.15 | 118 | 0.484 | 0.705 | 0.703 |
| −0.15 to −0.10 | 130 | 0.553 | 0.675 | 0.662 |
| −0.10 to −0.05 | 234 | 0.593 | 0.664 | 0.701 |
| −0.05 to −0.02 | 207 | 0.605 | 0.639 | 0.647 |
| −0.02 to 0.02 | 326 | 0.564 | 0.565 | 0.558 |
| 0.02 to 0.05 | 171 | 0.537 | 0.502 | 0.485 |
| 0.05 to 0.10 | 158 | 0.493 | 0.422 | 0.418 |
| 0.10 to 0.15 | 90 | 0.527 | 0.406 | 0.378 |
| ≥ 0.15 | 66 | 0.552 | 0.331 | 0.364 |
