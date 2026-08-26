"""Real-data draft universe + the **E5 metric** as the RL reward and the promotion gate (E11).

`train.py` shipped against a synthetic scarcity universe (`draft_universe`) scored by a static
roster-sum proxy. Neither is the thing we care about: E5 retired hindsight scoring in favour of
`SeasonEvalResult.started_points` — the points a **locked** lineup actually scored, per seat, over
a corpus season's regular weeks under sampled availability + injury + byes + contested waivers.
This module is the adapter between the two:

* `real_universe` — the e7b corpus pool for one matrix row as the `{pid: (pos, value·week⁻¹)}`
  board `DraftEnv`/`live_draft_value` expect. The synthetic universe stays for fast unit tests.
* `row_template` — that row's own starting slots **plus its bench** (`"BN"`), so a rollout drafts
  a roster the E5 evaluator can actually price (bench insurance is exactly what E5 sees).
* `e5_league_reward` — a `DraftEnv.league_reward_fn`: every team's return IS its E5
  `started_points`. One `evaluate_rosters` call per rollout, ~0.2 s at `n_seasons=1`.
* `policy_pick_fn` / `season_metric_edge` — seat a `FastDraftPolicy`/`RLDraftPolicy` in
  `season_eval.draft_league` and read the paired per-(config, season) edge over a baseline policy
  seated in the *same* seats with the *same* seed. That vector feeds `bootstrap_ci` /
  `select_live_policy` unchanged: the promotion bar is still "CI clears 0", now measured on the
  metric that matters.

`ponytail:` no new evaluator — the reward, the gate and the ablation all call E5's
`evaluate_rosters`/`evaluate_season`; this module only reshapes rosters into its argument types.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

from blitz_engine.value.mcts import slot_positions
from blitz_engine.value.policy import FastDraftPolicy

#: Which seat of `DEFAULT_POLICY_MIX` the candidate policy replaces in the A/B. `engine_msv` is
#: the engine's own seat, so the edge reads "the fitted policy vs the engine's shipped heuristic".
DEFAULT_REPLACES = "engine_msv"


# ── the real board ─────────────────────────────────────────────────────────────────────
def real_pool(year: int, row_id: str) -> list[Any]:
    """The e7b corpus pool for `row_id` as E5 `SeasonPlayer`s (cached per (year, row_id))."""
    from blitz_engine.simulation import season_eval as se

    return se.build_players(year, row_id)


def real_universe(
    year: int, row_id: str, *, players: Sequence[Any] | None = None, top_n: int = 0
) -> tuple[dict[str, tuple[str, float]], list[Any]]:
    """`({player_id: (position, value·week⁻¹)}, pool)` from the corpus — the real `draft_universe`.

    Value units match `live_draft_value`/`draft_universe`: a pre-season **projection per week**,
    the only pre-week-1 information E5 lets a drafter see. `top_n` truncates to the N most
    projected players (draft-relevant board; keeps `live_draft_value` off the deep tail).
    """
    pool = list(players) if players is not None else real_pool(year, row_id)
    if not pool:
        return {}, []
    weeks = max(1, len(pool[0].points_if_plays))
    pool = sorted(pool, key=lambda p: (-p.projection, p.player_id))
    if top_n:
        pool = pool[:top_n]
    return {p.player_id: (p.position, p.projection / weeks) for p in pool}, pool


def row_template(row: Mapping[str, Any]) -> tuple[str, ...]:
    """A matrix row's draft template: its starting slots, then one `"BN"` per bench slot."""
    slots = dict(row["starting_slots"])
    starters = [s for slot, n in slots.items() for s in [slot] * int(n)]
    return tuple(starters) + ("BN",) * int(row.get("bench_slots", 0))


def slots_after(template: Sequence[str], positions: Sequence[str]) -> list[str]:
    """`template` with one slot consumed per already-drafted position (most specific first)."""
    left = list(template)
    for pos in positions:
        slot = next((s for s in left if s == pos), None)
        slot = slot or next((s for s in left if pos in slot_positions(s)), None)
        if slot is not None:
            left.remove(slot)
    return left


