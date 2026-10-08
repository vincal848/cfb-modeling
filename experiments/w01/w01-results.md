# W01 results

**Verdict: UNDERPOWERED, NOT RUN.** Protocol: [W01](../protocols/W01-protocol.md). No total was compared with any
wind figure.

Day-ahead wind forecasts exist only for 2024 and 2025 (Open-Meteo Previous Runs API returns nothing earlier).
Outdoor games with wind >= 15 mph and a closing total, using CFBD realized wind as the proxy for the forecast
count (counts only, from `experiments/w01/w01-sizing.json`):

| season | games with weather | outdoor with wind | windy (>= 15 mph) | windy with a closing total |
|---|---|---|---|---|
| 2024 | 3,218 | 3,146 | 274 | 135 |
| 2025 | 3,204 | 3,134 | 200 | 80 |
| total | | | | **215** |

The protocol's gate needs 860 games (56.6% unders against 52.38%, one-sided 5%, 80% power); 215 is 25% of that.
The practitioner edge cannot be tested at bet time with the data that exists. At 215 games the smallest
detectable under rate (80% power) is about 60.9% (52.38% + 2.49 x 3.4 points), far above the claimed 56.6%.

**Next:** log the Open-Meteo day-ahead forecast for every 2026 outdoor game from now on (forward-only, free).
By the end of 2026 that adds roughly 100 windy games; W01 becomes testable only after about three more seasons.
A cheaper question that does not need bet-time forecasts: is the market's total already adjusted for wind?
That needs the realized-wind history (CFBD, 2014-2025) and would be descriptive, not a
trading test.
