# B01 baselines: development results

Generated 2026-10-02T05:08:12+00:00. Protocol V01 v1.0 (frozen). **Evaluation class: reconstructed.** Seasons [2019, 2020, 2021] (development role only), horizon 1440 minutes, 20,000 draws per game. Lower is better for every score.

Each model's configuration was selected on these same games, so these scores are optimistic. They are development evidence, not test results.

Tuning pass 2. Pass 1 (commit 7aa513e) selected values at the edges of its grid, so pass 2 widened the grid once; no further pass is planned.

## Selected configurations

- **elo**: `elo|carryover=0.75|hfa=35|k=30`
- **hfa_only**: `hfa_only|half_life_days=365`
- **ridge**: `ridge|cov_scale=1.2|half_life_days=180|penalty=1`

## Overall

| Model | Games | Energy score | Winner log loss | Brier | Margin CRPS | Total CRPS | Margin MAE | Total MAE |
|---|---|---|---|---|---|---|---|---|
| elo | 2343 | 10.799 | 0.511 | 0.171 | 9.567 | 9.861 | 13.54 | 13.87 |
| hfa_only | 2343 | 12.645 | 0.662 | 0.235 | 12.703 | 9.882 | 17.78 | 13.89 |
| ridge | 2343 | 10.462 | 0.499 | 0.167 | 9.351 | 9.474 | 13.25 | 13.38 |

Interval coverage (nominal 50 / 80 / 95%):

| Model | Margin coverage | Margin width | Total coverage | Total width |
|---|---|---|---|---|
| elo | 52.2% / 80.8% / 95.6% | 23.2 / 43.8 / 66.4 | 53.9% / 82.1% / 95.7% | 24.1 / 45.7 / 69.2 |
| hfa_only | 54.8% / 79.7% / 94.7% | 31.1 / 57.9 / 86.6 | 53.4% / 82.0% / 95.9% | 24.0 / 45.7 / 69.3 |
| ridge | 50.3% / 78.9% / 94.4% | 21.6 / 40.8 / 61.8 | 52.0% / 79.3% / 94.2% | 22.0 / 41.7 / 63.2 |

## By season (energy score)

| Model | 2019 | 2020 | 2021 |
|---|---|---|---|
| elo | 10.724 | 11.114 | 10.671 |
| hfa_only | 12.820 | 12.644 | 12.470 |
| ridge | 10.301 | 10.715 | 10.462 |

## Paired comparisons

Challenger minus baseline, per game, on identical games; week-block bootstrap unless noted. Negative favors the challenger. 'Better' means the whole 95% interval is below 0 (V01 rule).

| Challenger | Baseline | Metric | Blocks | Games | Mean diff | 95% interval | Better |
|---|---|---|---|---|---|---|---|
| ridge | hfa_only | energy_score | week | 2343 | -2.1826 | [-2.3834, -1.9821] | yes |
| ridge | hfa_only | energy_score | three_week | 2343 | -2.1826 | [-2.4115, -1.9435] | yes |
| ridge | hfa_only | energy_score | season_half | 2343 | -2.1826 | [-2.4052, -1.9452] | yes |
| ridge | hfa_only | winner_log_loss | week | 2343 | -0.1637 | [-0.1847, -0.1420] | yes |
| ridge | hfa_only | margin_crps | week | 2343 | -3.3513 | [-3.7316, -2.9699] | yes |
| ridge | hfa_only | total_crps | week | 2343 | -0.4085 | [-0.6420, -0.2015] | yes |
| elo | hfa_only | energy_score | week | 2343 | -1.8464 | [-2.0554, -1.6403] | yes |
| elo | hfa_only | energy_score | three_week | 2343 | -1.8464 | [-2.1087, -1.5423] | yes |
| elo | hfa_only | energy_score | season_half | 2343 | -1.8464 | [-2.0334, -1.6326] | yes |
| elo | hfa_only | winner_log_loss | week | 2343 | -0.1519 | [-0.1731, -0.1309] | yes |
| elo | hfa_only | margin_crps | week | 2343 | -3.1354 | [-3.4883, -2.7848] | yes |
| elo | hfa_only | total_crps | week | 2343 | -0.0207 | [-0.0294, -0.0120] | yes |
| ridge | elo | energy_score | week | 2343 | -0.3362 | [-0.4806, -0.2014] | yes |
| ridge | elo | energy_score | three_week | 2343 | -0.3362 | [-0.4713, -0.2145] | yes |
| ridge | elo | energy_score | season_half | 2343 | -0.3362 | [-0.4767, -0.2364] | yes |
| ridge | elo | winner_log_loss | week | 2343 | -0.0117 | [-0.0204, -0.0034] | yes |
| ridge | elo | margin_crps | week | 2343 | -0.2159 | [-0.3269, -0.1091] | yes |
| ridge | elo | total_crps | week | 2343 | -0.3878 | [-0.6206, -0.1810] | yes |
| ridge | hfa_only | energy_score | week, exclude 2020 | 1775 | -2.2637 | [-2.5058, -2.0163] | yes |
| ridge | elo | energy_score | week, exclude 2020 | 1775 | -0.3161 | [-0.4860, -0.1591] | yes |

