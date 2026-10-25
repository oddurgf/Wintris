# Wintris · mælaborð deildarinnar

League site for the Wintris fantasy basketball league (12 teams, H2H 9-cat on Fantrax).
It shows all-play records, a luck index, power rankings, close categories, playoff odds, team pages,
a record book, schedule swaps and a weekly recap card, with each team's Fantrax logo.

The site updates itself every Monday at 10:00 Iceland time, after the week's last games on Sunday night, and again on Thursday at 10:00 to pick up Fantrax's stat corrections.

## How it works

| File | What it is |
|---|---|
| `index.html` | The site: layout, calculations and charts |
| `data.js` | All the numbers, built automatically. Don't edit by hand |
| `data/` | Teams, schedule, sample numbers and the weekly stats from Fantrax |
| `scripts/fetch_weeks.py` | Pulls finished weeks from Fantrax using your login cookie |
| `scripts/fetch_logos.py` | Downloads the team logos from Fantrax into `data/logos.json` (skipped without failing the update if it breaks) |
| `scripts/build_data.py` | Combines `data/` into `data.js` |
| `.github/workflows/update.yml` | Runs the update Monday and Thursday at 10:00 (Iceland time) and publishes the site |

Until the first week has finished, the site shows made-up sample numbers with a yellow banner.
The banner disappears by itself once real weeks arrive.

## One-time setup

1. **Turn on Pages:** Settings → Pages → under *Build and deployment*, set **Source** to **GitHub Actions**.
2. **Add your Fantrax cookie:** Settings → Secrets and variables → Actions → **New repository secret**.
   Name it `FANTRAX_COOKIE` and paste the cookie value (see below).
3. **Test it:** Actions tab → **Update league data** → **Run workflow**. When it turns green, the site is live at
   `https://<your-username>.github.io/<repo-name>/`.

### Getting your Fantrax cookie (Chrome or Edge, on a computer)

1. Log in to fantrax.com and open your league.
2. Press **F12** (Mac: **Cmd + Option + I**) and open the **Network** tab.
3. Reload the page. Type `req` in the filter box and click one of the `req?leagueId=...` rows.
4. Under **Headers → Request Headers**, find **cookie** and copy its whole value (a long line of text).
5. Paste it as the `FANTRAX_COOKIE` secret.

The cookie is encrypted by GitHub and never visible in the code or the logs, even though the repository is public.

## When something breaks

- **GitHub emails you** if an update fails. The usual reason is an expired Fantrax login:
  copy a fresh cookie (steps above), update the secret, then press **Run workflow**.
- **"Matchup check mismatches" in the log** means the script's category count disagreed with Fantrax's own result.
  Nothing is published in that case, so the site keeps the last good numbers.
