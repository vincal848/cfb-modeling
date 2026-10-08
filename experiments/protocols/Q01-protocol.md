# Q01: maker-side quoting with a conservative fill model (I4)

Registered 2026-10-08, before any Kalshi trade tape was downloaded or any fill simulated.
**Trial ledger:** three declared cells.

Question: every taker rule so far dies on the spread. Does a resting bid, placed around a declared anchor and
filled only on a trade-through, earn money after maker fees on Kalshi 2025 CFB markets?

## Fill model (conservative on fills, but an upper bound overall)

- Tape: `/historical/trades` for the market, limited to [start - 6h, start) (CFBD kickoff). Pre-game only.
- A resting YES bid at price b fills on the first later trade with `yes_price < b` (strictly through the bid), for
  at most the printed size; a resting NO bid at n fills on a trade with `yes_price > 1 - n`. One contract per side
  per game, at most one fill per side.
- **Queue position is unknown and ignored**, so each fill is optimistic; nothing in the tape shows our order
  would have been ahead of others at the same price. All results are an upper bound on what a real maker earns.
  Quotes are placed at the start of the window and never cancelled or repriced.
- Fee: maker 0.0175 p (1 - p) per contract (K01). P&L per fill = settlement - price - fee.
- Adverse selection: for each fill at time t, fair(t + d) = last trade price at or before t + d (d = 5, 30, 60
  minutes; missing if t + d is after kickoff). Reported: mean of (fair(t + d) - price) for YES bids and
  (price - fair(t + d)) for NO bids, with game-block intervals. Descriptive.

## Cells (declared)

| cell | market | quotes | anchor |
|---|---|---|---|
| Q1 | game winner (home market, KXNCAAFGAME) | YES bid at a - 0.03, NO bid at (1 - a) - 0.03, floored to the cent | a = de-vigged CFBD consensus home win probability (a maker with an external book feed) |
| Q2 | same | same | a = Kalshi hourly mid at the last candle ending <= start - 6h (no look-ahead) |
| Q3 | K04 exact-margin ranges for keys +/-3, +/-7 (KXNCAAFSPREAD rungs |k| - 0.5, |k| + 0.5) | rest a YES bid joined at the lo-rung bid and a NO bid joined at 1 - the hi-rung ask (T-6h candle), only when the K04 model value q exceeds the net cost bid_lo - ask_hi plus both maker fees plus 0.01 | K04 kernel model |

Each Q3 leg is a separate contract; P&L is reported per fill and, descriptively, for games where both legs filled
(a naked leg is directional risk).

## Test and decision

- Pass = lower bound > 0 of the 95% game-block bootstrap (4,000 reps, seed 7) of P&L per fill, holm over the ledger
  total (p = share of bootstrap means <= 0).
- Nulls: (a) simulated efficient (martingale) tape, must not pass; simulated mean-reverting noise around a known
  anchor, must pass (tests). (b) Real data: anchors permuted across games within week, must not pass.
- 2025 is the only season; nothing was used to tune. A pass would mean "paper-quote forward", never "trade".
