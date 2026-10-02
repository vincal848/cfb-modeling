# R02 destination and adaptation: development results

Seasons [2019, 2020, 2021], reconstructed. **Descriptive, not causal**: players choose to move, so these gaps are associations conditional on the P04 forecast, not effects of transferring. Residual = actual season EPA per opportunity minus the P04 forecast from history before that season; gaps are movers minus stayers, weighted by opportunities, with a bootstrap over players. Players without history are excluded (no pre-move forecast).

## Adaptation gap by category and position

| Category | Group | Movers | Stayers | Mover opportunities | Gap (EPA/opportunity) | 95% interval |
|---|---|---|---|---|---|---|
| passing | QB | 100 | 574 | 11,652 | -0.004 | [-0.063, +0.046] |
| receiving | RB | 33 | 269 | 251 | -0.074 | [-0.283, +0.131] |
| receiving | TE | 31 | 604 | 433 | -0.010 | [-0.172, +0.168] |
| receiving | WR | 155 | 1738 | 3,193 | +0.033 | [-0.037, +0.098] |
| rushing | QB | 88 | 551 | 2,115 | +0.025 | [-0.054, +0.108] |
| rushing | RB | 82 | 1182 | 3,926 | +0.012 | [-0.034, +0.055] |

## Support by move direction (player-seasons with opportunities, all categories)

| Direction | Player-season-categories | Opportunities | Mean residual | Support |
|---|---|---|---|---|
| FCS/other -> FCS/other | 5 | 38 | -0.071 | thin: no comparison claimed |
| FCS/other -> G5 | 16 | 1,012 | +0.093 | thin: no comparison claimed |
| FCS/other -> IND | 2 | 33 | -0.030 | thin: no comparison claimed |
| FCS/other -> P5 | 7 | 95 | +0.128 | thin: no comparison claimed |
| G5 -> FCS/other | 40 | 323 | -0.064 | adequate |
| G5 -> G5 | 41 | 1,535 | +0.070 | adequate |
| G5 -> IND | 2 | 71 | +0.061 | thin: no comparison claimed |
| G5 -> P5 | 54 | 2,583 | +0.005 | adequate |
| IND -> FCS/other | 2 | 43 | +0.009 | thin: no comparison claimed |
| IND -> G5 | 8 | 168 | +0.008 | thin: no comparison claimed |
| IND -> P5 | 2 | 234 | +0.149 | thin: no comparison claimed |
| P5 -> FCS/other | 19 | 104 | -0.185 | thin: no comparison claimed |
| P5 -> G5 | 107 | 5,512 | +0.137 | adequate |
| P5 -> IND | 9 | 175 | +0.233 | thin: no comparison claimed |
| P5 -> P5 | 175 | 9,644 | +0.057 | adequate |
| stayed | 4,918 | 215,452 | +0.058 | adequate |

## Censoring: appearance the next season

Of players with opportunities in the previous season, the share with any opportunity this season. 'Not on a roster' covers graduation, the draft, leaving the sport and missing roster coverage; these are distinct exits CFBD does not separate. Non-appearance is never scored as zero ability.

| Season | Group | Appeared | Total | Share |
|---|---|---|---|---|
| 2019 | mover | 121 | 167 | 72.5% |
| 2019 | stayer | 1,822 | 2,168 | 84.0% |
| 2019 | not on a roster | 0 | 1,448 | 0.0% |
| 2020 | mover | 100 | 137 | 73.0% |
| 2020 | stayer | 1,389 | 1,970 | 70.5% |
| 2020 | not on a roster | 0 | 1,683 | 0.0% |
| 2021 | mover | 197 | 237 | 83.1% |
| 2021 | stayer | 1,437 | 1,844 | 77.9% |
| 2021 | not on a roster | 0 | 508 | 0.0% |
