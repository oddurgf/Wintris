# CLAUDE.md

## What this is

The public site for **Wintris**, a 12-team H2H 9-category fantasy basketball league on Fantrax
(league id `f29oe0zdmv5gs7rl`, season 2026–27, 19 regular-season weeks, top 6 make the playoffs).
It shows all-play records, a luck index, power rankings, close categories ("hjartasár"), playoff
odds (and their history), team pages (category heatmap, punt detector, "hvað vantaði?"), a league
tab (schedule swap, record book, yo-yo index) and a weekly recap card, with team logos. Live at https://oddurgf.github.io/Wintris/.

**This repo is the master copy.** The earlier claude.ai dashboard is archived and no longer
updated. Make all changes here. There is one site and one data pipeline.

## Files and data flow

```
Fantrax ──scripts/fetch_weeks.py──▶ data/weekly_stats.json ─┐
Fantrax ──scripts/fetch_logos.py──▶ data/logos.json ─────────┴─scripts/build_data.py──▶ data.js ──▶ index.html (site)
```

| File | Role |
|---|---|
| `index.html` | The whole site: layout, CSS, the calculations and charts (d3 v7 from cdnjs). Its first `<script>` is a small engine that stands in for the old dashboard runtime (`window.dash`: `data`, `calc`, `onData`, `params`/`setParams`, `setLink`, `colors`), serving data from `data.js` and running each `dash.calc` in the browser. |
| `data.js` | `window.WINTRIS_DATA = {teams, schedule, weekly_stats, sample_stats, logos, updated}`. Generated. |
| `data/logos.json` | `{teamId, logo}` rows, logo = base64 data URL of the 128px Fantrax logo (the site can't load images from other hosts reliably, and a missing logo falls back to an initials badge). |
| `scripts/fetch_logos.py` | Downloads the logos (`getFantasyTeams` + fantraximg.com). Runs in the workflow with `continue-on-error`, so a logo failure never blocks the stats. |
| `data/teams.json`, `data/schedule.json` | Fixed league facts (team ids/names/short names; weeks 1–19 matchups). |
| `data/weekly_stats.json` | One row per team per finished week: `week, teamId, PTS, REB, AST, ST, BLK, TPM, TO, FGP, FTP, GP`. Written by `fetch_weeks.py`. |
| `data/sample_stats.json` | Made-up weeks 1–6, used only while `weekly_stats.json` has no real weeks (the site then shows a yellow "Sýnigögn" banner). |
| `scripts/fetch_weeks.py` | Re-fetches **every** finished regular-season week from Fantrax's internal `fxpa/req` `getLiveScoringStats` (Period view) and checks each real matchup against Fantrax's own W-L-T. Exits non-zero on login failure or a mismatch. Needs a browser-like User-Agent (Fantrax 403s Python's default). |
| `scripts/build_data.py` | Bundles `data/*.json` into `data.js`. |
| `.github/workflows/update.yml` | Scheduled Tue 00:17 and 07:37 UTC (and manual "Run workflow"): fetch → build → commit data → deploy Pages. On a push to `main` it skips the fetch and only redeploys. |

Scoring rules the calculations assume: TO is lower-wins; a tied category counts as half; a matchup
can be a draw. A Fantrax week (scoring period) closes **Monday 18:59 US Eastern** (22:59 UTC in summer time,
23:59 UTC in winter). `fetch_weeks.py` only counts a week once it has formally closed, so the main
run is Tuesday 00:17 UTC, just after the close; the 07:37 run is a catch-up for stat corrections.

## Rules

- **The site's text is Icelandic.** Keep all visible text, labels and award texts in Icelandic.
- **Never edit `data.js` by hand.** Change `data/*.json` or the scripts and run
  `python3 -I scripts/build_data.py`.
- **Never put the Fantrax cookie in any file**, commit, log or output. It lives only in the GitHub
  Actions secret `FANTRAX_COOKIE`, which `fetch_weeks.py` reads from the environment.
- **A feature that needs new Fantrax data also needs `fetch_weeks.py` updated** (new fields in its
  rows), plus `build_data.py` if it is a new file. The current rows only have team category totals
  and games played per week; player-level stats, transactions, draft and lineups are not fetched.
- Keep calculations as `dash.calc(...)` blocks in `index.html` so the engine runs them the same way.

## Before every push: check the site in a headless browser

Serve the repo locally, then open it with Playwright (preinstalled in cloud sessions) and click
every tab (`.wx-tab`) at a desktop width (1280×900) and a phone width (390×844). Confirm there are
no console errors or page errors, and that the page doesn't scroll sideways.

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
