# C01: low-attention cohorts (I6)

Registered 2026-10-08, before any cohort-level cover rate or ladder trade was tabulated. **Trial ledger:** 13 declared
cells (`experiments/trials.csv`); Holm uses the full ledger total as the family size.

Question: do the S01 rules or the K04 rule work in the cohorts where books and Kalshi are thinnest?

## Cohorts (fixed here, no search)

- **fcs**: either team is FCS (`homeClassification` / `awayClassification` = fcs in CFBD `/games`).
- **g5_midweek**: either team is in a Group of Five conference (American Athletic, Conference USA, Mid-American,
  Mountain West, Sun Belt) and the kickoff falls on Tuesday to Friday US Eastern.
- **early**: regular-season weeks 1-3.
- **low_volume** (K04 only): the lowest tercile of full-game Kalshi volume (game-winner `volume_fp`, tercile cuts
  from the 2025 events).

## Cells

- S01 cells C1 home_field, C2 big_fav, C3 two_ats_losses (exactly as in S01) restricted to each of fcs, g5_midweek,
  early: 9 cells. Discovery 2014-2023 (C1 2021-2023); 2024-2025 sealed and opened once for Holm survivors.
  A cell with fewer than 30 bets has p = 1.
- K04 rule (exactly as in K04) restricted to each of the four cohorts: 4 cells, tested on 2025.
- Per-cell statistic and null as in S01 (week-block bootstrap, permuted covers). Holm over the ledger total.

## Note registered in advance

K04's trade decision depends only on a row's own quotes and model value, so a cohort subset of a rule that fired
zero times fires zero times. The K04 cohort cells are run for completeness and are expected to be empty.
