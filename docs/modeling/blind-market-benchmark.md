# Blind market draft benchmark

This benchmark asks a narrower and more realistic question than the same-policy v5 harness:

> How does one team using the shipped TypeScript v5 policy perform when every other team drafts
> from an independent historical human-market ranking that cannot see BlitzBoard values?

It is a diagnostic and regression gate. It is not fit, promotion, or proof that a roster will win.

The preregistered 2024 mechanism extension and academic evidence review are documented in
[`recent-era-game-theory-experiments.md`](recent-era-game-theory-experiments.md). Its corrected
campaign artifacts supersede the initial recent-era hashes, but do not replace this benchmark's
three-season aggregate result.

## Authority boundary

- The test seat runs `frontend/lib/draftAI.ts::pickForTeam` with `DEFAULT_POLICY`.
- Eleven or more opponents run `pickHumanAdp`, depending on league size.
- A human opponent can read only player identity, position, provider ADP, its own roster, league
  slots, draft progress, and a seeded random stream.
- It cannot read projection, VOR, replacement level, boom/bust, availability, rank, explanations,
  or any other BlitzBoard score.
- The bridge gives human opponents the complete provider board. It never sends them through
  `candidatePool`, because that function is projection-sorted.
- An adversarial test mutates every model field to extreme, infinite, and NaN values and requires
  the same seeded human pick byte-for-byte. Changing ADP must change strict-provider picks.

The shipped v5 recommendation function is not changed or fitted by this benchmark.

## Market source

The current historical opponent source is Fantasy Football Calculator's aggregate ADP API. It is
free, requires no account, exposes historical 12-team half-PPR and 2QB boards, and includes the
provider sample window and draft count. Each raw response is hashed before use.

| Season | Format | Provider drafts | Raw players | SHA-256 |
|---|---:|---:|---:|---|
| 2018 | half-PPR | 2,414 | 222 | `5c88429b8f386b228edec3f8294018cfe9ddc2ee0634a65930186c598674584e` |
| 2018 | 2QB | 772 | 215 | `842b371b1275dd53dcf3d818aefc17578044a29580b0eb2d61fcb9ec316fe918` |
| 2021 | half-PPR | 3,949 | 222 | `17e4d005383dbc78e7755fbd77d72268b6b34a650df35c215e8491dc42876ac8` |
| 2021 | 2QB | 1,705 | 207 | `bbf6a046e82b4026ae75d6f254453370da704cb7cec27c7b97c3818a9eb672b1` |
| 2024 | half-PPR | 906 | 178 | `078df731fbe26812d59535b5c3339ae96b9cc062cc2239218a4da9d5ddbee7b1` |
| 2024 | 2QB | 3,580 | 212 | `5c60396e524257e5e0c96a9f613791accc6b2043a35c4d4bdb601549a98b87e9` |

This is a human-market proxy, not a claim to reproduce ESPN, Sleeper, or FantasyPros proprietary
recommendation logic.

## Preseason-universe correction

The frozen season fixtures retain the top 260 skill players by *realized* season points. That is
appropriate for their original compact test purpose but creates survivorship bias in a preseason
draft benchmark: a highly drafted player who later missed much of the season can disappear from
the draft pool.

The benchmark corrects that boundary before drafting:

1. Match provider names, suffixes, abbreviated names, K/PK and DEF/DST aliases to fixture IDs.
2. Restore provider-ranked skill players absent from the fixture using current and prior nflverse
   weekly caches.
3. Give restored veterans the repository's existing prior-season per-game projection proxy.
4. Give unmatched rookies a zero projection rather than inventing a vendor forecast.
5. Add the same restored IDs to both the TypeScript draft pool and Python evaluation pool.
6. Record fixture matches, restored players, synthetic IDs, and total preseason-universe coverage.

Coverage is 98.5–99.4% across the six season/format snapshots. Remaining misses are primarily
special-team identity mismatches. No outcome value is used to decide whether a player is draftable.

## Human pick model

`topK=1` reproduces strict provider autopick: earliest legal available ADP. Larger values select
within the best legal `K` candidates using two seeded uniform draws multiplied together. This is
top-heavy: small reaches are common, large reaches are increasingly rare, and nobody can reach
outside the bounded candidate window.

Roster safety is separate from fantasy strategy:

- a bipartite maximum matching over positions and starter slots measures starter capacity;
- when remaining picks equal missing starters, only a player who increases capacity is eligible;
- a roster cannot select a second K or DST;
- all ties, missing ADP, and non-finite ADP use a stable player-ID order;
- identical seeds replay exactly; different seeds create bounded meaningful variation.

The opponent policy does not hard-code zero-RB, hero-RB, QB timing, or any other fantasy strategy.
Those behaviors come from the historical market board.

## Frozen campaign design

The primary campaign contains 864 complete drafts and 6,912 season trajectories:

- seasons: 2018, 2021, 2024;
- league sizes: 10, 12, 14;
- quarterback formats: 1QB, 2QB, superflex;
- bench sizes: 4, 6, 8;
- test seats: deterministic random seat within front, middle, and back thirds;
- four independent seeds per season × scenario × seat band;
- paired opponent widths: `topK` 1, 4, 8, and 12 on the same seed and seat;
- eight availability/injury/waiver trajectories per completed draft.

