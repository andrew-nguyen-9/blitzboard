"""Value surface + value fixes for the interim engine (v4 wave 2).

The deep equity ValueEngine lands later (E4-value-equity); until then the engine rides
on the SHIPPED pipeline value (`pipeline/models/value_engine.py`). This package is the
seam:

    * `interim`       — a thin hook that adapts the pipeline's value OUTPUT into the engine's
                         ranked `InterimValue` surface (reuse, never reimplement value).
    * `fa_penalty`    — the truly-free-agent bug fix: detect players with no team AND no
                         draft/role news, sink them below the whole visible board, keep them
                         VISIBLE (not removed). Non-FA rows are untouched.
    * `roster_solver` — the interim-board fix: IP legal-lineup + K/DST caps.
    * `bench`         — expected-contribution bench value.

The DEEP equity engine (E4-value-equity) lands alongside as new files that *swap under* this
interim surface without touching its draft contract:

    * `equity`      — championship-equity objective: exact ΔP(win league) offline (re-uses
                       E3 `simulate_league`) + a calibrated live proxy + `live_draft_value`,
                       the single per-pick value board the draft room ranks by.
    * `replacement` — dynamic, demand-derived replacement level → live VORP (per pick).
    * `vona`        — value-over-next-available + positional-run probability.
    * `opponent`    — strategy-archetype mixture opponent model (live + history priors).

MCTS/RL land in later E4 units.
"""
from __future__ import annotations

from blitz_engine.value.bench import (
    bench_value,
    default_bench_value,
    expected_bench_starts,
)
from blitz_engine.value.equity import (
    LiveBoard,
    calibrate_equity_sensitivity,
    championship_equity,
    equity_proxy,
    live_draft_value,
)
from blitz_engine.value.fa_penalty import (
    FA_PENALTY_FACTOR,
    FA_SINK_MARGIN,
    FAStatus,
    apply_fa_penalty,
    is_truly_free_agent,
)
from blitz_engine.value.interim import (
    InterimValue,
    interim_surface,
    load_pipeline_value_engine,
)
from blitz_engine.value.mcts import (
    SUPERFLEX_TEMPLATE,
    DraftState,
    MctsPlan,
    NashCheck,
    equity_evaluator,
    mcts_plan,
    nash_aware_check,
    nash_check,
    slot_positions,
    starter_value,
)
from blitz_engine.value.opponent import (
    ARCHETYPES,
    OpponentField,
    OpponentModel,
)
from blitz_engine.value.policy import (
    DEFAULT_WEIGHTS,
    FEATURE_NAMES,
    DistillSample,
    FastDraftPolicy,
    PolicyWeights,
    distill_policy,
    marginal_starter_value,
    position_features,
    shapley_efficiency_gap,
    shapley_pick_attribution,
)
from blitz_engine.value.replacement import (
    demand_by_position,
    demand_replacement_levels,
    dynamic_vorp,
    static_replacement_levels,
    vorp_board,
)
from blitz_engine.value.roster_solver import (
    InfeasibleRosterError,
    Lineup,
    Player,
    RosterRequirements,
    optimize_lineup,
    slot_accepts,
    solve_roster,
)
from blitz_engine.value.vona import (
    VonaResult,
    run_probability,
    vona,
    vona_board,
)

__all__ = [
    "InterimValue",
    "interim_surface",
    "load_pipeline_value_engine",
    # deep equity engine (E4-value-equity)
    "LiveBoard",
    "championship_equity",
    "calibrate_equity_sensitivity",
    "equity_proxy",
    "live_draft_value",
    "demand_by_position",
    "demand_replacement_levels",
    "static_replacement_levels",
    "dynamic_vorp",
    "vorp_board",
    "VonaResult",
    "vona",
    "vona_board",
    "run_probability",
    "ARCHETYPES",
    "OpponentModel",
    "OpponentField",
    # offline MCTS + Nash (E4-mcts-policy)
    "SUPERFLEX_TEMPLATE",
    "DraftState",
    "MctsPlan",
    "NashCheck",
    "mcts_plan",
    "equity_evaluator",
    "starter_value",
    "nash_check",
    "nash_aware_check",
    "slot_positions",
    # distilled fast policy + Shapley (E4-mcts-policy)
    "FastDraftPolicy",
    "PolicyWeights",
    "DistillSample",
    "FEATURE_NAMES",
    "DEFAULT_WEIGHTS",
    "distill_policy",
    "position_features",
    "shapley_pick_attribution",
    "shapley_efficiency_gap",
    "marginal_starter_value",
    "FAStatus",
    "is_truly_free_agent",
    "apply_fa_penalty",
    "FA_PENALTY_FACTOR",
    "FA_SINK_MARGIN",
    "InfeasibleRosterError",
    "Lineup",
    "Player",
    "RosterRequirements",
    "bench_value",
    "default_bench_value",
    "expected_bench_starts",
    "optimize_lineup",
    "slot_accepts",
    "solve_roster",
]
