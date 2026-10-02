# B01 baselines: development results

Generated 2026-10-01T20:27:26+00:00. Protocol V01 v1.0 (frozen). **Evaluation class: reconstructed.** Seasons [2019, 2020, 2021] (development role only), horizon 1440 minutes, 20,000 draws per game. Lower is better for every score.

Each model's configuration was selected on these same games, so these scores are optimistic. They are development evidence, not test results.

## Selected configurations

- **elo**: `elo|carryover=0.75|hfa=50|k=30`
- **hfa_only**: `hfa_only|half_life_days=365`
- **ridge**: `ridge|half_life_days=240|penalty=2`

## Overall

| Model | Games | Energy score | Winner log loss | Brier | Margin CRPS | Total CRPS | Margin MAE | Total MAE |
|---|---|---|---|---|---|---|---|---|
| elo | 2343 | 10.803 | 0.509 | 0.170 | 9.573 | 9.862 | 13.53 | 13.86 |
| hfa_only | 2343 | 12.645 | 0.662 | 0.235 | 12.703 | 9.882 | 17.78 | 13.89 |
| ridge | 2343 | 10.498 | 0.502 | 0.168 | 9.468 | 9.415 | 13.37 | 13.28 |

Interval coverage (nominal 50 / 80 / 95%):

| Model | Margin coverage | Margin width | Total coverage | Total width |
|---|---|---|---|---|
| elo | 52.0% / 81.0% / 96.0% | 23.3 / 43.9 / 66.5 | 53.7% / 82.0% / 95.7% | 24.2 / 45.7 / 69.2 |
| hfa_only | 54.8% / 79.7% / 94.7% | 31.1 / 57.9 / 86.6 | 53.4% / 82.0% / 95.9% | 24.0 / 45.7 / 69.3 |
| ridge | 48.8% / 77.3% / 93.5% | 21.0 / 39.7 / 60.1 | 50.9% / 77.9% / 93.6% | 21.0 / 39.8 / 60.5 |

## By season (energy score)

| Model | 2019 | 2020 | 2021 |
|---|---|---|---|
| elo | 10.717 | 11.133 | 10.678 |
| hfa_only | 12.820 | 12.644 | 12.470 |
| ridge | 10.354 | 10.786 | 10.459 |

## Paired comparisons

Challenger minus baseline, per game, on identical games; week-block bootstrap unless noted. Negative favors the challenger. 'Better' means the whole 95% interval is below 0 (V01 rule).

| Challenger | Baseline | Metric | Blocks | Games | Mean diff | 95% interval | Better |
|---|---|---|---|---|---|---|---|
| ridge | hfa_only | energy_score | week | 2343 | -2.1467 | [-2.3465, -1.9457] | yes |
| ridge | hfa_only | energy_score | three_week | 2343 | -2.1467 | [-2.3739, -1.9052] | yes |
| ridge | hfa_only | energy_score | season_half | 2343 | -2.1467 | [-2.3690, -1.9029] | yes |
| ridge | hfa_only | winner_log_loss | week | 2343 | -0.1602 | [-0.1807, -0.1391] | yes |
| ridge | hfa_only | margin_crps | week | 2343 | -3.2351 | [-3.6202, -2.8628] | yes |
| ridge | hfa_only | total_crps | week | 2343 | -0.4672 | [-0.6746, -0.2807] | yes |
| elo | hfa_only | energy_score | week | 2343 | -1.8424 | [-2.0505, -1.6363] | yes |
| elo | hfa_only | energy_score | three_week | 2343 | -1.8424 | [-2.1051, -1.5415] | yes |
| elo | hfa_only | energy_score | season_half | 2343 | -1.8424 | [-2.0376, -1.6186] | yes |
| elo | hfa_only | winner_log_loss | week | 2343 | -0.1532 | [-0.1739, -0.1326] | yes |
| elo | hfa_only | margin_crps | week | 2343 | -3.1294 | [-3.4762, -2.7803] | yes |
| elo | hfa_only | total_crps | week | 2343 | -0.0199 | [-0.0287, -0.0111] | yes |
| ridge | elo | energy_score | week | 2343 | -0.3043 | [-0.4380, -0.1794] | yes |
| ridge | elo | energy_score | three_week | 2343 | -0.3043 | [-0.4267, -0.1927] | yes |
| ridge | elo | energy_score | season_half | 2343 | -0.3043 | [-0.4029, -0.2221] | yes |
| ridge | elo | winner_log_loss | week | 2343 | -0.0070 | [-0.0159, +0.0017] | no |
| ridge | elo | margin_crps | week | 2343 | -0.1057 | [-0.2202, +0.0004] | no |
| ridge | elo | total_crps | week | 2343 | -0.4473 | [-0.6528, -0.2593] | yes |
| ridge | hfa_only | energy_score | week, exclude 2020 | 1775 | -2.2390 | [-2.4778, -1.9936] | yes |
| ridge | elo | energy_score | week, exclude 2020 | 1775 | -0.2908 | [-0.4412, -0.1463] | yes |

