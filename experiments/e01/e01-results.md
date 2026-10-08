# E01 results

**Verdict: NO EDGE: the efficiency blend adds nothing the opener lacks**

Protocol sha256 `834775ec0758d6bdc4fd09e66800588ed495a392025e6efca39b36fd933fc7c5`; generated 2026-10-08T01:42:18+00:00. Reconstructed replay.
Selected σ_e = 4; blend = +0.05 + 0.916·B02 + 0.067·efficiency.

## Margin error (no market input)

| Seasons | Games | B02 | Efficiency | Blend | Opener | Close |
|---|---|---|---|---|---|---|
| 2019-2021 | 2343 | 13.10 | 13.87 | 13.08 | nan | nan |
| 2022 | 896 | 13.06 | 13.79 | 13.04 | 12.09 | 12.00 |
| 2023 | 910 | 12.73 | 13.43 | 12.71 | 12.36 | 12.18 |

σ_e selection on 2019–2021 (blend MAE): 4: 13.079, 6: 13.092, 8: 13.097, 11: 13.091

## Market tests (95% week-block intervals)

| Run | Season | CLV slope | Encompassing vs opener | Encompassing vs close |
|---|---|---|---|---|
| real | 2022 | -0.021 [-0.041, +0.006] | -0.111 [-0.303, +0.168] | -0.083 [-0.252, +0.168] |
| real | 2023 | +0.096 [+0.021, +0.219] | +0.083 [-0.145, +0.392] | -0.064 [-0.285, +0.234] |
| null | 2022 | -0.011 [-0.021, -0.002] | +0.031 [-0.008, +0.087] | +0.041 [+0.002, +0.088] |
| null | 2023 | +0.001 [-0.009, +0.010] | +0.018 [-0.012, +0.055] | +0.013 [-0.014, +0.049] |

## Trade rule at the opener (M02 harness)

| Run | g | Season | Trades | Per trade | Interval | CLV | Close our way |
|---|---|---|---|---|---|---|---|
| real | 2 | 2022 | 481 | -0.0431 | [-0.0953, +0.0160] | -0.15 | 40.1% |
| real | 2 | 2023 | 527 | -0.0095 | [-0.0493, +0.0335] | +0.31 | 46.5% |
| null | 4 | 2022 | 633 | +0.0049 | [-0.0251, +0.0434] | -0.17 | 39.3% |
| null | 4 | 2023 | 679 | -0.0106 | [-0.0427, +0.0252] | +0.03 | 43.2% |
