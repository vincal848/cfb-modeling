# P03 opportunity shares: development results

Seasons [2019, 2020, 2021], reconstructed. Each team-game-category share forecast uses only earlier games of the season, the previous season and the season's roster. Log score is per opportunity (lower is better); new players and unassigned opportunities count against the UNKNOWN group. The configuration was selected on these games, so its scores are optimistic.

Selected: `shares|half_life=2|prior_w=0.5|alpha=0.1|kappa=3`

| Model | Category | Team-games | Opportunities | Log score | Participation log loss | Max conservation error |
|---|---|---|---|---|---|---|
| last game | carries | 4,676 | 163,773 | 2.0139 | 0.7313 | 1.42e-14 |
| last game | dropbacks | 4,675 | 155,128 | 0.8948 | 1.0147 | 1.42e-14 |
| last game | targets | 4,675 | 144,967 | 2.5185 | 0.6794 | 1.42e-14 |
| shares | carries | 4,676 | 163,773 | 1.7734 | 0.7392 | 4.26e-14 |
| shares | dropbacks | 4,675 | 155,128 | 0.7243 | 1.3373 | 3.55e-14 |
| shares | targets | 4,675 | 144,967 | 2.1957 | 0.5945 | 4.26e-14 |

By season (log score, all categories):

| Season | Shares | Last game |
|---|---|---|
| 2019 | 1.5465 | 1.7696 |
| 2020 | 1.6023 | 1.8079 |
| 2021 | 1.5311 | 1.8186 |

## Participation: P(at least one opportunity), log loss over known players

Separate participation model selected: half-life 4 games, prior strength 1. 'From shares' is 1 - (1 - share)^N, which assumes independent opportunities.

| Category | Last-game indicator | From shares | Participation model |
|---|---|---|---|
| carries | 0.7171 | 0.7392 | 0.4532 |
| dropbacks | 0.6029 | 1.3373 | 0.3920 |
| targets | 0.8402 | 0.5945 | 0.5009 |

## Grid (pooled log score)

