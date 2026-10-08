# Academic CFB (NCAA FBS) prediction studies vs betting markets

Scope note: Sage (Journal of Sports Analytics, Journal of Sports Economics) full texts returned HTTP 403 and a mirror was CAPTCHA-gated, so several numbers below come from search-engine snippets of the full text (flagged "[snippet]") rather than a direct read. Treat [snippet] numbers as needing confirmation against the PDF before relying on them.

## Which studies claim to beat or match the opening or closing line, and how rigorous is their out-of-sample design?

### Takeaway
Only one 2018–2026 peer-reviewed CFB paper I found makes a formal model-vs-line claim with a held-out test set: Coleman (2025, JSA). Its edge is against the *opening* line and is small (about 51–53% ATS overall, about 55% when it disagrees with the open by more than 3 points). The benchmark result from earlier work, Fair & Oster (2007), is that rating systems, alone or optimally combined, add *no* information beyond the closing Vegas spread.

### Cited Findings
- **Coleman (2025), "A predictive metamodel for college football," Journal of Sports Analytics 11, doi:10.1177/22150218251365223.** 29 rating systems, 5,925 games 2016–24, k-fold cross-validation focused on predictiveness, five-system metamodel predicting next-week victory margin. Abstract: "achieves strong results vis-à-vis the opening, midweek, and closing betting lines, and is statistically significant in the presence of the opening line in validation and test samples." — [LIDA record](https://lida.sport-iat.de/dfb/Record/4094978?lng=en); [Sage DOI](https://doi.org/10.1177/22150218251365223)
- Coleman (2025) design [snippet]: 4,416 games 2016–22 (2020 omitted) for training/validation; 1,509 games 2023–24 as a temporal test set. The adjusted metamodel (MM*) went 53.08% ATS vs the opening line in validation (N = 3,964) and 51.47% in test (N = 1,364). When MM* differed from the opening line by more than a field goal in test (n = 291), it went 55.33% (p < .05, one-tailed). — [ResearchGate/Sage snippet](https://www.researchgate.net/publication/394184848_A_predictive_metamodel_for_college_football)
- Coleman (2025) [snippet]: the metamodel picked the straight-up winner in 72.96% of games in both validation and test, with slightly better mean error and MAE in test than in validation. — [Sage snippet](https://doi.org/10.1177/22150218251365223)
- Coleman (2025) reference list: South & Egros 2020; Coleman 2014; Fair & Oster 2007; Pasteur 2010 (two papers). The abstract says only two prior studies had tried to build a predictive ensemble ("metamodel") of rating systems. — [Semantic Scholar API record](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1177/22150218251365223?fields=title,abstract,references.title)
- **Fair & Oster (2007), "College Football Rankings and Market Efficiency," Journal of Sports Economics** (Cowles DP 1381, 2002, revised 2005). Ranking systems carry independent predictive information, and an optimally weighted combination beats every individual system. But "none of the systems, including the optimal combination, contains any useful information that is not in the final Las Vegas point spread." Comparison is against the *final/closing* line. — [RePEc Cowles DP](https://ideas.repec.org/p/cwl/cwldpp/1381.html); [Fair site](https://fairmodel.econ.yale.edu/rayfair/pdf/2002B.HTM); [Sage](https://journals.sagepub.com/doi/abs/10.1177/1527002505276724)
- **Harville (2003)**, as described by West & Lamsal (2008): a modified least-squares rating with home-field advantage and margin of victory removed (per BCS rules) "had better predictive accuracy for future games than the Las Vegas betting line." This is a secondary description; I did not verify it in the original. — [West & Lamsal 2008 preprint, JQAS](https://public.websites.umich.edu/~bwest/inpress_063008.pdf)
- **Ramesh, Mostofa, Bornstein & Dobelman (2019), "Beating the House: Identifying Inefficiencies in Sports Betting Markets," arXiv:1910.08858.** A non-parametric win-probability model on NFL, NBA, NCAAF, NCAAB and WNBA claims "above market returns" in all five leagues. The abstract gives no CFB-specific numbers or out-of-sample details. — [arXiv](https://arxiv.org/abs/1910.08858)

### Inferences
- Coleman's claim is narrow: significance only *conditional on the opening line*, a test-set ATS rate (51.47%) below the 52.4% break-even at -110, and a profitable-looking 55.33% only on a filtered subset of 291 games, judged by a one-tailed test. Choosing the 3-point threshold is itself a multiple-testing degree of freedom. Results "vis-à-vis" midweek and closing lines are described only as "strong," which suggests they are weaker than the opening-line result (unconfirmed).
- Coleman's 2023–24 test set is a genuine temporal holdout. The leakage question is whether each of the 29 systems' ratings were archived *as published before each week*. Massey's comparison archive is week-stamped, but I could not confirm Coleman's timing from the text.
- Taken together, Fair & Oster (closing line, no added information) and Coleman (opening line, a small edge) are consistent: whatever rating-system information exists gets priced in between the open and the close.

### Gaps
- I could not retrieve Coleman 2025's five member systems, their weights, or its exact midweek and closing-line ATS rates and MAE because the Sage full text was blocked. Get the PDF through the CMU library.
- I found no 2018–2026 CFB paper reporting log loss or ROI against moneylines.
- Fair & Oster's exact sample years, MSE values and number of games were not in the abstract pages I could reach.

## Coleman's work and Song/Boulier/Stekler-style rating-system-vs-line comparisons

### Takeaway
Coleman's line of work runs from meta-rankings (2014), to travel effects in the betting market (2017), to the 2025 metamodel. The comparisons of many rating systems against the Vegas line in this tradition are by Fair & Oster and by Boulier/Stekler.

### Cited Findings
- **Coleman (2014), "Minimum violations and predictive meta-rankings for college football," Naval Research Logistics 61(1):17–33, doi:10.1002/nav.21563.** Builds an ensemble probability model from 36 ranking systems, used as targets in hierarchical (multi-objective binary integer linear program, MOMBILP) optimization. One MOMBILP was the leading predictive system while within 0.64% of the retrodictive optimum; another was within 2.55% of the best predictor. Bowl-game predictions were statistically comparable to the leading systems. No Vegas-line comparison. — [UNF Digital Commons](https://digitalcommons.unf.edu/unf_faculty_publications/2666)
- **Coleman (2017), "Team Travel Effects and the College Football Betting Market," Journal of Sports Economics.** Exists and is relevant to market inefficiency; the abstract and numbers could not be fetched (403). — [Sage](https://journals.sagepub.com/doi/abs/10.1177/1527002515574514)
- **Boulier & Stekler (1999), "Are sports seedings good predictors?: an evaluation," International Journal of Forecasting 15(1):83–91.** An earlier benchmark of rankings as forecasts; I did not confirm CFB-specific content. — [RePEc](https://ideas.repec.org/a/eee/intfor/v15y1999i1p83-91.html)
- Pasteur (2010) extended the Colley method to predictive football rankings and is cited by Coleman 2025 as prior ensemble work. — [Semantic Scholar refs](https://api.semanticscholar.org/graph/v1/paper/DOI:10.1177/22150218251365223?fields=title,abstract,references.title)

### Inferences
- The "Song/Boulier/Stekler" comparisons of rating systems with the Vegas line that I could confirm are mostly NFL (Song, Boulier & Stekler, IJF 2007, from training knowledge, unverified here). For CFB, the equivalent benchmark is Fair & Oster 2007.

### Gaps
- I found no Song/Boulier/Stekler paper specific to college football. If one exists it did not surface in searches.

## Machine-learning CFB studies: features, and whether they beat lines out of sample

### Takeaway
The peer-reviewed CFB machine-learning work I found evaluates straight-up winner accuracy, not ATS. None shows an out-of-sample edge against a spread.

### Cited Findings
- **South & Egros (2020), "Forecasting college football game outcomes using modern modeling techniques," Journal of Sports Analytics, doi:10.3233/JSA-190314.** Trained on 2011–14, tested on 2015 (a temporal split). Compared ridge, lasso, elastic net, neural nets, random forests, kNN, stochastic gradient boosting, and Bayesian regression with team-specific variances. The top models picked the correct winner "over 70% of the time"; lasso was most accurate on 2015 win/loss. No ATS or line comparison in the abstract. — [Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3233/JSA-190314?fields=title,authors,year,abstract,venue)
- **Frontiers in Artificial Intelligence (Aug 2020).** Logistic regression and decision trees on CFB found the point spread, as a team-strength input, and red-zone offense useful for predicting results. The spread is used as a *feature*, so this is not a test against the market. — [DOAJ](https://doaj.org/article/73004bbd4ff248fca5c03c27e46afe95); [Frontiers PDF](https://www.frontiersin.org/journals/artificial-intelligence/articles/10.3389/frai.2020.00061/pdf)
- A non-academic blog (CollegeFootballData) shows gradient-boosted decision trees (LightGBM, NGBoost) for spread prediction. — [CFBD blog](https://blog.collegefootballdata.com/predicting-spreads-gbdt/)
- A systematic review of machine learning in sports betting exists (arXiv 2410.21484) but did not surface CFB-specific ATS results. — [arXiv](https://arxiv.org/html/2410.21484v1)

### Inferences
- About 72–73% straight-up accuracy appears to be the ceiling for both machine learning (South & Egros, "over 70%") and Coleman's metamodel (72.96%). That accuracy says nothing about ATS edge.
- Leakage risk in this literature: season-aggregate statistics such as red-zone percentage computed over the full season and then used to "predict" games in that same season. The Frontiers paper should be checked for this.

### Gaps
- I found no peer-reviewed CFB gradient-boosting or neural-net paper reporting ATS win rate or ROI against a held-out season.

## Bayesian, hierarchical and state-space models of CFB team strength

### Takeaway
Bayesian work touching CFB mostly uses market lines as *inputs* to infer team strength, rather than trying to beat the lines.

### Cited Findings
- **Lopez, Matthews & Baumer (2018), "How often does the best team win?" (Annals of Applied Statistics; arXiv:1701.05976).** A Bayesian state-space model fit to betting-market data, estimating team strength, between-season, within-season and game-to-game variability, and home advantage. It covers the four major North American pro leagues, not CFB. — [arXiv](https://arxiv.org/pdf/1701.05976)
- South & Egros (2020) included a Bayesian regression with team-specific variances among their top performers. — [Semantic Scholar](https://api.semanticscholar.org/graph/v1/paper/DOI:10.3233/JSA-190314?fields=title,authors,year,abstract,venue)
- West & Lamsal (2008, JQAS) review least-squares and mixed-model rating lineages (Stefani 1980/1987, Stern 1995, Bassett 1997, Harville 1980/2003) and fit a linear model for 2004–06 FBS bowl outcomes. — [preprint](https://public.websites.umich.edu/~bwest/inpress_063008.pdf)

### Gaps
- I found no 2018–2026 Glickman-style dynamic or state-space CFB model evaluated ATS against lines.

## Where CFB betting markets are least efficient

### Takeaway
Documented pockets: the first game of the season for last year's top-10 teams (holdover bias), bowls versus the regular season, momentum, and over-bias in totals for nationally televised games. Several of these have weakened over time.

### Cited Findings
- **Bennett (2019), Atlantic Economic Journal 47(1).** Holdover bias: in the first game of the season, bets against the previous season's final AP Top 25 teams won "significantly more than half the time." Bets against the prior top 10 won "significantly more than the 52.4% necessary for profitability," especially against non-Power 5 opponents. Teams ranked 11–25 showed no meaningful inefficiency. — [RePEc](https://ideas.repec.org/a/kap/atlecj/v47y2019i1d10.1007_s11293-019-09611-y.html)
- **Cox, Schwartz, Van Ness & Van Ness (2021), "The Predictive Power of College Football Spreads: Regular Season Versus Bowl Games," Journal of Sports Economics 22(3):251–273.** The spread is a more accurate predictor in the regular season than in bowls. The market is mostly efficient on favorites covering but processes momentum, especially negative momentum, inefficiently, within transaction costs. — [RePEc](https://ideas.repec.org/a/sae/jospec/v22y2021i3p251-273.html); [Sage](https://journals.sagepub.com/doi/abs/10.1177/1527002520975837)
- **Economics Bulletin (2022) 42(3).** The 2020–21 COVID-season CFB spread market was statistically inefficient. Contrarian (anti-herding) strategies had win rates above 50% at various probability cutoffs. — [Econ Bulletin PDF](http://www.accessecon.com/Pubs/EB/2022/Volume42/EB-22-V42-I3-P139.pdf); [RePEc](https://ideas.repec.org/a/ebl/ecbull/eb-22-00065.html)
- **Totals (Paul & Weinbach; Weinbach & Paul).** A slight, non-significant over bias overall, significant only for nationally televised games on major networks. Books shade totals upward, and a later 2003–2015 sample found the totals market largely corrected, with neither over nor under profitable. — [bepress Paul](https://works.bepress.com/rodney_paul/12); [J. Prediction Markets 2009](https://ideas.repec.org/a/buc/jpredm/v3y2009i2p21-37.html); [Westga 2008](https://www.westga.edu/~bquest/2008/football08.pdf)
- **Farinella & Moffett (Journal of Business Inquiry, ~2016).** Betting on teams of the 15 highest-paid coaches over 10 years went 53.95% ATS, rejecting a fair bet. The result was driven by four "superstar" coaches; 11 of 15 were priced efficiently, efficiency improved after five years, and no profitable totals strategy was found. — [Westga 2016 PDF](https://www.westga.edu/~bquest/2016/football2016.pdf)
- Regional information effects in CFB spread betting were studied in Journal of Economics and Finance (2009/2010). — [Springer](https://link.springer.com/article/10.1007/s12197-009-9113-3)

### Inferences
- The evidence is consistent with *opening* and *early-season* lines being the softest, which matches Coleman's opening-line-only significance and Bennett's week-1 holdover bias. Closing lines look efficient against public rating systems, per Fair & Oster.
- Many of these "inefficiencies" are single-sample findings with one-tailed tests and data-mined filters (coaches, momentum, herding cutoffs). Several report decay (totals, coaches), so expect shrinkage out of sample.

### Gaps
- I found no academic study isolating FCS-vs-FBS games, weather, or small conferences as inefficiency pockets, beyond Bennett's non-Power 5 finding.
- I found no academic CFB study comparing opening-to-closing line movement as an information measure for 2018–2026.
