# K04: key-number mass in Kalshi CFB spread ladders

Registered 2026-10-08, before any Kalshi spread-ladder price or any pre-2025 margin-given-spread
estimate was computed. Only market counts were looked at (766 spread events in the 2025 archive).
**Trial count: this is the first test of the key-number idea; one fixed rule, no grid.** Prior market
tests in this repo: M01, M02, E01, E02, K01, K02, K03 (7 protocols).

Question: Kalshi lists "Team wins by over k.5 points" rungs, so the probability of an exact margin
k is the difference of two adjacent rungs. If makers price adjacent rungs smoothly, they under-weight
the jumps at margins 3 and 7 that football scores produce. Does buying the exact-margin range at the
real quotes, when a model fitted on earlier seasons says it is worth more, make money after fees?

## Model (CFBD only, seasons before 2025)

- Games: cached CFBD `/lines` 2014-2024 with a closing consensus spread (`consensus_lines`, median
  across providers) and a final score. `mu = -spread` is the expected home margin, `m = home - away`.
- Kernel pmf: `P(m = k | mu) = sum_i w_i 1[m_i = k] / sum_i w_i`, `w_i = exp(-(mu_i - mu)^2 / (2 h^2))`.
- Bandwidth `h` in {0.5, 1, 2, 3}: fit on 2014-2022, scored on 2023-2024 by the summed Bernoulli log loss
  of the four events m = +3, -3, +7, -7. Then refit on 2014-2024 with the chosen `h`.
- Benchmark: a Gaussian pmf `N(mu, sd)`, `sd` the 2014-2022 residual sd, mass on each integer = the CDF
  difference over `[k - 0.5, k + 0.5]`.
- **Gate (CFBD only, before any Kalshi price):** if the kernel's held-out key-number log loss is not lower
  than the Gaussian's, the key-number mass is not there to exploit. K04 stops, is recorded as
  "no edge (no structure to price)", and no ladder candles are downloaded.

## Data (Kalshi, public, cached under provider 'KALSHI')

- `/historical/markets` for KXNCAAFSPREAD and KXNCAAFGAME (mapping to CFBD games via `map_events`);
  hourly candlesticks over [start - 30 h, start - 5 h] only for the rungs the rule can use (below).
  No authentication, no order endpoints. Start time = the CFBD kickoff.
- Games: all 2025-season events (the archive ends 2026-08-08) that map to a CFBD game with a closing
  spread and a result. Unmapped events are dropped with counts reported.

## Rule (fixed, no grid)

- Signed keys `k` in {+3, -3, +7, -7} (home-minus-away margin). For `k > 0` the ladder is the home team's, for
  `k < 0` the away team's; rungs `lo = |k| - 0.5`, `hi = |k| + 0.5`. YES on `lo` pays iff the team wins
  by >= |k|; NO on `hi` pays iff it wins by <= |k|; both pay iff the margin is exactly |k|.
- Entry quotes: the last valid hourly candle (`0 < bid < ask < 1`) with `end_period_ts <= start - 6 h`,
  for both rungs. Cost `c = ask_lo + (1 - bid_hi)`; payoff `1 + 1[margin = |k|]` (team-signed).
- Fee: K03's per-order rounding (`ceil(100 * 0.07 * p * (1 - p) * 100) / 100 / 100`) on each leg at its price.
- Trade when `q - (ask_lo - bid_hi) - fee_lo - fee_hi > 0.01`, where `q = P(m = k | mu)` from the
  kernel model at the CFBD closing spread. P&L = `1[margin = |k|] - (ask_lo - bid_hi) - fee_lo - fee_hi`. A
  ladder missing either rung or a crossed pair (`ask_lo <= bid_hi`) is no trade (counted).

## Test and decision

- The whole 2025 Kalshi season is the test. Mean P&L per trade, game-block bootstrap (blocks = game, 4,000
  reps, seed 7, 95% interval). **Pass = interval lower bound > 0.** Fees are in; capacity is unknown.
- Power, stated before the run: per-trade P&L sd is about 0.3, so 5c needs about 220 trades and 3c
  about 620; if there are fewer than 200 trades, a non-pass is "underpowered", not "no edge".
- 2026-to-date holdout (live Kalshi series, same rule, same model): evaluated **once, only if the 2025 test
  passes and both nulls fail**. Never tuned on.

## Nulls and checks (must fail / must find)

1. Simulated no-edge ladders (`tests/numerical/test_k04.py`): true margins drawn from a pmf with
   key-number spikes, market rungs set to that same pmf plus a 1c half-spread; the full pipeline
   must not pass. Planted: market rungs from a smooth pmf, outcomes from the spiked one; the pipeline
   must pass.
2. Real-data placebo: the same pipeline on the **neighbouring cells** m = +4, -4, +8, -8 (rungs 3.5/4.5 and
   7.5/8.5), where there is no key-number mass; it must not pass. If it passes the pipeline is broken
   and nothing is claimed.

Amendment, same day and before any Kalshi price was read: the first draft's placebo (model probability
permuted across games within a week) was dropped. A simulation showed it passes whenever the whole
ladder is mispriced, because permuting `q` only changes which rows are traded, not whether the
rows earn money, so it cannot tell a real edge from a broken pipeline.
