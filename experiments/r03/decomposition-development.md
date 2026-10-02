# R03 player-informed team decomposition: development results

Forward-residual correction of B02 (`dynamic|q_week=0.25|rho=0.9|s0=8|sigma=11`) margin forecasts by the difference in the two teams' preseason roster offense features (R01). Fit on earlier development seasons, applied to the next (2019 -> 2020, 2019-2020 -> 2021). Reconstructed. Lower is better; differences are corrected minus B02, week-block bootstrap. Games where a team lacks a roster feature get no correction.

| Feature | Test season | Games | Fitted beta | In-sample MSE gain | Margin MSE change | Margin CRPS change |
|---|---|---|---|---|---|---|
| raw | 2020 | 568 | +20.79 | +0.667 | -2.252 | -0.0326 |
| raw | 2021 | 887 | +26.26 | +1.344 | +2.877 | +0.0582 |
| residualized | 2020 | 568 | +85.72 | +1.100 | -1.588 | -0.0131 |
| residualized | 2021 | 887 | +68.55 | +1.377 | +1.480 | +0.0346 |

Pooled over test seasons (95% interval):

- raw: margin CRPS change +0.0228 [-0.0172, +0.0608]
- residualized: margin CRPS change +0.0160 [-0.0321, +0.0619]

Games with a roster feature for both teams: 79.7%.
