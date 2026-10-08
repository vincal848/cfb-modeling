# M02: results (2022 select, 2023 validate)

Protocol: [M02](../protocols/M02-protocol.md), sha256 `79275ed623b496de6e17d7ca64a8e3f0c9b130c29b3c7b33a4ed12fc8293f2fd`. Run 2026-10-07. Raw output: `m02-validation.json`.
1806 games; 1667 with an open and close from the same books (2022: 818, 2023: 849; Bovada among them: 818 / 828). **Evaluation class: reconstructed.**

**Verdict: the opener rule did not pass 2023. B02 does not beat the opener after costs.**

Per trade is dollars per $1 contract at the opener after the 1c half-spread and the fee. Interval is a week-block bootstrap, 95%. CLV is in points.

| Run | g | Season | Trades | Per trade | Interval | CLV | Close moved our way | Slope [interval] |
|---|---|---|---|---|---|---|---|---|
| Real | 3 | 2022 | 359 | -0.0428 | [-0.0974, +0.0163] | -0.12 | 42.9% | -0.021 [-0.039, +0.005] |
| Real | 3 | 2023 | 399 | +0.0139 | [-0.0244, +0.0632] | +0.49 | 47.9% | +0.090 [+0.018, +0.206] |
| Null | 2 | 2022 | 730 | +0.0232 | [-0.0223, +0.0720] | -0.06 | 40.8% | -0.003 [-0.010, +0.005] |
| Null | 2 | 2023 | 763 | -0.0386 | [-0.0831, +0.0007] | -0.04 | 44.2% | -0.001 [-0.011, +0.007] |

Null check (B02 margin shuffled within week): did not pass, as required.
