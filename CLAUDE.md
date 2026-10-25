# CLAUDE.md

## What this is

The public site for **Wintris**, a 12-team H2H 9-category fantasy basketball league on Fantrax
(league id `f29oe0zdmv5gs7rl`, season 2026–27, 19 regular-season weeks, top 6 make the playoffs).
Live at https://oddurgf.github.io/Wintris/. It is built mobile-first (most people open it from a
link on their phone) and has three pages, a bottom tab bar on phones and top tabs on computers:

- **Vikan** (home): week stepper (with the week's games max), generated headline, the Messenger
  recap image with the week's awards beside it (a fold on phones), the week's results with tags
  (Sóp, Óheppni, Réðst á …) and games played, close categories, all-play matrix, category leaders
  and next week's games.
- **Liðið mitt**: team dropdown (remembered in localStorage), 4 tiles, the week's head-to-head box
  (margins, games played vs the week's max, how the opponent played vs his own average), then
  segments *Tímabilið* / *Flokkar* / *Framundan* (next games and every week's games min/max).
- **Deildin**: segments *Staðan* (one merged standings table with a Staða/Kraftröðun sort and a
  "Sýna alla dálka" toggle), *Heppni* (incl. *Mótherjinn í stuði*), *Hjartasár* and *Met* (incl.
  *Verðlaunaskápurinn*, the season's weekly awards per team).

- **Útskýringar** (`#utskyringar`, no tab): the help page, opened from the "?" in the site header.
  A short Icelandic explanation and a screenshot (`img/utskyringar/*.webp`, taken from the demo
  data) for each metric. When a metric, award or limit changes, update its text here too.

Shareable links: `#vikan/3`, `#lid/<teamId>/3`, `#deildin/heppni`, `#utskyringar`. Old links (`#yfirlit`,
`#hjartasar` …) still land on the right view. Any team name opens Liðið mitt for that team. Long
method notes sit behind a "?" button on each card, with a one-line subtitle visible.

**This repo is the master copy.** The earlier claude.ai dashboard is archived and no longer
updated. Make all changes here. There is one site and one data pipeline.

## Files and data flow

```
Fantrax ──scripts/fetch_weeks.py──▶ data/weekly_stats.json ─┐
                               ├──▶ data/periods.json ──────┤
                               └──▶ data/gp_limits.json ────┤
Fantrax ──scripts/fetch_logos.py──▶ data/logos.json ─────────┴─scripts/build_data.py──▶ data.js ──▶ index.html (site)
```

| File | Role |
|---|---|
| `index.html` | The whole site: layout, CSS, the calculations and charts (d3 v7 from cdnjs). Its first `<script>` is a small engine that stands in for the old dashboard runtime (`window.dash`: `data`, `calc`, `onData`, `params`/`setParams`, `setLink`, `colors`), serving data from `data.js` and running each `dash.calc` in the browser. |
| `data.js` | `window.WINTRIS_DATA = {teams, schedule, weekly_stats, sample_stats, logos, periods, gp_limits, update_status, updated}`. Generated. |
| `data/periods.json` | Fantrax scoring periods `{number, startDate, endDate}` (all 22, from the public `getLeagueInfo`), saved by `fetch_weeks.py` on every run. The site's `week_dates` calc turns them into game days: a week closes on a Monday (usually 18:59 ET, sometimes noon), so its last game day is the Sunday before; week 1 is Tue 20 Oct – Sun 25 Oct. Shown next to the week stepper, on the matchup box, Framundan and the recap image. |
| `data/gp_limits.json` | Each regular-season week's games-played limits `{week, min, max}` (all 19 weeks, future ones too), from `getTeamRosterInfo` with `view: "GAMES_PER_POS"` (`scMinMaxData`). Its `period` is a **roster period** (a lineup day), not a scoring week, so `fetch_weeks.py` asks for each week's first day (from `rosterPeriods`, else by counting days from 20 Oct: week 2 = 7, week 3 = 14). Saved by `fetch_weeks.py` on every run; a week Fantrax won't answer for keeps its old value. Usually 28 max; shorter weeks (week 1, All-Star week) are lower. |
| `data/update_status.json` | `{week, runs}`: the latest finished week and the UTC time of each successful `fetch_weeks.py` run for it (a new week starts a new list). Drives the update status at the top right of the header: one tick after a Monday–Wednesday run (preliminary), two once a Thursday-or-later run has re-fetched the week (Fantrax's final numbers). Hidden while the site shows sample data. Explained on Útskýringar (`#ex-uppfaersla`). |
| `data/logos.json` | `{teamId, logo}` rows, logo = base64 data URL of the 128px Fantrax logo (the site can't load images from other hosts reliably, and a missing logo falls back to an initials badge). |
| `scripts/fetch_logos.py` | Downloads the logos (`getFantasyTeams` + fantraximg.com). Runs in the workflow with `continue-on-error`, so a logo failure never blocks the stats. |
| `data/teams.json`, `data/schedule.json` | Fixed league facts (team ids/names/short names; weeks 1–19 matchups). |
| `data/weekly_stats.json` | One row per team per finished week: `week, teamId, PTS, REB, AST, ST, BLK, TPM, TO, FGP, FTP, GP`. Written by `fetch_weeks.py`. GP is `playerGameInfo[0]` of the live-scoring response, whose list is `[played, playing now, remaining, minutes played, minutes remaining]`. |
| `data/sample_stats.json` | Made-up weeks 1–6, used only while `weekly_stats.json` has no real weeks (the site then shows a yellow "Sýnigögn" banner). |
| `scripts/fetch_weeks.py` | Re-fetches **every** finished regular-season week from Fantrax's internal `fxpa/req` `getLiveScoringStats` (Period view) and checks each real matchup against Fantrax's own W-L-T. Exits non-zero on login failure or a mismatch. Needs a browser-like User-Agent (Fantrax 403s Python's default). |
| `scripts/build_data.py` | Bundles `data/*.json` into `data.js`. |
| `.github/workflows/update.yml` | Scheduled Monday and Thursday 10:00 UTC (and manual "Run workflow"): fetch → build → commit data → deploy Pages. On a push to `main` it skips the fetch and only redeploys. |

Scoring rules the calculations assume: TO is lower-wins; a tied category counts as half; a matchup
can be a draw. A Fantrax week (scoring period) closes **Monday 18:59 US Eastern** (22:59 UTC in summer time,
23:59 UTC in winter). The Monday 10:00 UTC run counts last week as finished anyway (`END_GRACE` in
`fetch_weeks.py`; the NBA week ends Sunday night), and the Thursday run picks up Fantrax's stat corrections.
Each week also has a games-played max (and min): a team at the max at the start of a day gets no stats
for the week and loses it, so a team can finish a little above the max.

## Rules

- **The site's text is Icelandic.** Keep all visible text, labels and award texts in Icelandic.
- **Never edit `data.js` by hand.** Change `data/*.json` or the scripts and run
  `python3 -I scripts/build_data.py`.
- **Never put the Fantrax cookie in any file**, commit, log or output. It lives only in the GitHub
  Actions secret `FANTRAX_COOKIE`, which `fetch_weeks.py` reads from the environment.
- **A feature that needs new Fantrax data also needs `fetch_weeks.py` updated** (new fields in its
  rows), plus `build_data.py` if it is a new file. The current rows only have team category totals
  and games played per week, plus the weekly games limits; player-level stats, transactions, draft
  and lineups are not fetched.
- Keep calculations as `dash.calc(...)` blocks in `index.html` so the engine runs them the same way.

## Before every push: check the site in a headless browser

Serve the repo locally, then open it with Playwright (preinstalled in cloud sessions) and click
every tab (`.wx-tab`) **and every segment** (`.wx-seg[data-seg="lid"|"deildin"] button`) at a desktop
width (1280×900) and a phone width (390×844). Confirm there are no console errors or page errors,
that the page doesn't scroll sideways, and on the phone that no table shows more than 5 columns
and tap targets are at least 44px. Only the three grids (all-play matrix, category heatmap,
schedule swap) and the standings table with all columns on may scroll sideways inside their box.

```bash
python3 -m http.server 8765 &   # from the repo root
```

Cloud sessions usually block `cdnjs.cloudflare.com` and Google Fonts. Then "d3 is not defined"
is an environment problem, not a site bug: get d3 from npm (`npm pack d3@7.9.0`, then use
`package/dist/d3.min.js`). In Playwright, answer requests to `https://cdnjs.cloudflare.com/**`
with that file, and answer requests to fonts.googleapis.com / fonts.gstatic.com with an empty
200 response.

## Publishing

Every push to `main` republishes https://oddurgf.github.io/Wintris/ within about a minute (the
`deploy` job in `update.yml`). There is no staging site, so check before pushing.
