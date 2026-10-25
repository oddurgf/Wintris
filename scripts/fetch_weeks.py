#!/usr/bin/env python3
"""Fetch Wintris weekly team category totals from Fantrax.

Usage: python3 -I fetch_weeks.py OUT.json [--include-current]
Writes rows {week, teamId, PTS, REB, AST, ST, BLK, TPM, TO, FGP, FTP, GP} for every
finished scoring period of the regular season (1-19), and each week's games-played
limits {week, min, max} (all 19 weeks, future ones too) to gp_limits.json next to OUT. The Fantrax login cookie is
read from the FANTRAX_COOKIE environment variable (a GitHub secret in the workflow).
Exits non-zero if Fantrax says we are not logged in or a matchup check fails.
"""
import json, os, sys, urllib.request
from datetime import datetime, timedelta, timezone

LEAGUE = "f29oe0zdmv5gs7rl"
UA = {"User-Agent": "Mozilla/5.0 (Wintris dashboard)"}
_cookie = os.environ.get("FANTRAX_COOKIE", "").strip()
if _cookie.lower().startswith("cookie:"):
    _cookie = _cookie[7:].strip()
if _cookie:
    UA["Cookie"] = _cookie
REG_WEEKS = 19
# The Monday run counts last week as finished even if Fantrax's stored end time is
# still a few hours away; Thursday's run then picks up any stat corrections.
END_GRACE = timedelta(hours=14)
CAT = {"3010#1390#-1": "PTS", "3010#1400#-1": "REB", "3010#1250#-1": "AST", "3010#1410#-1": "ST",
       "3010#1260#-1": "BLK", "3010#1435#-1": "TPM", "3010#1460#-1": "TO", "3010#1520#-1": "FGP", "3010#1550#-1": "FTP"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)

