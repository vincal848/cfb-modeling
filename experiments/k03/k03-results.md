# K03 results

**Verdict: NO EDGE: validation interval lower bound is not > 0**

Protocol sha256 `4c61262a5ac5fe7d7fbdfcfc8cd98fde1e342d407cf33f679fe491d780a9f0f1`; generated 2026-10-08T01:26:32+00:00; Kalshi calls 0.
Events per series: {'KXNFLGAME': 330, 'KXNBAGAME': 1446, 'KXMLBGAME': 3942, 'KXNHLGAME': 1537, 'KXNCAAMBGAME': 5269, 'KXWNBAGAME': 544, 'KXNCAAFGAME': 936}. Dropped: {'not_two_markets': 0, 'not_one_yes_one_no': 36}. MLB start-time agreement: 0.9988452655889145.

## Selected rule (select split): {'hours': 6, 'c': 0.95}

| split | trades | per trade | 95% interval | hit rate |
|---|---|---|---|---|
| select | 708 | +0.0024 | [-0.0046, +0.0117] | 0.980 |
| validate | 148 | +0.0133 | [-0.0072, +0.0332] | 0.980 |

Validation by league (descriptive):

| series | trades | per trade | 95% interval |
|---|---|---|---|
| KXMLBGAME | 1 | +0.0186 | [+0.0186, +0.0186] |
| KXNBAGAME | 13 | +0.0380 | [+0.0318, +0.0430] |
| KXNCAAFGAME | 0 | +nan | [+nan, +nan] |
| KXNCAAMBGAME | 133 | +0.0109 | [-0.0112, +0.0325] |
| KXNFLGAME | 0 | +nan | [+nan, +nan] |
| KXNHLGAME | 0 | +nan | [+nan, +nan] |
| KXWNBAGAME | 1 | +0.0186 | [+0.0186, +0.0186] |

## Select-split grid

| rule | trades | per trade | 95% interval |
|---|---|---|---|
| h24_c0.85 | 1357 | -0.0321 | [-0.0504, -0.0137] |
| h24_c0.9 | 1037 | -0.0244 | [-0.0455, -0.0023] |
| h24_c0.95 | 662 | -0.0160 | [-0.0414, +0.0083] |
| h6_c0.85 | 1309 | -0.0056 | [-0.0205, +0.0078] |
| h6_c0.9 | 1022 | -0.0021 | [-0.0134, +0.0099] |
| h6_c0.95 | 708 | +0.0024 | [-0.0046, +0.0117] |

## Null (outcomes shuffled within week)

Selected {'hours': 24, 'c': 0.85}, validate {'trades': 1048, 'per_trade': -0.41523492366412207, 'lo': -0.44014199526391035, 'hi': -0.38963022185946483, 'hit_rate': 0.49427480916030536}, passed=False.

## Calibration, 24h before start (all events, YES side)

| bucket | n | mean mid | win rate |
|---|---|---|---|
| (-0.001, 0.05] | 238 | 0.031 | 0.008 |
| (0.05, 0.1] | 286 | 0.076 | 0.042 |
| (0.1, 0.2] | 666 | 0.154 | 0.132 |
| (0.2, 0.3] | 877 | 0.256 | 0.269 |
| (0.3, 0.4] | 1423 | 0.357 | 0.367 |
| (0.4, 0.5] | 2308 | 0.454 | 0.495 |
| (0.5, 0.6] | 2267 | 0.548 | 0.542 |
| (0.6, 0.7] | 1280 | 0.647 | 0.627 |
| (0.7, 0.8] | 848 | 0.751 | 0.750 |
| (0.8, 0.9] | 653 | 0.851 | 0.858 |
| (0.9, 0.95] | 247 | 0.926 | 0.943 |
| (0.95, 1.0] | 218 | 0.970 | 0.991 |

## Calibration, 6h before start (all events, YES side)

| bucket | n | mean mid | win rate |
|---|---|---|---|
| (-0.001, 0.05] | 369 | 0.028 | 0.008 |
| (0.05, 0.1] | 291 | 0.076 | 0.041 |
| (0.1, 0.2] | 674 | 0.153 | 0.159 |
| (0.2, 0.3] | 968 | 0.256 | 0.265 |
| (0.3, 0.4] | 1657 | 0.356 | 0.373 |
| (0.4, 0.5] | 2834 | 0.453 | 0.483 |
| (0.5, 0.6] | 2841 | 0.549 | 0.540 |
| (0.6, 0.7] | 1478 | 0.646 | 0.618 |
| (0.7, 0.8] | 903 | 0.748 | 0.748 |
| (0.8, 0.9] | 689 | 0.849 | 0.839 |
| (0.9, 0.95] | 322 | 0.925 | 0.938 |
| (0.95, 1.0] | 322 | 0.973 | 0.978 |
