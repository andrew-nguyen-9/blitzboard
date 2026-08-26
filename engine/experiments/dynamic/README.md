# E11 — dynamic fit (MCTS → distill → PPO) on real data, graded by the E5 metric

**Result: NEGATIVE. Nothing was promoted. The shipped `DEFAULT_WEIGHTS` are unchanged.**

Everything here is scored on **one** metric: `SeasonEvalResult.started_points` (E5) — the points a
**locked** lineup actually scored, per seat, over a corpus season's regular weeks under sampled
e2a availability × e3 clinical injury × byes × contested waivers, leakage-guarded every week. The
retired hindsight metric is not used, and no side metric was invented.

## The A/B

Both arms draft the same real e7b corpus pool (`build_players(year, row_id)`) with the same
`EvalConfig.seed`, and the candidate policy is seated in the mix's `engine_msv` seats via
`draft_league(pick_fn=…)` (`real_env.policy_pick_fn`). Every other seat is E5's own `_pick`, so
the field is identical and the difference is genuinely paired — `season_metric_edge` against a
copy of itself returns exactly `[0.0, …]` (asserted in `tests/test_rl_policy.py`).

Grid: seasons **2018 / 2021 / 2024** × rows **t8-1qb-std-te0.0-b4-ir0**,
**t12-1qb-half-te0.5-b8-ir0**, **t10-2qb-ppr-te0.0-b8-ir1** = 9 configs × `n_seasons=4`
= **36 paired evaluation points**, seed `20260825`. Promotion bar (unchanged): the 95 % bootstrap
CI of the paired edge must clear 0.

## Verdicts (`results/`)

| experiment | mean edge (pts/season) | 95 % CI | verdict | promoted |
|---|---|---|---|---|
| MCTS-distilled weights vs shipped cold weights | **−60.2** | [−93.3, −25.7] | no-help | no |
| PPO (real universe, E5 reward) vs distilled baseline | **−26.7** | [−45.7, −7.2] | no-help | no |

Both CIs sit **entirely below zero**: these are not "failed to prove a win", they are measured
losses. The distilled policy reproduces MCTS's own picks better after fitting
(agreement 0.36 → 0.64 over 84 real decision points at `--mcts-iter 500`), which is precisely the
point — **MCTS's objective is not the E5 metric**. Its leaf evaluator is the static
`starter_value` roster sum, which cannot see a bye, an inactive, or a waiver hole; distilling it
faithfully moves the live policy *away* from the metric that matters. Scaling PPO made it worse
(6×2 episodes → +1.7 [−18.6, +23.2]; 30×6 → −26.7 [−45.7, −7.2]), the signature of optimising a
reward whose per-rollout noise (`n_seasons` ≤ 2 availability draws) exceeds its signal.

## Reproduce

```sh
cd engine
PY=../pipeline/.venv/bin/python   # linked worktree: use the absolute venv path
$PY experiments/dynamic/run_dynamic_fit.py distill --mcts-iter 500 --drafts 9   # ~57 s
$PY experiments/dynamic/run_dynamic_fit.py gate --n-seasons 4                   # ~5 s
$PY experiments/dynamic/run_dynamic_fit.py ppo --ppo-iters 30 --episodes 6 \
      --reward-seasons 2 --n-seasons 4                                          # ~40 s
```

Local compute only: float32 CPU, a 4→16→1 net, a ≤90-player board, no cloud burst. PPO
checkpoints `checkpoints/ppo_latest.pt` + `checkpoints/trace.json` every iteration (the `.pt` is
gitignored; the trace is committed as the run's receipt).

## Invariants

`(cd engine && ../pipeline/.venv/bin/python -m pytest tests/regression/test_draft_invariants.py -k
"bench_positional_mix or kdst_timing")` — green. Since nothing was promoted, the boards the live
policy drafts are unchanged.
