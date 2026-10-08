# Research index: where an edge could come from

Started 2026-10-07, after [M01](../experiments/m01/m01-results.md) showed that B02 carries no
information beyond CFB closing lines: in every model-minus-market gap bucket, outcomes track
the market. So we stop trying to out-forecast the closing price. Each idea below targets a
**structural** source of mispricing instead: who trades, when, on which venue, and on which
contract.

Every idea gets a protocol in `experiments/protocols/` before its first look, a null that
must fail, and a results page. Its status here links to that page.

## Ideas

| # | Idea | Evidence | Our data | Test | Effort | Wave | Status |
|---|---|---|---|---|---|---|---|
| I1 | **Kalshi venue biases**: the favorite-longshot bias, takers losing to makers, miscalibration near expiry | Bürgi et al., *Makers and Takers: The Economics of the Kalshi Prediction Market* ([UCD WP2025_19](https://www.ucd.ie/economics/t4media/WP2025_19.pdf), [CEPR DP20631](https://cepr.org/publications/dp20631)): contracts under 10¢ lose >60%, those over 50¢ earn small positive returns, takers lose ~32% and makers ~10%. [arXiv 2607.14430](https://arxiv.org/abs/2607.14430): 23M Kalshi sports trades, calibrated mid-life but step-like in the last 10 minutes, parlays overpriced. [arXiv 2609.12878](https://arxiv.org/abs/2609.12878) (Polymarket): the bias shrinks once contracts are grouped by event | Kalshi 2025 CFB game markets: hourly candles + sampled trade tape | `k01`: returns by price × time to expiry × taker side; Sep–Oct select, Nov–Jan validate | S | 1 | ❌ [no edge](../experiments/k01/k01-results.md): best rule +0.4¢ in validation, interval [−10, +6]¢ (46 trades). **Lead:** contracts under 10¢ win 1–2% against a 4.4% price, i.e. a longshot bias in the tail, but the CFB sample is too small → I1b |
| I2 | **Kalshi vs sportsbook consensus**: when Kalshi and the books disagree, who's right? | Practitioner reports of 1–8 pt cross-venue gaps (non-academic, weak prior) | Kalshi bid/ask at T−24h and T−1h vs de-vigged CFBD 2025 lines | `k02`: outcome ~ logit(Kalshi) + logit(book); gap-trade P&L at real asks | S | 1 | ❌ [no edge](../experiments/k02/k02-results.md): validation −0.1¢/trade. Kalshi at T−1h is *more* informative than the CFBD consensus (coef 1.92 [0.32, 3.53] vs −0.94), so Kalshi isn't the dumb money; median spread 1¢ |
| I3 | **Beat the opener, not the close**: predict open→close movement and bet early | Coleman 2025, [*A predictive metamodel for college football*](https://lida.sport-iat.de/dfb/Record/4094978?lng=en), *J. Sports Analytics*: 5 of 29 rating systems combined, significant against the **opening** line in validation and test. Older work: no rating system beats the *final* spread | CFBD openers 2022+ (Bovada; DK/ESPN Bet from 2024), B02 | `m02`: close − open ~ B02 − opener; trade-at-opener P&L, closing-line value | S | 1 | ❌ [no edge](../experiments/m02/m02-results.md): 2023 +1.4¢/trade, interval [−2.4, +6.3]¢; slope flips sign 2022→2023 |
| I4 | **Market making** in thin games: quote around book fair value, earn the spread, avoid the taker fee | Bürgi et al.: makers are the profitable side; reported maker gains of ~+1.1%/trade after institutional LPs arrived. Observed CFB spreads of 20¢+ in small games | Kalshi order book and trade tape; fills simulated from trades (adverse selection is the risk) | Simulated quoting with an adverse-selection penalty; then forward paper quotes | M | 2 | — |
| I5 | **In-play overreaction** after surprise events | Norton, Gray & Faff (ODI cricket on Betfair, +20% after wickets); Angelini, De Angelis & Singleton ([Reading](https://research.reading.ac.uk/football-research/new-journal-article-informational-efficiency-and-behaviour-within-in-play-prediction-markets/)): prices overreact to surprise news; tennis: mispricing higher in-play than pre-match | P01 state machine + P02 EP, CFBD plays; Kalshi 1-min candles | Live win probability vs price path after scores and turnovers | L | 2 | — |
| I6 | **Low-attention cohorts**: FCS, G5 midweek, early season | Thin-market inefficiency; Kalshi volume varies ~1000× across games | Cohort labels (`evaluation/cohorts.py`), Kalshi volume | I1–I3 rerun by cohort (registered, not mined) | S | 2 | — |
| I7 | **Matchup / intransitivity** effects a single spread can't express | [arXiv 2510.20454](https://arxiv.org/html/2510.20454v1) (tennis GNN, significant selective returns); intransitive EPL triads with profitable simple rules | P03/P04 shares and EPA | Style-interaction features vs opener residuals | M | 3 | — |
| I8 | **Derivative consistency**: halves, quarters and team totals vs the full-game price | The same no-arbitrage logic as the parlay overpricing in 2607.14430 | Kalshi KXNCAAF1H*/2H*/TEAMTOTAL/quarter series | Implied full-game distribution from each contract family; trade outliers | M | 2 | — |
| I9 | **LLM news agent** (QB status, injuries, weather) for speed, not forecasting | [WC2026-Agents](https://arxiv.org/abs/2607.17765), [LLM-SoccerArena](https://arxiv.org/abs/2607.24573): frontier LLMs don't beat markets; web access improves Brier by only ~0.02 | Live only | Prospective log of news time vs price move | M | 3 | low prior |
| I1b | **Longshot bias pooled across Kalshi sports**: sell sub-10¢ contracts (buy ≥90¢) in game markets for every league, to get enough events to test the tail bias K01 hinted at | K01 calibration tail; Bürgi et al. | Kalshi `/historical/markets` + candles for NFL/NBA/MLB/NHL/CBB game series | Same rule as K01, pooled, one validation split | S | 2 | ❌ [no edge](../experiments/k03/k03-results.md): 14,004 events / 7 leagues; best rule (≥95¢, 6h) +1.3¢ [−0.7, +3.3]¢ on 148 validation trades; at 24h favorites *lose* (−3.2¢ at ≥85¢) |
| E01/E02 | **EPA/play team rating** (report idea 1), Kalman opponent adjustment, blended with B02 | [CFB modeling report](../reports/College%20football%20modeling%20vs%20betting%20lines.md) | P02 EP folds, exact+events plays | M02 harness | M | — | ❌ [no edge](../experiments/e02/e02-results.md): efficiency alone predicts margins worse than final scores (dev MAE 13.54 vs 13.10) and gets ≈0 blend weight |
| I10 | **Sizing** under estimation error | Baker & McHale, *Optimal betting under parameter uncertainty* (shrunken Kelly beats Kelly out of sample); Meister, [arXiv 2412.14144](https://arxiv.org/abs/2412.14144) (Kelly in prediction markets) | — | Applied to survivors only | S | — | — |
| I11 | **Key-number mass in Kalshi CFB spread ladders**: adjacent rungs price the exact-margin probability; are the jumps at 3 and 7 under-weighted? | Football margin pmf has spikes at 3 and 7 (CFBD 2014-2024); Kalshi lists "wins by over k.5" rungs | CFBD margins + Kalshi 2025 spread-ladder candles | [`k04`](../experiments/protocols/K04-protocol.md): kernel P(m=k given spread) vs two-leg range quotes at T-6h, after fees; nulls on simulated ladders and neighbouring cells | M | 2 | ❌ [no edge](../experiments/k04/k04-results.md): 0 trades on 1,508 quoted 2025 ladders, best net edge -0.9¢; mid-implied exact-margin probability 5.3% vs model 5.7% vs realized 5.9%, while spread plus fees cost 8.4¢ above the mid. 2026 holdout unopened |
| I12 | **Forecast wind on totals** (bet-time information only) | Practitioner 56.6% unders at 13+ mph uses realized wind | Open-Meteo day-ahead forecast (2024+ only), CFBD venues | [`w01`](../experiments/protocols/W01-protocol.md) | S-M | 2 | ⏸ [underpowered, not run](../experiments/w01/w01-results.md): 215 windy outdoor games with a total in 2024-25 vs 860 needed |
| I13 | **Structural-bias sweep**: home-field after 2020, big favorites, two ATS losses (national-TV over not run) | Folklore / JSE-style cells; Winkelmann et al. 2024: such biases did not persist | CFBD lines 2014-2025 | [`s01`](../experiments/protocols/S01-protocol.md): three cells, Holm over the 15-test ledger, 2024-25 sealed | S | 2 | ❌ [no edge](../experiments/s01/s01-results.md): all three cells lose after costs in 2014-2023 (home-field -2.5¢, big favorites -1.4¢, two ATS losses -2.1¢ per bet); none survives Holm at family size 15; 2024-25 sealed |
| I14 | **One-time-zone travel cell** (late-season away underdogs) | JSE 2017 (cell definition is our reading) | CFBD lines, `/teams` time zones | [`t01`](../experiments/protocols/T01-protocol.md) | S | 2 | ⏸ [underpowered, not run](../experiments/t01/t01-results.md): 643 cell games in 2014-2023 vs 2,240 needed |

## Not pursued

- **Wong teasers in CFB** (S01 check, 2014-2025 margins): the four teased legs through 3 and 7 win 70.6% of 1,453
  games (fav -7.5/-8.5 to -1.5/-2.5: 69.0% / 69.7%; dog +1.5/+2.5 to +7.5/+8.5: 72.8% / 71.0%), against the 73.9%
  per leg a two-team 6-point teaser at -120 needs. CFB key numbers are thinner than the NFL's.
- **I3 in-play under-reaction and I4 market making** (wave 2, not started): CFBD plays carry the game clock but no
  wall-clock time, so Kalshi minute candles cannot be aligned to plays without first building and validating a
  stoppage model (the protocol's own "main risk"); maker fills would be simulated from trades with unknown queue
  position, biased in favour of the strategy. Both need a timestamp-alignment protocol before any test.

- **Out-forecasting the closing price** with a team-strength model: M01, no edge.
- **Plain Kalshi/Polymarket arbitrage bots**: crowded, latency-bound, and every public "arb
  finder" already scans it.

## Data notes

- The Kalshi public API (no key) archives settled markets, trades and candlesticks under
  `/historical/*`. The 2025 CFB season is there: 1,872 game-winner markets (two per game),
  10,071 spread and 7,777 total markets. Kalshi CFB markets start with the 2025 season, so
  any Kalshi-only test has one season of history plus the live 2026 season.
- `src/cfb/ingestion/kalshi.py` is read-only, with cached ledger rows under provider
  `KALSHI`. It has no auth and no order calls. Trading stays manual.
- **CFBD closing lines reach back to 2014** (checked 2026-10-08 on the cached `/lines`
  payloads, FBS games with a spread: 2014 865, 2015 832, 2016 866, 2017 873, 2018 869,
  2019 881, 2020 567, 2021 887, 2022 1,459, 2023 1,413, 2024 1,557, 2025 1,597). Before 2021
  the books are CFBD's `consensus`, `teamrankings`, `numberfire` (+ `Caesars` from 2018,
  `Bovada` from 2019): the time of the quote is not documented, so "closing" is an
  assumption. Real sportsbooks with an *opener* appear only from 2021 (Bovada, William Hill,
  later DraftKings and ESPN Bet). Totals are present for 760-880 games a year from 2014.
- **The CFBD `/games/weather` endpoint works with the existing key** (HTTP 200 and a full
  `windSpeed` column for 2015 week 5, 59 games, and 2019 week 5, 53 games; the cached
  2024 week 5 returned 225/225). It is a record of the conditions at the game, not a
  forecast, so using it on a bet would be look-ahead. Bet-time wind needs a forecast
  archive (Open-Meteo, see W01).
- **Kalshi CFB ladders (2025 season, archive)**: 766 spread events and 769 total events;
  a spread ladder is "Team wins by over k.5 points" for each side (494 events have both
  teams' ladders), a total ladder has 5-17 rungs. Only the markets were counted when
  sizing K04; no price or outcome was looked at.
- `CFB_DATA_DIR` points a git worktree at another clone's `data/` so the request ledger is
  shared (default: `<repo>/data`).
- `experiments/trials.csv` is the ledger of primary market tests registered in this repo (protocol, date, number of
  tests). Holm families take their size from it. Raw data pulls are logged in the SQLite request ledger
  (`raw_requests`) as before.
