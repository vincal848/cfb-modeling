# D02 findings: season coverage, 2014–2025

Run date: 2026-10-01. Source: live CFBD, Tier 4. Raw table: [coverage-2014-2025.md](coverage-2014-2025.md) (per-season detail, including mismatch kinds and books per game, is in the `.json`).

Population: games with at least one team in that season's `/teams/fbs`. Each season pulled `/teams/fbs`, `/calendar`, and `/games` and `/lines` by season type, then `/games/teams`, `/drives` and `/plays` per calendar week.

The full backfill used 585 calls (124,933 → 124,348 remaining). There were no failed partitions and no suspected truncation; the largest single `/plays` week returned 24,398 rows.

## Headline numbers

- 10,372 FBS-involving games across 12 seasons; 10,371 have final scores. The one unscored game is in 2024.
- Team box stats: 99.9–100% of scored games in every season.
- Drives and plays: 98.0–100%. The gaps are in 2014–2019, the largest being 2014 (98.0%) and 2016 (98.2%). From 2020 on, every scored game has drives and plays.
- Lines (any book): 95.6–100%. 2015 is the weakest season, with 38 scored games that have no line.
- No null team classifications in the FBS population once membership comes from `/teams/fbs`.

## Findings that change the implementation

1. **Opening lines and moneylines exist only from 2021.**
   - `spreadOpen` and moneylines are 0% for 2014–2020, then 83–100% from 2021.
   - Any open-to-close comparison, or any moneyline-based benchmark, is limited to 2021–2025. Before 2021 the market benchmark is a single spread of unknown timing (see D01 finding 1).
   - V01 must state which seasons each market benchmark covers rather than pooling across the 2021 break.

2. **Play-by-play is not always a reliable source of the final score.**
   - The check compares the last drive's end score with the official final score. 244 of the scored games with drives (about 2.4%) disagree.
   - The worst season is 2021 (92.6% match, 66 games); 2014–2019 match at 98.3–99.7%.
   - The disagreements fall into three kinds:

     | Kind | Count | Meaning |
     |---|---|---|
     | Play-by-play ends before Q4 | 9 | The feed is missing the end of the game (e.g. 2024 California–UC Davis stops in Q3 at 14–13; final 31–13). |
     | Short of final, Q4 reached | 147 | One or more scores are missing from the feed. |
     | Over final, or mixed | 88 | Scores in the feed are wrong (e.g. 2024 Ohio State–Western Michigan: a TD drive goes 49→57; final 56–0). |

   - In the 2024 games spot-checked, the official final score was correct and the error was in the play-by-play. This was not checked for every game.
   - **D08 consequence:** the official `/games` score is the outcome of record. Games whose play-by-play does not reach the final score must be quarantined from play-derived models (P01–P02 state machine, EP/EPA, drive models), not from team-level score models.

3. **Mid-game scores in drives can be corrupt even when the end score is right.**
   - Example: 2024 Tulane–Kansas State, drive 8 records a start score of −7 and an end score of 35, but the game's last drive ends at the correct 27–34.
   - Taking the maximum score seen across drives (the first version of this audit) counted such games as mismatches; using the last drive fixes that.
   - **P01 consequence:** the possession state machine must reconcile score changes drive by drive and flag impossible values (negative scores, jumps that no scoring play explains), rather than trusting each drive's reported score.

4. **Drives and plays are not independent checks.** In 2024 all 36 games flagged by the max-score method disagreed identically in drives and plays. They come from the same feed, so agreement between them is not confirmation.

## Findings that need no change but must be recorded

5. **2020 is a short season**: 568 FBS-involving games (others: 868–934) and only 34 FBS-vs-non-FBS games. Fold design (V01) should treat 2020 as atypical rather than as an ordinary training season.
6. **The FBS count grows** from 128 (2014) to 136 (2025). Membership must be taken per season.
7. **Books per game changes over time**: mostly 3 books through 2017; mostly 4–5 in 2018–2022; mostly 3 again in 2023–2025. Any consensus line must be defined over whichever books are present and record the count.

None of these require a spec deviation. Finding 1 narrows what V01 can claim for market benchmarks; findings 2–3 feed D08 and P01.
