# Q01 results

**Verdict: NO EDGE: no maker cell has a Holm-significant positive P&L per fill**

Upper bound: queue position is ignored. Ledger family size 33; protocol sha256 `3043f5cfa4dd76210147b95bea387c9baa48d7a08a84dc6a58715a37af545fe9`. Games with a home market and a kickoff: 916 ({'events': 936, 'mapped': 916, 'ambiguous_side': 0}).

## Real

| cell | fills | P&L per fill | 95% interval | fair-value drift after fill |
|---|---|---|---|---|
| Q1 | 138 | -0.0563 | [-0.1219, +0.0147] | 5m -0.0126; 30m -0.0125; 60m -0.0111 |
| Q2 | 79 | +0.0088 | [-0.0894, +0.1089] | 5m -0.0039; 30m -0.0070; 60m -0.0070 |
| Q3 | 402 | +0.0179 | [-0.0237, +0.0597] | 5m -0.0145; 30m -0.0067; 60m -0.0040 |

## Null (anchors permuted within week; Q3 on neighbouring cells 4, 8)

| cell | fills | P&L per fill | 95% interval | fair-value drift after fill |
|---|---|---|---|---|
| Q1 | 780 | -0.2434 | [-0.2749, -0.2116] | 5m -0.2573; 30m -0.2578; 60m -0.2604 |
| Q2 | 804 | -0.2585 | [-0.2896, -0.2262] | 5m -0.2698; 30m -0.2714; 60m -0.2726 |
| Q3 | 87 | +0.0019 | [-0.1035, +0.1029] | 5m -0.0199; 30m -0.0168; 60m -0.0169 |

Q3 leg pairing: {'ladder_rows': 1151, 'games_with_both_legs': 41, 'games_with_any_fill': 361}
