# R01 roster projection: development results

Seasons [2019, 2020, 2021], reconstructed. Target: each team's offensive EPA per play (P01 exact-tier games). Predictors are past-only and linearly calibrated on 2017 through the season before. 'roster' is the preseason roster-scenario strength (P03 shares x P04 abilities); 'naive' is last season's team EPA per play, which ignores roster turnover.

| Season | Teams | MSE naive | MSE roster | MSE both | Corr naive | Corr roster |
|---|---|---|---|---|---|---|
| 2019 | 130 | 0.00787 | 0.00812 | 0.00754 | 0.461 | 0.487 |
| 2020 | 116 | 0.01050 | 0.01215 | 0.01052 | 0.450 | 0.271 |
| 2021 | 114 | 0.00776 | 0.01039 | 0.00789 | 0.560 | 0.281 |
| All | 360 | 0.00868 | 0.01014 | 0.00861 | 0.488 | 0.339 |

Paired squared-error differences (bootstrap over teams, 95% interval):

- both minus naive: -0.000073 [-0.000408, +0.000290]
- roster minus naive: +0.001452 [+0.000411, +0.002615]

Calibration coefficients fit on earlier seasons (intercept, slopes):

- 2019: naive [-0.0041, 0.4187], roster [0.0053, 0.7955], both [0.0004, 0.3467, 0.3158]
- 2020: naive [-0.0019, 0.4357], roster [0.0122, 0.942], both [0.0058, 0.3302, 0.4567]
- 2021: naive [-0.0032, 0.4627], roster [0.0123, 0.9077], both [0.0043, 0.3751, 0.3905]
