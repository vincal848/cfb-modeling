# D01 findings: CFBD endpoint contracts

Run date: 2026-10-01. Source: live CFBD, Tier 4. Raw table: [endpoint-audit-2024.md](endpoint-audit-2024.md).

The sample partition was season 2024, week 5, and Michigan for team-scoped endpoints. All 20 registered endpoints returned HTTP 200. The run used 19 calls; `/info` appears not to count against the quota.

These findings come from one sample partition. Coverage across seasons is the job of D02.

## Findings that change the implementation

1. **Historical lines have no observation timestamp.** Each `/lines` entry has `provider`, `spread`, `spreadOpen`, `overUnder`, `overUnderOpen` and moneylines, but no time at which the price was observed.
   - Under methodology §8 ("market features require book, line, odds, snapshot time"), historical CFBD lines cannot enter a **strict** market-informed forecast. At best they are a *reconstructed* benchmark of unknown timing (roughly open vs. a later or closing value).
   - The market-informed product can only be evaluated prospectively, from our own timestamped captures starting now.
   - The football-only product is unaffected.
   - Sign convention seen: `spread: -2` paired with `"formattedSpread": "Auburn -2"`, with Auburn as the home team. That is a handicap applied to the home team, which matches the blueprint's `h` (home covers if `M + h > 0`). This needs confirming on more games before any settlement code relies on it.
   - Up to three books per game. Some games have none.

2. **`/games` mixes pregame and postgame facts in one record.**
   - Schedule fields (`startDate`, `startTimeTBD`, `neutralSite`, `venueId`, teams) are knowable before kickoff.
   - Result fields (`homePoints`, `homeLineScores`, `*PostgameElo`, `*PostgameWinProbability`, `excitementIndex`, `attendance`) are not.
   - D05 must split each game into a **schedule fact** and a **result fact**, each with its own `available_at`. Otherwise a snapshot that admits the game record admits its score.
   - `*PregameElo` is provider-computed with roughly 80% nulls in this sample. It is comparison-only; the plan recomputes Elo itself (B01).

3. **Population filter is required.** `/games?year&week` returns every division: 270 games in week 5, of which only 56 involve an FBS team (53 FBS–FBS and 3 FBS–FCS). Classification is occasionally null (5 games), so filtering must not silently drop FBS games whose opponent's classification is missing.

4. **`/games/weather` is realized weather, not a forecast.** It has observed temperature, wind, precipitation and similar fields. Methodology §6 forbids realized weather as a pregame predictor, so it stays `comparison_only`. Pregame weather needs timestamped forecasts captured prospectively.

5. **Portal records have no athlete ID.**
   - The fields are name, position, origin, destination (21% null), `transferDate`, `eligibility`, stars and rating.
   - This confirms the crosswalk requirement (D06).
   - `transferDate` looks like an entry timestamp and could serve as evidence of when the event happened. It is **not** publication evidence (methodology §2).

6. **Roster→recruit links are partial.** 92 of 139 Michigan 2024 roster rows carry `recruitIds`. Missing links stay unresolved; they are not name-matched by default.

7. **Player play-stat cap not approached.** A team-week partition of `/plays/stats` returned 87 rows against the documented 2,000 cap. Team-week is a safe partition; whole-week pulls still need checking in D02.

## Unchanged

`/plays` (17,323 rows for the full week) and `/drives` (2,345) returned without an observed cap. Whether they are complete is a D02 question: reconcile play-derived scores against `/games` finals.
