# B02: development results

Generated 2026-10-02T05:23:10+00:00. Protocol V01 v1.0 (frozen). **Evaluation class: reconstructed.** Seasons [2019, 2020, 2021] (development role only), horizon 1440 minutes, 20,000 draws per game. Lower is better for every score.

Each model's configuration was selected on these same games, so these scores are optimistic. They are development evidence, not test results.

Tuning pass 1. The grid was fixed before this run.

## Selected configurations

- **dynamic**: `dynamic|q_week=0.25|rho=0.9|s0=8|sigma=11`
- **elo**: `elo|carryover=0.75|hfa=35|k=30`
- **hfa_only**: `hfa_only|half_life_days=365`
- **ridge**: `ridge|cov_scale=1.2|half_life_days=180|penalty=1`

## Overall

| Model | Games | Energy score | Winner log loss | Brier | Margin CRPS | Total CRPS | Margin MAE | Total MAE |
|---|---|---|---|---|---|---|---|---|
| dynamic | 2343 | 10.391 | 0.497 | 0.166 | 9.227 | 9.471 | 13.08 | 13.40 |
| elo | 2343 | 10.799 | 0.511 | 0.171 | 9.567 | 9.861 | 13.54 | 13.87 |
| hfa_only | 2343 | 12.645 | 0.662 | 0.235 | 12.703 | 9.882 | 17.78 | 13.89 |
| ridge | 2343 | 10.462 | 0.499 | 0.167 | 9.351 | 9.474 | 13.25 | 13.38 |

Interval coverage (nominal 50 / 80 / 95%):

| Model | Margin coverage | Margin width | Total coverage | Total width |
|---|---|---|---|---|
| dynamic | 53.4% / 82.1% / 96.1% | 23.1 / 43.6 / 66.0 | 53.9% / 81.5% / 95.3% | 23.0 / 43.4 / 65.8 |
| elo | 52.2% / 80.8% / 95.6% | 23.2 / 43.8 / 66.4 | 53.9% / 82.1% / 95.7% | 24.1 / 45.7 / 69.2 |
| hfa_only | 54.8% / 79.7% / 94.7% | 31.1 / 57.9 / 86.6 | 53.4% / 82.0% / 95.9% | 24.0 / 45.7 / 69.3 |
| ridge | 50.3% / 78.9% / 94.4% | 21.6 / 40.8 / 61.8 | 52.0% / 79.3% / 94.2% | 22.0 / 41.7 / 63.2 |

## By season (energy score)

| Model | 2019 | 2020 | 2021 |
|---|---|---|---|
| dynamic | 10.243 | 10.723 | 10.325 |
| elo | 10.724 | 11.114 | 10.671 |
| hfa_only | 12.820 | 12.644 | 12.470 |
| ridge | 10.301 | 10.715 | 10.462 |

## Paired comparisons

Challenger minus baseline, per game, on identical games; week-block bootstrap unless noted. Negative favors the challenger. 'Better' means the whole 95% interval is below 0 (V01 rule).

| Challenger | Baseline | Metric | Blocks | Games | Mean diff | 95% interval | Better |
|---|---|---|---|---|---|---|---|
| dynamic | ridge | energy_score | week | 2343 | -0.0718 | [-0.1407, -0.0094] | yes |
| dynamic | ridge | energy_score | three_week | 2343 | -0.0718 | [-0.1597, +0.0081] | no |
| dynamic | ridge | energy_score | season_half | 2343 | -0.0718 | [-0.1512, +0.0037] | no |
| dynamic | ridge | winner_log_loss | week | 2343 | -0.0020 | [-0.0067, +0.0022] | no |
| dynamic | ridge | margin_crps | week | 2343 | -0.1243 | [-0.2476, -0.0181] | yes |
| dynamic | ridge | total_crps | week | 2343 | -0.0023 | [-0.0347, +0.0314] | no |
| dynamic | elo | energy_score | week | 2343 | -0.4080 | [-0.5437, -0.2759] | yes |
| dynamic | elo | energy_score | three_week | 2343 | -0.4080 | [-0.5031, -0.3112] | yes |
| dynamic | elo | energy_score | season_half | 2343 | -0.4080 | [-0.5048, -0.3101] | yes |
| dynamic | elo | winner_log_loss | week | 2343 | -0.0137 | [-0.0227, -0.0044] | yes |
| dynamic | elo | margin_crps | week | 2343 | -0.3402 | [-0.4938, -0.1980] | yes |
| dynamic | elo | total_crps | week | 2343 | -0.3901 | [-0.6209, -0.1820] | yes |
| dynamic | hfa_only | energy_score | week | 2343 | -2.2544 | [-2.4843, -2.0302] | yes |
| dynamic | hfa_only | energy_score | three_week | 2343 | -2.2544 | [-2.5145, -1.9702] | yes |
| dynamic | hfa_only | energy_score | season_half | 2343 | -2.2544 | [-2.4772, -2.0000] | yes |
| dynamic | hfa_only | winner_log_loss | week | 2343 | -0.1657 | [-0.1871, -0.1439] | yes |
| dynamic | hfa_only | margin_crps | week | 2343 | -3.4756 | [-3.8946, -3.0587] | yes |
| dynamic | hfa_only | total_crps | week | 2343 | -0.4108 | [-0.6442, -0.2031] | yes |
| dynamic | ridge | energy_score | week, exclude 2020 | 1775 | -0.0974 | [-0.1850, -0.0215] | yes |

