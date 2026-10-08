# G01: development results

Generated 2026-10-02T18:42:16+00:00. Protocol V01 v1.0 (frozen). **Evaluation class: reconstructed.** Seasons [2019, 2020, 2021] (development role only), horizon 1440 minutes, 20,000 draws per game. Lower is better for every score.

Each model's configuration was selected on these same games, so these scores are optimistic. They are development evidence, not test results.

Tuning pass 1. The grid was fixed before this run.

## Selected configurations

- **dynamic**: `dynamic|q_week=0.25|rho=0.9|s0=8|sigma=11`
- **elo**: `elo|carryover=0.75|hfa=35|k=30`
- **g01**: `g01|disp_r=10|pace_k=50`
- **hfa_only**: `hfa_only|half_life_days=365`
- **ridge**: `ridge|cov_scale=1.2|half_life_days=180|penalty=1`

## Overall

| Model | Games | Energy score | Winner log loss | Brier | Margin CRPS | Total CRPS | Margin MAE | Total MAE |
|---|---|---|---|---|---|---|---|---|
| dynamic | 2343 | 10.391 | 0.497 | 0.166 | 9.227 | 9.471 | 13.08 | 13.40 |
| elo | 2343 | 10.799 | 0.511 | 0.171 | 9.567 | 9.861 | 13.54 | 13.87 |
| g01 | 2343 | 10.496 | 0.502 | 0.167 | 9.309 | 9.482 | 13.13 | 13.37 |
| hfa_only | 2343 | 12.645 | 0.662 | 0.235 | 12.703 | 9.882 | 17.78 | 13.89 |
| ridge | 2343 | 10.462 | 0.499 | 0.167 | 9.351 | 9.474 | 13.25 | 13.38 |

Interval coverage (nominal 50 / 80 / 95%):

| Model | Margin coverage | Margin width | Total coverage | Total width |
|---|---|---|---|---|
| dynamic | 53.4% / 82.1% / 96.1% | 23.1 / 43.6 / 66.0 | 53.9% / 81.5% / 95.3% | 23.0 / 43.4 / 65.8 |
| elo | 52.2% / 80.8% / 95.6% | 23.2 / 43.8 / 66.4 | 53.9% / 82.1% / 95.7% | 24.1 / 45.7 / 69.2 |
| g01 | 46.4% / 76.4% / 92.9% | 19.7 / 38.1 / 60.4 | 51.6% / 80.7% / 94.9% | 22.5 / 43.0 / 66.7 |
| hfa_only | 54.8% / 79.7% / 94.7% | 31.1 / 57.9 / 86.6 | 53.4% / 82.0% / 95.9% | 24.0 / 45.7 / 69.3 |
| ridge | 50.3% / 78.9% / 94.4% | 21.6 / 40.8 / 61.8 | 52.0% / 79.3% / 94.2% | 22.0 / 41.7 / 63.2 |

## By season (energy score)

| Model | 2019 | 2020 | 2021 |
|---|---|---|---|
| dynamic | 10.243 | 10.723 | 10.325 |
| elo | 10.724 | 11.114 | 10.671 |
| g01 | 10.351 | 10.845 | 10.416 |
| hfa_only | 12.820 | 12.644 | 12.470 |
| ridge | 10.301 | 10.715 | 10.462 |

## Paired comparisons

Challenger minus baseline, per game, on identical games; week-block bootstrap unless noted. Negative favors the challenger. 'Better' means the whole 95% interval is below 0 (V01 rule).

