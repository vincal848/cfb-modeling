# M01: market edge protocol

Registered 2026-10-07, before any model probability was compared with any market price.
Question: does B02 (selected development configuration, not re-tuned) carry tradable
information beyond closing sportsbook prices, after Kalshi-style costs?

## Data

- Market: CFBD `/lines` (cached; no new calls). Per game, the median across providers of
  the closing home spread, total, and de-vigged home moneyline probability. Openers are not used.
- Model: B02 `dynamic|q_week=0.25|rho=0.9|s0=8|sigma=11`, one forward pass from 2014 under the
  V01 fold snapshots, horizon 1440 minutes. Probabilities are closed-form from its Gaussian
  predictive (no draws). Market prices are never model inputs.

## Markets and pricing

Three binary markets per game: home win (fair price = de-vigged moneyline), home covers the
closing spread (fair price 0.50), over the closing total (fair price 0.50). We buy YES or NO
at fair + 0.01 (one-cent half-spread), paying a fee of 0.07·a·(1−a) per contract. Pushes pay 0.

## Strategy (fixed grid)

Blended probability `p = σ(w·logit(p_model) + (1−w)·logit(p_market))`, w ∈ {0.25, 0.5, 1.0};
trade a side when `p − a − fee ≥ t`, t ∈ {0.02, 0.04, 0.06}; one contract per trade. Each
market type is selected separately.

## Roles

| Season | Use |
|---|---|
| 2022 | Select (w, t) per market by ROI per contract; ≥ 100 trades required |
| 2023 | Validate the selected rule once. Week-block bootstrap, 4,000 reps, 95% interval |
| 2024–2025 | Opened **only** if a market's 2023 interval lower bound is > 0. One look per market |

## Null check

The same pipeline is run with p_model permuted across games within each week (seed 20261007).
Its 2023 ROI must not have an interval lower bound > 0; if it does, the pipeline is broken
and no result is reported.

## Decision

A market is tradable only if both 2023 and 2024–2025 have interval lower bounds > 0.
Anything else means: do not trade it.
