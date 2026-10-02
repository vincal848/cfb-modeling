# Fixture candidates for the play-by-play state machine

Compiled 2026-10-02. Each candidate below was checked against ESPN's play-by-play for the listed gameId. The data was read from ESPN's public summary endpoint, `https://site.api.espn.com/apis/site/v2/sports/football/college-football/summary?event=<gameId>`. That endpoint returns the same data the ESPN game page shows. Two candidates were also checked against a written game recap (noted below).

Notes:
- Dates are local game dates. ESPN stores kickoff in UTC, so a late kickoff can show the next day.
- Score order is winner first.
- "Q5+" means overtime. ESPN numbers OT periods 5, 6, …, but some older games put every OT play in period 5.
- ESPN's running scores (`awayScore`/`homeScore`) on individual plays are sometimes wrong, especially in overtime. Fixtures should assert on the play text and the final score, not on per-play running scores.

## 1. Interception or fumble return touchdown

| # | Game (date) | Final | Play | Source |
|---|---|---|---|---|
| 1a | Kentucky at Florida (2022-09-10) | Kentucky 26, Florida 16 | Q3 3:25 — Keidron Smith (UK) 65-yard interception return TD (Matt Ruffolo kick) | [ESPN 401403871](https://www.espn.com/college-football/game/_/gameId/401403871) |
| 1b | Wake Forest at Vanderbilt (2022-09-10) | Wake Forest 45, Vanderbilt 25 | Q1 2:11 — Coby Davis (WF) 31-yard interception return TD (Matthew Dennis kick) | [ESPN 401403879](https://www.espn.com/college-football/game/_/gameId/401403879) |
| 1c | Arkansas vs Texas A&M, Arlington (2022-09-24) | Texas A&M 23, Arkansas 21 | Q2 3:11 — Demani Richardson (TAMU) 82-yard fumble return TD; two-point pass failed (also usable for item 4b) | [ESPN 401403893](https://www.espn.com/college-football/game/_/gameId/401403893) |
| 1d | LSU at Texas A&M (2018-11-24) | Texas A&M 74, LSU 72 (7OT) | Q4 10:12 — Michael Divinity Jr. (LSU) 58-yard fumble return TD (Cole Tracy kick) | [ESPN 401012356](https://www.espn.com/college-football/game/_/gameId/401012356) |

## 2. Safety

| # | Game (date) | Final | Play | Source |
|---|---|---|---|---|
| 2a | South Dakota State at Iowa (2022-09-03) | Iowa 7, South Dakota State 3 | Two Iowa safeties: Q3 4:03 (Jack Campbell) and Q4 3:58 (Joe Evans). SDSU is FCS | [ESPN 401405062](https://www.espn.com/college-football/game/_/gameId/401405062) |
| 2b | Central Michigan at Oklahoma State (2022-09-01) | Oklahoma State 58, Central Michigan 44 | Q1 0:55 — safety credited to Lamont Bishop (OSU) | [ESPN 401416569](https://www.espn.com/college-football/game/_/gameId/401416569) |
| 2c | Kentucky at Florida (2022-09-10) | Kentucky 26, Florida 16 | Q2 4:12 — team safety awarded to Florida. ESPN text: "TEAM run for a loss of 39 yards … fumbled, recovered by Kent for a SAFETY" | [ESPN 401403871](https://www.espn.com/college-football/game/_/gameId/401403871) |

## 3. Penalty that wiped out a touchdown

| # | Game (date) | Final | Play | Source |
|---|---|---|---|---|
| 3a | Ohio State at Indiana (2023-09-02) | Ohio State 23, Indiana 3 | Q3 3:25 — McCord 24-yard pass to Marvin Harrison Jr. for a TD "nullified by penalty": OSU illegal touching. NO PLAY | [ESPN 401520156](https://www.espn.com/college-football/game/_/gameId/401520156) |
| 3b | Central Michigan at Penn State (2022-09-24) | Penn State 33, Central Michigan 14 | Q4 9:21 — Richardson 28-yard pass to Joel Wilson to the PSU 0, "TOUCHDOWN CMU, score nullified by penalty": CMU holding, 10 yards from the PSU28 to the PSU38. NO PLAY. (Also Q3 8:53: CMU TD wiped out by offensive pass interference) | [ESPN 401405098](https://www.espn.com/college-football/game/_/gameId/401405098) |
| 3c | Illinois at Penn State (2021-10-23) | Illinois 20, Penn State 18 (9OT) | Q4 13:12 — Chase Brown 14-yard TD run "nullified by penalty", ILL holding. ESPN puts a second wiped-out ILL TD (Sitkowski pass, ILL pass interference) at the same 13:12 time; check the order before using it | [ESPN 401282717](https://www.espn.com/college-football/game/_/gameId/401282717) |

## 4. Failed PAT (missed or blocked) and failed two-point try

| # | Game (date) | Final | Play | Source |
|---|---|---|---|---|
| 4a | Florida State vs LSU, New Orleans (2022-09-04) | Florida State 24, LSU 23 | Q4 0:00 — Daniels 2-yard TD pass to Jaray Jenkins as time expired; Damian Ramos PAT **blocked**, so the game ends (try after a TD at 0:00) | [ESPN 401403867](https://www.espn.com/college-football/game/_/gameId/401403867) |
| 4b | NC State at East Carolina (2022-09-03) | NC State 21, East Carolina 20 | Q4 2:58 — Rahjai Harris 3-yard TD run; Owen Daffer PAT **missed** ("PAT MISSED") | [ESPN 401411096](https://www.espn.com/college-football/game/_/gameId/401411096) |
| 4c | Rutgers at Boston College (2022-09-03) | Rutgers 22, Boston College 21 | Q2 13:40 — Aron Cruickshank 26-yard TD run; Jude McAtamney PAT **missed** | [ESPN 401405069](https://www.espn.com/college-football/game/_/gameId/401405069) |
| 4d | Utah at Florida (2022-09-03) | Florida 29, Utah 26 | Q3 0:12 — Micah Bernard 7-yard TD run; **two-point run failed** | [ESPN 401403857](https://www.espn.com/college-football/game/_/gameId/401403857) |
| 4e | Arkansas vs Texas A&M (2022-09-24) | Texas A&M 23, Arkansas 21 | Q2 3:11 — after Richardson's fumble-return TD, **two-point pass failed** | [ESPN 401403893](https://www.espn.com/college-football/game/_/gameId/401403893) |

## 5. Defensive two-point return on a try

| # | Game (date) | Final | Play | Source |
|---|---|---|---|---|
| 5a | New Mexico at Wyoming (2023-09-30) | Wyoming 35, New Mexico 26 | Q1 10:50 — after New Mexico's opening TD (Hixon 17-yard pass), DeVonne Harris blocked the PAT and Jakorey Hawkins returned it for a defensive two-point score. NM 6, WYO 2 | [ESPN 401532588](https://www.espn.com/college-football/game/_/gameId/401532588); recap: [GoLobos.com (official UNM)](https://golobos.com/news/2023/09/30/wyoming-uses-big-plays-to-edge-unm-35-26/) |
| 5b | Eastern Michigan at Central Michigan (2023-09-30) | Central Michigan 26, Eastern Michigan 23 | Q3 9:23 — EMU PAT blocked and returned by Dakota Cochran (CMU) for two points, tying the game 16-16 | [ESPN 401532410](https://www.espn.com/college-football/game/_/gameId/401532410); recap: [CBS Sports/AP](https://www.cbssports.com/college-football/gametracker/recap/NCAAF_20230930_EMICH@CMICH/) |
| 5c | UCF at Kansas (2023-10-07) | Kansas 51, UCF 22 | Q3 7:02 — "Demari Henderson Defensive PAT Conversion" (UCF scores 2 on a Kansas try). Not checked against a recap | [ESPN 401525860](https://www.espn.com/college-football/game/_/gameId/401525860) |

## 6. Overtime games

### Pre-2019 format (2014–2018): every period starts at the 25; two-point try mandatory from OT3

| # | Game (date) | Final | Key plays | Source |
|---|---|---|---|---|
| 6a | LSU at Texas A&M (2018-11-24) | Texas A&M 74, LSU 72 (**7OT**) | Q4 0:00 — Mond 19-yard TD pass to Quartney Davis plus kick ties 31-31. OT1: field goals each side. OT2: TDs plus kicks each side. OT3–OT7: two-point try required after each TD (e.g., OT5: both two-point passes fail; OT7: LSU two-point fails, TAMU's Mond pass to Kendrick Rogers succeeds). Full possessions from the 25 through OT7 | [ESPN 401012356](https://www.espn.com/college-football/game/_/gameId/401012356) |
| 6b | Wisconsin at Purdue (2018-11-17) | Wisconsin 47, Purdue 44 (**3OT**) | OT1–2: TDs plus kicks each side. OT3: Purdue 41-yard FG, then Jonathan Taylor 17-yard TD run ends the game with **no try** (ESPN puts all OT plays in period 5) | [ESPN 401013353](https://www.espn.com/college-football/game/_/gameId/401013353) |

### 2019–2020 format: two-point try mandatory from OT3; single two-point plays from OT5

| # | Game (date) | Final | Key plays | Source |
|---|---|---|---|---|
| 6c | North Carolina at Virginia Tech (2019-10-19) | Virginia Tech 43, North Carolina 41 (**6OT**) | OT1: FG each side. OT2: TD plus kick each side. OT3–OT5: ESPN lists no scoring plays. OT6: Quincy Patterson two-point run wins it. This is a single-play two-point period (OT5+ format) | [ESPN 401112489](https://www.espn.com/college-football/game/_/gameId/401112489) |
| 6d | Texas vs Oklahoma, Dallas (2020-10-10) | Oklahoma 53, Texas 45 (**4OT**) | OT1–2: TD plus kick each side. OT4: Rattler 25-yard TD pass to Drake Stoops plus mandatory two-point pass to Theo Wease. Texas does not score | [ESPN 401236005](https://www.espn.com/college-football/game/_/gameId/401236005) |

### 2021+ format: two-point try mandatory from OT2; single two-point plays from OT3 (reached the shootout)

| # | Game (date) | Final | Key plays | Source |
|---|---|---|---|---|
| 6e | Illinois at Penn State (2021-10-23) | Illinois 20, Penn State 18 (**9OT**) | OT1: PSU 31-yard FG, ILL 39-yard FG. OT2: ILL 22-yard FG, PSU 40-yard FG (no TDs, so no mandatory two-point try). OT3–OT9 are two-point-only periods: OT8, ILL Peters pass to Isaiah Williams (good), PSU Cain run (good). OT9: ILL Peters pass to Casey Washington (good), PSU fails. ESPN's OT play-by-play is duplicated and out of order; the scoring-play list is consistent | [ESPN 401282717](https://www.espn.com/college-football/game/_/gameId/401282717) |
| 6f | Georgia Tech at Georgia (2024-11-29) | Georgia 44, Georgia Tech 42 (**8OT**) | OT1: TD plus kick each side. OT2: GT Haynes King 1-yard TD run, mandatory two-point pass fails (UGA also scored in OT2; check against the box score). OT5: Beck two-point pass to Dillon Bell and King two-point pass to Malik Rutherford both good. OT8: Nate Frazier two-point run wins it. ESPN running scores in OT are wrong (e.g., "42 50" in OT1) | [ESPN 401628439](https://www.espn.com/college-football/game/_/gameId/401628439) |

Other long 2021+ overtime games found in the ESPN scoreboard scan, not examined: Bowling Green 59, Eastern Kentucky 57 (7OT, 2022-09-10, ESPN 401416595); Toledo 48, Pittsburgh 46 (6OT, 2024 GameAbove Sports Bowl, ESPN 401677180); South Florida 41, San José State 39 (5OT, 2024 Hawai'i Bowl, ESPN 401677087).

## Count per item

| Item | Candidates |
|---|---|
| Interception / fumble return TD | 4 (2 INT, 2 fumble) |
| Safety | 3 |
| Penalty-nullified TD | 3 |
| Missed/blocked PAT | 3 (1 blocked, 2 missed) |
| Failed two-point try | 2 |
| Defensive two-point return | 3 (2 confirmed by written recaps) |
| OT pre-2019 | 2 |
| OT 2019–2020 | 2 (1 reached the OT5+ two-point periods) |
| OT 2021+ reaching the two-point shootout | 2 |
