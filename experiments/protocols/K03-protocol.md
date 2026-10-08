# K03: pooled Kalshi favorite-longshot protocol

Registered 2026-10-07, before any non-CFB Kalshi price was downloaded. Market counts per series
were looked up only to size the sample; no prices or outcomes were seen.
Motivation: K01's CFB calibration showed contracts under 10¢ winning 1–2% against a 4.4%
average price, at every entry hour, but with only about 100 such events. Bürgi et al.
(UCD WP2025_19) report a venue-wide favorite-longshot bias on Kalshi. Question: does buying
heavy favorites (which is the same as selling longshots) at the real ask make money after the
fee, pooled across leagues, out of sample?

## Data

- Cached public Kalshi data only (provider 'KALSHI'): `/historical/markets` and hourly
  candlesticks over [start − 30 h, start − 5 h]. No authentication, no order endpoints.
- Series (two-outcome game winners): KXNFLGAME, KXNBAGAME, KXMLBGAME, KXNHLGAME, KXNCAAMBGAME,
  KXWNBAGAME, KXNCAAFGAME. Historical archive only (settled before Kalshi's cutoff, 2026-08-08).
- One market per event (the alphabetically first ticker); one contract per event. An event
  must have exactly two markets, and their results must be one yes and one no; otherwise it
  is dropped (ties, voids), with counts reported.
- Start time = `expected_expiration_time` − 3 h. This matched CFBD kickoffs exactly for 78% of
  CFB events, with about 5% off by 3 h or more. The large entry buffers below cover it.
  Agreement with the start time embedded in MLB tickers is reported.

## Entry, pricing, rule (fixed grid)

- Entry: the last hourly candle with `end_period_ts` ≤ start − h, h ∈ {24, 6}, with a valid
  `yes_bid.close` and `yes_ask.close`.
- Buy YES at `yes_ask` if `yes_ask` ≥ c, else NO at `1 − yes_bid` if that is ≥ c;
  c ∈ {0.85, 0.90, 0.95}.
- Taker fee with Kalshi's per-order rounding at an assumed 100-contract order:
  fee per contract = ceil(100 · 0.07 · p · (1 − p) · 100) / 100 / 100 dollars.
  Order-book depth is not observed, so capacity is unknown.

## Roles

| Events starting | Use |
|---|---|
| before 2026-01-01 | Select (h, c): max mean P&L per trade, ≥ 300 trades |
| 2026-01-01 to the cutoff | Validate the selected rule once. Calendar-week block bootstrap, 4,000 reps, seed 7, 95% interval |

Per-league validation results are reported as descriptive only, with no claims.

## Null check

Outcomes shuffled across events within each calendar week (seed 20261007). Its validation
must not have an interval lower bound > 0; if it does, the pipeline is broken and nothing is claimed.

## Decision

Pass = the validation interval lower bound is > 0. A pass means "paper-trade this forward on
live 2026 markets", not "trade it": the archive has no depth, and the edge may be too small to
survive real order sizes.
