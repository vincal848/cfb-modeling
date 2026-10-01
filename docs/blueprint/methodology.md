# Full modeling methodology

Version 1.0 — October 1, 2026

## 1. Objective and scope

Produce reproducible, calibrated forecasts connecting players to rosters, teams, and games. Evaluate transfers and on-field movement through explicit conditional scenarios. Publish probability distributions, parameter uncertainty, data-quality indicators, and a deterministic choice policy.

The initial population is games involving an FBS team, retaining FCS opponents and using more strongly pooled opponent effects where evidence is sparse. Keep regular-season and postseason indicators. Exclude canceled and unresolved games from final-score training; postponed games retain stable identity and revised schedule versions. Historical games with different rules are handled by a season rules registry.

Production products are separate: preseason, weekly pregame, near-kickoff, and later live forecasts. Football-only and market-informed forecasts are also separate. A forecast evaluated at one horizon is never compared silently against another horizon.

Initial information cutoffs are seven days, 24 hours, and 60 minutes before scheduled kickoff. For games scheduled inside a horizon or changed after the snapshot, label the actual lead time and schedule version. The preseason cutoff is a configured timestamp preceding the season's first included kickoff. Store UTC; display America/New_York with daylight-saving conversion.

### Estimands

| Product | Estimand | Unit |
|---|---|---|
| Player opportunity | Probability of any recorded opportunity and distribution of opportunity share | player-game or player-season |
| Player performance | Context-adjusted future outcomes conditional on opportunity | attributed play, player-game |
| Player development | Next-season opportunity and ability distribution | player-season |
| Transfer | Future opportunity/performance at a named destination under declared assumptions | player-destination-cutoff |
| Roster | Expected unit strength under a coherent opportunity allocation | team-position-cutoff |
| Team | Filtered offensive/defensive/special-teams/pace state | team-cutoff |
| Game | Joint final scores, winner, margin, total | game-cutoff |
| Movement | Future trajectory and outcome conditional on observed frames | player-play-frame |
| Decision | Action maximizing a frozen objective over feasible choices | forecast-policy |

Opportunity is not the same as injury availability. Absence from a stat line is not evidence of injury. A transfer forecast is not a causal estimate of the transfer's effect. Retrospective performance and future ability are distinct outputs.

## 2. Data design and historical truth

Use immutable raw responses, normalized canonical facts, then versioned modeling snapshots. Required core families: schedules/results, team and player game statistics, drives, plays, attributed player events, rosters, recruiting, coach history, transfers, and explicitly timestamped market observations. Advanced CFBD metrics are comparison features only when their availability and methodology are evidenced.

