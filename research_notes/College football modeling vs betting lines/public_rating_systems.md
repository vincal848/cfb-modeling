# Public college football rating/prediction systems: methodology and tracked performance vs the line

Source note on the Prediction Tracker (PT) numbers below: I downloaded the raw season-total tables directly (URL pattern `https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=YY`, YY = 16..26) and parsed them; every number below is copied from those tables, not from a summarizer. Columns on PT: "Pct. Correct" (straight-up), "Against Spread", "Absolute Error" (= average |prediction − actual margin|), "Bias" (= average(prediction − actual)), "Mean Square Error", games, SU W/L, ATS W/L. PT notes "Retrodictive records are found by taking the ratings from the current week and applying them to the entire season to date" — the season-total tables are the predictive (made-before-the-game) records. Universe is FBS (NCAA IA) games. — [PT 2024 results](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=24)

## Q1. Which systems are independently tracked vs the line, and what are their multi-season records?

### Takeaway
The Prediction Tracker is the only systematic independent tracker found. Over 2016–2025 no tracked public system beats the market in any meaningful way: the best 10-season ATS records are ~50.4–51.1% (below the ~52.4% break-even at -110), and the updated/closing line has the lowest MAE in almost every season (≈11.85–12.9 pts) versus ≈12.0–13.5 for the best computers. ESPN FPI and Sagarin are the closest computers on MAE; SP+ is **not** tracked by PT at all.

### Cited Findings

**PT season totals, selected systems (ATS = against-spread %, ATS W-L excludes pushes/no-pick games; MAE = absolute error in points)** — all from [PT results pages](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=24) for the given season (change `year=`):

| Season (games) | Line (updated) MAE / ATS | Line (opening) MAE / ATS | ESPN FPI MAE / ATS (W-L) | Sagarin Points MAE / ATS | Sagarin Ratings MAE / ATS | TeamRankings MAE / ATS | FEI Projections MAE / ATS | Massey Ratings MAE / ATS | Massey Consensus MAE / ATS | System Average MAE / ATS |
|---|---|---|---|---|---|---|---|---|---|---|
| 2016 (761) | 12.8984 / 0.53846 | n/a | 13.1888 / 0.53369 (396-346) | 13.3936 / 0.50000 | 13.3559 / 0.50674 | 13.3436 / 0.50474 | 14.7546 / 0.48607 | 13.3559 / 0.53576 | 13.7626 / 0.51009 | 13.1610 / 0.51012 |
| 2017 (780) | 12.2750 / 0.53077 | 12.4051 / 0.51192 | 12.4195 / 0.51248 (390-371) | 12.5081 / 0.52431 | 12.6038 / 0.53482 | 12.6187 / 0.51455 | 13.4938 / 0.50877 (243 g) | 13.3692 / 0.49014 | 15.0957 / 0.48620 | n/a |
| 2018 (773) | 12.6449 / 0.55906 | 12.7723 / 0.49601 | 12.8816 / 0.51316 (390-370) | 12.9961 / 0.49211 | n/a | 12.8431 / 0.53386 | 14.1339 / 0.48750 | 13.2540 / 0.48620 | 13.8362 / 0.49671 | 12.9581 / 0.49934 |
| 2019 (774) | 12.2054 / 0.53406 | 12.2532 / 0.49848 | 12.5460 / 0.48231 (368-395) | 12.5064 / 0.50850 | 12.4075 / 0.52026 | 12.3921 / 0.51394 | 13.0232 / 0.54018 (410-349) | 12.7143 / 0.50262 | 13.3102 / 0.50588 | 12.3399 / 0.50916 |
| 2020 (534) | 12.8951 / 0.49407 | 13.4551 / 0.48253 | 13.0050 / 0.51243 (268-255) | 13.7995 / 0.48859 | n/a | 13.0077 / 0.51657 | 13.2866 / 0.51154 | 13.6463 / 0.50000 | 13.4967 / 0.52099 | 13.0749 / 0.48479 |
| 2021 (770) | 12.6247 / 0.50000 | 12.7526 / 0.50000 | 13.0218 / 0.46772 (355-404) | 13.3517 / 0.45850 | 13.2541 / 0.44737 | 13.1130 / 0.48271 | 13.0317 / 0.50412 | 13.4370 / 0.48289 | 13.5983 / 0.48748 | 12.9646 / 0.48617 |
| 2022 (776) | n/a in parse | 12.0805 / 0.50779 | 12.2733 / 0.50526 (384-376) | 12.5489 / 0.50392 | 12.4622 / 0.50651 | 12.3957 / 0.47895 | 12.6622 / 0.49433 | 12.4786 / 0.53194 (408-359) | 13.0411 / 0.47005 | 12.4338 / 0.49935 |
| 2023 (792) | 12.1237 / 0.57102 | 12.1818 / 0.51192 | 12.4915 / 0.48258 (374-401) | 12.5538 / 0.50129 | 12.5000 / 0.49096 | n/a | 12.6829 / 0.49347 | 12.7605 / 0.50000 | n/a | 12.5147 / 0.49354 |
| 2024 (799) | 12.0469 / 0.52609 | 12.2196 / 0.47313 | 12.3612 / 0.52235 (409-374) | 12.2884 / 0.51596 | 12.3412 / 0.50447 | 12.4332 / 0.48579 | 12.7892 / 0.48391 | 12.9585 / 0.49170 | 13.6064 / 0.44814 | 12.5583 / 0.46999 |
| 2025 (808) | 11.8496 / 0.47395 | 11.8948 / 0.51807 | 12.2506 / 0.48198 (361-388; 762 g) | 12.0909 / 0.51580 | 12.0769 / 0.52785 (417-373) | 12.1277 / 0.51088 | 12.3052 / 0.50708 | 12.3949 / 0.49873 | 12.7072 / 0.50127 | 11.9783 / 0.52785 |
| 2026 thru 10-04 (271) | 11.5074 / 0.53968 | 11.9723 / 0.49519 | 11.8232 / 0.48828 | 11.7735 / 0.55472 (147-118) | 11.9304 / 0.53962 | 11.8842 / 0.48289 | 12.3893 / 0.51341 | 12.1205 / 0.47925 | 13.0906 / 0.48679 | 12.0182 / 0.46038 |

