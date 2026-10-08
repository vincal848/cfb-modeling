# K02 results

**Verdict: NO EDGE: h=24, d=0.02 did not validate (lower bound not above 0).**

Protocol sha256 `e481b2b7ee7e9eb8e443d47cedeba6495bc8b16fafba45c5a1d93e54bbe5c497`; generated 2026-10-07T23:23:55+00:00; Kalshi network calls: 0.

## Data

| Count | n |
|---|---|
| events | 936 |
| mapped | 916 |
| ambiguous_side | 0 |
| no_book | 66 |
| no_result | 0 |
| no_candles | 0 |
| games_with_quote_h24 | 849 |
| games_with_quote_h1 | 850 |

Match rate (events mapped to a CFBD game): 97.9%.

## Information test

| h | games | coef logit(Kalshi) | coef logit(book) | log loss Kalshi | log loss book | Brier Kalshi | Brier book |
|---|---|---|---|---|---|---|---|
| h24 | 849 | 0.602 [-0.537, 1.741] | 0.473 [-0.732, 1.678] | 0.5072 | 0.5085 | 0.1703 | 0.1705 |
| h1 | 850 | 1.923 [0.318, 3.528] | -0.944 [-2.653, 0.764] | 0.5040 | 0.5080 | 0.1691 | 0.1703 |

## Bid-ask spread at entry

| h | n | mean | p10 | p25 | median | p75 | p90 |
|---|---|---|---|---|---|---|---|
| h24 | 849 | 0.015 | 0.010 | 0.010 | 0.010 | 0.020 | 0.020 |
| h1 | 850 | 0.012 | 0.010 | 0.010 | 0.010 | 0.010 | 0.020 |

## Real: selection (weeks 1-7) and validation (week 8 on)

Selected h=24, d=0.02 (floor 100 trades).

- Fit: 176 trades, +0.0138 per trade [-0.0266, +0.0584], hit 36.4%
- Validation: 175 trades, -0.0007 per trade [-0.0432, +0.0436], hit 38.9%
- Passed: False

| rule | fit result |
|---|---|
| h24_d0.02 | 176 trades, +0.0138 per trade [-0.0266, +0.0584], hit 36.4% |
| h24_d0.04 | 42 trades, +0.0053 per trade [-0.0429, +0.0512], hit 52.4% |
| h24_d0.06 | 13 trades, +0.0841 per trade [-0.0882, +0.3836], hit 76.9% |
| h1_d0.02 | 120 trades, -0.0154 per trade [-0.0408, +0.0147], hit 22.5% |
| h1_d0.04 | 21 trades, +0.0445 per trade [-0.0161, +0.3786], hit 42.9% |
| h1_d0.06 | 3 trades, +0.0600 per trade [+0.0600, +0.0600], hit 66.7% |

## Null (book permuted within week): selection (weeks 1-7) and validation (week 8 on)

Selected h=24, d=0.04 (floor 100 trades).

- Fit: 341 trades, +0.0062 per trade [-0.0261, +0.0408], hit 35.8%
- Validation: 404 trades, +0.0084 per trade [-0.0179, +0.0339], hit 37.1%
- Passed: False

| rule | fit result |
|---|---|
| h24_d0.02 | 374 trades, +0.0053 per trade [-0.0216, +0.0313], hit 37.4% |
| h24_d0.04 | 341 trades, +0.0062 per trade [-0.0261, +0.0408], hit 35.8% |
| h24_d0.06 | 311 trades, +0.0048 per trade [-0.0291, +0.0367], hit 33.8% |
| h1_d0.02 | 368 trades, -0.0216 per trade [-0.0739, +0.0177], hit 34.8% |
| h1_d0.04 | 340 trades, -0.0222 per trade [-0.0731, +0.0135], hit 33.5% |
| h1_d0.06 | 328 trades, -0.0218 per trade [-0.0704, +0.0157], hit 32.3% |

## Look-ahead check

Same rule with the later Kalshi mid as the reference: 119 trades, +0.0398 per trade [-0.0386, +0.1195], hit 56.3%.
Slope of the Kalshi move on (book - entry mid): 0.49871878195550895.