| Configuration | Log score | Participation log loss |
|---|---|---|
| `shares|half_life=2|prior_w=0.5|alpha=0.1|kappa=3` | 1.5545 | 0.7615 |
| `shares|half_life=2|prior_w=0.25|alpha=0.1|kappa=3` | 1.5548 | 0.7335 |
| `shares|half_life=2|prior_w=0.5|alpha=0.03|kappa=3` | 1.5575 | 0.7581 |
| `shares|half_life=1|prior_w=0.25|alpha=0.1|kappa=3` | 1.5575 | 0.7132 |
| `shares|half_life=2|prior_w=0.5|alpha=0.1|kappa=6` | 1.5578 | 0.7373 |
| `shares|half_life=1|prior_w=0.5|alpha=0.1|kappa=3` | 1.5589 | 0.7508 |
| `shares|half_life=2|prior_w=0.5|alpha=0.01|kappa=3` | 1.5591 | 0.7581 |
| `shares|half_life=2|prior_w=0.25|alpha=0.03|kappa=3` | 1.5605 | 0.7299 |
| `shares|half_life=2|prior_w=0.5|alpha=0.03|kappa=6` | 1.5619 | 0.7348 |
| `shares|half_life=2|prior_w=0.25|alpha=0.01|kappa=3` | 1.5637 | 0.7308 |
| `shares|half_life=1|prior_w=0.5|alpha=0.03|kappa=3` | 1.5638 | 0.7480 |
| `shares|half_life=2|prior_w=0.5|alpha=0.01|kappa=6` | 1.5638 | 0.7351 |
| `shares|half_life=1|prior_w=0.25|alpha=0.03|kappa=3` | 1.5652 | 0.7100 |
| `shares|half_life=1|prior_w=0.5|alpha=0.1|kappa=6` | 1.5661 | 0.7232 |
| `shares|half_life=1|prior_w=0.5|alpha=0.01|kappa=3` | 1.5666 | 0.7491 |
| `shares|half_life=2|prior_w=0.25|alpha=0.1|kappa=6` | 1.5694 | 0.7076 |
| `shares|half_life=1|prior_w=0.25|alpha=0.01|kappa=3` | 1.5697 | 0.7121 |
| `shares|half_life=1|prior_w=0.5|alpha=0.03|kappa=6` | 1.5722 | 0.7214 |
| `shares|half_life=2|prior_w=0.1|alpha=0.1|kappa=3` | 1.5736 | 0.7128 |
| `shares|half_life=1|prior_w=0.5|alpha=0.01|kappa=6` | 1.5754 | 0.7229 |
| `shares|half_life=1|prior_w=0.1|alpha=0.1|kappa=3` | 1.5767 | 0.6864 |
| `shares|half_life=1|prior_w=0.25|alpha=0.1|kappa=6` | 1.5770 | 0.6842 |
| `shares|half_life=2|prior_w=0.25|alpha=0.03|kappa=6` | 1.5771 | 0.7060 |
| `shares|half_life=2|prior_w=0.25|alpha=0.01|kappa=6` | 1.5809 | 0.7076 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.1|kappa=3` | 1.5829 | 0.7081 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.1|kappa=3` | 1.5845 | 0.7569 |
| `shares|half_life=2|prior_w=0.1|alpha=0.03|kappa=3` | 1.5856 | 0.7096 |
| `shares|half_life=1|prior_w=0.25|alpha=0.03|kappa=6` | 1.5868 | 0.6832 |
| `shares|half_life=2|prior_w=0.5|alpha=0.1|kappa=12` | 1.5890 | 0.7020 |
| `shares|half_life=1|prior_w=0.1|alpha=0.03|kappa=3` | 1.5910 | 0.6836 |
| `shares|half_life=1|prior_w=0.25|alpha=0.01|kappa=6` | 1.5920 | 0.6860 |
| `shares|half_life=2|prior_w=0.1|alpha=0.01|kappa=3` | 1.5928 | 0.7128 |
| `shares|half_life=2|prior_w=0.5|alpha=0.03|kappa=12` | 1.5944 | 0.7008 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.03|kappa=3` | 1.5950 | 0.7578 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.1|kappa=6` | 1.5967 | 0.7252 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.03|kappa=3` | 1.5967 | 0.7084 |
| `shares|half_life=2|prior_w=0.5|alpha=0.01|kappa=12` | 1.5968 | 0.7016 |
| `shares|half_life=1|prior_w=0.1|alpha=0.01|kappa=3` | 1.5996 | 0.6881 |
| `shares|half_life=2|prior_w=0.1|alpha=0.1|kappa=6` | 1.6017 | 0.6874 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.01|kappa=3` | 1.6022 | 0.7632 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.1|kappa=3` | 1.6054 | 0.6741 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.01|kappa=3` | 1.6058 | 0.7149 |
| `shares|half_life=1|prior_w=0.5|alpha=0.1|kappa=12` | 1.6072 | 0.6826 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.03|kappa=6` | 1.6087 | 0.7275 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.1|kappa=6` | 1.6091 | 0.6756 |
| `shares|half_life=1|prior_w=0.1|alpha=0.1|kappa=6` | 1.6103 | 0.6582 |
| `shares|half_life=2|prior_w=0.25|alpha=0.1|kappa=12` | 1.6142 | 0.6737 |
| `shares|half_life=1|prior_w=0.5|alpha=0.03|kappa=12` | 1.6149 | 0.6825 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.01|kappa=6` | 1.6163 | 0.7333 |
| `shares|half_life=2|prior_w=0.1|alpha=0.03|kappa=6` | 1.6172 | 0.6887 |
| `shares|half_life=1|prior_w=0.5|alpha=0.01|kappa=12` | 1.6186 | 0.6845 |
| `shares|half_life=2|prior_w=0.25|alpha=0.03|kappa=12` | 1.6239 | 0.6747 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.03|kappa=6` | 1.6254 | 0.6785 |
| `shares|half_life=2|prior_w=0.1|alpha=0.01|kappa=6` | 1.6255 | 0.6935 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.03|kappa=3` | 1.6269 | 0.6752 |
| `shares|half_life=2|prior_w=0.25|alpha=0.01|kappa=12` | 1.6283 | 0.6771 |
| `shares|half_life=1|prior_w=0.1|alpha=0.03|kappa=6` | 1.6284 | 0.6602 |
| `shares|half_life=1|prior_w=0.25|alpha=0.1|kappa=12` | 1.6334 | 0.6456 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.01|kappa=6` | 1.6353 | 0.6858 |
| `shares|half_life=1|prior_w=0.1|alpha=0.01|kappa=6` | 1.6382 | 0.6663 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.01|kappa=3` | 1.6408 | 0.6846 |
| `shares|half_life=1|prior_w=0.25|alpha=0.03|kappa=12` | 1.6456 | 0.6476 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.1|kappa=6` | 1.6471 | 0.6430 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.1|kappa=12` | 1.6501 | 0.6788 |
| `shares|half_life=1|prior_w=0.25|alpha=0.01|kappa=12` | 1.6515 | 0.6513 |
| `shares|half_life=2|prior_w=0.1|alpha=0.1|kappa=12` | 1.6595 | 0.6595 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.03|kappa=12` | 1.6641 | 0.6832 |
| `shares|half_life=0.5|prior_w=0.5|alpha=0.01|kappa=12` | 1.6723 | 0.6897 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.03|kappa=6` | 1.6728 | 0.6494 |
| `shares|half_life=2|prior_w=0.1|alpha=0.03|kappa=12` | 1.6780 | 0.6655 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.1|kappa=12` | 1.6805 | 0.6325 |
| `shares|half_life=1|prior_w=0.1|alpha=0.1|kappa=12` | 1.6810 | 0.6260 |
| `shares|half_life=2|prior_w=0.1|alpha=0.01|kappa=12` | 1.6873 | 0.6720 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.01|kappa=6` | 1.6879 | 0.6607 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.03|kappa=12` | 1.6997 | 0.6390 |
| `shares|half_life=1|prior_w=0.1|alpha=0.03|kappa=12` | 1.7025 | 0.6333 |
| `shares|half_life=0.5|prior_w=0.25|alpha=0.01|kappa=12` | 1.7104 | 0.6475 |
| `shares|half_life=1|prior_w=0.1|alpha=0.01|kappa=12` | 1.7133 | 0.6412 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.1|kappa=12` | 1.7348 | 0.6077 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.03|kappa=12` | 1.7645 | 0.6203 |
| `shares|half_life=0.5|prior_w=0.1|alpha=0.01|kappa=12` | 1.7808 | 0.6336 |
| `last_game` | 1.7973 | 0.7500 |
