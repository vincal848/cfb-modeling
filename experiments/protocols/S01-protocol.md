# S01: structural-bias sweep on CFB closing lines

Registered 2026-10-08, before any against-the-spread outcome was tabulated by cell. Cells come from
the literature and betting folklore, not from this data. **Trial ledger:** `experiments/trials.csv`
lists every primary test registered in this repo (15 after this protocol). Holm uses that count as
the family size, which is conservative: the tests not run here count as p = 1.

## Data and pricing

- CFBD `/lines` and `/games` (cached; no new calls), 2014-2025. Closing line = the median spread
  across providers (`consensus_lines`); the pre-2021 books are CFBD's `consensus`, `teamrankings`
  and `numberfire`, whose quote time is not documented.
- A bet buys one side at 0.50 + 0.01 half-spread with fee 0.07 p (1 - p), as in M01. The home team covers when
  `home - away + spread > 0`; a push is no trade. P&L per bet = win - 0.51 - fee.

## Cells (direction fixed here, no tuning, no grid)

| cell | bets | sample |
|---|---|---|
| C1 home_field | AWAY team, non-neutral games (home-field "over-priced" after 2020) | seasons 2021-2025 |
| C2 big_fav | UNDERDOG when the consensus spread is >= 21 points | 2014-2025 |
| C3 two_ats_losses | the team that failed to cover in each of its last two lined games that season (bet it to cover); games where both teams qualify are dropped | 2014-2025 |
| C4 tv_over | OVER in nationally televised games | **not run**: no TV field is cached and the folklore has no precise definition |

## Roles

| Seasons | Use |
|---|---|
| 2014-2023 (C1: 2021-2023) | Discovery. Per cell, mean P&L per bet with a week-block bootstrap (4,000 reps, seed 7); one-sided p = share of bootstrap means <= 0. Holm over the ledger family, alpha = 0.05 |
| 2024-2025 | Sealed (M01 keeps it sealed too). Opened once, only for cells that survive Holm in discovery. Confirmed only if the interval lower bound is > 0 |

## Checks that must fail / find

- Null: cover outcomes permuted across games within each week (seed 20261008), same cells; no cell
  may survive Holm. Planted: a synthetic season with a 60% cover rate in a cell must survive.

## Wong-teaser check (a descriptive "not pursued" confirmation, 10 minutes)

A 6-point two-team teaser pays about -120, so each leg must win about 73.9% of the time. For games with a
closing spread of -7.5 or -8.5 (favorite teased to -1.5 / -2.5) or +1.5 / +2.5 (underdog teased to +7.5 / +8.5),
count how often the teased leg wins on 2014-2025 margins. Reported pooled; not part of the Holm family.
