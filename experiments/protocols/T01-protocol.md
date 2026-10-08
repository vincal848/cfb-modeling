# T01: one-time-zone travel cell (JSE 2017 reading)

Registered 2026-10-08, before any cover outcome was tabulated for this cell. Only team time zones and
game counts were looked at. **Trial ledger:** one test, appended to `experiments/trials.csv` (family size 16).

The cell comes from the hypothesis list ("late-season underdogs with a 1-hour deficit", Journal of
Sports Economics 2017). The primary source was not available to the agent that registered this
protocol, so the precise definition below is a **reading** of it and may differ from the paper. A null
here does not refute the paper.

## Definition (fixed, no grid)

- Games: CFBD regular-season games with a consensus closing spread, `neutralSite` false, week >= 9, an away
  team that is the underdog (consensus spread < 0 means the home team is favored).
- Time zone: each team's `location.timezone` from the cached `/teams` 2024 payload (the host's time zone is the
  home team's; teams with no time zone are dropped, counts reported). The shift is the absolute difference of the
  two zones' UTC offsets on the game date, in hours; the cell requires exactly 1.
- Bet: the away underdog covers, at 0.50 + 0.01 and fee 0.07 p (1 - p), pushes dropped (S01 pricing).

## Power gate, before any cover outcome is opened

A 55% cover rate against the 52.38% break-even needs about 2,240 games (one-sided 5%, 80% power). If the number of
cell games in discovery seasons (2014-2023) is below 2,240, T01 is recorded as "underpowered, not run".

## Test

2014-2023 discovery: week-block bootstrap (4,000 reps, seed 7), one-sided p < 0.05 / 16 (Holm family size 16,
this being the only test in the family). 2024-2025 opened once, only if discovery passes: lower bound of P&L per bet > 0.
Null: cover outcomes permuted within week; must not pass.
