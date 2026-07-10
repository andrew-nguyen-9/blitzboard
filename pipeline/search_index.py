"""Sitewide search index builder (Epic 9a).

Refreshes `public.search_index` (one ranked row per searchable entity) and
`public.search_meta` (a Bloom filter over the corpus trigrams for the client
membership pre-check). Idempotent: upserts by (entity_type, entity_id), so a
re-run overwrites in place and writes zero partial rows when Supabase is unset
(common.upsert dry-runs). Degrade contract: any empty/absent source simply
contributes no rows — the index is whatever data exists.

Entities:
  * team    — the 32 NFL teams (static, public; mirrors frontend/lib/teams.ts)
  * player  — public.players            → /players/<id>
  * news    — public.news_articles      → article url
  * article — public.articles (E9b)     → indexed ONLY if the table exists;
              silently skipped this wave if E9b hasn't landed.

The Bloom filter and its trigram tokenizer are byte-for-byte identical to the
TS side (frontend/lib/search.ts) so a filter built here reads correctly there:
same normalization, same 3-gram window, same FNV-1a hashing, same LSB-first bit
packing. See that file's header for the pre-check semantics.
"""
from __future__ import annotations

import base64
import math
import re

from common import console, fetch_all, upsert

# ------------------------------------------------------------------
# Per-type rank multipliers (few, high-signal teams float above noise).
# ------------------------------------------------------------------
WEIGHTS = {"team": 1.3, "player": 1.0, "article": 0.8, "news": 0.6}

# 32 NFL teams — abbr matches Sleeper/ESPN codes used across the app
# (frontend/lib/teams.ts owns logo remaps; this is the search-side mirror).
NFL_TEAMS: list[tuple[str, str, str]] = [
    ("ARI", "Arizona", "Cardinals"), ("ATL", "Atlanta", "Falcons"),
    ("BAL", "Baltimore", "Ravens"), ("BUF", "Buffalo", "Bills"),
    ("CAR", "Carolina", "Panthers"), ("CHI", "Chicago", "Bears"),
    ("CIN", "Cincinnati", "Bengals"), ("CLE", "Cleveland", "Browns"),
    ("DAL", "Dallas", "Cowboys"), ("DEN", "Denver", "Broncos"),
    ("DET", "Detroit", "Lions"), ("GB", "Green Bay", "Packers"),
    ("HOU", "Houston", "Texans"), ("IND", "Indianapolis", "Colts"),
    ("JAX", "Jacksonville", "Jaguars"), ("KC", "Kansas City", "Chiefs"),
    ("LAC", "Los Angeles", "Chargers"), ("LAR", "Los Angeles", "Rams"),
    ("LV", "Las Vegas", "Raiders"), ("MIA", "Miami", "Dolphins"),
    ("MIN", "Minnesota", "Vikings"), ("NE", "New England", "Patriots"),
    ("NO", "New Orleans", "Saints"), ("NYG", "New York", "Giants"),
    ("NYJ", "New York", "Jets"), ("PHI", "Philadelphia", "Eagles"),
    ("PIT", "Pittsburgh", "Steelers"), ("SEA", "Seattle", "Seahawks"),
    ("SF", "San Francisco", "49ers"), ("TB", "Tampa Bay", "Buccaneers"),
    ("TEN", "Tennessee", "Titans"), ("WAS", "Washington", "Commanders"),
]

# ==================================================================
# Bloom filter — MUST stay in lockstep with frontend/lib/search.ts.
# ==================================================================
_NORM_RE = re.compile(r"[^a-z0-9]+")


def normalize(s: str | None) -> str:
    """Lowercase, non-alphanumerics → single space, trim. Identical in TS."""
    if not s:
        return ""
    return _NORM_RE.sub(" ", s.lower()).strip()


def trigrams(s: str) -> set[str]:
    """Set of length-3 sliding-window substrings of the normalized string.
    Internal 3-grams are a subset of pg_trgm's word trigrams, so shared grams
    guarantee a shared pg_trgm trigram → the pre-check never drops a real hit."""
    n = normalize(s)
    return {n[i : i + 3] for i in range(len(n) - 2)} if len(n) >= 3 else set()


def _fnv1a(data: bytes) -> int:
    h = 0x811C9DC5
    for b in data:
        h ^= b
        h = (h * 0x01000193) & 0xFFFFFFFF
    return h


