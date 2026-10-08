# E02 results

**Verdict: NO EDGE: the efficiency blend adds nothing the opener lacks**

Protocol sha256 `3dea6953c62361e68951487c90ea6fb2797ba49dc5d64c2ed769930cdec9ccde`; generated 2026-10-08T01:51:51+00:00. Reconstructed replay.
Selected σ_e = 2; blend = +0.10 + 0.894·B02 + 0.082·efficiency.

## Margin error (no market input)

| Seasons | Games | B02 | Efficiency | Blend | Opener | Close |
|---|---|---|---|---|---|---|
| 2019-2021 | 2343 | 13.10 | 14.30 | 13.06 | nan | nan |
| 2022 | 896 | 13.06 | 15.21 | 13.06 | 12.09 | 12.00 |
| 2023 | 910 | 12.73 | 14.77 | 12.81 | 12.36 | 12.18 |

σ_e selection on 2019–2021 (blend MAE): 2: 13.059, 3: 13.064, 4: 13.072, 6: 13.087

## Market tests (95% week-block intervals)

| Run | Season | CLV slope | Encompassing vs opener | Encompassing vs close |
|---|---|---|---|---|
| real | 2022 | -0.012 [-0.037, +0.024] | -0.113 [-0.343, +0.247] | -0.093 [-0.290, +0.213] |
| real | 2023 | +0.104 [+0.028, +0.232] | +0.054 [-0.183, +0.367] | -0.102 [-0.328, +0.185] |
| null | 2022 | -0.011 [-0.021, -0.002] | +0.030 [-0.010, +0.085] | +0.039 [-0.000, +0.086] |
| null | 2023 | +0.001 [-0.008, +0.010] | +0.020 [-0.014, +0.057] | +0.015 [-0.017, +0.051] |

## Trade rule at the opener (M02 harness)

| Run | g | Season | Trades | Per trade | Interval | CLV | Close our way |
|---|---|---|---|---|---|---|---|
| real | 1 | 2022 | 615 | -0.0348 | [-0.0773, +0.0112] | -0.08 | 39.8% |
| real | 1 | 2023 | 667 | -0.0282 | [-0.0660, +0.0115] | +0.26 | 46.3% |
| null | 4 | 2022 | 633 | +0.0017 | [-0.0282, +0.0386] | -0.17 | 39.2% |
| null | 4 | 2023 | 682 | -0.0099 | [-0.0427, +0.0261] | +0.06 | 43.7% |

## Development diagnostic (2019–2021 only; no lines, nothing from 2022 on computed)

E01/E02 chose σ_e by the blend's MAE. The blend is about 90% B02, so that criterion barely moves
with σ_e and drifted to the grid's lower edge. Re-scanning σ_e by efficiency-alone MAE:

| σ_e | Exact-tier states | Exact + events states |
|---|---|---|
| 4 | 13.871 | 13.797 |
| 8 | 13.588 | 13.535 |
| 11 | 13.595 | 13.535 |
| 16 | 13.679 | 13.599 |
| 24 | 13.884 | 13.776 |

B02 (final scores only): **13.097**. At every σ_e the efficiency weight in a blend with B02 is
about 0 (−0.20 to +0.09). The per-game EPA itself is sound: the single-game EPA/play margin
correlates 0.92 with the point margin (2019). So the defect is in turning per-play efficiency
into a forward team rating, not in EPA itself.

**Conclusion:** in this form (garbage-filtered EPA/play, opponent-adjusted by the B02 Kalman
filter), play efficiency is not a better model than final scores, so it cannot beat the
opener. No further market look is warranted for this build.
