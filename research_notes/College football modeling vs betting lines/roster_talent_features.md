# Roster-Based Information as Predictors of CFB Team Performance and Betting Outcomes

Scope note: ~17 tool calls. Several peer-reviewed sources (SAGE, Springer) returned 403/login redirects, so some academic findings come from abstracts (RePEc) or search-result snippets only; those are flagged. Practitioner evidence is flagged as such. Nothing here has been independently replicated by me.

## How predictive are talent composites / blue-chip ratios, and are they priced?

### Takeaway
Recruit quality has a robust, statistically significant but modest causal-ish effect on wins (pre-portal, 2002-2012 data), and recruiting ratings remain the strongest single roster predictor of end-of-season strength in the portal era (r ~0.64 with Elo, 2022-2023). I found no rigorous test of whether talent composites are already priced by spreads or win totals.

### Cited Findings
- Bergman & Logan (2016), *Journal of Sports Economics* 17(6):578-600, FBS 2002-2012, individual recruit star ratings: controlling for school fixed effects "lowers the estimated effect of recruit quality on wins by more than 25%, but the remaining effect is still statistically and economically significant"; ~$150,000 expected BCS bowl revenue per 5-star recruit — [RePEc/IDEAS](https://ideas.repec.org/a/sae/jospec/v17y2016i6p578-600.html)
- Same study (per OSU alumni feature, secondary source): each five-star recruit adds ~0.306 wins/season; a five-star raises BCS-bowl odds ~4% with school fixed effects — [OSU Economics](https://economics.osu.edu/newsletter/2014/alumni-feature-stephen-bergman); paper page [ResearchGate](https://www.researchgate.net/publication/273592662_The_Effect_of_Recruit_Quality_on_College_Football_Team_Performance)
- Practitioner/secondary claim: 17 years of recruiting rankings explain "up to 36 percent" of variability in team performance (underlying study not identified in what I fetched — treat as unverified) — [AthleticDirectorU](https://athleticdirectoru.com/articles/do-football-recruiting-ratings-matter/)
- Blue-chip ratio (Bud Elliott, 247/CBS): >50% blue-chips is the claimed championship threshold; claim that every national champion since 2011 met it. This is a descriptive necessary-condition heuristic, not a predictive test (and is noted to have weakened — Indiana 2025 won the title ranking 44th in returning production, and by search snippets lacks a blue-chip roster profile) — [Autzen Zoo](https://autzenzoo.com/blue-chip-ratio-divides-contenders-and-pretenders-in-college-football-01k0ceah9qge); [SI](https://www.si.com/college/georgia/football/georgia-still-a-national-title-contender-according-to-247-sports-blue-chip-ratio)
- Portal-era parity: 247 2025 Team Talent Composite had 11 teams >= 900 points vs. six the prior year (first time six had done so); top: Georgia 1,002.98, Alabama 993.55, Ohio State 973.69. Methodology paywalled — [247Sports](https://247sports.com/article/team-talent-composite-2025-how-nil-and-the-transfer-portal-leveled-the-playing-field-for-top-programs-253009907/)
- Practitioner (CFBD blog): talent composite is "sticky," doesn't predict game-to-game variance, but should be used as a prior, especially early season — [CFBD blog](https://blog.collegefootballdata.com/college-football-modeling-tips/)
- Other peer-reviewed related work surfaced but not read: Evans & Pitts (2018) cross-sport recruiting effects, JSE — [SAGE](https://doi.org/10.1177/1527002516684171); Brook (2022) bowl participation effects on recruiting/success — [SAGE](https://doi.org/10.1177/15270025221074692); IJSAS 2025 "Winning Over Recruiting" (recruiting + coaching investment) — [IJSAS](https://ijsas.wordpress.com/2025/05/29/winning-over-recruiting-the-influence-of-recruiting-and-coaching-investment-on-on-field-success-in-college-football/)

### Inferences
- Because talent is slow-moving and public, and books build win totals from power ratings that include roster info (practitioner description, [OddsShopper](https://www.oddsshopper.com/articles/betting-101/college-football-win-totals)), the level effect is very likely priced; any edge would be in the *changes* (portal-driven composite shifts) or in how fast a model down-weights the prior.
- The fixed-effects result (>25% shrinkage) means much of raw talent-wins correlation is program quality (coaching, facilities); a model should include program/coach priors alongside talent to avoid double counting.

### Gaps
- Langelett (2003) and Caro (2012) specifics not retrieved (no access).
- No peer-reviewed or credible test found of talent composite vs. closing spreads or win totals (ATS residual on talent). This is the core open question — needs own backtest (CFBD has talent + lines).
- No On3 vs 247 vs Rivals head-to-head predictive comparison found.

## Returning production: correlation with YoY change and market tests

### Takeaway
Connelly's returning production is the best-documented continuity metric: teams returning >=80% improved ~6.4 SP+ points on average (since 2014). Its weights are public and portal-adjusted. I found no rigorous market-efficiency test of it; anecdotal evidence (Clemson 2025) shows large misses.

### Cited Findings
- Teams with >=80% returning production improved ~6.4 adjusted points/game in next-season SP+; >=70% improved 4.0 points on average since 2014; in 2019 and 2022 (non-pandemic years) >=80% teams improved 6.8 points — [Yahoo/ESPN summary](https://news.yahoo.com/does-oklahoma-big-12-stack-203811037.html)
- Returning rushing and OL starts carry less year-to-year value; secondary (back-of-defense) turnover moves SP+ more than front-seven turnover — same source.
- Current formula (ESPN 2026): Offense = 39.6% OL snaps, 35.0% WR/TE receiving yards, 22.3% QB passing yards, 3.1% RB rushing yards. Defense = 65.9% snaps, 19.2% tackles, 14.9% TFLs. Transfers' prior production is added to numerator and denominator at new school; half credit for players moving up from lower divisions — [ESPN 2026](https://www.espn.com/college-football/story/_/id/48259759/college-football-returning-production-2026-notre-dame-texas)
- National average returning production: 2021 76.7% (COVID extra-year), 2022 62.9%, 2023 60.2%, 2024 59.9%, 2025 53.7% — same source. Portal-era churn is steadily lowering continuity.
- 2025 out-of-sample anecdote: top-10 returning-production teams improved on average 1.0 wins and 6.4 SP+ ranking spots; of bottom 15 (<=36%), 10 regressed, 8 by >=11 spots — same source (small n, descriptive).
- Clemson 2025 returned 81%, ranked 4th preseason, out of the rankings by Sept. 14; Indiana (2025 champion) ranked 44th — [FootballScoop](https://www.footballscoop.com/2026/03/23/returning-production-numbers-college-football-2026)
- Portal-era regression (practitioner Substack, 2022-2023): adding returning PPA to recruiting + portal ratings raised adj. R^2 of end-of-season Elo from 0.410 to 0.499; relative importance recruiting 53.5%, returning PPA 32.9%, portal 13.6% — [Beyond the Score](https://beyondthescoresports.substack.com/p/does-success-in-the-transfer-portal)

### Inferences
- Returning production is already a headline input to SP+ preseason projections and is widely published each February; it is likely priced into win totals. Edge, if any, more plausibly comes from *component* weighting (e.g., secondary/QB continuity vs OL) or from transfer-quality adjustments the public metric handles crudely (portal production counted at face value regardless of level, except lower-division half credit).
- Falling averages (76.7% to 53.7%) mean historical thresholds (>=80%) are now rare; coefficients estimated on 2014-2019 data may not transfer.

### Gaps
- No exact correlation coefficient (r) for returning production vs SP+ change found in fetched sources.
- No study tests returning production against closing spreads or win totals (market under/over-reaction). Needs own backtest.

## Transfer portal era (2021-2026): transfer impact, QB transfers, portal-heavy teams ATS

### Takeaway
Credible evidence is thin and practitioner-only: portal class ratings add little beyond recruiting ratings in explaining team strength (not significant in a 2022-2023 regression). I found no rigorous study of transfer QB performance or portal-heavy teams ATS.

### Cited Findings
- 2022-2023 regression of end-of-season Elo (CFBD) on 247 recruiting and portal ratings: R^2 = 0.410; recruiting r = 0.64, portal r = 0.39; portal not significant controlling for recruiting; relative importance 81%/19%. Portal remained non-significant after adding returning PPA. Practitioner, two seasons, no market test — [Beyond the Score](https://beyondthescoresports.substack.com/p/does-success-in-the-transfer-portal)
- 247 analysis: top programs still get the best portal talent, but net volume losses reduce their share of top players; parity increased since 2021 — [247Sports](https://247sports.com/article/team-talent-composite-2025-how-nil-and-the-transfer-portal-leveled-the-playing-field-for-top-programs-253009907/)
- Mountain West blog analysis argues portal/NIL changed rosters more than wins (not fetched; practitioner) — [MWC Connection](https://www.mwcconnection.com/mountain-west-transfer-portal/91687/college-football-transfer-portal-nil-sports)
- CFBD tracks every portal entrant with 247 transfer ratings, enabling own analysis — [IU portal analysis](https://blogs.iu.edu/iuindysii/2024/05/15/ncaa-transfer-portal-analysis/)
- Anecdotal transfer-QB successes (Mensah at Duke leading EPA/play + CPOE; Colandrea at Nebraska 2026) — [CFBNumbers](https://cfbnumbers.substack.com/p/2025-cfb-season-qb-advanced-stats); [CBS](https://www.cbssports.com/college-football/news/college-football-qb-power-rankings-anthony-colandrea-nebraska-indiana/) — anecdotes, not evidence.

### Inferences
- Portal ratings are a noisier, collinear version of talent; the incremental value is likely in *production-weighted* transfers (prior EPA/PFF grades adjusted for level of competition) rather than star ratings.
- A Group-of-5 -> Power-4 step-up discount is an obvious feature to test; Connelly only applies a half-credit discount for lower-division moves, not G5->P4.

### Gaps
- No study on transfer QB year-1 efficiency change vs. prior school (level-adjusted) found.
- No ATS analysis of portal-heavy teams (e.g., % of starters as transfers) found — even practitioner. Biggest research gap in this section.
- Destination/adaptation effects (scheme fit, mid-year vs spring arrival) undocumented.

## Coaching changes, bowl opt-outs, and early-season (weeks 0-4) uncertainty

### Takeaway
Early-season and bowl markets carry the most roster uncertainty. Some academic evidence of early-season holdover bias exists (paywalled); a practitioner stat suggests new coaches go slightly under .500 ATS early (47%, not significant). Bowl lines move sharply on opt-outs/coaching news, and bookmakers describe bowls as a "race to information." Peer-reviewed work finds bowl spreads predict outcomes differently from regular-season spreads (paywalled).

### Cited Findings
- New head coaches vs returning coaches, first four weeks, since 2021: 115-170 SU, 134-151 ATS (47%) — search-snippet attribution to [Las Vegas Review-Journal](https://www.reviewjournal.com/sports/betting/early-season-trends-can-dictate-college-football-betting-3887069/) (not fetched; n=285, 47% vs 50% is ~1 SE, not significant).
- "Holdover Bias in the College Football Betting Market" (Atlantic Economic Journal, 2019): reported inefficiency in pricing the first game of the season, especially for prior-year top-25 teams (abstract via snippet; paywalled) — [Springer](https://link.springer.com/article/10.1007/s11293-019-09611-y)
- Cox, Schwartz, Van Ness & Van Ness (2021), JSE, "The Predictive Power of College Football Spreads: Regular Season Versus Bowl Games" — compares spread accuracy in bowls vs regular season (could not retrieve abstract; 403) — [SAGE](https://journals.sagepub.com/doi/abs/10.1177/1527002520975837)
- Older general inefficiency evidence: 11,000+ games 1985-2003, favorites systematically overpriced (pre-2018, may not hold today) — [AEA 2010 paper](https://www.aeaweb.org/conference/2010/retrieve.php?pdfid=406); Arscott (2023) JSE on censoring bias in CFB betting market efficiency (not retrieved) — [SAGE](https://doi.org/10.1177/15270025221148991)
- Bowl line moves (2025-26), ESPN with bookmaker quotes: Texas-Michigan Citrus Bowl -4.5 to -7 after Michigan coaching change; Utah-Nebraska -14 to -16.5 after staff changes; Caesars' Feazel: "It's a race to information. We're trying to get to that coin flip as quickly as possible" — [ESPN](https://www.espn.com/espn/betting/story/_/id/47307193/college-football-betting-2025-bowls-lines-opt-outs-coaching-changes)
- Earlier examples: Missouri +6.5 to -2.5 vs Ohio State (Cotton Bowl, McCord in portal); UNC +3.5 to +6.5 after Drake Maye opt-out — [Yahoo Sports](https://sports.yahoo.com/college-football-betting-how-opt-outs-have-affected-bowl-game-betting-lines-200205644.html)
- Practitioner claim that backup QBs sometimes offset "overinflated" opt-out moves (no data) — [Yahoo](https://sports.yahoo.com/college-football-betting-how-opt-outs-have-affected-bowl-game-betting-lines-200205644.html); opt-out tracker for data collection — [SBR](https://www.sportsbookreview.com/picks/college-football/ncaaf-bowl-game-opt-out-tracker/)
- Practitioner: first two weeks are most volatile; unopposed early-week steam moves lines due to thin liquidity; 2026 early lines frequently played back later in week — [ESPN 2026 storylines](https://www.espn.com/espn/betting/story/_/id/49734086/college-football-betting-storylines-2026-season-ohio-state-texas-notre-dame-miami)
- Win totals described as among the softest markets (130+ FBS teams can't be sharpened like NFL) — practitioner, [OddsShopper](https://www.oddsshopper.com/articles/betting-101/college-football-win-totals); ESPN annual win-total hits/misses review — [ESPN](https://www.espn.com/sports-betting/insider/story/_/id/32431283/hits-misses-preseason-college-football-win-totals-revisited)

### Inferences
- Signal decay: roster priors (talent, returning production) matter most weeks 0-4 and should be down-weighted as in-season efficiency data accumulates (CFBD advice; consistent with SP+ practice). No source gave a quantified decay curve — fit one empirically (e.g., weight of preseason prior vs games played that minimizes closing-line error).
- Bowl opt-outs: market reacts strongly and fast; the testable hypothesis is over-reaction (fade the move) — no rigorous evidence either way found.

### Gaps
- No sourced quantified decay rate for any roster signal.
- Coaching-change mispricing beyond the one practitioner ATS stat: none found. First-year coach full-season ATS, or interim coaches in bowls, untested in sources reached.
- Bowl opt-out ATS effect size: no study found.

## Injury/availability data sources and their market value

### Takeaway
Before 2023 there were no mandated CFB injury reports. The Big Ten (2023), SEC (2024), ACC (2025), and CFP (2025) now require availability reports; no NCAA-wide football mandate was found (NCAA mandated reports for March Madness basketball, announced Oct 2025). No evidence on the market value of these reports was found.

### Cited Findings
- Big Ten (2023): reports due >= 2 hours before kickoff; statuses "questionable" or "out" — [CBS Sports](https://picks-s6.cbssports.com/college-football/news/college-football-playoff-will-require-teams-to-provide-player-availability-reports-beginning-with-2025-season/)
- SEC (2024): four statuses (out/questionable/probable/available), Wednesday report updated daily, final <= 90 minutes pre-kickoff — same source.
- CFP requires availability reports starting 2025 season — same source.
- ACC requires availability reports for conference football games in 2025, submitted two days before games, posted on ACC.com — [The Osceola](https://theosceola.com/p/notes-acc-to-require-availability-reports-for-league-games-in-2025)
- NCAA previously shelved a plan to require football injury reports — [Casino.org](https://www.casino.org/news/ncaa-shelves-plan-requiring-injury-reports-for-college-football-teams); NCAA mandated availability reports for March Madness (Oct 2025), integrity-driven — [SBC Americas](https://sbcamericas.com/2025/10/31/ncaa-player-injury-report-march-madness/); [Legal Sports Report](https://www.legalsportsreport.com/245543/ncaa-to-mandate-injury-reports-for-march-madness-amid-betting-integrity-push/)

### Inferences
- Coverage is conference-dependent (Big 12, G5 status unverified), so an availability feature will be missing-not-at-random; model it per conference.
- Big Ten's 2-hour, two-status reports give little lead time for pregame modeling; SEC's daily reports are more usable.

### Gaps
- Whether the NCAA adopted an FBS-wide football availability rule for 2025 or 2026: not confirmed — did not find one.
- Big 12 / G5 policies not verified.
- No study of market reaction to availability reports (line moves after report releases) found.
