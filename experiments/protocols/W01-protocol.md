# W01: forecast wind and CFB totals

Registered 2026-10-08, before any total was compared with any wind figure. Only an Open-Meteo
coverage probe (does the archive hold a day-ahead forecast for a given date) was run.
**Trial count: first wind test; one fixed rule.** Prior market tests: M01, M02, E01, E02, K01, K02, K03,
and K04 (registered the same day).

Question: do outdoor college football totals go under more often than the closing total implies when
the **day-ahead wind forecast** is high? Practitioner tables (Action Network, 56.6% unders at 13+ mph
since 2005) use realized wind, which a bettor does not have at bet time, so they are no evidence here.

## Information rule

- Bet-time wind = Open-Meteo Previous Runs API `wind_speed_10m_previous_day1` (mph) at the venue
  coordinates, hour of kickoff, i.e. the forecast issued the day before. CFBD `/games/weather` is a record of
  the conditions at the game and is **not** used as a signal.
- Probe result (2026-10-08): that variable is empty before 2024-01-01 and populated for 2024 and 2025.
  So bet-time forecasts exist for the 2024 and 2025 seasons only.

## Rule and test

- Bet UNDER at the closing total (consensus median, same construction as M01) at price 0.50 + 0.01 half-spread
  with Kalshi's taker fee 0.07 p (1 - p), when the game is outdoors (`gameIndoors` false) and the forecast
  wind is >= 15 mph. A push is no trade.
- Null: under rate versus the closing total <= 52.38% (the break-even before the fee).
- Pass = game-block bootstrap (blocks = week, 4,000 reps, seed 7) lower bound of P&L per bet > 0.
- Placebo: the same rule on the forecast for a randomly chosen other game in the same week (seed 20261008);
  must not pass.

## Power gate (before any total is opened)

- 56.6% unders against 52.38% needs about 860 games (one-sided 5%, 80% power); 55% needs 2,240.
- Sizing uses only counts of outdoor games with wind >= 15 mph in 2024-2025 (CFBD realized wind as a proxy for
  the forecast count) that have a closing total. **If that count is below 860, W01 is recorded as
  "underpowered, not run": no total is compared with any wind figure.** Nothing is loosened afterwards
  (no lower threshold, no realized wind, no earlier seasons).
