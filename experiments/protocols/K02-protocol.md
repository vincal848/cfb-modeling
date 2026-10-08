# K02: Kalshi vs sportsbook consensus protocol

Registered 2026-10-07, before any 2025 Kalshi price was compared with any sportsbook price.
Question: when Kalshi's price for a 2025 game winner differs from the de-vigged sportsbook
consensus, which one does the outcome side with, and is buying the cheap side on Kalshi (at its
real ask, after fees) profitable out of sample?

2025 is the sealed V01 test season for model comparisons. This test uses **no model forecasts**
(venue against venue), so it does not open the seal for any model.

## Data

- Kalshi: KXNCAAFGAME markets and hourly candles, replayed from the raw ledger (no calls, no
  authentication). Two markets per game; the **home** market is the one whose `yes_sub_title`
  matches the home team's names and not the away team's. Games with zero or two such matches,
  no event mapping (`map_events`), or no candles are dropped and counted. Match rate is reported.
- Book: CFBD `/lines` 2025 (regular + postseason), `consensus_lines`: median across providers of
  the de-vigged closing home moneyline probability. Openers are not used. Games without a
  moneyline are dropped and counted.
- Outcome: CFBD `game_result` (home win = home_points > away_points; ties dropped).
- Kalshi entry quote at horizon h hours before kickoff: the last candle ending at or before
  kickoff − h with a valid yes_bid and yes_ask (0 < bid < ask < 1), at most 12 hours stale;
  otherwise the game has no quote at that h. Mid = (bid + ask) / 2; spread = ask − bid.
  h ∈ {24, 1}. Block (week) = season_type + week.

## (a) Information test

Per h, on all games with both prices: logistic regression of home win on
logit(Kalshi mid) and logit(book) with an intercept (Newton-Raphson, Wald 95% intervals).
Also log loss and Brier for each venue (and for the mean of the two as reference).
Descriptive only; no selection.

## (b) Trade rule

Gap = book − Kalshi mid. If gap ≥ d, buy home YES at yes_ask; if gap ≤ −d, buy the away side at
1 − yes_bid. Fee 0.07·a·(1−a) on the price a paid; one contract per game; P&L = outcome − a − fee.
Grid: h ∈ {24, 1}, d ∈ {0.02, 0.04, 0.06}.

| Window | Use |
|---|---|
| Regular-season weeks 1–7 | Select (h, d) by max mean P&L per trade, **≥ 100 trades** required. If no rule has 100, the requirement drops to **≥ 50** (decided now); if none has 50, report no selection |
| Regular week 8 through postseason | Validate the selected rule once. Week-block bootstrap (`block_bootstrap`), 4,000 reps, seed 7, 95% interval. **Pass = lower bound > 0** |

No retuning after the validation window is seen.

## Look-ahead check

The CFBD close is the book's final line and may postdate the Kalshi entry time, so a positive
result could be look-ahead. The selected rule is therefore also run with the book's role played
by the Kalshi mid itself at a later hour (h=24 -> mid at 1h; h=1 -> mid at kickoff, last candle
ending at or before kickoff), same d, same validation window. Also reported: slope of the Kalshi
move (later mid − entry mid) on (book − entry mid); a slope near 1 means Kalshi moves to the
books, near 0 means it does not. If the later-Kalshi reference is also profitable, the edge is
timing, not information from the books.

## Null check

The same pipeline with book probabilities permuted across games within each week (seed
20261007). Its validation interval lower bound must not exceed 0; if it does, the pipeline is
broken and no result is reported.

## Decision

Tradable only if the real validation passes and the null does not. Anything else: no edge.