CFBD documents plays, player attribution, usage, and portal records with different start dates; enriched passing/rushing has a shorter history. A listed range does not establish complete coverage. [CFBD availability](https://apinext.collegefootballdata.com/data-availability). Inspect actual completeness by family, season, team, and field before choosing the cohort. Do not force every model to use the same historical start year.

For each mutable record, store `event_time`, `available_at`, `ingested_at`, `source_version`, `request_id`, and `payload_hash`. Availability evidence is one of `prospective_observation`, `archived_publication`, `reconstructed`, or `unknown`. A date referring to the event is not publication evidence. A response first retrieved in 2026 does not establish what a model knew in 2022.

Strict prospective/replay forecasts admit facts only when evidenced availability is at or before the cutoff. Historical experiments without this evidence are labeled reconstructed retrospective evaluations. Corrected past outcomes can be used as training labels; corrected historical predictor details still require a reconstruction caveat. Publish both cohort coverage and exclusions.

Do not use final season ratings, actual game weather, later roster destinations, final recruiting rankings, or closing lines as early pregame predictors without cutoff evidence. CORE's historical results are expressly retrospective; `throughWeek` alone does not establish historical publication. [CORE methodology](https://api.collegefootballdata.com/core-ratings).

### Identity and coverage

Use canonical string IDs for players and teams. Preserve source IDs and an identity-link table with match status and evidence. Roster recruiting links are useful when present. Portal records documented without canonical athlete IDs require a crosswalk. Names, positions, origin, roster history, and recruiting information can propose candidates; ambiguous matches require review or remain unresolved. [Player reference](https://apinext.collegefootballdata.com/api/players).

Keep roster membership valid-time history separate from the player entity. Record entry, commitment, withdrawal, and enrollment as different events when the source supports them. Do not equate portal entry with departure or a named destination with actual enrollment.

For each API adapter, define supported filters, response cap, request partitioning, and completeness check. The documented player play-stat endpoint has a 2,000-record cap; partition into supported smaller requests and investigate any capped result. Do not assume undocumented pagination. [Play reference](https://apinext.collegefootballdata.com/api/plays).

Structural missingness, source omission, unknown identity, and genuine zero are different states. Fit imputers on training periods only and retain missingness indicators. Validate IDs, score reconciliation, possession ordering, field position, and attribution coverage. Mark a game incomplete rather than inventing its missing plays.

## 3. Play value and EPA

Fit a college-specific expected-points model on preplay state: possession, down, distance, field position, period, time, score context, and relevant rules. Begin with a multinomial next-scoring-event model with signed scoring values and a no-score outcome. Treat touchdown plus conversion value explicitly through a learned conversion model; do not hard-code every touchdown sequence as seven points. Use a regularized additive classifier before flexible boosting.

Define a state-value convention from the current possessing team's perspective. For an observed transition, `EPA = scoring_reward + possession_sign * EP(next_state) - EP(current_state)`. `scoring_reward` is actual points credited minus points conceded during the transition; `possession_sign` is +1 if the perspective is unchanged and -1 otherwise. At a true game terminal state, future EP is zero. Handle touchdowns, conversions, safeties, returns, penalties, nullified plays, end-of-half states, and overtime using explicit transition tests. Never count the same scoring event in both reward and the next state's value.

EPA is a derived noisy target. Refit the EP model inside each chronological training fold, or use historically evidenced provider outputs as a separately labeled benchmark. For parameter uncertainty, propagate EP model variation where feasible and report an approximation if fixed EPA labels are used. For total pipeline uncertainty, use block-resampled refits as a sensitivity check.

The nflWAR approach motivates the value-to-player connection, not an assumption that NFL coefficients apply to college football. [Yurko, Ventura, and Horowitz](https://arxiv.org/abs/1802.00998).

## 4. Player opportunity, ability, and development

Separate volume from effectiveness. First estimate the probability of at least one recorded role-specific opportunity with a hierarchical logistic model. Conditional on an eligible group receiving opportunities, allocate them with a logistic-normal share model and multinomial counts. Group totals come from the game/roster model; allocations sum to that total. QB attempts, carries, and receiving targets are distinct opportunity categories, with an explicit unassigned category where attribution is incomplete.

If all players in a category are predicted inactive or unknown, route the allocation to an explicit replacement/unknown group. Do not renormalize only observed players and thereby inflate their forecasts.

For position p, use latent standardized ability:

`a[i,t] = mu[p] + rho[p] * (a[i,t-1] - mu[p]) + beta[p]' x[i,t] + epsilon[i,t]`.

Use experience, prior performance, recruit information known at the cutoff, and suitable physical features. Class year is not automatically age or remaining eligibility. Initialize new players from position/recruit priors with missingness-aware pooling. Transfers keep the same latent player identity; destination context changes separately. Do not fit unsupported individual slopes for extremely sparse players.

Initial likelihoods:

| Role | Opportunity | Performance likelihood |
|---|---|---|
| QB | dropbacks/attempt shares | completion/interception/sack Bernoulli models; robust passing EPA model |
| RB | carries and relevant target shares | success Bernoulli; yard/value Student-t or mixture |
| WR/TE | target shares | catches conditional on targets; receiving-value distribution |
| Kicker | attempts by modeled distance/context | hierarchical logistic make model |
| Punter | punt opportunities | robust net field-position model with returns/context |
| OL/defense | participation only with evidence | unit effects initially; participation-based impact extension later |

Scrambles, sacks, kneels, spikes, and designed runs require a declared taxonomy. Separate these categories where the source supports it and carry an unknown label otherwise. Player value model covariates can include realized play type for retrospective attribution; pregame prediction must marginalize over or predict that type.

A passing model includes QB, receiving role, offensive context, opponent defense, and preplay state. QB/receiver effects are confounded when combinations rarely change. Fit partial pooling, monitor posterior correlations, compare simpler parameterizations, and avoid reporting unique causal credit. Offensive line and defender impact cannot be inferred comprehensively from touches alone.

Proposed standardized priors: coefficients Normal(0,0.5), group-effect standard deviations half-Normal(0,0.5), correlation matrices LKJ(2), and persistence constrained to [0,1]. These are starting choices, checked through prior prediction and sensitivity; do not apply them unchanged to unstandardized points or yards. For Student-t residuals use degrees of freedom greater than 2 when means/variances are required. [Bayesian workflow](https://arxiv.org/abs/2011.01808).

Output posterior ability, next-period usage/performance distributions, probability above a declared position benchmark, sample size, prior influence, and coverage flags. Report rank intervals or pairwise superiority probabilities instead of presenting noisy ranks as certain.

## 5. Transfers, exits, and destination scenarios

Build destination evaluation before destination selection prediction. Given a player, destination, cutoff roster, and season, predict opportunity competition, contextual performance, and team-strength change. Fit a pooled adaptation effect by position, prior level, and experience. Repeated transfers share a player effect. Restrict comparisons to destinations with adequate covariate support; label extrapolation.

Do not treat next-year nonappearance as zero ability. Use a participation/exit component and conditional observed performance. Graduation, draft entry, loss of eligibility, withdrawal, and missing source coverage are distinct competing or censoring mechanisms. Sparse portal years limit interaction complexity.

Portal-entry forecasting needs an eligible population containing nonentrants. A discrete-time hazard model predicts entry while handling known competing exits. Conditional destination prediction needs a defined candidate set and an outside/unknown alternative; accuracy is meaningless if candidate sets differ silently. This is a later exploratory feature because historical publication timing and eligibility coverage may be incomplete.

Transfer value is the paired difference between coherent roster scenarios using common random numbers. Reallocate opportunities and replacement players in each scenario. Show expected improvement, outcome interval, probability of improvement, and assumptions. Selection bias prevents automatic causal interpretation. Do not convert latent ability directly into wins without running the team/game model.

## 6. Roster aggregation and dynamic teams

For each position/category, `R[j,p,t] = sum_i q[i,j,p,t] * a[i,t]`. q is a future opportunity share within that category; it is random and correlated with roster scenarios. Include continuity, recruiting priors, and known additions/departures only through nonduplicative features.

Define team offense as roster-explained strength plus residual context, with corresponding defense, special teams, and pace models. Use centered team effects, season intercepts, and separate weekly/offseason innovations. The residual strength follows an AR(1) state process. Filter states using past games only; full-season smoothed states belong only in retrospective analysis. [Glickman and Stern](https://glicko.net/research/nfl.pdf).

Initial implementation fits a team-only model. Introduce roster covariates jointly or fit a residual correction on forward-generated predictions. Do not append a player adjustment to an already player-informed rating without checking duplication. Coaching effects are strongly pooled and interpreted as predictive context, not coaching causality.

Use rest, neutral-site status, travel where reliably derived, home advantage, known rules, and scenario availability. Realized game-day weather is not a pregame forecast; use timestamped weather forecasts or omit it. FCS opponents receive explicit uncertainty rather than a single universal strength.

## 7. Game models and score coherence

Ship winner/margin/total baselines first: recomputed Elo, regularized margin regression, and a dynamic Student-t margin model. A separate total model is a benchmark, not a coherent joint score generator. Do not derive scores by independently rounding incompatible margin/total predictions.

Production experts return nonnegative integer final score samples with explicit overtime treatment. Implement three complementary experts sequentially:

1. Dynamic joint-score expert: initially a correlated count model using team offense/defense and shared game pace. Fit dispersion and dependence, simulate regulation scores, then apply a season-specific overtime kernel to ties. Diagnose key-number and tail behavior; count scores are an approximation rather than a football scoring mechanism.
2. Feature expert: regularized/boosted paired score means and scales. Use held-forward paired score residuals with an explicit joint dependence model. A concrete distributional version is a bivariate latent log-score Student-t with discretization into score cells. Define zero-score cells using a lower boundary of negative infinity; other cells have log boundaries log(s+0.5) and log(s+1.5) for log(score+1). Learn means from features and covariance from prior residuals. Apply a fitted overtime kernel to tied regulation samples. Any training data used to learn regulation parameters must have regulation labels, not silently final scores.
3. Drive simulator: predict drive outcome, elapsed time, and subsequent possession field position, conditional on opponent, team states, score/time, and shared game effects. Model turnovers and return points explicitly, keep conversion scoring separate, end regulation at the clock limit, then execute the rules registry for overtime.

If regulation endpoints cannot be reconstructed accurately, fit an explicitly final-score statistical expert conditioned on unequal scores for modern completed games. Do not add overtime again. Keep the drive simulator conditional on complete state reconstruction. Expert contracts state whether scores are regulation or final. Production stack inputs must all be final scores.

The simulator's transitions are coupled: turnovers change possession/field position, return touchdowns change scoring, possession durations change remaining opportunities. Draw shared pace, roster, and team conditions once per game. Do not independently forecast each team's possession count.

Derive all production outcomes from paired final scores: `M=H-A`, `T=H+A`, `P(home win)=P(M>0)`. Quantile intervals come from that same mixture. Mean implied scores may be fractional; a representative integer score is a separately labeled modal or selected scenario, not a rounded mean described as the most likely score.

## 8. Forecast stacking and calibration

Use a mixture `F_stack = sum_m w_m F_m`, weights nonnegative and summing to one. Learn weights on chronological out-of-sample forecasts. Begin with global weights and at most three experts. [Yao et al.](https://arxiv.org/abs/1704.02030).

For sample-based joint scores use energy score: `ES(F,y)=E||X-y|| - 0.5 E||X-X'||`. Compute with independent or appropriately paired Monte Carlo samples; use fixed subsamples/seeds and enough draws that simulation noise does not determine weights. Fit on a held-forward block and regularize toward a simple mixture, choosing regularization inside earlier temporal validation. Winner Brier/log loss and margin/total CRPS are companion diagnostics. Do not optimize likelihood on raw finite simulation histograms with zero-count cells. [Proper scoring rules](https://sites.stat.washington.edu/people/raftery/Research/PDF/Gneiting2007jasa.pdf).

Separate football-only and market-informed stacks. Market features require book, line, odds, snapshot time, and overtime settlement convention. Do not use CFBD spread-derived pregame probability as an independent football-only feature. Evaluate against a timestamp-matched market benchmark and report games lacking comparable lines.

Do not independently overwrite winner probability after producing a joint score distribution. If later winner calibration is required, reweight winner/loser regions of the joint distribution using a fitted calibration map, preserving each region's conditional score distribution. Reevaluate margin and total scores after reweighting. Tiny region mass requires stabilization. Interval-only conformal adjustments are labeled as separate interval products; they are not silently substituted into the original coherent joint distribution.

## 9. Uncertainty and deterministic decisions

Distinguish outcome probabilities, posterior parameter credible intervals, future outcome prediction intervals, scenario sensitivity, model disagreement, data-quality flags, and Monte Carlo error. A win probability is not a model-confidence percentage. Posterior intervals remain conditional on the fitted model.

Draw roster, player, and team quantities jointly or retain matched draw IDs and common contextual effects in a modular approximation. Do not sample correlated team/QB effects independently. Add a block-refit sensitivity experiment for uncertainty omitted by staged fitting. Display 50/80/95% prediction intervals and measure their coverage. Adaptive conformal methods are optional prospective interval correction; they do not establish conditional coverage for every matchup. [Gibbs and Candes](https://arxiv.org/abs/2106.00170).

Forced winner policy: choose home when unrounded probability exceeds 0.5, away when below; exact equality uses lexicographically smaller canonical string team ID. Forecast distributions with modern final-game tie mass are invalid until their overtime/final-score handling is repaired. Forced picks remain visible even when the recommendation is withheld for weak evidence.

Spread convention: h is the handicap applied to HOME, so cover is `M+h>0`; push is equality. Total threshold l: over is `T>l`, under is `T<l`, push equality. Freeze book/odds/cutoff/settlement convention. Per-unit net EV at decimal odds d is `p_win*(d-1)-p_loss`; a push returns zero net. Missing prices or mismatched settlement means recommendation unavailable.

Proposed research recommendation policy: select the positive-EV side with greatest expected value, requiring EV at least 0.03 and all mandatory quality gates; otherwise PASS. The 0.03 value is a configurable research default, not a discovered profitable threshold. Tie-break policies are fixed before evaluation. Do not tune thresholds on a final test set. This plan does not prescribe capital allocation or staking.

Roster choice maximizes expected team-strength improvement over declared feasible destinations. Store eligibility, roster constraints, and any supplied cost assumptions. Apply exact numeric utility before deterministic ID tie-break. Display uncertainty and sensitivity separately from the selection.

Every forecast and decision records snapshot hash, cutoff, model/policy version, dependency lock hash, sample artifact hash, random seed, and reason codes. Cache distributions and derive all views from them. Do not round before making decisions.

Estimate simulation error from independent simulation batches or an effective-sample-size calculation when draws reuse correlated posterior samples. The simple Bernoulli standard-error formula applies only to independent draws; it is not a parameter credible interval. Increase simulation effort near a decision boundary and report a boundary-sensitive flag when numerical resolution remains inadequate.

## 10. Tracking extension

Requires licensed/reliably accessible frame coordinates, stable player IDs, ball location, frame times, direction, and event markers. Verify coverage and usage rights before ingestion. Full participation is a separate useful extension even without coordinates.

Normalize attack direction, units, timestamps, missing frames, stationary frames, and boundary conventions. Do not use future trajectory frames or postplay outcomes as frame-level predictors. Begin with constant-velocity baselines and a ball-carrier step-and-turn model: stationary/moving hurdle, positive step length lognormal, and moving turn angle von Mises with player/position pooling. Condition on current/prior motion and nearby teammates/opponents. [Nguyen and Yurko, 2026 preprint](https://arxiv.org/html/2603.17866v1).

Fit an outcome distribution from the current frame, then map it through the college EP model. [Going Deep](https://arxiv.org/abs/1906.01760). Split by games and held-out players; measure trajectory error, likelihood/coverage, outcome scores, and physical plausibility. Fixed defender trajectories produce conditional hypothetical comparisons, not full behavioral counterfactuals. A responsive multi-agent simulation is a later research project with its own validation.

Aggregate tracking measures into a player/team forecast only using games available by the forecast cutoff. Missing tracking must trigger the CFBD-only model, not exclusion of that game from ordinary forecasts. NFL prototypes require college-specific external validation before college player rankings are promoted.

## 11. Validation and promotion

Default historical design: 2014-2018 warm-up, 2019-2021 rolling development, 2022 stack fitting, 2023 optional calibration, 2024-2025 untouched historical test, and 2026 prospective logging from implementation onward. These are proposed splits; change only after a data coverage audit and before inspecting candidate results. Transfer modules use their shorter available cohort and position-pooled specifications. Enriched 2025+ fields and tracking have separate experiments rather than shrinking the core to one season.

Nested chronological fitting includes imputers, EP labels, player effects, team filtering, expert hyperparameters, weights, and calibration. Each outer validation forecast is generated by a complete past-only chain. Stack training covariates must be predictions generated without that game's outcome. [Leave-future-out validation](https://arxiv.org/abs/1902.06281).

Report winner log loss/Brier/reliability, margin/total MAE and CRPS, joint energy score, interval width/coverage, player opportunity and conditional-performance scores, and cohort counts. Include early-season, FBS/FCS, transfer-heavy, sparse-player, postseason, and missing-data cohorts. Small cohorts show uncertainty, not definitive pass/fail conclusions.

Use paired chronological week-block resampling for performance differences; assess alternative longer blocks and repeated-team dependence. Play-level independence is inappropriate. Use ablations for player, roster, transfer, tracking, and market features. Performance claims must state whether the evaluation is prospective, archived replay, or reconstructed.

Promotion requires no leakage finding; valid data contracts; resolved numerical failures; competitive primary score versus the champion; no unexplained large deterioration in complementary scores; coverage reported with uncertainty; and reproducible decisions. To claim superiority, paired uncertainty should support it on the prespecified primary metric. Failure to establish improvement keeps the simpler champion. After opening a holdout, archive its result and use a new prospective period for future confirmation.

## 12. Views and interpretation

Player view: opportunity/ability intervals, development, evidence, prior influence, and identity flags. Transfer view: feasible destinations, opportunity competition, paired scenario changes, support flags. Team view: components, continuity, filtered-state uncertainty. Game view: joint score scenarios, winner probability, margin/total intervals, forced pick, recommendation and reason codes. Tracking view: observed motion, alternatives, conditional outcome value. Evaluation view: proper scores, calibration, coverage, cohort counts, and experiment provenance. Audit view: snapshot contents and versions.

Feature explanations describe predictive association. Suppress causal language unless an independently justified causal design exists. Show uncertainty and data support without inventing one universal confidence label.