## Cohorts (energy score; cohorts under 100 games are descriptive only)

| Cohort | Games | dynamic | elo | hfa_only | ridge |
|---|---|---|---|---|---|
| early_season | 780 | 10.572 | 10.929 | 13.289 | 10.779 |
| fbs_vs_nonfbs | 265 | 10.524 | 10.889 | 14.831 | 10.867 |
| postseason | 104 | 10.370 | 10.854 | 11.174 | 10.266 |
| neutral_site | 153 | 10.310 | 10.953 | 11.502 | 10.270 |
| season_2020 | 568 | 10.723 | 11.114 | 12.644 | 10.715 |
| pbp_unreconciled | 86 | 9.917 | 10.361 | 11.744 | 10.142 |
| missing_team_stats | 0 | n/a | n/a | n/a | n/a |
| no_line | 8 | 12.113 | 12.944 | 17.938 | 12.084 |

## Tuning grid (mean development energy score)

| Model | Configuration | Energy score |
|---|---|---|
| dynamic | `dynamic|q_week=0.25|rho=0.9|s0=8|sigma=11` | 10.3907 |
| dynamic | `dynamic|q_week=1|rho=0.75|s0=5|sigma=11` | 10.3957 |
| dynamic | `dynamic|q_week=1|rho=0.9|s0=5|sigma=11` | 10.4084 |
| dynamic | `dynamic|q_week=0.25|rho=0.75|s0=8|sigma=11` | 10.4151 |
| dynamic | `dynamic|q_week=0.25|rho=0.75|s0=5|sigma=11` | 10.4161 |
| dynamic | `dynamic|q_week=0.25|rho=0.9|s0=8|sigma=12` | 10.4162 |
| dynamic | `dynamic|q_week=1|rho=0.9|s0=8|sigma=11` | 10.4233 |
| dynamic | `dynamic|q_week=0.25|rho=0.9|s0=5|sigma=11` | 10.4282 |
| dynamic | `dynamic|q_week=1|rho=0.75|s0=5|sigma=12` | 10.4315 |
| dynamic | `dynamic|q_week=1|rho=0.9|s0=5|sigma=12` | 10.4346 |
| dynamic | `dynamic|q_week=0.25|rho=0.75|s0=8|sigma=12` | 10.4396 |
| dynamic | `dynamic|q_week=1|rho=0.75|s0=8|sigma=11` | 10.4415 |
| dynamic | `dynamic|q_week=1|rho=0.9|s0=8|sigma=12` | 10.4443 |
| dynamic | `dynamic|q_week=1|rho=0.6|s0=5|sigma=11` | 10.4554 |
| dynamic | `dynamic|q_week=0.25|rho=0.75|s0=5|sigma=12` | 10.4594 |
| dynamic | `dynamic|q_week=0.25|rho=0.9|s0=5|sigma=12` | 10.4627 |
| dynamic | `dynamic|q_week=1|rho=0.75|s0=8|sigma=12` | 10.4652 |
| dynamic | `dynamic|q_week=0.25|rho=0.6|s0=5|sigma=11` | 10.4821 |
| dynamic | `dynamic|q_week=1|rho=0.6|s0=5|sigma=12` | 10.4981 |
| dynamic | `dynamic|q_week=0.25|rho=0.6|s0=8|sigma=11` | 10.4981 |
| dynamic | `dynamic|q_week=1|rho=0.6|s0=8|sigma=11` | 10.5149 |
| dynamic | `dynamic|q_week=0.25|rho=0.6|s0=8|sigma=12` | 10.5208 |
| dynamic | `dynamic|q_week=0.25|rho=0.6|s0=5|sigma=12` | 10.5305 |
| dynamic | `dynamic|q_week=1|rho=0.6|s0=8|sigma=12` | 10.5378 |
| dynamic | `dynamic|q_week=4|rho=0.75|s0=5|sigma=11` | 10.5413 |
| dynamic | `dynamic|q_week=4|rho=0.6|s0=5|sigma=11` | 10.5445 |
| dynamic | `dynamic|q_week=4|rho=0.75|s0=5|sigma=12` | 10.5604 |
| dynamic | `dynamic|q_week=4|rho=0.6|s0=5|sigma=12` | 10.5715 |
| dynamic | `dynamic|q_week=4|rho=0.75|s0=8|sigma=11` | 10.6103 |
| dynamic | `dynamic|q_week=4|rho=0.9|s0=5|sigma=11` | 10.6189 |
| dynamic | `dynamic|q_week=4|rho=0.75|s0=8|sigma=12` | 10.6236 |
| dynamic | `dynamic|q_week=4|rho=0.9|s0=5|sigma=12` | 10.6278 |
| dynamic | `dynamic|q_week=4|rho=0.6|s0=8|sigma=11` | 10.6390 |
| dynamic | `dynamic|q_week=4|rho=0.9|s0=8|sigma=11` | 10.6471 |
| dynamic | `dynamic|q_week=4|rho=0.9|s0=8|sigma=12` | 10.6550 |
| dynamic | `dynamic|q_week=4|rho=0.6|s0=8|sigma=12` | 10.6554 |
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
