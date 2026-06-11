# Data Sources

| Source | Role | Auth | Cost | Reliability | Notes |
|--------|------|------|------|-------------|-------|
| **Sleeper API** | Player universe, trending adds/drops | None | Free | High | `/v1/players/nfl`, `/v1/players/nfl/trending/{add,drop}`, `/v1/draft/{id}/picks` |
| **nflverse / `nfl_data_py`** | Historical stats, play-by-play, weekly | None | Free | High | Feeds homegrown projections; pip `nfl_data_py` |
| **ESPN Fantasy API** | League rules, rosters, draft feed, league news | Cookies (`espn_s2`+`SWID`) | Free | **Fragile** | Unofficial; `lm-api-reads.fantasy.espn.com`; lib `espn-api`; breaks on ESPN changes |
| **RSS feeds** | News for sentiment | None | Free | Med | ESPN, Rotoworld/NBC, Yahoo, PFF, beat writers |
| **Reddit** | Crowd sentiment / trending | App creds (free) | Free | Med | r/fantasyfootball; PRAW |
| **X/Twitter** | Breaking news | Paid | $$ | — | **Deferred** behind placeholder key |
| **FantasyPros / Sportradar** | Consensus projections, ADP, rankings | API key | $$ | High | **Deferred**; placeholder env keys; ADP scraping as interim consensus |
| **HF Inference Endpoint** | Serve fine-tuned FinBERT | API key | $ | High | **Deferred**; v1 sentiment runs in-Action (VADER) |

## Env keys (`.env.example` — all placeholders, never committed)

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://YOURPROJECT.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# ESPN league (my league; per-user later)
ESPN_LEAGUE_ID=
ESPN_SEASON=2026
ESPN_S2=
ESPN_SWID=

# Reddit (PRAW)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=ffdt/0.1

# Deferred / placeholder
TWITTER_BEARER_TOKEN=
FANTASYPROS_API_KEY=
SPORTRADAR_API_KEY=
HF_ENDPOINT_URL=
HF_API_KEY=

# Optional: Anthropic (one-time weak-labeling of training corpus only, NOT live scoring)
ANTHROPIC_API_KEY=
```

## Consensus rankings/projections — sources to "piggyback" on others' analysis (D6)

Yes — to blend in others' values cleanly, a couple of additions help. Ranked by effort/value:

| Source | Gives us | Auth/Cost | Superflex? | Verdict |
|--------|----------|-----------|-----------|---------|
| **ESPN league API** | ESPN's *own* projections + ranks for rostered/available players | already connected (our cookies) | uses our OP slot → already superflex-correct | **Free win — use first** |
| **Fantasy Football Calculator** | ADP by format (PPR/half/superflex), free JSON | none | **yes** (has superflex ADP) | **Add — free, no key** |
| **FantasyPros** | Consensus expert rankings (ECR), tiers, ADP — the gold standard | API key (paid tiers); site scrape is ToS-gray | **yes** (superflex/2QB ECR) | **Add behind placeholder key**; interim = careful scrape or manual CSV import |
| **Sleeper** (already have) | ADP via draft data, trending | none | derive | already in stack |
| **Articles via our RSS/Reddit pipeline** | expert takes, ranking blurbs | none | n/a | our `SentimentScorer` can extract ranking sentiment; bonus signal |

**Recommendation:** Start consensus with **ESPN projections (free, already have) + FFC ADP
(free, superflex-aware)**. Add **FantasyPros** behind a placeholder key when you want true
expert-consensus ECR (its superflex rankings are the best fix for the OP-slot QB problem).
No paid key required to ship — ESPN + FFC cover the v1 ensemble.

```bash
# add to .env.example (consensus piggyback)
FANTASYPROS_API_KEY=        # optional; expert consensus ECR (superflex variant)
FFC_ENABLED=true            # Fantasy Football Calculator ADP — free, no key
# ESPN projections come through the existing ESPN_* cookies
```

## Sentiment cron schedule (D3)
- Every **30 min**, window **08:00–01:00**, **only on waiver-relevant days**.
- Active-day set is **configurable** (default: Tue + Wed waiver run, plus game days Thu/Sun/Mon).
- Dormant the rest of the week → near-zero cost, no wasted API calls.

## Training corpus strategy (sentiment model)
1. `news_sentiment.py` archives **every** article it ingests → `news_articles` (text + meta + VADER score).
2. Over a season this accumulates a labeled-ish corpus.
3. Bootstrap labels cheaply (VADER, or a *one-time* Anthropic pass) → train FinBERT to imitate at scale.
4. Swap `FinbertScorer` behind the `SentimentScorer` interface; no downstream changes.
