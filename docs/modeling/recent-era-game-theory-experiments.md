# Recent-era game-theory experiments

Status: preregistered before campaign execution. These experiments are synthetic diagnostics, not
fit, promotion, or permission to change the shipped v5 policy.

## Result

The corrected campaign completed 1,800 drafts and 28,800 season trajectories. Every draft was
legal and duplicate-free. Two additional 18-draft/72-trajectory replay campaigns produced the same
evidence hash: `c888bd7cdfde0d8419f818dca1640a7a0876823efd5afe8931ba9f40db898f6a`.

The 360-draft shipped-v5 baseline is **COMPETITIVE for the 2024 fixture only**:

| Metric | Estimate | Clustered CI95 |
|---|---:|---:|
| Starter strength versus league median | 1.028 | 1.020–1.036 |
| Paired H2H | 0.532 | 0.523–0.542 |
| Playoff delta versus league baseline | +0.079 | +0.053–+0.106 |
| Mean finish | 5.23 | — |
| Top-half rate | 68.6% | — |

This does not override the three-season aggregate `UNDERPERFORMS` result. It is evidence of era
instability: the current policy performs materially better on the latest canonical fixture than on
2018 or 2021.

Preregistered paired results use treatment minus reference. H1-H3 use 98.33% intervals.

| Question | Paired H2H delta | Interval | Conclusion |
|---|---:|---:|---|
| H1 shipped minus no run depletion | +0.0109 | +0.0054–+0.0170 | Supported; starter strength, playoff delta, and finish rank also improve |
| H2 shipped minus no handcuff amplification | 0.0000 | 0.0000–0.0000 | The 1.6× amplification is behaviorally inert in this campaign |
| H3 one-QB depth 2 minus shipped depth 3 | +0.0088 | +0.0026–+0.0154 | Supported within 2024; legal and duplicate-free, with no conclusive playoff harm |
| H4 heterogeneous minus homogeneous opponents | +0.0008 | -0.0096–+0.0121 | Passes the preregistered -0.01 noninferiority margin narrowly |

H1 changed 40 of 360 test-team drafts. Post-hoc inspection found all changes in 1QB leagues; no
2QB or superflex pick changed. H3 changed 156 of 180 test-team drafts. It reduced average 1QB
quarterbacks from 3.59 to 3.07 and shifted 94 selections from QB into 45 RB, 31 WR, and 18 TE
selections. These mechanism counts are diagnostic, not additional confirmatory tests.

H2's exact zero is narrower than “handcuffing never works”: this coefficient did not cross a pick
decision boundary in the tested population. H4's bound is close to its margin and should be
retested on the next canonical season.

Authoritative corrected hashes:

- baseline: `6cb5d5fdd9976241308c7b6a3b583aefcda78ca09b6d38e469121474f3cd2cc5`;
- no-run ablation: `a969ed856194295f926c099d918d0889b1ea631966b73627e669ae82e2ad3df9`;
- no-handcuff-amplification: `02d6c286e0ce7012ce43e5b183fdbfde85d8bb0b2f24188e35c9043951c245c6`;
- heterogeneous field: `eb47d518be5de666082a36e761d7bf9bbdd889a7ad114ebc672d6580419524ce`;
- 1QB reference: `ad3b292d63ceaae7c12b7fa287f3a04111482eaed73b8444f5b1db8ec31bb9b8`;
- 1QB depth-2 candidate: `9c62819f4472b0ae731fd9221f8bf937182287ac87b728730a006f60c2002947`;
- paired effects: `57ccc8652273bd168478836df4221a130e1e639ab2a7c7f65d83836d51fb1c0d`;
- post-hoc subgroups: `9c88794b61fdf2cf37e93f130094df2c4bb9f927010e8a10c6e2b512b73dfccb`.

### Identity correction

The first campaign exposed a provider nickname mismatch: `Hollywood Brown` did not join the weekly
identity `Marquise Brown`. That gave him zero prior projection and omitted his current outcome.
The shared normalization boundary now has a tested alias, restoring his 151.2-point prior proxy and
2024 weekly record. All campaigns were rerun under `-v2` artifact names. The old hashes are
superseded. J.J. McCarthy remains the only 2024 synthetic player because he had no prior NFL history
or regular-season snap; that limitation is recorded rather than filled with future information.

## Decision ledger

Three options were considered:

1. Train a reinforcement-learning drafting agent. Rejected: no trustworthy current human-draft
   training corpus or untouched multi-season holdout exists, so added complexity would overfit.
2. Add paired ablations and opponent mixtures to the existing blind-market harness. Selected: it
   reuses the production picker, frozen market inputs, evaluator, and deterministic replay boundary.
3. Scrape proprietary ESPN, Sleeper, and FantasyPros recommendations. Rejected: their complete
   recommendation methods and historical decision feeds are not public, and fabricated parity is
   worse than an honest market proxy.

The latest repository-authoritative outcome fixture is 2024. It is the primary recent-era slice.
2018 and 2021 remain distribution-shift stress tests. A 2025 claim is prohibited until a canonical
2025 fixture and preseason information set are added through the normal data pipeline.

## Preregistered questions

All campaigns use frozen 2024 Fantasy Football Calculator ADP, the same derived seed and test seat
within each pair, 10/12/14-team 1QB/2QB/superflex scenarios, front/middle/back seat bands, 20
repetitions per cell, and 16 season trajectories per completed draft. The baseline opponent uses
`topK=8`. Primary effects are paired by derived seed and scenario. Policy-family intervals use
98.33% confidence (Bonferroni family-wise 5% across H1-H3); opponent robustness uses 95%.

