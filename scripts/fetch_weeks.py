#!/usr/bin/env python3
"""Fetch Wintris weekly team category totals from Fantrax.

Usage: python3 -I fetch_weeks.py OUT.json [--include-current]
Writes rows {week, teamId, PTS, REB, AST, ST, BLK, TPM, TO, FGP, FTP, GP} for every
finished scoring period of the regular season (1-19). The Fantrax login cookie is
read from the FANTRAX_COOKIE environment variable (a GitHub secret in the workflow).
Exits non-zero if Fantrax says we are not logged in or a matchup check fails.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

LEAGUE = "f29oe0zdmv5gs7rl"
UA = {"User-Agent": "Mozilla/5.0 (Wintris dashboard)"}
_cookie = os.environ.get("FANTRAX_COOKIE", "").strip()
if _cookie.lower().startswith("cookie:"):
    _cookie = _cookie[7:].strip()
if _cookie:
    UA["Cookie"] = _cookie
REG_WEEKS = 19
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

def finished_weeks(include_current):
    info = get(f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={LEAGUE}")
    now = datetime.now(timezone.utc)
    out = []
    for p in info["scoringPeriods"]:
        n = p["number"]
        end = datetime.strptime(p["endDate"].replace(".0", ""), "%Y-%m-%dT%H:%M:%S%z")
        start = datetime.strptime(p["startDate"].replace(".0", ""), "%Y-%m-%dT%H:%M:%S%z")
        if n <= REG_WEEKS and (end < now or (include_current and start < now)):
            out.append(n)
    return out

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
        r["GP"] = a.get("playerGameInfo", [None])[0]
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
    weeks = finished_weeks("--include-current" in sys.argv)
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