def fxpa(method, data):
    body = json.dumps({"msgs": [{"method": method, "data": {"leagueId": LEAGUE, **data}}]}).encode()
    req = urllib.request.Request(f"https://www.fantrax.com/fxpa/req?leagueId={LEAGUE}", body, {"Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    err = d.get("pageError") or d["responses"][0].get("pageError")
    if err:
        sys.exit(f"Fantrax error: {err.get('code')} (login cookie missing or expired?)")
    return d["responses"][0]["data"]

def save_periods(info, path):
    """Keep each scoring period's dates (public league info) so the site can show them."""
    rows = [{k: p[k] for k in ("number", "startDate", "endDate", "name", "caption") if k in p}
            for p in info["scoringPeriods"]]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=0)

def finished_weeks(include_current, periods_out=None):
    info = get(f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={LEAGUE}")
    if periods_out:
        save_periods(info, periods_out)
    now = datetime.now(timezone.utc)
    out = []
    for p in info["scoringPeriods"]:
        n = p["number"]
        end = datetime.strptime(p["endDate"].replace(".0", ""), "%Y-%m-%dT%H:%M:%S%z")
        start = datetime.strptime(p["startDate"].replace(".0", ""), "%Y-%m-%dT%H:%M:%S%z")
        if n <= REG_WEEKS and (end < now + END_GRACE or (include_current and start < now)):
            out.append(n)
    return out

def roster_period_for_weeks():
    """Map each scoring week to its first roster period (lineup day).

    The roster page's `period` is a roster period, not a scoring week: Wintris sets lineups
    daily, so roster period 7 is the first day of week 2. Uses Fantrax's own rosterPeriods
    when they carry dates, else counts days from the season's first day."""
    info = get(f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={LEAGUE}")
    day = lambda v: str(v)[:10]
    starts = {p["number"]: day(p["startDate"]) for p in info["scoringPeriods"] if p["number"] <= REG_WEEKS}
    rp = info.get("rosterPeriods")
    rps = list(rp.values()) if isinstance(rp, dict) else rp if isinstance(rp, list) else []
    dated = sorted((day(r["startDate"]), int(r["number"])) for r in rps if isinstance(r, dict) and "startDate" in r and "number" in r)
    if dated:
        out = {w: next((n for d, n in dated if d >= s0), None) for w, s0 in starts.items()}
        how = "rosterPeriods"
    else:
        first = datetime.strptime(starts[1], "%Y-%m-%d")
        out = {w: (datetime.strptime(s0, "%Y-%m-%d") - first).days + 1 for w, s0 in starts.items()}
        how = "day count"
    print(f"roster periods ({how}): " + ", ".join(f"w{w}->{n}" for w, n in sorted(out.items())))
    return out

def gp_limits(team_id, path):
    """Each week's games-played min/max, from the roster page's "games per position" view.

    Fantrax shows the same limits for every team. A week Fantrax won't answer for keeps
    the value from the last run, so a hiccup never wipes the limits."""
    try:
        with open(path, encoding="utf-8") as f:
            old = {r["week"]: r for r in json.load(f)}
    except (OSError, ValueError):
        old = {}
    num = lambda v: int(v) if str(v).strip().isdigit() else None
    try:
        first_day = roster_period_for_weeks()
    except Exception as e:  # keep last run's limits rather than block the stats update
        print(f"No roster periods ({type(e).__name__}); keeping the old games limits")
        return
    rows = []
    for week in range(1, REG_WEEKS + 1):
        row = old.get(week)
        try:
            if first_day.get(week) is None:
                raise LookupError("no roster period")
            d = fxpa("getTeamRosterInfo", {"teamId": team_id, "period": str(first_day[week]), "view": "GAMES_PER_POS"})
            gp = [x for x in (d.get("scMinMaxData") or {}).get("tableData", []) if "(GP)" in x.get("scoringCategory", "")]
            if gp:
                row = {"week": week, "min": num(gp[0].get("min")), "max": num(gp[0].get("max"))}
        except SystemExit:
            raise
        except Exception as e:  # a missing week must not stop the stats update
            print(f"Week {week}: no games limit ({type(e).__name__})")
        if row:
            rows.append(row)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0)
    print("games limits: " + ", ".join(f"w{r['week']} {r['min']}-{r['max']}" for r in rows))

def week_rows(week):
    d = fxpa("getLiveScoringStats", {"period": str(week), "newView": True, "playerViewType": "1", "sppId": "-1", "viewType": "2"})
    rows, wlt = [], {}
    for tid, t in d["statsPerTeam"]["statsMap"].items():
        a = t["ACTIVE"]
        tot = a["statsMap"]["_3010"]["object2"]
        r = {"week": week, "teamId": tid}
        for x in tot:
            if x["scipId"] in CAT:
                r[CAT[x["scipId"]]] = x["av"]
        missing = [c for c in CAT.values() if c not in r]
        if missing:
            sys.exit(f"Week {week} team {tid}: missing {missing}")
        # playerGameInfo is [played, playing now, remaining, minutes played, minutes remaining]
        gp = a.get("playerGameInfo", [None])[0]
        r["GP"] = int(gp) if gp is not None else None
        rows.append(r)
        w = list((a.get("wltPerMchup") or {}).values())
        if w:
            wlt[tid] = w[0]
    return rows, wlt, d.get("matchups", [])

def check(rows, wlt, matchups, week):
    """Recompute each real matchup and compare with Fantrax's own W-L-T."""
    by = {r["teamId"]: r for r in rows}
    bad = []
    for m in matchups:
        a, b = m.split("_")
        cw = cl = ct = 0
        for c in CAT.values():
            x, y = round(by[a][c] * 10000), round(by[b][c] * 10000)
            dlt = (y - x) if c == "TO" else (x - y)
            cw, cl, ct = cw + (dlt > 0), cl + (dlt < 0), ct + (dlt == 0)
        if a in wlt and [cw, cl, ct] != [int(v) for v in wlt[a]]:
            bad.append(f"{a} vs {b}: mine {cw}-{cl}-{ct}, Fantrax {wlt[a]}")
    return bad

if __name__ == "__main__":
    out = sys.argv[1]
    if not _cookie:
        sys.exit("FANTRAX_COOKIE is empty: add your Fantrax login cookie as a GitHub secret (see README).")
    data_dir = os.path.dirname(os.path.abspath(out))
    weeks = finished_weeks("--include-current" in sys.argv, os.path.join(data_dir, "periods.json"))
    with open(os.path.join(data_dir, "teams.json"), encoding="utf-8") as f:
        gp_limits(json.load(f)[0]["teamId"], os.path.join(data_dir, "gp_limits.json"))
    allrows, problems = [], []
    for w in weeks:
        rows, wlt, mus = week_rows(w)
        if len(rows) != 12:
            sys.exit(f"Week {w}: expected 12 teams, got {len(rows)}")
        problems += [f"week {w}: {p}" for p in check(rows, wlt, mus, w)]
        allrows += rows
    json.dump(allrows, open(out, "w"), indent=0)
    print(f"weeks: {weeks}; rows: {len(allrows)}")
    if problems:
        print("MATCHUP CHECK MISMATCHES:\n" + "\n".join(problems))
        sys.exit(2)
