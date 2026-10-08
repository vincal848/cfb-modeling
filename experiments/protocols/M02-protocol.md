# M02: beat the opener protocol

Registered 2026-10-07, before any B02-versus-opener quantity was computed.
Question: does B02 minus the opening spread predict the open-to-close line move, so that betting
B02's side at the opener earns positive closing-line value (CLV) and positive P&L after costs?
Motivation: Coleman 2025 finds rating systems significant against opening lines; M01 found no
information beyond closing lines.

## Data

- Market: CFBD `/lines` (cached; no new calls). Per game, the median closing and opening home spread
  across providers that have BOTH `spread` and `spreadOpen`, so open and close come from the same books.
  Games with no such provider are dropped. Opener coverage counts are reported.
- Model: B02 `dynamic|q_week=0.25|rho=0.9|s0=8|sigma=11`, same forward pass as M01. Its predicted
  margin `m` is the home minus away mean. Market prices are never model inputs.

## Estimands

- `gap = −m − open` (spread units; negative = B02 likes the home side more than the opener does).
- `move = close − open`.
- (a) Slope `b` in `move = a + b·gap`, OLS, fit on 2022; reported on 2023 with a week-block bootstrap
  interval (4,000 reps, seed 7). Hypothesis: b > 0.
- (b) Trade rule: when `|gap| ≥ g`, buy the side B02 favors (home cover if gap < 0, else away) at the
  OPENING spread, price 0.50 + 0.01 half-spread, fee 0.07·p(1−p), one contract. Settles on the actual
  margin versus the opening spread; a push is no trade.
- CLV: mean of (open − close) for home bets and (close − open) for away bets, in points, and the share
  of bets where the close moved our way (CLV > 0).

## Fixed grid and selection

`g ∈ {1, 2, 3, 4}` points. Select g on 2022 by mean P&L per trade, requiring ≥ 100 trades.

## Roles

| Season | Use |
|---|---|
| 2022 | Select g; fit the slope |
| 2023 | Validate the selected g once. Week-block bootstrap, 4,000 reps, seed 7, 95% interval |
| 2024–2025 | Sealed. Not computed by this module |

## Null check

B02 margin `m` permuted across games within each week (seed 20261007), same pipeline. Its 2023 rule must
not pass; if it does the pipeline is broken and no result is reported.

## Decision

The rule passes only if the 2023 P&L-per-trade interval lower bound is > 0. CLV and slope are
reported as diagnostics; they do not rescue a failed P&L test. Nothing is tuned after 2023 is seen.
