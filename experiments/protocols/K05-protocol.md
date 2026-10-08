# K05: derivative consistency on Kalshi CFB (I8), power-gated

Registered 2026-10-08, before any derivative-market price was read. Only market and event counts were looked at.
**Trial ledger:** one test (`experiments/trials.csv`).

Question: do the 1H / 2H / team-total / quarter contracts imply a full-game total or margin distribution that
disagrees with the full-game ladder by more than the cost of crossing both legs?

## Sizing, from market metadata only (2026-10-08)

The derivative series (KXNCAAF1HTOTAL, 2HTOTAL, TEAMTOTAL, 1HSPREAD, 2HSPREAD, quarter series) are **absent from
the `/historical/*` archive** (0 markets for the 2025 season). They exist only on the live endpoint, from the
2026 season (first open 2026-08-26). Settled 2026 events to date: full-game total 656, 1H total 332, 2H total 146,
team total 331; events with full-game + 1H + 2H total ladders: 146; with full-game + 1H: 332.

## Rule (declared if the gate passes)

Implied full-game total median from (1H + 2H) ladders and from the team-total ladders, against the full-game ladder
median, by interpolating each ladder's 0.5 crossing at the T-6h quote. Trade the full-game rung when the gap
exceeds the cost of crossing every leg plus fees plus 1 cent. Test: game-block bootstrap of P&L per trade, lower
bound > 0; null: gap computed against another game's ladder in the same week.

## Power gate

An effect of 5 cents per game needs about 620 games (P&L sd 0.5, one-sided 5%, 80% power); 3 cents needs 1,700.
The only available history is 2026 to date, and there is no earlier season to fit or select on, so the dependence
between the halves (needed to build the implied distribution) would have to be estimated on the same sample.
**If the best-covered family has fewer than 620 settled games, K05 is recorded "underpowered, not run" and no
derivative price is read.** Nothing is loosened afterwards.
