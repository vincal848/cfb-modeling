# K05 results

**Verdict: UNDERPOWERED, NOT RUN.** Protocol: [K05](../protocols/K05-protocol.md). No derivative price was read.

The derivative series are not in Kalshi's `/historical` archive; they exist only from the 2026 season. Settled events
to 2026-10-08 (counts in `k05-sizing.json`):

| family | settled events |
|---|---|
| full-game total | 656 |
| 1H total | 332 |
| 2H total | 146 |
| team total | 331 |
| 1H spread | 332 |

Overlap with a full-game ladder: 1H 332, team total 331, 1H + 2H both 146. The gate needs 620 games for a 5-cent
effect and 1,700 for 3 cents. Even the best-covered family reaches 54% of the 5-cent requirement, and the sample is
a single partial season with no earlier data to fit the dependence between halves.

**Next:** the 2026 season keeps adding about 55 games a week per family, so 1H + full reaches 620 around week 12 of
the 2026 season (late November) and the 2H and team-total families later. The forward logger (README) can snapshot
these ladders too if extended; until then there is nothing to test.