# ── the E5 metric as a reward ──────────────────────────────────────────────────────────
def e5_league_reward(
    pool: Sequence[Any],
    row: Mapping[str, Any],
    *,
    n_seasons: int = 1,
    base_seed: int | None = None,
) -> Callable[[Mapping[int, Sequence[tuple[str, str, float]]], int], list[float]]:
    """A `DraftEnv.league_reward_fn` whose per-team return is E5 `started_points`.

    The rollout's rosters are re-hydrated into `SeasonPlayer`s and played through E5's
    imperfect-information season (sampled availability × injury × byes, contested waivers,
    leakage-guarded every week). The rollout `seed` shifts `EvalConfig.seed`, so different
    episodes see different availability trajectories over the same real board.
    """
    from blitz_engine.simulation import season_eval as se

    by_id = {p.player_id: p for p in pool}
    default_seed = se.SEASON_EVAL_SEED if base_seed is None else base_seed

    def reward(
        rosters: Mapping[int, Sequence[tuple[str, str, float]]], seed: int
    ) -> list[float]:
        teams = sorted(rosters)
        built = [[by_id[pid] for pid, _, _ in rosters[t] if pid in by_id] for t in teams]
        res = se.evaluate_rosters(
            list(pool), built, row,
            config=se.EvalConfig(n_seasons=n_seasons, seed=default_seed + 7919 * seed),
        )
        return [float(v) for v in res.started_points]

    return reward


# ── seating a live policy in E5's draft ────────────────────────────────────────────────
def policy_pick_fn(
    policy: FastDraftPolicy | Any,
    row: Mapping[str, Any],
    *,
    replaces: str = DEFAULT_REPLACES,
    board_top_n: int = 90,
) -> Callable[..., Any]:
    """A `season_eval.draft_league` `pick_fn` seating `policy` wherever the mix says `replaces`.

    Every other seat falls through to E5's own `_pick`, so the field is unchanged and the two arms
    of an A/B differ only in the treated seats. The policy sees a `live_draft_value` board built
    from the top `board_top_n` remaining projections (the draft-relevant board; the deep tail
    cannot be picked and only costs equity math).
    """
    from blitz_engine.simulation import season_eval as se
    from blitz_engine.value.opponent import OpponentField

    template = row_template(row)
    weeks_cache: dict[str, int] = {}
    field = OpponentField.uniform(max(1, int(row["teams"]) - 1))

    def pick(
        policy_name: str,
        roster: list[Any],
        board: list[Any],
        slots: Mapping[str, int],
        rounds: int,
        rates: Mapping[str, float],
        top_k: int = 24,
    ) -> Any:
        if policy_name != replaces:
            return se._pick(policy_name, roster, board, slots, rounds, rates, top_k)
        if not weeks_cache:
            weeks_cache["w"] = max(1, len(board[0].points_if_plays))
        weeks = weeks_cache["w"]
        cands = board[:board_top_n]
        by_pos: dict[str, list[tuple[str, float]]] = {}
        for p in cands:
            by_pos.setdefault(p.position, []).append((p.player_id, p.projection / weeks))
        left = slots_after(template, [p.position for p in roster])
        choice = policy.pick_live(by_pos, field, left) if left else None
        if choice is not None:
            pid = choice[0]
            hit = next((p for p in cands if p.player_id == pid), None)
            if hit is not None:
                return hit
        return se._pick(policy_name, roster, board, slots, rounds, rates, top_k)

    return pick


# ── MCTS on the real board → distillation samples ──────────────────────────────────────
def distill_samples(
    year: int,
    row: Mapping[str, Any],
    *,
    n_iter: int = 300,
    seed: int = 0,
    board_top_n: int = 90,
    players: Sequence[Any] | None = None,
) -> tuple[list[Any], list[str]]:
    """Walk one real draft, run MCTS at every one of my turns → `(samples, best_actions)`.

    Each decision point yields a `DistillSample` of the live board's `position_features` and the
    search's visit distribution, plus the search's robust-child `best_action` (the agreement
    target). Between my turns the field's picks are sampled from `OpponentField`, exactly as the
    search's own open-loop depletion assumes.
    """
    import numpy as _np

    from blitz_engine.value.equity import live_draft_value
    from blitz_engine.value.mcts import DraftState, mcts_plan
    from blitz_engine.value.opponent import OpponentField
    from blitz_engine.value.policy import DistillSample, position_features

    uni, pool = real_universe(year, str(row["id"]), players=players, top_n=board_top_n)
    teams = int(row["teams"])
    field = OpponentField.uniform(max(1, teams - 1))
    template = row_template(row)
    rng = _np.random.default_rng(seed)

    by_pos: dict[str, list[tuple[str, float]]] = {}
    for pid, (pos, val) in uni.items():
        by_pos.setdefault(pos, []).append((pid, val))
    for lst in by_pos.values():
        lst.sort(key=lambda pv: pv[1], reverse=True)

    slots_left = list(template)
    samples: list[Any] = []
    best_actions: list[str] = []
    for r in range(len(template)):
        board = {p: tuple(lst) for p, lst in by_pos.items() if lst}
        state = DraftState(board=board, slots_left=tuple(slots_left))
        if not state.legal_actions():
            break
        plan = mcts_plan(state, field, n_iter=n_iter, seed=seed * 1009 + r)
        lb = live_draft_value({p: list(lst) for p, lst in board.items()}, field)
        pos_of = {pid: p for p, lst in board.items() for pid, _ in lst}
        feats = position_features(lb, slots_left, pos_of)
        target = plan.policy_target()
        if feats and target and plan.best_action in feats:
            samples.append(DistillSample(features=feats, target=target))
            best_actions.append(str(plan.best_action))
        take = plan.best_action or next(iter(feats), None)
        if take is None:
            break
        by_pos[take].pop(0)
        slot = next((s for s in slots_left if s == take), None)
        slot = slot or next((s for s in slots_left if take in slot_positions(s)), None)
        if slot is not None:
            slots_left.remove(slot)
        # the field drafts between my turns (value-greedy, same model the search assumes)
        top = {p: lst[0][1] for p, lst in by_pos.items() if lst}
        for probs in field.pick_position_sequence(top, None):
            items = [(p, max(0.0, float(w))) for p, w in probs.items() if by_pos.get(p)]
            total = sum(w for _, w in items)
            if total <= 0:
                continue
            draw, acc = rng.random() * total, 0.0
            for p, w in items:
                acc += w
                if draw <= acc:
                    by_pos[p].pop(0)
                    break
            top = {p: lst[0][1] for p, lst in by_pos.items() if lst}
    return samples, best_actions


