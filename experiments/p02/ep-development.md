# P02 expected points: development results

Reconstructed evaluation on development seasons [2019, 2020, 2021]. Each season's EP model is fit only on earlier seasons (2014 onward), with its penalty chosen on the season before it. States are P01 exact-tier regulation scrimmage plays. Next-score log loss is per play; lower is better.

## Folds

| Season | Train plays | Penalty (full / yardline) | Learned try value | Converged |
|---|---|---|---|---|
| 2019 | 565,779 | 1e-06 / 1e-06 | 0.959 | True |
| 2020 | 678,900 | 1e-06 / 1e-06 | 0.960 | True |
| 2021 | 748,796 | 1e-06 / 1e-06 | 0.960 | True |

## Held-out next-score log loss

| Season | Plays | Class prior | Yard line only | Full |
|---|---|---|---|---|
| 2019 | 113,121 | 1.4767 | 1.4047 | 1.1976 |
| 2020 | 69,896 | 1.4620 | 1.3971 | 1.2083 |
| 2021 | 86,406 | 1.4886 | 1.4166 | 1.2184 |
| All | 269,423 | 1.4767 | 1.4066 | 1.2071 |

Paired differences (per play, week-block bootstrap, 95% interval):

- Full minus yard line only: -0.1995 [-0.2055, -0.1931]
- Full minus class prior: -0.2696 [-0.2769, -0.2622]

## Calibration: EP versus realized next-score points (deciles of EP)

| Decile | Plays | Mean EP | Mean realized | Difference |
|---|---|---|---|---|
| 1 | 26,943 | -1.885 | -1.771 | +0.114 |
| 2 | 26,942 | -0.335 | -0.300 | +0.035 |
| 3 | 26,942 | +0.371 | +0.404 | +0.033 |
| 4 | 26,942 | +0.884 | +0.889 | +0.006 |
| 5 | 26,943 | +1.394 | +1.401 | +0.007 |
| 6 | 26,942 | +1.955 | +1.999 | +0.044 |
| 7 | 26,942 | +2.578 | +2.636 | +0.057 |
| 8 | 26,942 | +3.276 | +3.295 | +0.020 |
| 9 | 26,942 | +4.054 | +4.096 | +0.042 |
| 10 | 26,943 | +5.149 | +5.239 | +0.090 |

## Calibration by outcome

| Next score | Mean predicted | Observed |
|---|---|---|
| TD_FOR | 0.4092 | 0.4119 |
| FG_FOR | 0.1686 | 0.1718 |
| SAFETY_FOR | 0.0026 | 0.0026 |
| TD_AGAINST | 0.2035 | 0.2011 |
| FG_AGAINST | 0.0648 | 0.0648 |
| SAFETY_AGAINST | 0.0021 | 0.0020 |
| NONE | 0.1490 | 0.1458 |

## EP at 1st and 10, start of game, tied (by fold)

| Yards to goal | 2019 | 2020 | 2021 |
|---|---|---|---|
| 5 | +5.06 | +5.02 | +5.04 |
| 15 | +4.78 | +4.76 | +4.74 |
| 25 | +4.17 | +4.17 | +4.19 |
| 35 | +3.71 | +3.70 | +3.71 |
| 50 | +2.73 | +2.73 | +2.75 |
| 65 | +1.77 | +1.78 | +1.78 |
| 75 | +1.02 | +1.01 | +1.02 |
| 85 | +0.35 | +0.36 | +0.38 |
| 95 | -0.50 | -0.49 | -0.43 |

## EPA sanity

- Mean EPA over all plays: +0.0044
- Mean EPA, pass plays: +0.0422 (119,211 plays)
- Mean EPA, rush plays: +0.0278 (125,359 plays)
