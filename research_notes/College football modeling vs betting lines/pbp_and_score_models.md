# Football (NFL/CFB) modeling: play-by-play efficiency ratings, QB/personnel adjustments, and score-distribution models vs betting lines

Scope note: about 20 search/fetch calls. Several primary pages could not be fetched (404/403), and many search results were low-quality SEO or AI-generated betting content. Sources are tagged **[PEER-REVIEWED]**, **[PREPRINT]**, **[PRACTITIONER]** (analytics blogs, model builders, betting media) or **[LOW-QUALITY/UNVERIFIED]**. Anything I could not source is in Gaps.

## Q1. Which play-by-play metrics best predict future margin, and how much do opponent adjustment and garbage-time filtering add?

### Takeaway
Practitioner evidence agrees that per-play EPA, especially offensive EPA, predicts future margin better than raw results. Gains from reweighting, garbage-time handling and opponent adjustment are real but small, on the order of a few percent of out-of-sample R². For CFB, the standard public opponent adjustment is ridge regression on team offense/defense dummies plus home field, but I found no published validation of its predictive lift over raw EPA. I found no peer-reviewed study comparing EPA, success rate and DVOA on week-to-week predictiveness.

### Cited Findings
- **Offense more stable than defense [PRACTITIONER]:** nfelo reports offensive EPA/play is "stickier" across windows than defensive EPA, and that weighting offensive EPA 1.6 to defensive EPA 1.0 works best for predicting future net EPA — [nfelo EPA tiers](https://www.nfeloapp.com/nfl-power-ratings/nfl-epa-tiers/)
- **Weighted EPA (WEPA) [PRACTITIONER, Sept 5 2020, 1999–2019 data]:**
  - Target is out-of-sample R² on point differential.
  - Validation: games 1–8 predict games 9–16 margin; 50 random within-season splits; week 17 predicting the next season.
  - Down-weights recovered fumbles and plays at extreme win probability (a continuous bell-curve weight on win probability, not a hard cutoff). Up-weights close-game plays. Scales completions/incompletions by depth of target.
  - Uses separate offensive and defensive weights. Interceptions are discounted a little for offense and heavily for defense.
  - Reports about a 3.75% median lift over plain EPA and says it beats DVOA, especially in weeks 3–12 and year over year — [nfelo WEPA methodology](https://www.nfeloapp.com/analysis/weighted-EPA-methodology-and-performance/)
  - A search snippet of an earlier version cites a 14% predictive improvement, which conflicts with the 3.75% figure. It probably refers to a different version or test — [nfelo WEPA (search snippet)](https://www.nfeloapp.com/analysis/weighted-epa-methodology-and-performance)
- **WEPA ported to CFB [PRACTITIONER]:** CollegeFootballData.com publishes WEPA and adjusted metrics for college — [CFBD WEPA docs](https://api.collegefootballdata.com/wepa.md); [CFBD PPA (predicted points added) docs](https://apinext.collegefootballdata.com/ppa.md)
- **Garbage-time filtering [PRACTITIONER / LOW-QUALITY, source attribution unclear]:**
  - A search-result summary (aggregator; original post not retrieved) says typical garbage-time filters do not improve out-of-sample predictive power with nflfastR's updated EP model the way they did with older models.
  - The same summary reports a slight signal for a 10–90% win-probability cutoff with median EPA and 20–80% with total EPA.
  - It also claims year-over-year correlation of context-adjusted offensive EPA is about 1.5x that of raw EPA — [MetricGate EPA context](https://metricgate.com/docs/gridiron-epa-per-play-context/). Treat all three as unverified.
- **ESPN FPI [PRACTITIONER, ESPN methodology]:** FPI is built on team EPA/play adjusted for "trash time" and opponent strength — [ESPN FPI methodology](https://africa.espn.com/nfl/story/_/id/13539941/how-espn-nfl-football-power-index-was-developed-implemented)
- **CFB ridge opponent adjustment [PRACTITIONER, Bud Davis, CFBD blog, Oct 12 2021]:**
  - Design: dummy columns for each FBS team's offense and defense plus an HFA column (+1 home offense, −1 away, 0 neutral), 261 predictors for 130 teams.
  - Alpha is chosen by RidgeCV over 75–325; full seasons land around 150–200 and partial seasons higher.
  - 2019 HFA came out to about 0.018 EPA/play.
  - No predictive validation against raw stats was given — [Opponent Adjusted Stats Using Ridge Regression](https://radsportsanalytics.com/blog/opponent-adjusted-stats-ridge-regression/)
- **cfbfastR adjusted ratings [PRACTITIONER, package docs; seen only as a search snippet]:**
  - Opponent-adjusted EPA/play is computed as the team's per-game pass/rush EPA net of each opponent's ridge-fitted defensive strength.
  - A drive-level ridge fit on per-drive EPA is also described — [cfbfastR load_cfb_ratings](https://rdrr.io/cran/cfbfastR/man/load_cfb_ratings.html); [weekly](https://rdrr.io/cran/cfbfastR/man/load_cfb_ratings_weekly.html)
- **Foundations of the EP model [PEER-REVIEWED]:** Yurko, Ventura & Horowitz's nflWAR (JQAS 2019) introduced multinomial-logistic expected points, the nflscrapR data (2009+), and multilevel-model WAR for offensive players — [arXiv 1802.00998](https://arxiv.org/abs/1802.00998v2); [JQAS](https://www.degruyterbrill.com/document/doi/10.1515/jqas-2018-0010/html)
- **Caveats on EP models [PREPRINT]:** Brill, Yee, Deshpande & Wyner (Sept 2024) argue that ML expected-points models such as nflfastR-style boosted models:
  - suffer selection bias and counter-intuitive overfitting;
  - do not quantify uncertainty;
  - ignore the dependence structure of football data.
  - They propose smoothing with a catalytic prior — [arXiv 2409.04889](https://arxiv.org/abs/2409.04889)
- **State-space team strength [PEER-REVIEWED benchmark]:** Glickman & Stern (1998) model NFL point differential with team strengths that evolve week to week and season to season — described in [Lopez, Matthews & Baumer, arXiv 1701.05976](https://arxiv.org/pdf/1701.05976); see also [state-space model post](https://statsbylopez.netlify.com/post/a-state-space-model-to-evaluate-sports-teams/)

### Inferences
- For CFB, opponent adjustment probably matters more than in the NFL. CFB schedules are far less connected and more unbalanced (130+ FBS teams, about 12 games, large talent gaps). That is the reason for ridge shrinkage, and the CFBD alpha range suggests strong regularization early in the season. This comes from the design, not from measured lift.
- Win-probability weighting (soft) is preferred over hard garbage-time cutoffs. In CFB, blowouts are more common, so the filter choice likely matters more than in the NFL. A CFB-specific test is needed.
- Offense-heavy weighting (around 1.6:1) and discounting fumble recoveries and defensive interceptions are cheap, defensible priors to carry over to CFB.

### Gaps
- I found no peer-reviewed, side-by-side study of EPA/play vs success rate vs early-down EPA vs pass/rush splits on week-to-week stability. The well-known practitioner claims (Baldwin, Hermsmeyer, Football Outsiders' "passing more stable than rushing", "early downs more predictive") were not retrieved directly and need sourcing from Open Source Football / Football Outsiders posts.
- I found no quantified lift from opponent adjustment in CFB (adjusted vs raw EPA predicting future margin or ATS).
- I found no arXiv paper specifically on EPA stability.

## Q2. What does research say about QB/injury adjustments and how the market reacts?

### Takeaway
Public QB adjustments mostly come from practitioner models (538/nfelo box-score QB value regressions, ELWAY). Market sizing of QB absences runs from a couple of points to more than a touchdown. Claims that the market misprices backups (e.g., under-pricing young backups) are anecdotal small samples. I found no peer-reviewed study of market over- or under-reaction to QB changes in this search.

### Cited Findings
- **538 QB value formula [PRACTITIONER]:** A regression of ESPN Total QBR yards-above-replacement on box-score stats: VALUE = −2.2·Att + 3.7·Cmp + Yds/5 + 11.3·PassTD − 14.1·INT − 8·Sacks − 1.1·RushAtt + 0.6·RushYds + 15.9·RushTD. It is opponent-adjusted by subtracting the defense's average VALUE allowed from the league average, and it adjusts team "effective" Elo when the QB changes — [538 NFL methodology](https://fivethirtyeight.com/methodology/how-our-nfl-predictions-work); [538 features version](https://fivethirtyeight.com/features/how-our-nfl-predictions-work)
- **nfelo [PRACTITIONER]:** Uses 538's QB model, expressed relative to the league median QB (= 0), for backup and starter adjustments — [nfelo team & scheme QBs](https://www.nfeloapp.com/analysis/team-and-scheme-nfl-qbs/)
- **ELWAY [PRACTITIONER]:** Nate Silver's successor to 538's NFL model documents its QB handling — [ELWAY methodology](https://www.natesilver.net/p/how-our-elway-forecasts-work-methodology) (details not retrieved)
- **Size of the market adjustment [PRACTITIONER]:**
  - Per-starter "QB worth to the spread" lists exist — [ESPN Chalk](https://www.espn.com/chalk/story/_/id/28162566/how-much-every-nfl-qb-worth-spread); [theScore](https://www.thescore.com/news/1824932)
  - Franchise QBs are typically worth 3–7 points — [WalterFootball](https://walterfootball.com/quarterbackinjuriesimpact.php)
  - 2019 Brees injury: the line moved from Seattle −1 to −5 (about 4 points). The Saints then went 5-0 ATS with Bridgewater, which was read as overreaction — [CBS Sports 2020](https://www.cbssports.com/nfl/news/nfl-betting-2020-knowing-how-to-adjust-lines-when-each-starting-qb-is-ruled-out-during-the-season)
- **Anecdotal backup mispricing [PRACTITIONER, small sample]:** In 2019, young backups Kyle Allen, Minshew, Rudolph, Daniel Jones and Bridgewater started 11-0 ATS — [Fox Sports Radio](https://foxsportsradio.iheart.com/content/2019-10-02-vegas-underprices-young-backup-quarterbacks/). This is a cherry-picked streak, not evidence.
- **Totals and short-run volatility [PRACTITIONER]:**
  - Totals usually drop 1–3 points when a starter is out.
  - With little data on the backup, short-run inefficiencies are plausible — [Deucescracked guide](https://www.deucescracked.com/blog/backup-quarterback-betting-impact-nfl-lines-guide-2026)
- **[LOW-QUALITY/UNVERIFIED — do not use]:** A claimed "2025 University of Chicago study" that 73% of pros bet within 60 minutes of injury reports, and a claimed 3.5-point average shift for a missing starting QB in 2023, both from betting-media pages with no primary source — [elovrador](https://www.elovrador.com/2026/06/26/how-injury-reports-shape-nfl-prop-betting-markets/); [WalterFootball](https://walterfootball.com/sportsbooksadjustodds.php)

### Inferences
- Carrying this to CFB is hard. There is no QBR-style box-score regression tuned to CFB in these sources, depth charts are less transparent, and transfer-portal roster churn makes priors weaker. A CFB QB adjustment would likely need to be built in-house (e.g., a 538-style VALUE regression on CFB box scores against CFB EPA) and validated against line moves.
- Since line moves on QB news are observable, the right test is whether closing-line moves on QB-out news predict ATS results (over- or under-reaction). No public study was found.

### Gaps
- I found no peer-reviewed paper on market efficiency around QB injuries or changes in the NFL or CFB.
- I found no study of non-QB injuries (OL, CB) and their spread impact.
- ELWAY's QB method was not retrieved in detail.

## Q3. Which score-distribution models are best calibrated for spreads, totals, team totals and halves, and are derivative markets less efficient?

### Takeaway
The canonical benchmark is a normal margin around the spread (Stern; not retrieved here). The best peer-reviewed NFL exact-score work found is Baker & McHale's point-process model, which can take the bookmaker spread and total as inputs. Count models (Poisson, bivariate Poisson, negative binomial, Skellam) are mostly validated on soccer and fit NFL scoring poorly without heavy modification, because NFL scoring comes in 3s and 7s. Key numbers make discrete or empirical margin distributions necessary for pricing half-points and alternate lines. Claims that derivative markets are less efficient are almost entirely practitioner assertions. The one peer-reviewed totals inefficiency found (unders on high totals) disappeared after 2009.

### Cited Findings
- **Baker & McHale, "Forecasting exact scores in National Football League games" [PEER-REVIEWED, IJF 2013]:**
  - A point-process model whose scoring hazards depend on team statistics from previous games and/or the bookmaker spread and over/under.
  - Evaluated out of sample with several criteria, including a Kelly betting strategy — summarized in [arXiv 1701.05976 / search summary](https://arxiv.org/pdf/1701.05976); repository record [Salford](https://salford-repository.worktribe.com/output/1432547/forecasting-exact-scores-in-national-football-league-games) (403, not read)
  - The actual betting P&L was not retrieved.
- **Paired-comparison NFL spread models [PEER-REVIEWED]:** "Improved paired comparison models for NFL point spreads by data transformation" (Loyola) — [record](https://scholars.luc.edu/en/publications/improved-paired-comparison-models-for-nfl-point-spreads-by-data-t/) (abstract not retrieved)
- **Optimal decisions from quantiles [PEER-REVIEWED, 2023]:**
  - The median predicted margin is enough for optimal side prediction in a game.
  - Choosing which games to bet requires further quantiles of the margin distribution, which argues for full-distribution models over point estimates — [PMC10306238](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10306238/)
- **Count-model background (soccer) [PEER-REVIEWED]:**
  - Maher (1982): independent Poisson fits reasonably, and a bivariate Poisson with about 0.2 correlation improves it — [IDEAS](https://ideas.repec.org/a/bla/stanee/v36y1982i3p109-118.html)
  - Tails are better described by negative binomial than by Poisson — [arXiv physics/0606016](https://arxiv.org/abs/physics/0606016)
  - Dixon–Coles extensions — [arXiv 2307.02139](https://arxiv.org/pdf/2307.02139)
  - These are soccer results. NFL applicability is untested in these sources.
- **Key numbers [PRACTITIONER]:**
  - NFL margins land on 3 and 7 about 15% and 9% of the time.
  - Books charge about 20–25 cents to move on or off 3, and about 15 cents on or off 7 — [TopEndSports half-point calculator](https://www.topendsports.com/sport/betting-tools/half-point-calculator.htm); see also [Covers key numbers 2025-26](https://www.covers.com/nfl/key-numbers); [OddsPapi half-point value (Python)](https://oddspapi.io/blog/?p=3165)
- **Totals inefficiency [PEER-REVIEWED, regional journal / AABRI]:** A contrarian under on posted totals of 47.5 or higher won 59.7% from 2001–2009, but the inefficiency vanished from 2010–2018 — [AABRI manuscript](https://jid.aabri.com/manuscripts/203263.pdf); related [AABRI](https://mobile.aabri.com/manuscripts/193138.pdf); [West Georgia 2008](https://www.westga.edu/~bquest/2008/football08.pdf)
- **Broader NFL market efficiency [PEER-REVIEWED, J. Economics & Finance]:**
  - Both spread and totals markets are statistically inefficient. Home underdogs, and home teams that have not covered recently, cover more often — [IDEAS 2024](https://ideas.repec.org/a/spr/jecfin/v48y2024i2d10.1007_s12197-023-09656-5.html); [IDEAS 2018](https://ideas.repec.org/a/spr/jecfin/v42y2018i4d10.1007_s12197-018-9431-4.html)
  - Note that "statistically inefficient" does not necessarily mean profitable after vig.
- **Weather [mix]:**
  - A peer-reviewed study (FIT Publishing, "The Impact of Atmospheric Conditions on Actual and Expected Scoring in the NFL") reports humidity and wind significantly explain actual-minus-total. Simple humidity/wind wagering strategies reject market efficiency — [FIT Publishing](https://fitpublishing.com/node/3503) (page 404 on fetch; claim is from the search summary)
  - Practitioners: wind is the only large, consistent weather effect, with a threshold around 15–20 mph; below 10 mph there is no measurable effect — [Deucescracked](https://www.deucescracked.com/blog/nfl-weather-betting-wind-totals-handicapping)
  - Unders cashed 54% in games with wind over 20 mph since 2015 — [Fox Sports](https://amp.foxsports.com/stories/nfl/nfl-odds-weather)
  - A CFB-relevant wind analysis — [Football Study Hall 2018](https://www.footballstudyhall.com/2018/6/25/17500384/football-betting-windy-conditions-effect)
- **Derivative markets [PRACTITIONER, unsupported assertions]:**
  - Claim: first-half, quarter and team-total lines are often derived mechanically (e.g., team total = (total ± spread)/2), so they are softer.
  - Claim: team totals are the "greatest inefficiency" — [PredictEm](https://www.predictem.com/?p=174841); [4for4 team totals series](https://www.4for4.com/2023/w8/week-8-nfl-betting-picks-team-and-game-totals)
  - No data was given to support either claim.

### Inferences
- For pricing alternate spreads, team totals and halves, a reasonable stack is:
  1. Center on the market spread and total.
  2. Get the margin and total distribution from a drive- or possession-level simulation, or from an empirical key-number-aware distribution conditioned on the spread and total.
  3. Model the correlation between home and away scores explicitly.
- Under a mechanical derivation like (total ± spread)/2, team totals implicitly assume that structure. Deviations caused by pace, or by correlation that depends on the spread, are where an edge would come from, if one exists.
- CFB has wider spreads, higher and more variable totals, and different overtime rules, so NFL key-number frequencies do not carry over. CFB margin distributions need to be estimated separately, probably conditioned on spread size.

### Gaps
- I did not retrieve the primary text of Stern (1991), the normal margin model and its standard deviation, so I cannot quote parameters.
- I found no football-specific bivariate Poisson, zero-inflated, Skellam or negative binomial calibration study.
- I found no peer-reviewed or reproducible public study showing derivative markets (alternate lines, team totals, halves) are less efficient than the main line.
- I found no drive-level or possession simulation papers (NFL or CFB), and no pace models for totals.
- I found no CFB key-number or margin-distribution study.
- No Unabated or Pinnacle resources on key numbers or correlated parlays surfaced in search.

## Q4. Is there evidence that a model + market combination (residual modeling, Bayesian updating from the line) adds value over the line alone?

### Takeaway
The evidence is thin. The closing spread explains almost all of the variation that rating models capture, and the strongest peer-reviewed design found (Baker & McHale) builds market lines into the model rather than beating them independently. I found no NFL/CFB study showing a robust, out-of-sample, after-vig edge from combining models with the market.

### Cited Findings
- **Ratings vs lines [PRACTITIONER]:** A latent-rating model of point spreads (R_home − R_road + HFA) explains NFL spreads with R² ≈ 0.98. Market lines are therefore essentially a power rating plus HFA, and a model's value has to come from the residual — [Modeling the NFL Betting Market, poliscidata](https://www.poliscidata.com/blog/modeling-the-nfl-betting-market/)
- **Baker & McHale [PEER-REVIEWED]:** Lets scoring hazards depend on the bookmaker spread and total, and evaluates Kelly betting out of sample. This is the closest peer-reviewed "model + market" design found, but the results were not retrieved — [arXiv 1701.05976 summary](https://arxiv.org/pdf/1701.05976)
- **Statistical inefficiencies such as home-underdog bias [PEER-REVIEWED]** suggest that residual features (home status, recent ATS record) carry some signal — [IDEAS 2024](https://ideas.repec.org/a/spr/jecfin/v48y2024i2d10.1007_s12197-023-09656-5.html)
- **Student capstone projects [LOW]:** Linear, gradient boosting and neural-network models on 2018–2023 NFL spreads and totals, with no market-beating result reported — [Quinnipiac capstone](https://iq.qu.edu/experiential-learning/course-projects-and-capstones/student-projects/predicting-nfl-total-score-and-point-spread-bets/)

### Inferences
- The defensible design is to treat the line as the prior and model the residual (closing margin minus spread) with play-by-play features such as opponent-adjusted EPA and WEPA, QB and injury deltas, and weather. Judge it by closing-line value and by calibration of the margin distribution, not by raw ATS win rate.
- Test the pipeline on shuffled or placebo residuals first, so you know it can come back with "no edge".
- CFB may offer more residual room than the NFL because of lower liquidity, more games, less-followed teams and early-season priors. That is plausible but unproven in these sources.

### Gaps
- I found no peer-reviewed NFL or CFB study of residual modeling or Bayesian updating from the line showing profitable out-of-sample results.
- I found no CFB-specific market-efficiency study in this search (adjacent researchers may cover it).
- I did not retrieve the out-of-sample Kelly results from Baker & McHale.
