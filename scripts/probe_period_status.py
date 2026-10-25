#!/usr/bin/env python3
"""One-off probe: does Fantrax flag a scoring period as final/processed, and when?

Prints only key paths whose name looks like a status, flag or time, from this season's
league and (if Fantrax links one) last season's. Never prints the cookie.
Delete this file and its workflow once we know the answer.
"""
import json, os, re, sys, urllib.request

LEAGUE = "f29oe0zdmv5gs7rl"
UA = {"User-Agent": "Mozilla/5.0 (Wintris dashboard)"}
_cookie = os.environ.get("FANTRAX_COOKIE", "").strip()
if _cookie.lower().startswith("cookie:"):
    _cookie = _cookie[7:].strip()
if _cookie:
    UA["Cookie"] = _cookie
PAT = re.compile(r"final|complet|process|status|official|lock|current|closed|done|result|pending|correct|"
                 r"date|time|updat|season|previous|prior|history|linked|renew|year|period", re.I)

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return json.load(r)

def fxpa(league, method, data):
    body = json.dumps({"msgs": [{"method": method, "data": {"leagueId": league, **data}}]}).encode()
    req = urllib.request.Request(f"https://www.fantrax.com/fxpa/req?leagueId={league}", body, {"Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    err = d.get("pageError") or d["responses"][0].get("pageError")
    if err:
        return {"_error": err.get("code")}
    return d["responses"][0]["data"]

def short(v):
    s = json.dumps(v, ensure_ascii=False)
    return s if len(s) <= 300 else s[:300] + " …"

def walk(v, path, seen, limit=200):
    if isinstance(v, dict):
        for k, x in v.items():
            p = f"{path}.{k}"
            if PAT.search(str(k)) and len(seen) < limit:
                seen.append(f"{p} = {short(x)}")
            walk(x, p, seen, limit)
    elif isinstance(v, list):
        for i, x in enumerate(v[:4]):
            walk(x, f"{path}[{i}]", seen, limit)

def report(name, d):
    print(f"\n===== {name} =====")
    if isinstance(d, dict):
        print("top-level keys:", sorted(d.keys()))
    seen = []
    walk(d, "", seen)
    print("\n".join(seen) or "(no matching keys)")

def ids(v, out):
    """League ids Fantrax mentions anywhere (to find last season's league)."""
    if isinstance(v, dict):
        for k, x in v.items():
            if isinstance(x, str) and re.fullmatch(r"[a-z0-9]{16}", x) and re.search(r"league", k, re.I):
                out.add(x)
            ids(x, out)
    elif isinstance(v, list):
        for x in v:
            ids(x, out)

def probe(league, periods):
    info = get(f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={league}")
    sp = info.get("scoringPeriods") or []
    print(f"\n##### league {league}: {len(sp)} scoring periods #####")
    for p in sp:
        if p.get("number") in periods:
            print("scoringPeriod", short(p))
    report("getLeagueInfo (minus scoringPeriods)", {k: v for k, v in info.items() if k != "scoringPeriods"})
    fli = fxpa(league, "getFantasyLeagueInfo", {})
    report("getFantasyLeagueInfo", fli)
    for n in periods:
        live = fxpa(league, "getLiveScoringStats", {"period": str(n), "newView": True, "playerViewType": "1", "sppId": "-1", "viewType": "2"})
        report(f"getLiveScoringStats period {n} (minus statsPerTeam)", {k: v for k, v in live.items() if k != "statsPerTeam"})
        print("miscData =", short(live.get("miscData")))
    for method, data in [("getStandings", {"view": "SCHEDULE"}), ("getStandings", {})]:
        try:
            report(f"{method} {data}", fxpa(league, method, data))
        except Exception as e:
            print(f"\n===== {method}: failed ({type(e).__name__}) =====")
    found = set()
    ids(info, found); ids(fli, found)
    return found - {league}

def round2():
    for n in (1, 2):
        live = fxpa(LEAGUE, "getLiveScoringStats", {"period": str(n), "newView": True, "playerViewType": "1", "sppId": "-1", "viewType": "2"})
        print(f"\nperiod {n}: allEventsFinished = {short(live.get('allEventsFinished'))}, live2 = {short(live.get('live2'))}")
        print("  matchups[0] =", short((live.get("matchups") or [None])[0]))
        print("  standingsTable =", short(live.get("standingsTable"))[:300])
    st = fxpa(LEAGUE, "getStandings", {"view": "SCHEDULE"})
    tl = st.get("tableList") or []
    print("\ngetStandings SCHEDULE tableList:", len(tl), "tables")
    for t in tl[:2]:
        print("  keys:", sorted(t.keys()) if isinstance(t, dict) else type(t).__name__)
        print("  header =", short(t.get("header")))
        print("  caption/subCaption =", short(t.get("caption")), short(t.get("subCaption")))
        print("  rows[0] =", short((t.get("rows") or [None])[0]))

if __name__ == "__main__":
    round2()
    sys.exit(0)
    others = probe(LEAGUE, {1, 2})
    print("\nother league ids mentioned:", sorted(others))
    for lg in sorted(others)[:3]:
        try:
            info = get(f"https://www.fantrax.com/fxea/general/getLeagueInfo?leagueId={lg}")
            n = len(info.get("scoringPeriods") or [])
            probe(lg, {1, 18, 19, max(n, 1)})
        except Exception as e:
            print(f"league {lg}: failed ({type(e).__name__})")