def _positions(gram: str, m: int, k: int) -> list[int]:
    """Kirsch–Mitzenmacher double hashing → k bit positions."""
    data = gram.encode("utf-8")
    h1 = _fnv1a(data)
    h2 = _fnv1a(b"\x00" + data) | 1  # odd, so it strides the whole range
    return [(h1 + i * h2) % m for i in range(k)]


def build_bloom(grams: set[str], p: float = 0.01) -> dict:
    """Pack `grams` into a Bloom filter blob for search_meta (base64 bits)."""
    n = len(grams)
    if n == 0:
        return {"key": "trgm_bloom", "m": 8, "k": 1, "n": 0, "bits": base64.b64encode(b"\x00").decode()}
    m = max(8, math.ceil(-(n * math.log(p)) / (math.log(2) ** 2)))
    m = ((m + 7) // 8) * 8  # byte-align for packing
    k = max(1, round((m / n) * math.log(2)))
    bits = bytearray(m // 8)
    for gram in grams:
        for pos in _positions(gram, m, k):
            bits[pos >> 3] |= 1 << (pos & 7)  # LSB-first
    return {"key": "trgm_bloom", "m": m, "k": k, "n": n, "bits": base64.b64encode(bytes(bits)).decode()}


# ==================================================================
# Source → rows
# ==================================================================
def _row(entity_type: str, entity_id: str, label: str, sublabel: str | None, url: str, *aliases: str) -> dict:
    haystack = " ".join(normalize(x) for x in (label, sublabel or "", *aliases) if x)
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "label": label,
        "sublabel": sublabel,
        "url": url,
        "search_text": haystack,
        "weight": WEIGHTS[entity_type],
    }


def team_rows() -> list[dict]:
    out = []
    for abbr, city, name in NFL_TEAMS:
        out.append(_row("team", abbr, f"{city} {name}", "NFL team", f"/players?team={abbr}", abbr, name))
    return out


def player_rows() -> list[dict]:
    rows = fetch_all("players", "id,full_name,position,nfl_team,search_name")
    out = []
    for p in rows:
        pid = p.get("id")
        name = p.get("full_name")
        if not pid or not name:
            continue
        sub = " · ".join(x for x in (p.get("position"), p.get("nfl_team")) if x) or None
        out.append(_row("player", pid, name, sub, f"/players/{pid}", p.get("search_name") or "", p.get("nfl_team") or ""))
    return out


def news_rows() -> list[dict]:
    rows = fetch_all("news_articles", "id,title,url,source")
    out = []
    for a in rows:
        aid, title = a.get("id"), a.get("title")
        if not aid or not title:
            continue
        out.append(_row("news", aid, title, a.get("source"), a.get("url") or f"/#news-{aid}"))
    return out


def article_rows() -> list[dict]:
    """E9b's articles — indexed only if that table exists yet. Any error
    (missing table / column) degrades to no article rows this wave."""
    try:
        rows = fetch_all("articles", "id,title,slug,summary")
    except Exception as e:  # table absent until E9b lands
        console.print(f"[dim]articles source unavailable ({type(e).__name__}) — skipping (E9b not landed)[/dim]")
        return []
    out = []
    for a in rows:
        aid, title = a.get("id"), a.get("title")
        if not aid or not title:
            continue
        slug = a.get("slug") or aid
        out.append(_row("article", str(aid), title, "Article", f"/articles/{slug}", a.get("summary") or ""))
    return out


def build() -> tuple[list[dict], dict]:
    """Assemble every entity row + the Bloom filter over their trigrams."""
    rows = team_rows() + player_rows() + news_rows() + article_rows()
    grams: set[str] = set()
    for r in rows:
        grams |= trigrams(r["search_text"])
    return rows, build_bloom(grams)


def main() -> None:
    rows, bloom = build()
    by_type: dict[str, int] = {}
    for r in rows:
        by_type[r["entity_type"]] = by_type.get(r["entity_type"], 0) + 1
    console.print(f"[bold]search_index[/bold]: {by_type or 'empty'} · bloom n={bloom['n']} m={bloom['m']} k={bloom['k']}")
    upsert("search_index", rows, on_conflict="entity_type,entity_id")
    upsert("search_meta", [bloom], on_conflict="key")


if __name__ == "__main__":
    main()
