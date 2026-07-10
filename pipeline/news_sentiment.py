"""
news_sentiment.py — RSS + Reddit → news_articles + trending (D2/D3).

Waiver-window batch job: pull recent NFL news (free RSS feeds + r/fantasyfootball),
score each article with the NFL-tuned VADER scorer, resolve which players it's
about, archive everything to `news_articles` (this IS the future FinBERT training
corpus), then compute a blended `trending` signal:

    trend = narrative (news sentiment)  ⊕  behavior (Sleeper add/drop velocity)

SOURCES (all free, no key — the $0 refresh; see docs/architecture/DATA_SOURCES.md):
    RSS   — ESPN, ProFootballTalk, Yahoo, CBS, FantasyPros, NFL.com
    Reddit— r/fantasyfootball + r/nfl via PUBLIC .rss (keyless). The richer praw
            path (self-text, hot ranking) is an OPTIONAL keyed source that only
            joins the run when REDDIT_CLIENT_ID/SECRET are set — absent ⇒ skipped.

CADENCE: every 30 min, 08:00–01:00, on waiver-relevant days (news-refresh workflow
step; see .github/workflows/etl_daily.yml). Idempotent — `news_articles` dedupes on
`url`, `trending` is a replaced snapshot; re-running writes no partial/dup rows.

DEGRADE / STALE-FALLBACK (E6): each source runs through `collect()` in the F2
adapter shape (fetch → normalize, degrade-safe). A source that RAISES or returns
nothing falls back to its last-good batch cached on disk (`.news_cache.json`);
a fresh pull refreshes that cache. One dead source can NEVER fail the run.

Usage:
    python news_sentiment.py
    python news_sentiment.py --no-reddit --max-articles 100
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import os
from collections import namedtuple

from common import console, get_supabase, upsert, fetch_all, retry_api
from models import VaderScorer, PlayerMatcher

# Free RSS feeds (no keys). Keyless Reddit rides in as public `.rss`. Add/remove freely.
FEEDS = [
    ("ESPN NFL", "https://www.espn.com/espn/rss/nfl/news"),
    ("PFT", "https://profootballtalk.nbcsports.com/feed/"),
    ("Yahoo NFL", "https://sports.yahoo.com/nfl/rss.xml"),
    ("CBS NFL", "https://www.cbssports.com/rss/headlines/nfl/"),
    ("FantasyPros", "https://www.fantasypros.com/nfl/rss/news.php"),
    ("NFL.com", "https://www.nfl.com/feeds/rss/news"),
    ("r/fantasyfootball", "https://www.reddit.com/r/fantasyfootball/.rss"),
    ("r/nfl", "https://www.reddit.com/r/nfl/.rss"),
]
SLEEPER_TRENDING = "https://api.sleeper.app/v1/players/nfl/trending/{kind}?lookback_hours=24&limit=200"

# Stale-fallback store: last-good articles per source, so a down source degrades
# to its previous batch instead of vanishing (or crashing) the run.
STALE_CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".news_cache.json")

# One news source in the F2 adapter shape: a `name` + a `fetch()` that returns
# already-normalized article dicts. `collect()` wraps it with the degrade contract.
NewsSource = namedtuple("NewsSource", "name fetch")


@retry_api
def _get_json(url: str):
    import httpx
    with httpx.Client(timeout=30) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.json()


def _normalize_entry(source: str, e) -> dict:
    """Pure: one feed entry → one article row (dict-friendly, no network)."""
    published = None
    pp = e.get("published_parsed") or e.get("updated_parsed")
    if pp:
        published = dt.datetime(*pp[:6]).isoformat()
    return {
        "source": source,
        "url": e.get("link"),
        "title": e.get("title", ""),
        "body": e.get("summary", "") or e.get("title", ""),
        "published_at": published,
    }


def _rss_fetcher(source: str, url: str, cap: int):
    """Build a keyless RSS `fetch()` for one feed (Reddit `.rss` included)."""
    def fetch() -> list[dict]:
        import feedparser
        feed = feedparser.parse(url)
        return [_normalize_entry(source, e) for e in feed.entries[:cap]]
    return fetch


def _reddit_praw_fetcher(limit: int = 80):
    """OPTIONAL keyed source: richer Reddit via praw. Keyless ⇒ returns [] so the
    public `.rss` source above still covers Reddit (degrade, not error)."""
    def fetch() -> list[dict]:
        cid, csec = os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
        if not cid or not csec:
            return []
        import praw
        reddit = praw.Reddit(client_id=cid, client_secret=csec,
                             user_agent=os.getenv("REDDIT_USER_AGENT", "ffdt/0.1"))
        out = []
        for post in reddit.subreddit("fantasyfootball").hot(limit=limit):
            out.append({
                "source": "r/fantasyfootball (praw)",
                "url": f"https://reddit.com{post.permalink}",
                "title": post.title,
                "body": (post.selftext or post.title)[:2000],
                "published_at": dt.datetime.utcfromtimestamp(post.created_utc).isoformat(),
            })
        return out
    return fetch


def build_sources(max_articles: int, use_reddit: bool = True) -> list[NewsSource]:
    """Assemble the degrade-safe source list in the F2 adapter shape."""
    cap = max_articles // max(len(FEEDS), 1) + 5
    srcs = [NewsSource(name, _rss_fetcher(name, url, cap)) for name, url in FEEDS]
    if use_reddit:
        srcs.append(NewsSource("r/fantasyfootball (praw)", _reddit_praw_fetcher()))
    return srcs


def _load_cache() -> dict:
    try:
        with open(STALE_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save_cache(cache: dict) -> None:
    try:
        with open(STALE_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f)
    except OSError as e:  # cache is best-effort; a write failure never fails the run
        console.print(f"[dim]news cache write skipped: {e}[/dim]")


def collect(sources: list[NewsSource], cache: dict) -> list[dict]:
    """Run every source degrade-safe with stale-fallback (E6).

    A source that RAISES or returns nothing falls back to its last-good cached
    batch; a source with fresh results refreshes the cache. Never raises — one
    dead source can't fail the run. `cache` is mutated in place (persist via
    `_save_cache`)."""
    out: list[dict] = []
    for src in sources:
        try:
            arts = src.fetch() or []
        except Exception as e:
            console.print(f"[yellow]⚠ {src.name} down: {e}[/yellow]")
            arts = []
        if arts:
            cache[src.name] = arts  # fresh pull → new last-good
        else:
            arts = cache.get(src.name, [])
            if arts:
                console.print(f"[dim]{src.name}: no fresh pull — {len(arts)} stale (last-good)[/dim]")
        out.extend(arts)
    console.print(f"[cyan]collected {len(out)} articles across {len(sources)} sources[/cyan]")
    return out


def compute_trending(sb, article_rows: list[dict], players: list[dict]) -> list[dict]:
    """Blend news sentiment with Sleeper add/drop velocity → trend_score."""
    sleeper_to_id = {str(p["sleeper_id"]): p["id"] for p in players if p.get("sleeper_id")}

    # behavior: Sleeper adds/drops
    adds, drops = {}, {}
    try:
        for d in _get_json(SLEEPER_TRENDING.format(kind="add")):
            pid = sleeper_to_id.get(str(d["player_id"]))
            if pid:
                adds[pid] = d.get("count", 0)
        for d in _get_json(SLEEPER_TRENDING.format(kind="drop")):
            pid = sleeper_to_id.get(str(d["player_id"]))
            if pid:
                drops[pid] = d.get("count", 0)
    except Exception as e:
        console.print(f"[yellow]⚠ Sleeper trending failed: {e}[/yellow]")

    # narrative: average sentiment per player across this run's articles
    sent_sum: dict[str, float] = {}
    sent_n: dict[str, int] = {}
    injured: set[str] = set()
    for a in article_rows:
        for pid in a.get("player_ids", []):
            sent_sum[pid] = sent_sum.get(pid, 0.0) + (a.get("sentiment") or 0.0)
            sent_n[pid] = sent_n.get(pid, 0) + 1
            if a.get("injury_flag"):
                injured.add(pid)

    now = dt.datetime.utcnow().isoformat()
    rows = []
    for pid in set(adds) | set(drops) | set(sent_sum):
        a, d = adds.get(pid, 0), drops.get(pid, 0)
        sent_avg = (sent_sum[pid] / sent_n[pid]) if pid in sent_n else 0.0
        # behavior signal in [-1,1] via tanh of net add velocity
        behavior = math.tanh((a - d) / 300.0)
        trend = round(0.55 * behavior + 0.45 * sent_avg - (0.25 if pid in injured else 0.0), 4)
        rows.append({
            "player_id": pid, "window_start": now,
            "sleeper_adds": a, "sleeper_drops": d,
            "sentiment_avg": round(sent_avg, 4), "trend_score": trend,
        })
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="Score NFL news + compute trending.")
    ap.add_argument("--max-articles", type=int, default=200)
    ap.add_argument("--no-reddit", action="store_true")
    args = ap.parse_args()

    sb = get_supabase()
    if sb is None:
        console.print("[red]Supabase not configured.[/red]")
        return

    players = fetch_all("players", "id,full_name,sleeper_id,position,nfl_team")
    matcher = PlayerMatcher(players)
    scorer = VaderScorer()

    cache = _load_cache()
    sources = build_sources(args.max_articles, use_reddit=not args.no_reddit)
    articles = collect(sources, cache)[: args.max_articles]
    _save_cache(cache)

    rows = []
    for a in articles:
        if not a.get("url"):
            continue
        text = f"{a['title']} . {a['body']}"
        res = scorer.score(text)
        pids = list(matcher.match(text))
        rows.append({
            "source": a["source"], "url": a["url"], "title": a["title"][:500],
            "body": a["body"][:4000], "published_at": a["published_at"],
            "player_ids": pids, "sentiment": res.sentiment,
            "injury_flag": res.injury_flag, "opportunity_flag": res.opportunity_flag,
            "scorer": scorer.name,
        })
    console.print(f"[cyan]scored {len(rows)} articles · "
                  f"{sum(1 for r in rows if r['player_ids'])} matched ≥1 player[/cyan]")
    upsert("news_articles", rows, on_conflict="url")  # corpus grows; url dedupes

    trend_rows = compute_trending(sb, rows, players)
    # trending is a current snapshot → replace
    sb.table("trending").delete().not_.is_("id", "null").execute()
    upsert("trending", trend_rows, on_conflict="id")
    console.print(f"[green]✓ trending computed for {len(trend_rows)} players[/green]")
    top = sorted(trend_rows, key=lambda r: r["trend_score"], reverse=True)[:8]
    id_to_name = {p["id"]: p["full_name"] for p in players}
    for r in top:
        console.print(f"   {id_to_name.get(r['player_id'],'?'):<24} "
                      f"trend {r['trend_score']:+.2f} (adds {r['sleeper_adds']}, sent {r['sentiment_avg']:+.2f})")


if __name__ == "__main__":
    main()