("n/a" = system absent that season or row not captured by my parser.) Other tracked CFBD-adjacent/other systems: "Beck Elo" (PT's own Elo) MAE 13.1126 / ATS 0.48724 in 2024 and 12.5122 / 0.49874 in 2025; "Computer Adjusted Line" 12.0839 / 0.48473 in 2024; "Dokter Entropy" 12.0366 / 0.50317 in 2025 and 11.5832 / 0.53612 in 2026-to-date — [PT 2024](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=24), [PT 2025](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=25), [PT 2026](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=26)

**Multi-season aggregates I computed from the PT tables (sum of ATS W-L; game-weighted MAE; only systems present in every season):**
- 2016–2025, top 10-season ATS: PI-Rate Bias 3771-3612 (51.08%), Donchess Inference 3694-3618 (50.52%), Keeper 3721-3645 (50.52%), Pi-Ratings Mean 50.39%, Massey Ratings 3726-3697 (50.20%), Sagarin Points 3725-3704 (50.14%), FEI Projections 3212-3197 (50.12%), ESPN FPI 3695-3680 (50.10%), Dokter Entropy 49.74%, System Median 49.58%, Beck Elo 3595-3834 (48.39%). Lowest weighted MAE among computers 2016–2025: Dokter Entropy 12.596, System Median 12.622, ESPN FPI 12.631, Pi-Ratings Mean 12.726, Sagarin Points 12.765. — computed from [PT tables](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=24)
- 2021–2025: Massey Ratings 1942-1934 (50.10%), Sagarin Points 49.94%, FEI Projections 49.63%, Sagarin Ratings 49.57%, System Average 49.55%, ESPN FPI 1883-1943 (49.22%), Beck Elo 48.52%. Weighted MAE: Line (opening) 12.222; System Average 12.486; ESPN FPI 12.479; Sagarin Ratings 12.521; Sagarin Points 12.560; FEI Projections 12.679; Massey Ratings 12.802. — computed from [PT tables](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=25)

**SP+ performance (self-reported / ESPN, not independently tracked by PT):**
- Connelly (Sept 2021): "SP+ is generally better against the spread, FPI is generally better in terms of absolute error." — [Bill Connelly on X](https://x.com/ESPN_BillC/status/1440001228017111044?lang=en)
- 2021 Week 1: SP+ "went just 22-22-2 against the Caesars closing line last week, 20-24-2 against the midweek spread"; SP+ average absolute error "13.2 points per game", second only to FPI among tracked systems that week. — [ESPN, SP+ vs spreads Week 1](https://www.espn.com/college-football/insider/story/_/id/32140951/how-sp+-computer-ratings-fared-vs-betting-spreads-cfb-week-1-games)
- 2024 after 4 weeks: "54% against the early spread so far this year" — [Connelly on X](https://x.com/ESPN_BillC/status/1837857641151778937)
- Historical claim: S&P+ had "52 to 54 percent success over a full season against the Las Vegas point spread" — [Saturday Down South](https://www.saturdaydownsouth.com/?p=256192) (secondary; no seasons given). A 2020 interim figure of 52.1% ATS was reported in search snippets but I could not open the primary.
- Note the distinction Connelly himself makes between grading vs **closing** line and vs **midweek** line (22-22-2 vs 20-24-2 in the same week). — [ESPN](https://www.espn.com/college-football/insider/story/_/id/32140951/how-sp+-computer-ratings-fared-vs-betting-spreads-cfb-week-1-games)

**ESPN FPI self-reported accuracy:** the FPI favorite won "75 percent of FBS-versus-FBS games" over 10 seasons, "comparable to the Vegas closing line"; teams given 70–80% won "73 percent of the time." — [ESPN Stats & Info, inside look at College FPI](https://africa.espn.com/blog/statsinfo/post/_/id/122612/an-inside-look-at-college-fpi)

**CFBD / community:** CFBD's own "pregame win probability" is market-derived: "derived from the available point spread and the historical relationship between spreads and game outcomes. This is a market-based estimate rather than a CFBD team-rating forecast." — [CFBD win probability docs](https://api.collegefootballdata.com/win-probability). A CFBD-blog GBDT spread model (714 features incl. pregame spreads, recruiting, returning production, opponent-adjusted stats; train <2019, test 2019+) reported spread RMSE 14.79 train / 15.72 test; no ATS figures published. — [CFBD/RAD blog, predicting spreads GBDT](https://radsportsanalytics.com/blog/predicting-spreads-gbdt/). A CFBD contest winner (2022, 726 games: 1st SU, 3rd ATS, 1st MAE) blended a preseason model with an in-season model and explicitly incorporated Vegas lines; no numbers published. — [Lessons from picking the 2022 CFB season](https://radsportsanalytics.com/blog/lessons-from-picking-the-2022-cfb-season/). Same blog cites Vegas line MAE "12.6". — [search snippet of CFBD blog](https://blog.collegefootballdata.com/lessons-from-picking-the-2022-cfb-season/)

### Inferences
- PT's ATS reference line appears to be the **"Line (Midweek)"**: it is the only line row with no ATS % and only a handful (2–27) of decided games, while "Line (updated)" and "Line (opening)" have 300–670 ATS-decided games — consistent with grading every system against the midweek line and dropping games where the prediction equals it. PT does not document this on the pages I could reach, so treat as inference. This means PT ATS% is vs a midweek line, not closing; beating it is easier than beating the close (the "Line (updated)" itself goes 52.6–57.1% vs it in 2016–2019/2023).
- Because the updated (closing) line wins MAE nearly every season, published computer ratings are best viewed as **features** to combine with the line, not stand-alone betting signals. "System Average"/"System Median" (ensembles) beat most individual systems on MAE but not ATS.
- Per-season ATS spikes (e.g., FEI 54.0% in 2019, Massey 53.2% in 2022, Sagarin Points 55.5% early 2026) mean-revert across seasons — classic multiple-testing selection; ~800 games/season gives an ATS standard error ≈1.8 pp.

### Gaps
- PT does not track SP+; no independent multi-season SP+ ATS/MAE record found. Connelly's year-end ATS numbers are scattered on X/ESPN Insider (paywalled) and were not retrievable.
- PT does not publish an explicit "MAE vs line" column (deviation of each system from the line) on the season-total page; only MAE vs actual result and bias. A "Second Half" tab exists (type=2) that I did not parse.
- PT does not document which sportsbook/time the opening/midweek/updated lines come from.
- No independent tracking found for PFF power rankings, CFBD Elo/SRS, or postgame win expectancy.

## Q2. How each system works, and which components are documented as most predictive

### Takeaway
The strongest public systems are play-by-play (SP+, FPI) or drive-based (FEI) opponent-adjusted efficiency models with garbage-time filtering and a preseason prior; score-only systems (Sagarin, Massey) use margin with diminishing returns. Success rate and explosiveness are the documented core of SP+; FPI is EPA-based with blowout capping and explicit rest/travel terms.

### Cited Findings

**SP+ (Bill Connelly, ESPN)**
- "SP+ is a tempo- and opponent-adjusted measure of college football efficiency. It is a predictive measure of the most sustainable and predictable aspects of football, not a résumé ranking." — [ESPN 2025 preseason SP+](https://www.espn.com/college-football/story/_/id/45966848/college-football-2025-preseason-sp+-rankings)
- Created at Football Outsiders in 2008; name from Success Rate and IsoPPP; built on five factors: efficiency, explosiveness, field position, finishing drives, turnovers. — [Saturday Down South](https://www.saturdaydownsouth.com/?p=256192)
- Five-factor win rates (Connelly's research, reported secondhand): winning explosiveness (PPP) → win 86%; efficiency (success rate) 83%; finishing drives (points per trip inside the 40) 75%; turnover margin 73%; field position 72%. — [The Sports Arsenal citing Connelly](https://thesportsarsenal.com/tag/bill-connelly/)
- Garbage time (older S&P+ definition): a game is not within 28 points in Q1, 24 in Q2, 21 in Q3, or 16 in Q4; those plays are filtered. — [Roll Bama Roll 2014 primer](https://www.rollbamaroll.com/2014/8/21/6044917/2014-alabama-crimson-tide-football-advanced-stats-primer) (secondary and dated; current SP+ garbage-time rule not found in a primary).
- Turnovers: S&P+ "measures four of five factors... efficiency, explosiveness, field position, and finishing drives" (turnovers treated separately as luck-prone). — [Football Study Hall on F/+](https://www.footballstudyhall.com/2014/12/11/7377487/college-football-ratings-fplus-spplus)
- 2025 change: "after quite a bit of experimenting, I ended up tamping down the overall top-to-bottom spread of points." — [ESPN 2025 preseason SP+](https://www.espn.com/college-football/story/_/id/45966848/college-football-2025-preseason-sp+-rankings)

**Postgame win expectancy (Connelly)**: "Given your success rates, big plays, field position components, turnovers, etc., you could have expected to win this game X% of the time"; it has nothing to do with pregame projections or opponent adjustments. — [search result summarizing Connelly, e.g. Saturday Down South](https://www.saturdaydownsouth.com/lsu-football/unlikeliest-cfb-win-of-the-year-lsu-florida-game-produced-incredible-stat/)

**FEI (Brian Fremeau, bcftoys.com)**
- "opponent-adjusted possession efficiency data representing the scoring advantage per non-garbage possession a team or unit would expect to have on a neutral field against an average opponent"; OFEI/DFEI/SFEI unit ratings; schedule strength and strength-of-record. — [BCFToys 2025 FEI](https://www.bcftoys.com/2025-fei/)
- Garbage possessions excluded: (1) ≤2-play clock-kills ending a half (or 2nd half tied) without turnover/score/FG try; (2) any second-half possession where "eight times the number of the losing team's remaining possessions plus one is less than the losing team's scoring deficit"; (3) ≤2-play clock-kills by a team trailing by >8 to end the game; (4) end-of-game clock-kills by a team leading by ≤8. — [BCFToys notes](https://www.bcftoys.com/notes)
- ~20,000 FBS-vs-FBS possessions considered per season. — [search summary of FEI description](https://www.saturdaydownsouth.com/florida-football/florida-ranks-no-60-fei-ratings)

**ESPN FPI**
- Offense/defense/special-teams components = points contributed to net margin vs average FBS opponent on a neutral field; built from EPA "per game", which "takes into account yards, turnovers, red zone efficiency and more"; EPA "individually adjusted for each game based on the strength of the opposing unit faced and where the game is played"; "applies a capping of sorts to each of these components to minimize effects of blowout games"; rest ("an additional 5 1/2 days of rest more than your opponent is worth one point per game"), travel ("every additional 1,000 miles traveled more than your opponent costs you a point"), and game type are modeled. — [ESPN Stats & Info](https://africa.espn.com/blog/statsinfo/post/_/id/122612/an-inside-look-at-college-fpi)

**Football Outsiders F/+**: simple combination (average) of S&P+ and FEI, requested by Aaron Schatz; FEI is drive-level, S&P+ play-level. — [Bless Your Chart Substack](https://blessyourchart.substack.com/p/149-a-conversation-about-college); [Football Study Hall](https://www.footballstudyhall.com/2014/12/11/7377487/college-football-ratings-fplus-spplus)

**Massey**: least-squares rating on scoring margin and opponent ratings; "diminishing returns" so blowouts are not much better than solid wins; team-specific home advantage estimated from home vs road performance; preseason ratings from a weighted average of previous years' final ratings, whose effect is "damped out completely" as the season progresses. Massey Consensus/composite averages many ranking systems. — [Massey description (search summary of masseyratings.com/theory/massey.htm)](https://masseyratings.com/theory/massey.htm) (site behind a Cloudflare challenge; text not directly read)

**Sagarin**: overall = combination of Predictor (scores only), Golden Mean (scores only, different undisclosed method) and Recent (recent games weighted more); "Elo chess" uses W/L only; formulas undisclosed. — [Wikipedia / summaries](https://en.wikipedia.org/wiki/Jeff_Sagarin)

**CFBD models**: CFBD documents PPA, win probability, WEPA (opponent-adjusted efficiency), Elo, SRS, CORE ("efficiency after play-context and opponent adjustment... points above average per 100 plays"); "PPA, win probability, WEPA, Elo, SRS, and CORE are proprietary CFBD models." Elo updates on result, rating gap, scoring margin and home field; exact constants not public. SRS = scoring margin adjusted for schedule and home field. — [CFBD methodology overview](https://api.collegefootballdata.com/methodology-overview); [CFBD Elo page](https://api.collegefootballdata.com/elo-ratings); [CFBD SRS page](https://api.collegefootballdata.com/srs-ratings). The older CFBD tutorial Elo used K=25, 1500 FBS / 1200 non-FBS start, no MOV, no HFA, no seasonal regression. — [Talking Tech: Elo](https://radsportsanalytics.com/blog/talking-tech-elo-ratings/)

**cfbfastR**: R wrapper around the CFBD API providing play-by-play with open-source EPA/WP models (benchmarking those metrics); not itself a rating system. — [cfbfastR GitHub](https://github.com/saiemgilani/cfbfastR)

### Inferences
- Success rate (efficiency) and explosiveness are the components with the strongest documented association with winning; turnovers are deliberately down-weighted/separated in SP+ because they are noisy. FPI caps blowouts rather than dropping garbage time; FEI and SP+ drop garbage possessions/plays.
- Home field: FPI and Massey document it (FPI also rest and travel); SP+ projections apply a home-field adjustment but I found no primary statement of its size.

### Gaps
- No primary current (2023–2026) SP+ methodology document with garbage-time thresholds, component weights, or HFA value was retrievable (ESPN's standalone SP+ explainer URL returned 404).
- TeamRankings and PFF power rankings/grades: no methodology documentation found in this pass.
- No well-documented open-source CFB model with a published multi-season ATS backtest found (GitHub search surfaced only cfbfastR itself).
- "Havoc" and "turnover luck regression" predictive value: no primary quantitative source found.

## Q3. Preseason ratings and how fast the prior fades

### Takeaway
SP+ and FPI both start from prior-season performance + returning production/starters + recruiting (+ coaching tenure for FPI) and fade the prior through the season; SP+'s prior weight drops sharply after a team's fourth game. Massey damps the prior out completely; Sagarin/FEI decay schedules are undocumented.

### Cited Findings
- SP+ preseason = returning production, recent recruiting, recent history; last year's SP+ adjusted for returning production is "about two-thirds" of the formula; recruiting uses the past few classes with diminishing weights (most recent heaviest); recent history ≈ previous four seasons. Transfers' prior production is credited to the new team; transfers up from lower divisions get half credit. — [ABC7/ESPN returning production 2025](https://abc7news.com/15951013); [ESPN spring SP+ 2025 via ABC7](https://abc7news.com/post/spring-update-2025-college-football-sp-rankings-every-fbs-team/16504408/)
- Returning production "correlate[s] most strongly to year-to-year improvement and regression"; national average returning production fell from 76.7% (2021) to 51.3% (2026) with the portal. — [ESPN 2025 preseason SP+](https://www.espn.com/college-football/story/_/id/45966848/college-football-2025-preseason-sp+-rankings); [ESPN final 2026 preseason SP+](https://africa.espn.com/college-football/story/_/id/49593338/final-preseason-college-football-sp+-rankings-takeaways-2026)
- SP+ fade: preseason numbers "slowly phased out from week to week" and their weight "drops considerably after four games." — [ESPN search summaries of Connelly's in-season SP+ articles](https://www.espn.com/college-football/story/_/id/46128861/2025-college-football-sp+-rankings-all-136-fbs-teams)
- SP+ 2025 preseason accuracy: "Of last year's projected top-15 teams in SP+, seven finished within one (regular-season) win of their August projections." — [ESPN final 2026 preseason SP+](https://africa.espn.com/college-football/story/_/id/49593338/final-preseason-college-football-sp+-rankings-takeaways-2026)
- FPI preseason: prior performance (most recent year counts "almost twice as much"), returning starters (QB "about 3.3 points per game"), recruiting (ESPN, Rivals, Scouts, Phil Steele), coaching tenure (new coach → slight regression to mean); prior "declines in weight as the season progresses" but "never completely disappears." — [ESPN Stats & Info](https://africa.espn.com/blog/statsinfo/post/_/id/122612/an-inside-look-at-college-fpi)
- Massey: preseason = weighted average of prior final ratings, "damped out completely" as season progresses. — [Massey description](https://masseyratings.com/theory/massey.htm)
- PT data show "FEI Projections" were tracked on only 243 games in 2017 and 621–672 in 2018/2021/2022 vs ~780 for others, suggesting FEI projections are not published for all weeks/games. — [PT 2017](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=17)

### Inferences
- FPI keeps a permanent prior; SP+ keeps a reduced prior after week 4; the portal era (returning production ~51%) likely makes priors less informative than in 2021 — a reason to re-estimate prior weights on recent seasons rather than reuse older calibrations.

### Gaps
- No exact week-by-week prior weight schedule published for SP+ or FPI; FEI preseason method and decay not found in the pages retrieved.

## Q4. Weekly (past-only) vs end-of-season ratings — leakage relevance

### Takeaway
For backtesting, the only clean past-only sources are the systems' actual pregame predictions (PT archives them per game and season) or rating snapshots dated before each week. Many convenient data endpoints expose final/end-of-season ratings, which leak.

### Cited Findings
- PT tables are predictive records of pregame predictions; it separately computes "retrodictive" records using current-week ratings applied to the whole season — i.e., PT distinguishes the two. — [PT 2024](https://www.thepredictiontracker.com/ncaaresults.php?type=1&year=24)
- CFBD Elo is "a sequential team-strength rating where each completed game updates the two teams' pregame ratings" (pregame ratings by game). — [CFBD Elo](https://api.collegefootballdata.com/elo-ratings)
- CFBD SRS evaluates "the network of game results together" (a simultaneous fit — season-level unless snapshotted). — [CFBD SRS](https://api.collegefootballdata.com/srs-ratings)
- CFBD's pregame win probability is spread-derived, so using it as a feature is equivalent to using the line. — [CFBD win probability](https://api.collegefootballdata.com/win-probability)
- SP+ and FPI are published weekly in-season by ESPN (weekly SP+ rankings articles, e.g. after Week 5); preseason SP+ is published in multiple versions (spring/May and final August). — [ESPN 2025 SP+ rankings](https://www.espn.com/college-football/story/_/id/46128861/2025-college-football-sp+-rankings-all-136-fbs-teams); [ESPN 2025 final preseason](https://www.espn.com/college-football/story/_/id/45966848/college-football-2025-preseason-sp+-rankings)

### Inferences
- CFBD's `/ratings/sp`, `/ratings/srs`, `/ratings/fpi` style endpoints should be treated as end-of-season unless a week parameter/snapshot is confirmed; joining season-final SP+/SRS to that season's games is look-ahead leakage. Elo pregame values are the safest CFBD rating feature. PT's per-game prediction archive is a ready leakage-free source for FPI, Sagarin, Massey, FEI, TeamRankings predictions.
- Even weekly SP+ can be revised (e.g., 2025 rescaling of point spread), so archived snapshots matter more than re-pulled history.

### Gaps
- Could not confirm from CFBD docs whether its SP+/FPI endpoints are week-indexed or end-of-season only (methodology overview does not cover them).
- No information found on whether Sagarin/Massey publish historical weekly snapshots (Massey site blocked by Cloudflare challenge; not bypassed).
