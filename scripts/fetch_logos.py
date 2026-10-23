#!/usr/bin/env python3
"""Fetch the fantasy team logos from Fantrax and store them as data URLs.

Usage: python3 -I scripts/fetch_logos.py data/logos.json
Writes rows {teamId, logo} where logo is a data:image/webp;base64 URL of the
128px logo. The Fantrax login cookie is read from the FANTRAX_COOKIE environment
variable (a GitHub secret in the workflow). On any failure the old file is kept.
"""
import base64, json, os, sys, urllib.request

LEAGUE = "f29oe0zdmv5gs7rl"
UA = {"User-Agent": "Mozilla/5.0 (Wintris dashboard)"}
_cookie = os.environ.get("FANTRAX_COOKIE", "").strip()
if _cookie.lower().startswith("cookie:"):
    _cookie = _cookie[7:].strip()
if _cookie:
    UA["Cookie"] = _cookie


def fantasy_teams():
    body = json.dumps({"msgs": [{"method": "getFantasyTeams", "data": {"leagueId": LEAGUE}}]}).encode()
    req = urllib.request.Request(f"https://www.fantrax.com/fxpa/req?leagueId={LEAGUE}", body, {"Content-Type": "application/json", **UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)
    err = d.get("pageError") or d["responses"][0].get("pageError")
    if err:
        sys.exit(f"Fantrax error: {err.get('code')} (login cookie missing or expired?)")
    return d["responses"][0]["data"]["fantasyTeams"]


def download(url):
    # Logos live on a public image host: no cookie needed.
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=60) as r:
        mime = r.headers.get_content_type() or "image/webp"
        return f"data:{mime};base64," + base64.b64encode(r.read()).decode()


if __name__ == "__main__":
    out = sys.argv[1]
    rows = []
    for t in fantasy_teams():
        url = t.get("logoUrl128") or t.get("logoUrl256")
        if url:
            rows.append({"teamId": t["id"], "logo": download(url)})
    if len(rows) < 12:
        sys.exit(f"Only {len(rows)} logos found; keeping the old file.")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=0)
    print(f"logos: {len(rows)} teams, {sum(len(r['logo']) for r in rows) // 1024} KB")
