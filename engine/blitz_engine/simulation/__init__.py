"""`blitz_engine.simulation` — the correlated Monte-Carlo core (E3).

Turns E1's per-player marginals into **joint** draft intelligence: it samples correlated
player-week outcomes (QB↔WR stacks, game shootouts, DST↔opp script) and reduces 10k–1M
draws — streamed, never materialised — to per-player positional-finish odds, boom/bust
rates, median ± 95 %, and P(beats ADP). Public surface:

    build_correlation / CorrelationSpec   the factor/rule matrix that ships in the snapshot
    sample_correlated                     the library-RNG batch sampler (Gaussian copula)
    simulate / simulate_projection        the memory-bounded streaming run → SimResult
    SimConfig / SimResult                 adaptive-scale knobs + per-player outputs
    evaluate_season                       E5 imperfect-information season metric (THE eval)
    to_snapshot                           E1 quantiles + E3 corr_matrix + mc_probs → Snapshot

Memory-critical: peak is bounded by one batch (`batch × P × float32`), independent of the
run count; `simulate` degrades the batch to hold the 16 GB budget and flags a cloud-burst
only when it can't. See E3-mc-core.done.md. E3-league-sim + E5-lineup read this.
"""
from __future__ import annotations

from blitz_engine.simulation.correlation import (
    CorrelationSpec,
    build_correlation,
    cholesky_factor,
    nearest_psd_correlation,
)
from blitz_engine.simulation.league import (
    LeagueConfig,
    LeagueResult,
    Roster,
    simulate_league,
)
from blitz_engine.simulation.mc import (
    FINISH_RANKS,
    INTERACTIVE_RUNS,
    PUBLISH_RUNS,
    SimConfig,
    SimResult,
    sample_correlated,
    simulate,
    simulate_projection,
    to_snapshot,
)
from blitz_engine.simulation.playoffs import Bracket, build_bracket
from blitz_engine.simulation.season_eval import (
    SEASON_EVAL_SEED,
    EvalConfig,
    SeasonEvalResult,
    SeasonPlayer,
    build_players,
    draft_league,
    evaluate_rosters,
    evaluate_season,
    hindsight_points,
)

__all__ = [
    "Bracket",
    "CorrelationSpec",
    "EvalConfig",
    "FINISH_RANKS",
    "INTERACTIVE_RUNS",
    "LeagueConfig",
    "LeagueResult",
    "PUBLISH_RUNS",
    "Roster",
    "SEASON_EVAL_SEED",
    "SeasonEvalResult",
    "SeasonPlayer",
    "SimConfig",
    "SimResult",
    "build_bracket",
    "build_correlation",
    "build_players",
    "cholesky_factor",
    "draft_league",
    "evaluate_rosters",
    "evaluate_season",
    "hindsight_points",
    "nearest_psd_correlation",
    "sample_correlated",
    "simulate",
    "simulate_league",
    "simulate_projection",
    "to_snapshot",
]