Every draft records base and derived seed, season, fixture, seat, team count, all selections, pick
trace, elapsed time, evaluator identity, market provenance, outcome metrics, and the explicit
`synthetic_non_authoritative` label.

## Evaluation and statistics

The benchmark uses the current `SeasonEvalResult.started_points` evaluator described in
`docs/modeling/draft-eval.md`: pre-week lock decisions, factorized availability, contested waivers,
paired H2H, and playoff/championship proxies.

Every test team reports:

- roster legality, starter completeness, and duplicate prevention;
- starter strength relative to its league median;
- bench replacement quality and bye/absence coverage;
- contingent-role limitation and upside proxy;
- position counts and redundancy;
- paired H2H, playoff, and championship proxies;
- uncertainty interval, degraded inputs, and model limitations;
- `ACCEPTABLE`, `BORDERLINE`, or `UNACCEPTABLE` classification;
- `winnable` only when the point estimate or uncertainty permits an above-average outcome.

The primary confidence intervals bootstrap independent design cells. Paired top-K arms sharing a
seed and seat are clustered once rather than falsely counted as four independent observations.
Top-K sensitivity deltas are computed within the paired cells.

Predeclared competitive baselines are starter strength 1.0, H2H 0.5, and playoff rate equal to
available playoff slots divided by league size:

- `COMPETITIVE`: all three lower confidence bounds clear baseline;
- `UNDERPERFORMS`: all three upper bounds remain below baseline;
- `INCONCLUSIVE`: otherwise.

## Current result

Evidence hash: `e9ddcafa25e73bdb1884613a89bd0214521cebc14d71a8c506ae320b0207974d`.

| Metric | Result |
|---|---:|
| Legal and duplicate-free drafts | 864 / 864 |
| Mean finish | 8.51 |
| Top-half rate | 27.9% |
| Starter strength | 0.948, clustered CI95 0.937–0.958 |
| Paired H2H | 0.445, clustered CI95 0.432–0.458 |
| Playoff delta | -0.119, clustered CI95 -0.147–-0.088 |
| Championship proxy | 0.046 |
| Classification | 291 acceptable / 446 borderline / 127 unacceptable |
| Verdict | **UNDERPERFORMS** |

Era stability is the main warning: 2018 and 2021 underperform; the 2024 slice clears every
competitive baseline. That means the aggregate is not evidence that the current policy is always
weak, but the method is not robust enough across eras to claim general superiority.

The strongest allocation diagnostic is QB capital. Across all formats, 52.5% of v5's first three
picks are QBs versus 16.3% for the human field. Every evaluated 1QB v5 roster holds more than two
QBs, with a median of three. This is a diagnosis target, not permission to tune on this campaign.
A correction requires a prospective or held-out test to avoid retrospective overfit.

## Metadata degradation and replay

- Two independent 108-draft runs at the same seed produced evidence hash
  `9fe21d683a44dc55c4ff96a3906a093ce9e9920283becd31b2dc808a719c32f0`.
- Randomly removing 10% of opponent ADP creates a paired +0.130 H2H delta for v5 because it weakens
  the field. Removing 30% creates irrational early reaches and is not a realistic comparison.
- Therefore degraded-opponent runs are robustness diagnostics only. They cannot support a claim
  that BlitzBoard became stronger.

## Public methodology boundaries for other products

- ESPN publicly describes a projection process combining statistical work and subjective team,
  coach, player, opportunity-share, and trend judgments. Its documented autopick follows its rank
  order while enforcing roster and position limits. Exact recommendation weights are not public.
- FantasyPros publicly documents Expert Consensus Rankings as a recency- and accuracy-qualified
  aggregation of expert ranks. Individual expert inputs may be visible; the complete product
  recommendation system is not public.
- Sleeper publicly describes ADP as an aggregate of platform mock and real drafts by format. Its
  public API documents league, draft, roster, and player data, not a proprietary expert-pick feed.

References:

- ESPN projections: <https://www.espn.com/fantasy/football/story/_/id/48276085/2026-fantasy-football-projections-draft-rankings-trends-carry-target-shares>
- ESPN autopick: <https://support.espn.com/hc/en-us/articles/360000989651-Autopick-Draft>
- FantasyPros ECR: <https://support.fantasypros.com/hc/en-us/articles/115001219327-What-is-ECR-Expert-Consensus-Rankings-and-how-do-you-calculate-it>
- FantasyPros accuracy: <https://www.fantasypros.com/about/faq/football-draft-accuracy-methodology/>
- Sleeper ADP: <https://sleeper.com/blog/what-does-adp-mean-in-fantasy-football/>
- Sleeper API: <https://docs.sleeper.com/>

## Reproduce

Save the six provider responses under one directory as
`ffc-{half-ppr|2qb}-{2018|2021|2024}.json`, then run:

```sh
cd engine
PYTHONPATH=. ../pipeline/.venv/bin/python -m blitz_engine.backtest.blind_market \
  --market-dir /path/to/frozen-market-snapshots \
  --weekly-dir ../pipeline/backtest/data \
  --base-seed 20260828 \
  --repetitions 4 \
  --top-k 1 --top-k 4 --top-k 8 --top-k 12 \
  --seasons-per-draft 8 \
  --output ../artifacts/blind-market/c09-full.json
```

The output includes a timing-independent SHA-256. Recalculation must match before evidence is used.
