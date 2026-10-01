# D01 endpoint audit (CFBD)

Generated 2026-10-01T18:28:24+00:00. Sample partition: `{"year": 2024, "week": 5, "team": "Michigan"}`. Calls remaining after the run: 124981.

Each endpoint got one sample call. Null rates come from that one partition and do not measure coverage across seasons (that is D02).

| Endpoint | Role | Status | Rows | Cap | Truncation? | Fields | Fields mostly null (>50%) |
|---|---|---|---|---|---|---|---|
| `/info` | ops | 200 | 1 |  | no | 9 | — |
| `/calendar` | core | 200 | 17 |  | no | 7 | — |
| `/teams` | core | 200 | 677 |  | no | 13 | `division`, `twitter` |
| `/teams/fbs` | core | 200 | 134 |  | no | 13 | `division` |
| `/conferences` | core | 200 | 256 |  | no | 6 | — |
| `/venues` | core | 200 | 852 |  | no | 14 | `constructionYear`, `elevation`, `grass`, `timezone` |
| `/games` | core | 200 | 270 |  | no | 34 | `attendance`, `awayPostgameElo`, `awayPostgameWinProbability`, `awayPregameElo`, `excitementIndex`, `homePostgameElo`, `homePostgameWinProbability`, `homePregameElo`, `notes`, `playoff` |
| `/games/teams` | core | 200 | 106 |  | no | 2 | — |
| `/games/players` | core_later | 200 | 106 |  | no | 2 | — |
| `/drives` | core_later | 200 | 2345 |  | no | 25 | — |
| `/plays` | core_later | 200 | 17323 |  | no | 27 | — |
| `/plays/stats` | core_later | 200 | 87 | 2000 | no | 19 | — |
| `/roster` | core_later | 200 | 139 |  | no | 16 | — |
| `/recruiting/players` | core_later | 200 | 4236 |  | no | 17 | — |
| `/coaches` | core_later | 200 | 152 |  | no | 5 | — |
| `/player/portal` | core_later | 200 | 3378 |  | no | 10 | — |
| `/lines` | market | 200 | 104 |  | no | 16 | — |
| `/games/weather` | comparison_only | 200 | 225 |  | no | 22 | — |
| `/player/usage` | comparison_only | 200 | 20 |  | no | 7 | — |
| `/ratings/sp` | comparison_only | 200 | 135 |  | no | 10 | `secondOrderWins`, `sos` |
