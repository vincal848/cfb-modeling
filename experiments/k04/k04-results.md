# K04 results

**Verdict: NO TRADES: the rule never fired (model value never exceeded cost + fees + 1c); the protocol reads fewer than 200 trades as underpowered, but see the diagnostics**

Protocol sha256 `00d7f9915b865ff573e1c3744acc53d53216f071b144efa8d8abfb74e1efa8a4`; generated 2026-10-08T05:39:06+00:00; Kalshi calls 0.

## Model gate (CFBD only)

11069 training games, 2014-2024. Held-out (2023-24) key-number log loss by bandwidth: {0.5: 0.18073196468607045, 1.0: 0.17896949564941259, 2.0: 0.17792896915387807, 3.0: 0.17777024522092794}; chosen h=3.0. Gaussian benchmark 0.19281. Gate passed: True.

Data: {'spread_events': 766, 'unmapped': 13, 'mapped': 753, 'no_result_or_spread': 0, 'no_rungs': 260, 'ladder_rows': 1559}

Diagnostics (descriptive, not a test): {'rows_with_quotes': 1508, 'mean_model_q': 0.05709841705537778, 'mean_mid_implied': 0.05300066312997348, 'mean_cost_ask_minus_bid': 0.10882625994694961, 'mean_fees': 0.028578978779840853, 'realized_hit_rate': 0.059018567639257294, 'best_net_edge': -0.008551746718467146}

## 2025 test

no trades

Underpowered (< 200 trades): True; per-trade sd None.

Placebo (cells 4, -4, 8, -8): no trades; passed=False.

| key | trades | per trade | hit rate |
|---|---|---|---|

## Reading

Over 1508 quoted key-number ladders the mid-implied exact-margin probability (0.053) is already close to the model (0.057) and to the realized rate (0.059). Buying the range costs the two-leg spread plus fees: 0.084 above the mid, 21 times the model-minus-mid gap. The best row had a net edge of -0.0086. The 2026 holdout stays unopened (the 2025 test did not pass).
