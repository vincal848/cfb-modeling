# K01: Kalshi favorite-rule protocol

Registered 2026-10-07, before any Kalshi 2025 price was compared with any outcome.
Question: does a simple favorite-buying rule on Kalshi 2025 college football game-winner
markets (series KXNCAAFGAME) make money after fees, out of sample?
Motivation (literature, not evidence here): Bürgi et al. report a favorite-longshot bias on
Kalshi with takers losing far more than makers; arXiv 2607.14430 reports calibration mid-life
and miscalibration in the last ~10 minutes (hourly candles cannot see that window).

## Data

- Cached public Kalshi data only (provider 'KALSHI'): `/historical/markets` and hourly
  candlesticks. No authentication, no order endpoints.
- Two markets per game mirror each other. One market per event is analyzed: the
  alphabetically first ticker. One contract per event.
- Kickoff: CFBD `start_utc` via `map_events` (match rate reported). Unmatched events use
  `expected_expiration_time` − 3.5 h and are flagged; they stay in the sample.
- Events with a kickoff before 2025-08-01, no result, or no candle at the entry hour are dropped
  (count reported).

## Entry and pricing (fixed grid)

- Entry candle: the last hourly candle whose `end_period_ts` is ≥ h hours before kickoff,
  h ∈ {24, 3, 1}. Prices are that candle's `yes_bid.close` and `yes_ask.close`.
- Favorite threshold c ∈ {0.60, 0.70, 0.80, 0.90}: buy YES if `yes_ask` ≥ c, else buy NO
  if `1 − yes_bid` ≥ c, else no trade.
- Taker variant: pay the ask (YES: `yes_ask`; NO: `1 − yes_bid`) plus fee 0.07·p·(1−p).
- Maker variant: pay the bid on the same side plus one cent (YES: `yes_bid + 0.01`; NO:
  `1 − yes_ask + 0.01`) and fee 0.0175·p·(1−p). Maker fills are **assumed, not observed**:
  this is an upper bound.
- P&L per contract = (1 if the side wins else 0) − price − fee. 24 rules in total.

## Roles (split by kickoff UTC date)

| Period | Use |
|---|---|
| Aug–Oct 2025 | Select the rule with the highest mean P&L per trade; ≥ 100 trades required |
| Nov 2025–Jan 2026 | Validate the selected rule once. Week-block bootstrap (`block_bootstrap`), 4,000 reps, seed 7, 95% interval |

Pass = validation interval lower bound > 0 (maker and taker reported; the pass applies to the
selected rule, whichever variant it is). No re-tuning after the validation look.

## Descriptive (no pass/fail)

- Calibration: mid price vs outcome by price bucket (width 0.1) × h.
- Bid-ask spread (ask − bid at h = 3) by decile of market volume; overall median.
- Maker/taker breakdown from public trades for a seeded random sample of ≤ 80 events
  (seed 20261007): taker mean P&L per contract by taker-price bucket, before fees.

## Null check

Outcomes permuted across events within each kickoff week (seed 20261007), same pipeline.
If its validation interval lower bound is > 0 the pipeline is broken and no result is reported.

## Decision

Tradable only if validation passes and the null does not. Otherwise: no edge, do not trade.