## Cohorts (energy score; cohorts under 100 games are descriptive only)

| Cohort | Games | elo | hfa_only | ridge |
|---|---|---|---|---|
| early_season | 780 | 10.929 | 13.289 | 10.779 |
| fbs_vs_nonfbs | 265 | 10.889 | 14.831 | 10.867 |
| postseason | 104 | 10.854 | 11.174 | 10.266 |
| neutral_site | 153 | 10.953 | 11.502 | 10.270 |
| season_2020 | 568 | 11.114 | 12.644 | 10.715 |
| pbp_unreconciled | 86 | 10.361 | 11.744 | 10.142 |
| missing_team_stats | 0 | n/a | n/a | n/a |
| no_line | 8 | 12.944 | 17.938 | 12.084 |

## Tuning grid (mean development energy score)

| Model | Configuration | Energy score |
|---|---|---|
| elo | `elo|carryover=0.75|hfa=35|k=30` | 10.7987 |
| elo | `elo|carryover=0.75|hfa=35|k=25` | 10.7989 |
| elo | `elo|carryover=0.75|hfa=50|k=30` | 10.8027 |
| elo | `elo|carryover=0.75|hfa=35|k=35` | 10.8059 |
| elo | `elo|carryover=0.75|hfa=50|k=35` | 10.8066 |
| elo | `elo|carryover=0.85|hfa=50|k=30` | 10.8072 |
| elo | `elo|carryover=0.75|hfa=50|k=25` | 10.8073 |
| elo | `elo|carryover=0.85|hfa=35|k=30` | 10.8074 |
| elo | `elo|carryover=0.85|hfa=50|k=35` | 10.8081 |
| elo | `elo|carryover=0.85|hfa=35|k=35` | 10.8102 |
| elo | `elo|carryover=0.85|hfa=35|k=25` | 10.8105 |
| elo | `elo|carryover=0.75|hfa=20|k=25` | 10.8113 |
| elo | `elo|carryover=0.85|hfa=50|k=25` | 10.8135 |
| elo | `elo|carryover=0.75|hfa=20|k=30` | 10.8138 |
| elo | `elo|carryover=0.85|hfa=20|k=30` | 10.8226 |
| elo | `elo|carryover=0.75|hfa=20|k=35` | 10.8226 |
| elo | `elo|carryover=0.85|hfa=20|k=25` | 10.8249 |
| elo | `elo|carryover=0.85|hfa=20|k=35` | 10.8266 |
| elo | `elo|carryover=0.95|hfa=50|k=35` | 10.8281 |
| elo | `elo|carryover=0.95|hfa=35|k=35` | 10.8322 |
| elo | `elo|carryover=0.95|hfa=50|k=30` | 10.8331 |
| elo | `elo|carryover=0.95|hfa=35|k=30` | 10.8359 |
| elo | `elo|carryover=0.95|hfa=50|k=25` | 10.8437 |
| elo | `elo|carryover=0.95|hfa=35|k=25` | 10.8453 |
| elo | `elo|carryover=0.95|hfa=20|k=35` | 10.8471 |
| elo | `elo|carryover=0.95|hfa=20|k=30` | 10.8502 |
| elo | `elo|carryover=0.95|hfa=20|k=25` | 10.8602 |
| hfa_only | `hfa_only|half_life_days=365` | 12.6451 |
| ridge | `ridge|cov_scale=1.2|half_life_days=180|penalty=1` | 10.4624 |
| ridge | `ridge|cov_scale=1.2|half_life_days=240|penalty=1` | 10.4645 |
| ridge | `ridge|cov_scale=1.1|half_life_days=240|penalty=1` | 10.4699 |
| ridge | `ridge|cov_scale=1.1|half_life_days=180|penalty=1` | 10.4753 |
| ridge | `ridge|cov_scale=1.2|half_life_days=240|penalty=0.5` | 10.4801 |
| ridge | `ridge|cov_scale=1.2|half_life_days=240|penalty=2` | 10.4835 |
| ridge | `ridge|cov_scale=1.2|half_life_days=180|penalty=0.5` | 10.4848 |
| ridge | `ridge|cov_scale=1.1|half_life_days=240|penalty=2` | 10.4858 |
| ridge | `ridge|cov_scale=1.2|half_life_days=180|penalty=2` | 10.4858 |
| ridge | `ridge|cov_scale=1|half_life_days=240|penalty=1` | 10.4861 |
| ridge | `ridge|cov_scale=1.1|half_life_days=240|penalty=0.5` | 10.4883 |
| ridge | `ridge|cov_scale=1.1|half_life_days=180|penalty=2` | 10.4936 |
| ridge | `ridge|cov_scale=1.2|half_life_days=300|penalty=1` | 10.4959 |
| ridge | `ridge|cov_scale=1.1|half_life_days=300|penalty=1` | 10.4971 |
| ridge | `ridge|cov_scale=1|half_life_days=240|penalty=2` | 10.4983 |
| ridge | `ridge|cov_scale=1|half_life_days=180|penalty=1` | 10.4986 |
| ridge | `ridge|cov_scale=1.1|half_life_days=180|penalty=0.5` | 10.5012 |
| ridge | `ridge|cov_scale=1|half_life_days=240|penalty=0.5` | 10.5073 |
| ridge | `ridge|cov_scale=1|half_life_days=300|penalty=1` | 10.5083 |
| ridge | `ridge|cov_scale=1.1|half_life_days=300|penalty=2` | 10.5088 |
| ridge | `ridge|cov_scale=1.2|half_life_days=300|penalty=0.5` | 10.5096 |
| ridge | `ridge|cov_scale=1.2|half_life_days=300|penalty=2` | 10.5105 |
| ridge | `ridge|cov_scale=1.2|half_life_days=240|penalty=0.25` | 10.5106 |
| ridge | `ridge|cov_scale=1|half_life_days=180|penalty=2` | 10.5125 |
| ridge | `ridge|cov_scale=1.1|half_life_days=300|penalty=0.5` | 10.5125 |
| ridge | `ridge|cov_scale=1|half_life_days=300|penalty=2` | 10.5176 |
| ridge | `ridge|cov_scale=1.1|half_life_days=240|penalty=0.25` | 10.5205 |
| ridge | `ridge|cov_scale=1.1|half_life_days=240|penalty=3` | 10.5237 |
| ridge | `ridge|cov_scale=1.2|half_life_days=240|penalty=3` | 10.5248 |
| ridge | `ridge|cov_scale=1.2|half_life_days=180|penalty=0.25` | 10.5252 |
| ridge | `ridge|cov_scale=1|half_life_days=300|penalty=0.5` | 10.5264 |
| ridge | `ridge|cov_scale=1|half_life_days=180|penalty=0.5` | 10.5280 |
| ridge | `ridge|cov_scale=1|half_life_days=240|penalty=3` | 10.5338 |
| ridge | `ridge|cov_scale=1.1|half_life_days=360|penalty=1` | 10.5341 |
| ridge | `ridge|cov_scale=1.2|half_life_days=300|penalty=0.25` | 10.5352 |
| ridge | `ridge|cov_scale=1.2|half_life_days=360|penalty=1` | 10.5367 |
| ridge | `ridge|cov_scale=1.2|half_life_days=180|penalty=3` | 10.5384 |
| ridge | `ridge|cov_scale=1.1|half_life_days=300|penalty=3` | 10.5393 |
| ridge | `ridge|cov_scale=1.1|half_life_days=300|penalty=0.25` | 10.5395 |
| ridge | `ridge|cov_scale=1|half_life_days=240|penalty=0.25` | 10.5418 |
| ridge | `ridge|cov_scale=1|half_life_days=360|penalty=1` | 10.5426 |
| ridge | `ridge|cov_scale=1.2|half_life_days=300|penalty=3` | 10.5426 |
| ridge | `ridge|cov_scale=1.1|half_life_days=360|penalty=2` | 10.5427 |
| ridge | `ridge|cov_scale=1.1|half_life_days=180|penalty=3` | 10.5430 |
| ridge | `ridge|cov_scale=1.1|half_life_days=180|penalty=0.25` | 10.5440 |
| ridge | `ridge|cov_scale=1|half_life_days=300|penalty=3` | 10.5459 |
| ridge | `ridge|cov_scale=1.2|half_life_days=360|penalty=2` | 10.5473 |
| ridge | `ridge|cov_scale=1.2|half_life_days=360|penalty=0.5` | 10.5492 |
| ridge | `ridge|cov_scale=1|half_life_days=360|penalty=2` | 10.5492 |
| ridge | `ridge|cov_scale=1.1|half_life_days=360|penalty=0.5` | 10.5494 |
| ridge | `ridge|cov_scale=1|half_life_days=300|penalty=0.25` | 10.5549 |
| ridge | `ridge|cov_scale=1|half_life_days=180|penalty=3` | 10.5584 |
| ridge | `ridge|cov_scale=1|half_life_days=360|penalty=0.5` | 10.5590 |
| ridge | `ridge|cov_scale=1.1|half_life_days=360|penalty=3` | 10.5674 |
| ridge | `ridge|cov_scale=1|half_life_days=360|penalty=3` | 10.5712 |
| ridge | `ridge|cov_scale=1.2|half_life_days=360|penalty=0.25` | 10.5719 |
| ridge | `ridge|cov_scale=1.1|half_life_days=360|penalty=0.25` | 10.5732 |
| ridge | `ridge|cov_scale=1.2|half_life_days=360|penalty=3` | 10.5736 |
| ridge | `ridge|cov_scale=1|half_life_days=180|penalty=0.25` | 10.5743 |
| ridge | `ridge|cov_scale=1|half_life_days=360|penalty=0.25` | 10.5847 |
