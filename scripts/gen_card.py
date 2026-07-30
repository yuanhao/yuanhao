#!/usr/bin/env python3
"""Generate the profile stats card (dark + light) from live GitHub data.

Stdlib only. Reads GITHUB_TOKEN from the environment when present — required in
CI for rate limits, optional locally for public data.

    python3 scripts/gen_card.py            # writes assets/card.svg + card-light.svg
"""
import json
import os
import sys
import urllib.error
import urllib.request

USER = "yuanhao"
ORGS = ["yologdev"]

# Curated rather than top-N-by-stars: this is a shopfront, not a leaderboard.
# Order is deliberate. Descriptions are written for this card, not pulled from
# the repo, so they stay short enough to fit.
FEATURED = [
    ("yologdev/yoyo-evolve", "A coding agent that evolves its own source, in public"),
    ("yologdev/yoagent", "The agent loop for Rust — 7 protocols, tools, MCP"),
    ("yologdev/yopedia", "A wiki for humans and agents to read and write"),
    ("yologdev/yoclaw", "OpenClaw reborn in Rust — an agent that remembers you"),
    ("yologdev/gasp", "Git Agent State Protocol — the repo is the agent"),
]

STAR_FLOOR = 10   # below this, the count is omitted rather than printed small
API = "https://api.github.com"
FONT = "'SF Mono', 'Fira Code', 'Cascadia Code', 'Menlo', 'Courier New', monospace"

DARK = dict(
    bg1="#0f0f1a", bg2="#1a1a2e", card="#0f172a", stroke="#334155",
    text="#e2e8f0", dim="#94a3b8", faint="#64748b",
    accent="#a855f7", star="#eab308", rule="#1e293b",
)
LIGHT = dict(
    bg1="#ffffff", bg2="#f8fafc", card="#f8fafc", stroke="#cbd5e1",
    text="#0f172a", dim="#475569", faint="#64748b",
    accent="#7c3aed", star="#ca8a04", rule="#e2e8f0",
)


def api(path):
    req = urllib.request.Request(f"{API}{path}", headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{USER}-profile-card",
    })
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"GitHub API {e.code} on {path}: {e.read()[:200].decode(errors='replace')}")


def all_repos(owner):
    """Works for both account types — `yologdev` is a User, not an Organization,
    and /orgs/{}/repos 404s on a user. Detect rather than assume."""
    kind = "orgs" if api(f"/users/{owner}")["type"] == "Organization" else "users"
    out, page = [], 1
    while True:
        batch = api(f"/{kind}/{owner}/repos?per_page=100&page={page}")
        out += batch
        if len(batch) < 100:
            return [r for r in out if not r["private"]]
        page += 1


def human(n):
    return f"{n/1000:.1f}K".replace(".0K", "K") if n >= 1000 else str(n)


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def collect():
    user = api(f"/users/{USER}")
    repos = [r for r in all_repos(USER) if not r["fork"] and not r["archived"]]
    for o in ORGS:
        repos += [r for r in all_repos(o) if not r["fork"] and not r["archived"]]

    by_name = {r["full_name"]: r for r in repos}
    featured = []
    for full, blurb in FEATURED:
        r = by_name.get(full)
        if r is None:
            print(f"  warn: {full} not found or archived — skipping", file=sys.stderr)
            continue
        featured.append((full.split("/")[1], r["stargazers_count"], blurb))

    return dict(
        name=user.get("name") or USER,
        login=user["login"],
        followers=user["followers"],
        stars=sum(r["stargazers_count"] for r in repos),
        repos=len(repos),
        featured=featured,
    )


def build(d, c):
    W, H = 900, 300 + 62 * len(d["featured"])
    L = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        "  <style>",
        f"    text {{ font-family: {FONT}; fill: {c['text']}; }}",
        "    .name { font-size: 30px; font-weight: 700; }",
        f"    .tag  {{ font-size: 13px; fill: {c['dim']}; }}",
        "    .num  { font-size: 27px; font-weight: 700; }",
        f"    .lbl  {{ font-size: 12px; fill: {c['dim']}; }}",
        f"    .hdr  {{ font-size: 12px; font-weight: 700; fill: {c['faint']}; letter-spacing: 0.12em; }}",
        "    .repo { font-size: 15px; font-weight: 700; }",
        f"    .desc {{ font-size: 12px; fill: {c['dim']}; }}",
        f"    .star {{ font-size: 13px; font-weight: 700; fill: {c['star']}; }}",
        "  </style>",
        "  <defs>",
        '    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">',
        f'      <stop offset="0%" stop-color="{c["bg1"]}"/>',
        f'      <stop offset="100%" stop-color="{c["bg2"]}"/>',
        "    </linearGradient>",
        "  </defs>",
        f'  <rect width="{W}" height="{H}" rx="14" fill="url(#bg)"/>',
        f'  <rect x="0.5" y="0.5" width="{W-1}" height="{H-1}" rx="14" fill="none" stroke="{c["stroke"]}"/>',
        f'  <text class="name" x="44" y="66">{esc(d["name"])}</text>',
        f'  <text class="tag"  x="44" y="90">@{esc(d["login"])} · I build agent infrastructure in Rust.</text>',
    ]

    for i, (num, lbl) in enumerate([
        (human(d["stars"]), "Stars"),
        (str(d["repos"]), "Repositories"),
        (str(d["followers"]), "Followers"),
    ]):
        x = 44 + i * 200
        L.append(f'  <text class="num" x="{x}" y="{150}">{num}</text>')
        L.append(f'  <text class="lbl" x="{x}" y="{171}">{lbl}</text>')

    L.append(f'  <line x1="44" y1="205" x2="{W-44}" y2="205" stroke="{c["rule"]}"/>')
    L.append('  <text class="hdr" x="44" y="238">WHAT I\'M BUILDING</text>')

    y = 278
    for name, stars, blurb in d["featured"]:
        L.append(f'  <text class="repo" x="44" y="{y}">{esc(name)}</text>')
        # Right-aligned so the counts form a column instead of trailing raggedly
        # off names of different lengths. Counts below STAR_FLOOR are omitted —
        # a project earns its place here on what it is, and printing a small
        # number next to it just draws the eye to the small number.
        if stars >= STAR_FLOOR:
            L.append(f'  <text class="star" x="{W-44}" y="{y}" text-anchor="end">★ {human(stars)}</text>')
        L.append(f'  <text class="desc" x="44" y="{y + 20}">{esc(blurb)}</text>')
        y += 62

    L.append("</svg>")
    return "\n".join(L)


if __name__ == "__main__":
    data = collect()
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out = os.path.join(here, "assets")
    os.makedirs(out, exist_ok=True)
    for suffix, theme in (("", DARK), ("-light", LIGHT)):
        p = os.path.join(out, f"card{suffix}.svg")
        with open(p, "w") as f:
            f.write(build(data, theme))
        print("wrote", p)
    print(f"  {data['stars']} stars · {data['repos']} repos · {data['followers']} followers")
