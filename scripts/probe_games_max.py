#!/usr/bin/env python3
"""One-off probe: look for each matchup's games max in the Fantrax responses.

Prints only key paths whose name looks like a games limit, plus playerGameInfo.
Never prints the cookie. Delete this file and its workflow once we know the answer.
"""
import json, os, re, sys, urllib.request

LEAGUE = "f29oe0zdmv5gs7rl"
UA = {"User-Agent": "Mozilla/5.0 (Wintris dashboard)"}
_cookie = os.environ.get("FANTRAX_COOKIE", "").strip()
if _cookie.lower().startswith("cookie:"):
    _cookie = _cookie[7:].strip()
if _cookie:
    UA["Cookie"] = _cookie
PAT = re.compile(r"max|limit|min|game|gp|cap", re.I)

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
        return {"_error": err.get("code")}
    return d["responses"][0]["data"]

def short(v):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 300 else s[:300] + " …"

def walk(v, path, seen, limit=150):
    if isinstance(v, dict):
        for k, x in v.items():
            p = f"{path}.{k}"
            if PAT.search(str(k)) and len(seen) < limit:
                seen.append(f"{p} = {short(x)}")
            walk(x, p, seen, limit)
    elif isinstance(v, list):
        for i, x in enumerate(v[:30]):
            walk(x, f"{path}[{i}]", seen, limit)

def report(name, d):
    print(f"\n===== {name} =====")
    if isinstance(d, dict):
        print("top-level keys:", sorted(d.keys()))
    seen = []
    walk(d, "", seen)
    print("\n".join(seen) or "(no matching keys)")

if __name__ == "__main__":
    week = sys.argv[1] if len(sys.argv) > 1 else "1"
    report("getLeagueInfo (public)", get(f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={LEAGUE}"))
    live = fxpa("getLiveScoringStats", {"period": week, "newView": True, "playerViewType": "1", "sppId": "-1", "viewType": "2"})
    print(f"\n===== getLiveScoringStats period {week}: playerGameInfo per team =====")
    for tid, t in ((live.get("statsPerTeam") or {}).get("statsMap") or {}).items():
        a = t.get("ACTIVE", {})
        print(tid, "team keys:", sorted(t.keys()), "ACTIVE keys:", sorted(a.keys()))
        print("   playerGameInfo =", short(a.get("playerGameInfo")))
    report(f"getLiveScoringStats period {week} (minus players)", {k: v for k, v in live.items() if k != "statsPerTeam"})
    for method, data in [("getLeagueHomeInfo", {}), ("getStandings", {}), ("getFantasyLeagueInfo", {}),
                         ("getMatchupScoringInfo", {"period": week}), ("getLeagueRules", {})]:
        try:
            report(method, fxpa(method, data))
        except Exception as e:
            print(f"\n===== {method}: failed ({type(e).__name__}) =====")
