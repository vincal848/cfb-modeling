# P04 skill-player effectiveness: development results

Seasons [2019, 2020, 2021], reconstructed. Each season's player EPA per opportunity is predicted from earlier seasons only, with EPA from the EP model fit before that season. Scores are per player-season, weighted by opportunities; lower is better. Only P01 exact-tier games contribute EPA.

## Fitted parameters by fold and position group

Each position group with at least 100 training player-seasons, 1,000 opportunities and a median of 5 opportunities per player-season gets its own development model; other groups (one-off trick plays, rare roles) are predicted by their training mean.

| Season | Category | Group | Training player-seasons | Persistence rho | Prior sd tau | Season innovation sd | Play sd sigma | Converged |
|---|---|---|---|---|---|---|---|---|
| 2019 | passing | OTHER | 147 | mean only | | | | |
| 2019 | passing | QB | 1,734 | 0.818 | 0.1389 | 0.1010 | 1.760 | True |
| 2019 | passing | RB | 265 | mean only | | | | |
| 2019 | passing | TE | 181 | mean only | | | | |
| 2019 | passing | WR | 982 | mean only | | | | |
| 2019 | receiving | OTHER | 669 | mean only | | | | |
| 2019 | receiving | QB | 580 | mean only | | | | |
| 2019 | receiving | RB | 2,485 | mean only | | | | |
| 2019 | receiving | TE | 1,463 | 0.000 | 0.1219 | 0.0310 | 1.605 | True |
| 2019 | receiving | WR | 5,165 | 0.598 | 0.1340 | 0.1059 | 1.605 | True |
| 2019 | rushing | OTHER | 644 | mean only | | | | |
| 2019 | rushing | QB | 1,638 | 0.679 | 0.1828 | 0.1551 | 1.242 | True |
| 2019 | rushing | RB | 3,428 | 0.678 | 0.0960 | 0.0648 | 1.242 | True |
| 2019 | rushing | TE | 136 | mean only | | | | |
| 2019 | rushing | WR | 1,676 | mean only | | | | |
| 2020 | passing | OTHER | 180 | mean only | | | | |
| 2020 | passing | QB | 2,218 | 0.795 | 0.1388 | 0.1056 | 1.761 | True |
| 2020 | passing | RB | 311 | mean only | | | | |
| 2020 | passing | TE | 227 | mean only | | | | |
| 2020 | passing | WR | 1,183 | mean only | | | | |
| 2020 | receiving | OTHER | 804 | mean only | | | | |
| 2020 | receiving | QB | 718 | mean only | | | | |
| 2020 | receiving | RB | 3,152 | mean only | | | | |
| 2020 | receiving | TE | 1,884 | 0.000 | 0.1265 | 0.0047 | 1.605 | True |
| 2020 | receiving | WR | 6,504 | 0.624 | 0.1357 | 0.1106 | 1.605 | True |
| 2020 | rushing | OTHER | 783 | mean only | | | | |
| 2020 | rushing | QB | 2,089 | 0.668 | 0.1783 | 0.1552 | 1.241 | True |
| 2020 | rushing | RB | 4,334 | 0.769 | 0.0936 | 0.0489 | 1.241 | True |
| 2020 | rushing | TE | 176 | mean only | | | | |
| 2020 | rushing | WR | 2,105 | mean only | | | | |
| 2021 | passing | OTHER | 206 | mean only | | | | |
| 2021 | passing | QB | 2,539 | 0.825 | 0.1402 | 0.1059 | 1.752 | True |
| 2021 | passing | RB | 336 | mean only | | | | |
| 2021 | passing | TE | 265 | mean only | | | | |
| 2021 | passing | WR | 1,309 | mean only | | | | |
| 2021 | receiving | OTHER | 906 | mean only | | | | |
| 2021 | receiving | QB | 795 | mean only | | | | |
| 2021 | receiving | RB | 3,625 | 1.000 | 0.1049 | 0.0005 | 1.601 | True |
| 2021 | receiving | TE | 2,225 | 0.068 | 0.1248 | 0.0846 | 1.601 | True |
| 2021 | receiving | WR | 7,422 | 0.619 | 0.1367 | 0.1144 | 1.601 | True |
| 2021 | rushing | OTHER | 895 | mean only | | | | |
| 2021 | rushing | QB | 2,397 | 0.667 | 0.1770 | 0.1640 | 1.239 | True |
| 2021 | rushing | RB | 4,949 | 0.784 | 0.0919 | 0.0551 | 1.239 | True |
| 2021 | rushing | TE | 206 | mean only | | | | |
| 2021 | rushing | WR | 2,408 | mean only | | | | |

## Held-forward scores

| Category | Player-seasons | Opportunities | Log score: model | group mean | last season raw | MSE: model | group mean | last season raw | 80% coverage |
|---|---|---|---|---|---|---|---|---|---|
| passing | 2,058 | 117,861 | -0.1142 | -0.1153 | 0.5052 | 0.12843 | 0.12927 | 0.22888 | 77.0% |
| receiving | 6,896 | 91,649 | 0.4246 | 0.4275 | 1.0138 | 0.22769 | 0.22826 | 0.51999 | 78.3% |
| rushing | 4,936 | 121,617 | -0.1842 | -0.1699 | 0.4051 | 0.09404 | 0.09504 | 0.19582 | 81.1% |

## By position group (MSE weighted by opportunities)

| Category | Group | Player-seasons | Opportunities | MSE: model | group mean | last season raw |
|---|---|---|---|---|---|---|
| passing | OTHER | 92 | 563 | 1.36922 | 1.36922 | 1.28250 |
| passing | QB | 1,198 | 114,247 | 0.05406 | 0.05492 | 0.14993 |
| passing | RB | 114 | 281 | 2.73257 | 2.73257 | 3.30745 |
| passing | TE | 136 | 423 | 2.50582 | 2.50582 | 2.38326 |
| passing | WR | 518 | 2,347 | 2.71090 | 2.71090 | 3.06249 |
| receiving | OTHER | 345 | 1,222 | 0.81085 | 0.81085 | 1.09770 |
| receiving | QB | 334 | 873 | 2.40542 | 2.40542 | 3.54126 |
| receiving | RB | 1,688 | 13,756 | 0.27950 | 0.27972 | 0.57399 |
| receiving | TE | 1,155 | 12,238 | 0.24634 | 0.24645 | 0.61196 |
| receiving | WR | 3,374 | 63,560 | 0.17176 | 0.17252 | 0.43799 |
| rushing | OTHER | 362 | 1,449 | 1.32219 | 1.32219 | 1.60310 |
| rushing | QB | 1,122 | 23,670 | 0.11808 | 0.11884 | 0.30954 |
| rushing | RB | 2,273 | 90,381 | 0.04332 | 0.04446 | 0.09887 |
| rushing | TE | 115 | 627 | 0.65432 | 0.65432 | 1.08895 |
| rushing | WR | 1,064 | 5,490 | 0.43719 | 0.43719 | 0.82809 |

## New versus returning players (model)

| Category | Group | Player-seasons | Mean predictive sd | 80% coverage |
|---|---|---|---|---|
| passing | new | 1,289 | 0.9978 | 77.9% |
| passing | returning | 769 | 0.1435 | 76.8% |
| receiving | new | 3,713 | 0.2225 | 81.1% |
| receiving | returning | 3,183 | 0.1110 | 77.2% |
| rushing | new | 2,800 | 0.2608 | 84.6% |
| rushing | returning | 2,136 | 0.1201 | 80.0% |
