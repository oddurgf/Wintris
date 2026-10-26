#!/usr/bin/env python3
"""One-off probe: does Fantrax give shot attempts (FGM/FGA, FTM/FTA) for Wintris teams?
Prints only stat names, ids and numbers. Never prints the cookie."""
import json, os, sys, urllib.request

LEAGUE = "f29oe0zdmv5gs7rl"
UA = {"User-Agent": "Mozilla/5.0 (Wintris dashboard)"}
c = os.environ.get("FANTRAX_COOKIE", "").strip()
if c.lower().startswith("cookie:"):
    c = c[7:].strip()
if c:
    UA["Cookie"] = c

def fxpa(method, data):
    body = json.dumps({"msgs": [{"method": method, "data": {"leagueId": LEAGUE, **data}}]}).encode()
    req = urllib.request.Request(f"https://www.fantrax.com/fxpa/req?leagueId={LEAGUE}", body, {"Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    err = d.get("pageError") or d["responses"][0].get("pageError")
    if err:
        print(method, "ERROR", err.get("code")); return None
    return d["responses"][0]["data"]

KEYS = ("FGA", "FTA", "FGM", "FTM", "Field Goals", "Free Throws", "Attempt", "1500", "1510", "1530", "1540")
def hunt(o, path="", out=None, depth=0):
    out = [] if out is None else out
    if depth > 14 or len(out) > 60: return out
    if isinstance(o, dict):
        for k, v in o.items():
            p = f"{path}.{k}"
            if isinstance(v, (str, int, float)) and any(s in str(v) or s in str(k) for s in KEYS):
                out.append((p, str(v)[:120]))
            hunt(v, p, out, depth + 1)
    elif isinstance(o, list):
        for i, v in enumerate(o[:40]):
            hunt(v, f"{path}[{i}]", out, depth + 1)
    return out

print("=== getLiveScoringStats week 1 ===")
d = fxpa("getLiveScoringStats", {"period": "1", "newView": True, "playerViewType": "1", "sppId": "-1", "viewType": "2"})
if d:
    print("top keys:", list(d.keys()))
    sp = d["statsPerTeam"]
    print("statsPerTeam keys:", list(sp.keys()))
    tid, t = next(iter(sp["statsMap"].items()))
    a = t["ACTIVE"]
    print("ACTIVE keys:", list(a.keys()))
    print("statsMap keys:", list(a["statsMap"].keys()))
    for k, v in a["statsMap"].items():
        print("--", k, json.dumps(v)[:1500])
    for p, v in hunt(d)[:60]:
        print("HIT", p, "=", v)

print("=== getTeamRosterInfo STATS ===")
for view in ("STATS", "SEASON_STATS"):
    r = fxpa("getTeamRosterInfo", {"teamId": tid if d else "", "period": "1", "view": view})
    if r:
        print(view, "keys:", list(r.keys()))
        for p, v in hunt(r)[:40]:
            print("HIT", view, p, "=", v)
        tables = r.get("tables") or []
        for tb in tables[:2]:
            print("header:", json.dumps(tb.get("header", {}))[:1500])
