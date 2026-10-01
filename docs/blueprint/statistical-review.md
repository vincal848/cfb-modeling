# Statistical design review

Reviewed design version 1.0, October 1, 2026. This is an internal design audit using rigorous applied-statistics standards. It is not a review or endorsement by Ron Yurko or CMU. No fitted model has been examined.

## Findings and resolution

| Severity | Finding | Resolution in specification | Evidence needed during implementation |
|---|---|---|---|
| Critical | Historical event dates do not establish forecast availability | Explicit availability evidence and strict/reconstructed modes | Snapshot replay with late arrivals and revised rosters |
| Critical | Final or retrospective ratings leak future information | Exclude without archived publication evidence | Feature availability ledger |
| Critical | Upstream fitting can leak despite chronological final splits | Entire chain is fitted inside forward folds | Fold manifests for EP, players, teams, transforms, experts |
| Critical | Sparse touches cannot identify every player's impact | All-position models gated on participation data | Participation completeness and substitution variation |
| Critical | Separate score/win/spread outputs can contradict | Joint final-score contract and coherent calibration | All views reconcile to the same weighted samples |
| High | Team and player evidence can be counted twice | Joint decomposition or forward residual correction | Ablation and residual dependence checks |
| High | QB/receiver/team effects are confounded | Pooling, correlation diagnostics, limited interpretation | Sensitivity across simpler parameterizations |
| High | Transfers are selected rather than randomized | Conditional scenarios and support flags | Cohort/censoring audit; no unsupported causal labels |
| High | Player nonappearance has multiple explanations | Opportunity/exit component separate from ability | Eligibility/source/exit evidence |
| High | Posterior means hide downstream uncertainty | Matched joint draws and block-refit sensitivity | Dependence preserved; wider intervals in sparse cohorts |
| High | Simulated regulation ties mishandled as final ties | Explicit final/regulation labels and OT regime | State tests and no unresolved modern final-score tie mass |
| High | Future tracking frames create target leakage | Frame-level cutoff and held-game/player validation | Feature provenance and time-direction tests |
| High | Hypothetical paths ignore opponent reactions | Conditional comparison labeling | Responsive simulation only if independently validated |
| Moderate | Flexible stacking overfits few games | At most three initial experts and global weights | Forward comparison against simplest champion |
| Moderate | Simulation noise can choose weights/actions | Fixed sample protocol and convergence checks | Sensitivity to more simulations near thresholds |
| Moderate | Aggregate calibration hides weak cohorts | Stratified diagnostics and cohort counts | Reliability and coverage with uncertainty |
| Moderate | Research default decision thresholds look optimized | Explicitly configurable, preregistered defaults | Validation-only policy tuning and frozen test evaluation |

## Claims allowed now

The CFBD core has a concrete implementation path. The SQLite contract and configuration can be checked locally. Forecast/decision traceability is specified. A tracking extension has explicit prerequisites and independent evaluation. The research supports the model classes and validation approach; it does not establish performance in this dataset.

## Claims withheld

No accuracy, profitable market edge, causal transfer effect, comprehensive individual defensive/line impact, college tracking accuracy, or calibrated interval coverage has been demonstrated. Numerical thresholds in this package are proposed defaults. Historical scores cannot be labeled prospective unless availability evidence exists.

## Release checklist

- Inputs: source coverage measured, identity links reviewed, missingness and truncation handled.
- Time: future facts excluded; unknown publication evidence disclosed; old forecasts never rewritten.
- State: scoring rewards, conversions, possession signs, clocks, and rules reconcile.
- Inference: sensible prior predictions; parameter recovery; R-hat/ESS/divergence checks; prior sensitivity.
- Prediction: held-forward proper scores, coverage/width, tail checks, and cohort diagnostics.
- Comparison: simplest champion retained unless evidence justifies additional complexity.
- Decisions: same immutable distribution and policy produce same unrounded choice; pushes/signs correct.
- Operation: source failure, missing tracking, incomplete players, and numerical failure exercise fallback.
- Communication: model-based scenarios and predictive associations are labeled; no causal or confidence overstatement.

## Final assessment

Approved as an implementation blueprint, subject to the specified gates. The design is coherent only if strict temporal provenance, opportunity conservation, final-score semantics, and matched uncertainty are actually implemented. Tracking and full-position attribution remain conditional extensions. A statistical production approval can occur only after models are fitted and the evidence above is reviewed.
