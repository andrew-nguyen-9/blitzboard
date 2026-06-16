"""
news_sentiment.py — RSS + Reddit → news_articles + trending (D2/D3).

Waiver-window batch job: pull recent NFL news (free RSS feeds + r/fantasyfootball),
score each article with the NFL-tuned VADER scorer, resolve which players it's
about, archive everything to `news_articles` (this IS the future FinBERT training
corpus), then compute a blended `trending` signal:

    trend = narrative (news sentiment)  ⊕  behavior (Sleeper add/drop velocity)

Runs every 30 min, 08:00–01:00, on waiver-relevant days only (see workflow).
Network-failure-safe: a dead feed is skipped, not fatal.

Usage:
    python news_sentiment.py
    python news_sentiment.py --no-reddit --max-articles 100
"""
from __future__ import annotations

import argparse
import datetime as dt
import math
import os

from common import console, get_supabase, upsert, fetch_all, retry_api
from models import VaderScorer, PlayerMatcher

# Free RSS feeds (no keys). Add/remove freely.
FEEDS = [
    ("ESPN NFL", "https://www.espn.com/espn/rss/nfl/news"),
    ("PFT", "https://profootballtalk.nbcsports.com/feed/"),
    ("Yahoo NFL", "https://sports.yahoo.com/nfl/rss.xml"),
    ("CBS NFL", "https://www.cbssports.com/rss/headlines/nfl/"),
]
SLEEPER_TRENDING = "https://api.sleeper.app/v1/players/nfl/trending/{kind}?lookback_hours=24&limit=200"


@retry_api
def _get_json(url: str):
    import httpx
    with httpx.Client(timeout=30) as c:
        r = c.get(url)
        r.raise_for_status()
        return r.json()


def fetch_rss(max_articles: int) -> list[dict]:
    import feedparser

    out: list[dict] = []
    for source, url in FEEDS:
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            console.print(f"[yellow]⚠ feed failed {source}: {e}[/yellow]")
            continue
        for e in feed.entries[: max_articles // max(len(FEEDS), 1) + 5]:
            published = None
            if getattr(e, "published_parsed", None):
                published = dt.datetime(*e.published_parsed[:6]).isoformat()
            out.append({
                "source": source,
                "url": e.get("link"),
                "title": e.get("title", ""),
                "body": e.get("summary", "") or e.get("title", ""),
                "published_at": published,
            })
    console.print(f"[cyan]RSS: {len(out)} articles[/cyan]")
    return out[:max_articles]


def fetch_reddit(limit: int = 80) -> list[dict]:
    cid, csec = os.getenv("REDDIT_CLIENT_ID"), os.getenv("REDDIT_CLIENT_SECRET")
    if not cid or not csec:
        console.print("[dim]Reddit creds not set — skipping[/dim]")
        return []
    try:
        import praw
        reddit = praw.Reddit(client_id=cid, client_secret=csec,
                             user_agent=os.getenv("REDDIT_USER_AGENT", "ffdt/0.1"))
        out = []
        for post in reddit.subreddit("fantasyfootball").hot(limit=limit):
            out.append({
                "source": "r/fantasyfootball",
                "url": f"https://reddit.com{post.permalink}",
                "title": post.title,
                "body": (post.selftext or post.title)[:2000],
                "published_at": dt.datetime.utcfromtimestamp(post.created_utc).isoformat(),
            })
        console.print(f"[cyan]Reddit: {len(out)} posts[/cyan]")
        return out
    except Exception as e:
        console.print(f"[yellow]⚠ Reddit fetch failed: {e}[/yellow]")
        return []


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

    articles = fetch_rss(args.max_articles)
    if not args.no_reddit:
        articles += fetch_reddit()

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