## Cohorts (energy score; cohorts under 100 games are descriptive only)

| Cohort | Games | elo | hfa_only | ridge |
|---|---|---|---|---|
| early_season | 780 | 10.931 | 13.289 | 10.758 |
| fbs_vs_nonfbs | 265 | 10.880 | 14.831 | 10.754 |
| postseason | 104 | 10.847 | 11.174 | 10.380 |
| neutral_site | 153 | 10.956 | 11.502 | 10.342 |
| season_2020 | 568 | 11.133 | 12.644 | 10.786 |
| pbp_unreconciled | 86 | 10.363 | 11.744 | 10.032 |
| missing_team_stats | 0 | n/a | n/a | n/a |
| no_line | 8 | 12.916 | 17.938 | 11.608 |

## Tuning grid (mean development energy score)

| Model | Configuration | Energy score |
|---|---|---|
| elo | `elo|carryover=0.75|hfa=50|k=30` | 10.8027 |
| elo | `elo|carryover=0.75|hfa=50|k=40` | 10.8167 |
| elo | `elo|carryover=0.75|hfa=65|k=30` | 10.8224 |
| elo | `elo|carryover=0.6|hfa=50|k=30` | 10.8268 |
| elo | `elo|carryover=0.75|hfa=50|k=20` | 10.8270 |
| elo | `elo|carryover=0.75|hfa=65|k=40` | 10.8284 |
| elo | `elo|carryover=0.6|hfa=50|k=40` | 10.8433 |
| elo | `elo|carryover=0.75|hfa=80|k=40` | 10.8523 |
| elo | `elo|carryover=0.75|hfa=80|k=30` | 10.8553 |
| elo | `elo|carryover=0.6|hfa=65|k=30` | 10.8561 |
| elo | `elo|carryover=0.75|hfa=65|k=20` | 10.8590 |
| elo | `elo|carryover=0.6|hfa=65|k=40` | 10.8616 |
| elo | `elo|carryover=0.6|hfa=50|k=20` | 10.8641 |
| elo | `elo|carryover=0.6|hfa=80|k=40` | 10.8932 |
| elo | `elo|carryover=0.6|hfa=80|k=30` | 10.8991 |
| elo | `elo|carryover=0.75|hfa=80|k=20` | 10.9048 |
| elo | `elo|carryover=0.6|hfa=65|k=20` | 10.9097 |
| elo | `elo|carryover=0.6|hfa=80|k=20` | 10.9691 |
| hfa_only | `hfa_only|half_life_days=365` | 12.6451 |
| ridge | `ridge|half_life_days=240|penalty=2` | 10.4983 |
| ridge | `ridge|half_life_days=480|penalty=2` | 10.6179 |
| ridge | `ridge|half_life_days=120|penalty=2` | 10.6232 |
| ridge | `ridge|half_life_days=240|penalty=5` | 10.6260 |
| ridge | `ridge|half_life_days=480|penalty=5` | 10.6769 |
| ridge | `ridge|half_life_days=480|penalty=10` | 10.8021 |
| ridge | `ridge|half_life_days=960|penalty=2` | 10.8163 |
| ridge | `ridge|half_life_days=120|penalty=5` | 10.8180 |
| ridge | `ridge|half_life_days=960|penalty=5` | 10.8332 |
| ridge | `ridge|half_life_days=240|penalty=10` | 10.8567 |
| ridge | `ridge|half_life_days=960|penalty=10` | 10.8930 |
| ridge | `ridge|half_life_days=960|penalty=20` | 11.0212 |
| ridge | `ridge|half_life_days=480|penalty=20` | 11.0261 |
| ridge | `ridge|half_life_days=120|penalty=10` | 11.1126 |
| ridge | `ridge|half_life_days=240|penalty=20` | 11.1862 |
| ridge | `ridge|half_life_days=960|penalty=50` | 11.3157 |
| ridge | `ridge|half_life_days=480|penalty=50` | 11.4257 |
| ridge | `ridge|half_life_days=120|penalty=20` | 11.4527 |
| ridge | `ridge|half_life_days=240|penalty=50` | 11.6219 |
| ridge | `ridge|half_life_days=120|penalty=50` | 11.8171 |