| Challenger | Baseline | Metric | Blocks | Games | Mean diff | 95% interval | Better |
|---|---|---|---|---|---|---|---|
| g01 | dynamic | energy_score | week | 2343 | +0.1049 | [+0.0663, +0.1438] | no |
| g01 | dynamic | energy_score | three_week | 2343 | +0.1049 | [+0.0705, +0.1388] | no |
| g01 | dynamic | energy_score | season_half | 2343 | +0.1049 | [+0.0876, +0.1215] | no |
| g01 | dynamic | winner_log_loss | week | 2343 | +0.0055 | [-0.0006, +0.0119] | no |
| g01 | dynamic | margin_crps | week | 2343 | +0.0816 | [+0.0480, +0.1143] | no |
| g01 | dynamic | total_crps | week | 2343 | +0.0103 | [-0.0430, +0.0634] | no |
| g01 | ridge | energy_score | week | 2343 | +0.0331 | [-0.0464, +0.1075] | no |
| g01 | ridge | energy_score | three_week | 2343 | +0.0331 | [-0.0418, +0.1132] | no |
| g01 | ridge | energy_score | season_half | 2343 | +0.0331 | [-0.0507, +0.1199] | no |
| g01 | ridge | winner_log_loss | week | 2343 | +0.0035 | [-0.0027, +0.0105] | no |
| g01 | ridge | margin_crps | week | 2343 | -0.0427 | [-0.1568, +0.0604] | no |
| g01 | ridge | total_crps | week | 2343 | +0.0080 | [-0.0476, +0.0685] | no |
| g01 | hfa_only | energy_score | week | 2343 | -2.1496 | [-2.3735, -1.9312] | yes |
| g01 | hfa_only | energy_score | three_week | 2343 | -2.1496 | [-2.4108, -1.8693] | yes |
| g01 | hfa_only | energy_score | season_half | 2343 | -2.1496 | [-2.3716, -1.9012] | yes |
| g01 | hfa_only | winner_log_loss | week | 2343 | -0.1602 | [-0.1848, -0.1357] | yes |
| g01 | hfa_only | margin_crps | week | 2343 | -3.3941 | [-3.8123, -2.9738] | yes |
| g01 | hfa_only | total_crps | week | 2343 | -0.4005 | [-0.6289, -0.1976] | yes |
| g01 | dynamic | energy_score | week, exclude 2020 | 1775 | +0.0995 | [+0.0546, +0.1438] | no |

## Cohorts (energy score; cohorts under 100 games are descriptive only)

| Cohort | Games | dynamic | elo | g01 | hfa_only | ridge |
|---|---|---|---|---|---|---|
| early_season | 780 | 10.572 | 10.929 | 10.747 | 13.289 | 10.779 |
| fbs_vs_nonfbs | 265 | 10.524 | 10.889 | 10.785 | 14.831 | 10.867 |
| postseason | 104 | 10.370 | 10.854 | 10.404 | 11.174 | 10.266 |
| neutral_site | 153 | 10.310 | 10.953 | 10.334 | 11.502 | 10.270 |
| season_2020 | 568 | 10.723 | 11.114 | 10.845 | 12.644 | 10.715 |
| pbp_unreconciled | 86 | 9.917 | 10.361 | 10.097 | 11.744 | 10.142 |
| missing_team_stats | 0 | n/a | n/a | n/a | n/a | n/a |
| no_line | 8 | 12.113 | 12.944 | 12.255 | 17.938 | 12.084 |

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
| g01 | `g01|disp_r=10|pace_k=50` | 10.4955 |
| g01 | `g01|disp_r=20|pace_k=15` | 10.5541 |
| g01 | `g01|disp_r=10|pace_k=15` | 10.5554 |
| g01 | `g01|disp_r=20|pace_k=50` | 10.6054 |
| g01 | `g01|disp_r=5|pace_k=50` | 10.6152 |
| g01 | `g01|disp_r=50|pace_k=15` | 10.6318 |
| g01 | `g01|disp_r=5|pace_k=15` | 10.7680 |
| g01 | `g01|disp_r=50|pace_k=50` | 10.8107 |
| g01 | `g01|disp_r=50|pace_k=5` | 10.8373 |
| g01 | `g01|disp_r=20|pace_k=5` | 10.8645 |
| g01 | `g01|disp_r=10|pace_k=5` | 10.9744 |
| g01 | `g01|disp_r=5|pace_k=5` | 11.2863 |
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

Overtime kernel fell back to all earlier regimes (fewer than 30 same-regime overtime games) in seasons: [2019, 2021].