- **H1 — positional-run value:** shipped v5 versus `runDepletion=1`. The term helps only if shipped
  v5 has a positive paired H2H effect and neither starter strength nor playoff delta is conclusively
  worse.
- **H2 — handcuff amplification:** shipped v5 versus `handcuffAmplify=1`. Either sign may be
  conclusive; an interval spanning zero is no evidence. This tests only the incremental same-team
  amplification, not all contingent-role value.
- **H3 — one-QB depth correction:** candidate `overfillDepth.QB=2` versus shipped depth 3 in 1QB
  scenarios only. It helps only if paired H2H improves, legal-roster rate remains 100%, and starter
  strength and playoff delta are not conclusively worse.
- **H4 — heterogeneous opponents:** shipped v5 against opponents whose fixed seat profiles rotate
  through `topK=1,4,8,12`, versus a homogeneous `topK=8` field. Robustness requires the lower 95%
  bound of the paired H2H delta to exceed -0.01 and no legality or duplication regression.

No result may be called generally optimal. The 2024 player outcomes are shared across experiments,
so H1-H3 are within-season mechanism tests, not out-of-era generalization.

## Evidence quality

| Source | Grade | Legitimate use | Boundary |
|---|---|---|---|
| Lee & Liu, *Judgment and Decision Making* (2022/2023), DOI 10.1017/S1930297500008901 | A | Direct evidence from 1,350 Sleeper leagues that humans use narrow roster strategies and sometimes react to the immediately preceding positional pick | One platform and 2017; cannot supply current effect sizes |
| Becker & Sun, *Journal of Quantitative Analysis in Sports* (2016), DOI 10.1515/jqas-2013-0009 | A- | Treat the draft as sequential robust optimization under uncertain opponent choices and optimize season wins, not raw points alone | Older assumptions and data; no evidence that its exact policy wins now |
| Fry, Lundberg & Ohlmann, *JQAS* (2007), DOI 10.2202/1559-0410.1050 | B+ | Opponent behavior and future availability belong in player choice; deterministic approximations can make the state space tractable | 2005 fantasy experiment and strong opponent-model assumptions |
| Haugh & Singal, *Management Science* (2020), DOI 10.1287/mnsc.2019.3528 | A- | Explicitly model opponents, correlation, and payoff shape rather than maximize expected points alone | Daily fantasy portfolio problem, not a snake season-long draft |
| Gneiting & Raftery, *JASA* (2007), DOI 10.1198/016214506000001437 | A | Evaluate probabilistic projections with proper scores, calibration, sharpness, and interval coverage | Methodological transfer; it does not define fantasy strategy |
| Bergmeir, Hyndman & Koo, *Computational Statistics & Data Analysis* (2018), DOI 10.1016/j.csda.2017.11.003 | A- | Time ordering and residual dependence matter in forecast validation | Time-series validation result, not fantasy-specific |
| Batchelor & Dua, *Management Science* (1995), DOI 10.1287/mnsc.41.1.68 | B+ | Diverse forecast combinations can reduce error variance | Does not show that any particular vendor blend improves NFL forecasts |

Grades reflect peer review, directness, reproducibility, recency, and transportability to this exact
snake-draft decision. Academic publication is evidence for a method, not authority for a coefficient.

## Factors not promoted to experiments

- **Reinforcement learning / Nash claims:** insufficient current repeated-game training data and no
  stable equilibrium guarantee when opponent strategies change.
- **Vendor consensus blending:** promising, but historical point-in-time ESPN/Sleeper/FantasyPros
  inputs are absent. Current pages cannot be backfilled without leakage.
- **Projection calibration:** required before using boom/bust probabilities as calibrated beliefs.
  The current fixture has proxies, not archived predictive distributions, so CRPS/Brier claims would
  be invalid.
- **NFL-team stacking:** correlation can improve a top-heavy payoff for an underdog, but season-long
  lineup, bye, and injury effects differ from DFS. It needs a separate causal policy and holdout.
- **Handcuffing as doctrine:** Lee & Liu found little use and no clear win benefit. Only the existing
  amplification is ablated; no new handcuff strategy is introduced.

## Next conclusive data additions

1. Add an authoritative 2025 fixture and point-in-time preseason inputs, then replay H1/H3/H4
   unchanged. This is the required temporal holdout before a policy change.
2. Archive probabilistic preseason distributions and score them with CRPS, interval coverage, and
   calibration diagnostics. Point projections and boom/bust proxies are not enough.
3. Obtain lawful point-in-time platform rankings from at least two independent providers. Test a
   simple equal-weight rank ensemble before any learned weighting; forecast-combination research
   supports diversity, not a fantasy-specific coefficient.
4. Add an empirically estimated preceding-pick response only after current draft logs can estimate
   it. The 2017 Sleeper effect is legitimate evidence of a factor, not a current parameter value.

## Primary sources

- <https://www.cambridge.org/core/journals/judgment-and-decision-making/article/drafting-strategies-in-fantasy-football-a-study-of-competitive-sequential-human-decision-making/2AB841B3F446833348D784C0FC54DAD2>
- <https://doi.org/10.1515/jqas-2013-0009>
- <https://doi.org/10.2202/1559-0410.1050>
- <https://pubsonline.informs.org/doi/10.1287/mnsc.2019.3528>
- <https://doi.org/10.1198/016214506000001437>
- <https://doi.org/10.1016/j.csda.2017.11.003>
- <https://pubsonline.informs.org/doi/10.1287/mnsc.41.1.68>