def policy_agreement(
    policy: FastDraftPolicy, samples: Sequence[Any], best_actions: Sequence[str]
) -> float:
    """Fraction of decision points where the linear policy's argmax == MCTS's robust child."""
    if not samples:
        return 0.0
    hits = 0
    for s, target in zip(samples, best_actions, strict=True):
        scores = {p: float(policy.weights.coef @ v) for p, v in s.features.items()}
        if scores and max(scores, key=lambda p: scores[p]) == target:
            hits += 1
    return hits / len(samples)


@dataclass(frozen=True)
class SeatedResult:
    """One arm of a seated A/B: the E5 result plus the columns the candidate actually held."""

    result: Any  # SeasonEvalResult
    seats: tuple[int, ...]

    @property
    def per_season(self) -> np.ndarray:
        """(n_seasons,) mean `started_points` over the treated seats — the paired arm vector."""
        return np.asarray(self.result.per_season)[:, list(self.seats)].mean(axis=1)


def evaluate_seated(
    policy: FastDraftPolicy | Any,
    year: int,
    row: Mapping[str, Any],
    *,
    config: Any = None,
    replaces: str = DEFAULT_REPLACES,
    players: Sequence[Any] | None = None,
    board_top_n: int = 90,
) -> SeatedResult:
    """Draft + evaluate one league under E5 with `policy` seated in the `replaces` seats."""
    from blitz_engine.simulation import season_eval as se

    cfg = config or se.EvalConfig(n_seasons=4)
    res = se.evaluate_season(
        year, row, config=cfg, players=players,
        pick_fn=policy_pick_fn(policy, row, replaces=replaces, board_top_n=board_top_n),
    )
    seats = tuple(i for i, p in enumerate(res.seat_policy) if p == replaces)
    return SeatedResult(result=res, seats=seats)


def season_metric_edge(
    candidate: FastDraftPolicy | Any,
    baseline: FastDraftPolicy | Any,
    configs: Sequence[tuple[int, Mapping[str, Any]]],
    *,
    n_seasons: int = 4,
    seed: int | None = None,
    replaces: str = DEFAULT_REPLACES,
    board_top_n: int = 90,
) -> list[float]:
    """Paired per-(config, season) `started_points` edge of `candidate` over `baseline`.

    Both arms are drafted from the same pool with the same `EvalConfig.seed`, so the availability,
    injury and bye draws are index-identical and the difference is genuinely paired. The returned
    vector is what `bootstrap_ci`/`select_live_policy` grade — E5's metric, nothing else.
    """
    from blitz_engine.simulation import season_eval as se

    cfg_seed = se.SEASON_EVAL_SEED if seed is None else seed
    out: list[float] = []
    for year, row in configs:
        pool = real_pool(year, str(row["id"]))
        cfg = se.EvalConfig(n_seasons=n_seasons, seed=cfg_seed)
        kw = dict(
            config=cfg, replaces=replaces, players=pool, board_top_n=board_top_n
        )
        treat = evaluate_seated(candidate, year, row, **kw)  # type: ignore[arg-type]
        ctrl = evaluate_seated(baseline, year, row, **kw)  # type: ignore[arg-type]
        if not treat.seats or not ctrl.seats:
            continue
        out.extend(float(v) for v in (treat.per_season - ctrl.per_season))
    return out
