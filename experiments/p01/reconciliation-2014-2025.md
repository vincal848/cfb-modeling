# P01 play-by-play scoring reconciliation

Every population game's CFBD plays are walked in game order under the season's rules from `config/rules_registry.json`. **exact**: every score change is explained and the walk ends at the official final. **events**: the classified scoring events sum to the official final (undescribed tries 0-2 points; failed tries may have been returned for 2), but some per-play changes are unexplained. **failed**: neither. Only exact games are fit for transition-level models (P02).

| Season | Games | Exact | Events | Failed | Exact share | Swapped columns | OT games |
|---|---|---|---|---|---|---|---|
| 2014 | 868 | 747 | 37 | 84 | 86.1% | 0 | 33 |
| 2015 | 870 | 732 | 51 | 87 | 84.1% | 0 | 35 |
| 2016 | 873 | 730 | 45 | 98 | 83.6% | 0 | 40 |
| 2017 | 874 | 746 | 49 | 79 | 85.4% | 0 | 34 |
| 2018 | 884 | 724 | 50 | 110 | 81.9% | 0 | 32 |
| 2019 | 888 | 755 | 57 | 76 | 85.0% | 0 | 29 |
| 2020 | 568 | 465 | 30 | 73 | 81.9% | 3 | 21 |
| 2021 | 887 | 588 | 191 | 108 | 66.3% | 1 | 27 |
| 2022 | 896 | 619 | 184 | 93 | 69.1% | 1 | 36 |
| 2023 | 910 | 716 | 145 | 49 | 78.7% | 4 | 30 |
| 2024 | 920 | 654 | 198 | 68 | 71.1% | 2 | 39 |
| 2025 | 934 | 649 | 175 | 110 | 69.5% | 0 | 44 |
| All | 10372 | 8125 | 1212 | 1035 | 78.3% | 11 | 400 |

## Games with each issue

| Issue | Games |
|---|---|
| `score_change_on_non_scoring_play` | 1489 |
| `score_decrease` | 791 |
| `scoring_play_without_score_change` | 686 |
| `touchdown_points_mismatch` | 528 |
| `scoring_flag_without_known_event` | 472 |
| `final_mismatch` | 342 |
| `field_goal_points_mismatch` | 226 |
| `touchdown_try_unexplained` | 211 |
| `no_plays` | 50 |
| `safety_points_mismatch` | 27 |
| `ot_kick_try_in_mandatory_period` | 8 |
| `two_point_play_points_mismatch` | 3 |
| `ot_shootout_violation` | 2 |

## Provider conventions handled (games affected)

- Touchdowns found from text under non-touchdown play types: 1005
- Stale rows skipped: 932
- Try points recorded on the next play: 7
- Try results inferred from the score change: 955
- Score columns swapped for the whole game: 11
