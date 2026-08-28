"""e10 — fit the STATIC (in-browser) draft weights against e5's metric, over the real TS policy.

The static tier is `frontend/lib/draftAI.ts` (`DEFAULT_POLICY`) + `frontend/lib/benchScore.ts`
(the weight tables). Both are TypeScript and both must stay a cheap closed form that runs in the
browser. v5-architecture §5 forbids re-implementing their scoring in Python — two copies drift —
so this module drives the **real** code through `frontend/scripts/draft-eval.mjs`, one node
process per BATCH of drafts, and scores the resulting rosters with e5's simulator.

    metric = blitz_engine.simulation.season_eval.SeasonEvalResult.started_points

Method — **mirrored half-league ablation** (e6's construct, reused verbatim). Both arms sit in the
SAME draft: seats alternate A/B, then a second draft swaps every seat's arm. Seat `t`'s paired
difference `A(t) - B(t)` therefore cancels the draft-slot effect, and every seat contributes one
observation per sampled season.

Gating — the DoD gates in `backtest.ablation` are MAE-shaped (lower is better) while the metric is
points (higher is better), so each arm is presented to them as a **shortfall** predictor,
`CEILING - started_points`, against an actual of 0. MAE is then a strictly decreasing affine
function of the metric, so `ablation()`'s verdict and `no_regression()`'s tolerance carry their
published meaning with no change to either module (this unit must not touch the yardstick).

Reproduce everything::

    cd engine && ../pipeline/.venv/bin/python -m blitz_engine.backtest.static_fit --all
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from blitz_engine.backtest.ablation import AblationResult, RegressionResult, ablation, no_regression
from blitz_engine.simulation import season_eval as se

__all__ = [
    "CEILING",
    "ArmScores",
    "Candidate",
    "CANDIDATES",
    "FIT_SEED",
    "gate",
    "GateReport",
    "run_bridge",
    "score_candidate",
    "smoke_rows",
]

#: Repo root (engine/blitz_engine/backtest/static_fit.py -> repo).
ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend"
FIXTURES = ROOT / "fixtures"
BRIDGE = FRONTEND / "scripts" / "draft-eval.mjs"
TSX = FRONTEND / "node_modules" / ".bin" / "tsx"

#: One seed for the whole fit, same convention as e5/e7b (`GOLDEN_SEED`).
FIT_SEED = se.SEASON_EVAL_SEED

#: Fixed reference total used to turn "points scored" into "points left on the table" for the
#: MAE-shaped gates. Any constant above the metric's range works; it cancels in every comparison.
CEILING = 3000.0


def smoke_rows() -> list[dict[str, Any]]:
    """The 16 e7a `matrix.smoke()` rows, as raw dicts."""
    matrix = json.loads((FIXTURES / "league_matrix.json").read_text())
    smoke = set(matrix["smoke"])
    return [r for r in matrix["rows"] if r["id"] in smoke]


# ── the node bridge ────────────────────────────────────────────────────────────────────


def run_bridge(jobs: list[dict[str, Any]], *, season: int = 2024) -> list[dict[str, Any]]:
    """One node process, many drafts. Raises with node's stderr if the bridge fails."""
    if not TSX.exists():  # pragma: no cover - environment guard
        raise RuntimeError(f"missing {TSX}; run `npm ci` in frontend/ first")
    proc = subprocess.run(
        ["node", "--import", "tsx", str(BRIDGE)],
        input=json.dumps({"season": season, "jobs": jobs}),
        capture_output=True,
        text=True,
        cwd=str(FRONTEND),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"draft-eval.mjs failed:\n{proc.stderr[-4000:]}")
    return json.loads(proc.stdout)["results"]


def _assign(teams: int, flip: bool) -> list[str]:
    return [("B" if (t % 2 == 0) != flip else "A") for t in range(teams)]


# ── scoring one A/B pair ───────────────────────────────────────────────────────────────


@dataclass
class ArmScores:
    """Paired per-(season, seat) started points for two arms over a set of matrix rows."""

    keys: list[tuple[int, str]]  # (season index, "<row_id>:<seat>")
    a: np.ndarray  # (n_obs,) started points, arm A
    b: np.ndarray  # (n_obs,) started points, arm B

    @property
    def delta(self) -> float:
        """Mean A − B in started points/season. Positive ⇒ the candidate scores more."""
        return float((self.a - self.b).mean())

    def frame(self) -> pd.DataFrame:
        """The walk-forward frame the gates consume; `actual` points are 0 by construction."""
        return pd.DataFrame(
            {
                "season": [k[0] for k in self.keys],
                "player_id": [k[1] for k in self.keys],
                "yards": 0.0,
                "tds": 0.0,
            }
        )

    def predictor(self, arm: str):
        """`(train, test) -> shortfall` — CEILING minus the arm's started points, per test row."""
        vals = self.a if arm == "A" else self.b
        table = {k: CEILING - v for k, v in zip(self.keys, vals, strict=True)}

        def _p(_train: pd.DataFrame, test: pd.DataFrame) -> np.ndarray:
            pairs = zip(test["season"], test["player_id"], strict=True)
            return np.asarray([table[(int(s), str(p))] for s, p in pairs], dtype=float)

        return _p


_POOL_CACHE: dict[tuple[int, str], list[se.SeasonPlayer]] = {}


def _pool(year: int, row_id: str) -> list[se.SeasonPlayer]:
    key = (year, row_id)
    if key not in _POOL_CACHE:
        _POOL_CACHE[key] = se.build_players(year, row_id)
    return _POOL_CACHE[key]


def score_arms(
    arms: dict[str, dict[str, Any]],
    *,
    rows: list[dict[str, Any]] | None = None,
    season: int = 2024,
    seed: int = FIT_SEED,
    n_seasons: int = 8,
) -> ArmScores:
    """Draft + evaluate arms A and B mirrored over `rows`; returns the paired seat-level scores."""
    rows = rows if rows is not None else smoke_rows()
    jobs = [
        {"row": row, "seed": seed, "arms": arms, "assign": _assign(int(row["teams"]), flip)}
        for flip in (False, True)
        for row in rows
    ]
    results = run_bridge(jobs, season=season)
    cfg = se.EvalConfig(n_seasons=n_seasons, seed=seed)

    keys: list[tuple[int, str]] = []
    a_vals: list[float] = []
    b_vals: list[float] = []
    half = len(rows)
    for i, row in enumerate(rows):
        pool = _pool(season, row["id"])
        by_id = {p.player_id: p for p in pool}
        per: list[np.ndarray] = []
        for res in (results[i], results[i + half]):
            rosters = [[by_id[pid] for pid in seat] for seat in res["rosters"]]
            out = se.evaluate_rosters(
                pool, rosters, row, seat_policy=res["arm_of_seat"], config=cfg
            )
            per.append(out.per_season)  # (n_seasons, teams)
        assign0 = results[i]["arm_of_seat"]
        for t, arm0 in enumerate(assign0):
            first, second = (0, 1) if arm0 == "A" else (1, 0)
            for s in range(per[0].shape[0]):
                keys.append((s, f"{row['id']}:{t}"))
                a_vals.append(float(per[first][s, t]))
                b_vals.append(float(per[second][s, t]))
    return ArmScores(keys=keys, a=np.asarray(a_vals), b=np.asarray(b_vals))


# ── the gate ───────────────────────────────────────────────────────────────────────────


@dataclass
class GateReport:
    """The three-part verdict a weight needs before it may ship."""

    name: str
    delta: float
    ablation: AblationResult
    regression: RegressionResult
    n_obs: int

    @property
    def ships(self) -> bool:
        """`helps` AND clean `no_regression` — the block-release bar, no exceptions."""
        return self.ablation.verdict == "helps" and self.regression.passed

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "delta_started_points": round(self.delta, 3),
            "verdict": self.ablation.verdict,
            "p_value": round(self.ablation.p_value, 5),
            "mae_with": round(self.ablation.mae_with, 3),
            "mae_without": round(self.ablation.mae_without, 3),
            "no_regression": self.regression.passed,
            "candidate_mae": round(self.regression.candidate_mae, 3),
            "reference_mae": round(self.regression.reference_mae, 3),
            "n_obs": self.n_obs,
            "ships": self.ships,
        }


def gate(name: str, scores: ArmScores, *, seed: int = 0, tolerance: float = 0.0) -> GateReport:
    """Run `ablation()` (A=with the change, B=without) and `no_regression()` (A vs B) on `scores`.

    `tolerance=0.0`: a shipped weight must be *no worse* than the incumbent, not merely
    within 2 %. Widening this to make a change pass is exactly the move the cycle forbids.
    """
    frame = scores.frame()
    full, abl = scores.predictor("A"), scores.predictor("B")
    abl_res = ablation(name, full=full, ablated=abl, frame=frame, seed=seed)
    reg = no_regression(full, frame=frame, reference=abl, tolerance=tolerance, seed=seed)
    return GateReport(
        name=name, delta=scores.delta, ablation=abl_res, regression=reg, n_obs=abl_res.n_obs
    )


# ── the candidates ─────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class Candidate:
    """One proposed weight change: `patch` is the arm-A payload for the bridge."""

    name: str
    patch: dict[str, Any]
    rationale: str
    rows: tuple[str, ...] = ()  # empty = the whole smoke grid
    extra: dict[str, Any] = field(default_factory=dict)


#: e3's published CLINICAL injury rates. NOTE the semantics: `fixtures/injury_rates.json` carries
#: an explicit `event` string and it is a clinical-injury incidence, NOT availability. The policy
#: knob it would land in (`injuryRate`) is documented as "fraction of the season a starter misses".
#: Those are different quantities; the candidate is measured, not assumed.
CLINICAL_RATES = {"QB": 0.0953, "RB": 0.1588, "WR": 0.1620, "TE": 0.1725, "K": 0.0847, "DST": 0.0}

CANDIDATES: tuple[Candidate, ...] = (
    Candidate(
        "byeStack_conditional",
        {
            "policy": {
                "byeStackDeepBenchSlots": 7,
                "byeStackPenaltyDeepBench": -12,
                "byeStackPenalty": 18,
            }
        },
        "e6 refuted a flat penalty: on >=7-slot benches clustering byes BEATS spreading "
        "(+18.9/+16.0/+12.4), on 6-slot benches it reverses (-23.6/-15.3). Sign must be "
        "conditional on bench depth.",
    ),
    Candidate(
        "byeStack_off",
        {"policy": {"byeStackPenalty": 0}},
        "Fallback if the conditional form does not clear: e6 says a single positive constant is "
        "wrong in one regime or the other, so 0 beats an unproven 12.",
    ),
    Candidate(
        "sf_multiplier_rb",
        {"bench": {"SF_MULTIPLIER": {"RB": 0.67}}},
        "e6: superflex DRAINS RB bench depth (derived ceiling 3.75 -> 2.50), so the shipped 1.2 "
        "BOOST is backwards. 0.67 = 2.50/3.75. WR's 1.1 is left alone — e6 confirmed its sign.",
    ),
    Candidate(
        "trade_value_zero",
        {"bench": {"SF_RB_WEIGHTS": {"TradeValue": 0}, "SF_WR_WEIGHTS": {"TradeValue": 0}}},
        "e5's simulator trades nothing, so TradeValue has ZERO GRADIENT under started_points and "
        "can never be free-fit. Ablate to 0 and report the (expected) neutral verdict; an "
        "unproven weight is worse than no weight.",
    ),
    Candidate(
        "injury_rate_clinical",
        {"policy": {"injuryRate": CLINICAL_RATES}},
        "e3's fitted rates. Semantics differ from the knob's docstring (clinical incidence vs "
        "fraction-of-season-missed), so this is measured, not assumed.",
    ),
    Candidate(
        "kdst_soft_penalty_e6",
        {"policy": {"kdstCapRoundsFromEnd": 2, "kdstSoftPenalty": 4.06}},
        "e6's `fixtures/bench_shape.json`, restricted to the HIGH-confidence rows (cap inside the "
        "bench phase, i.e. cap <= bench_slots — e6 flags the rest low-confidence because e5 models "
        "no K/DST streaming and over-rewards locking a kicker early). Median over those 9 rows: "
        "cap = 2 (already shipped, unchanged) and soft_penalty = 4.06 (shipped: 20).",
    ),
)


def score_candidate(cand: Candidate, **kw: Any) -> ArmScores:
    """Arm A = the candidate patch, arm B = the shipped weights (empty patch)."""
    rows = [r for r in smoke_rows() if not cand.rows or r["id"] in cand.rows]
    return score_arms({"A": cand.patch, "B": {}}, rows=rows, **kw)


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - CLI
    import argparse

    ap = argparse.ArgumentParser(description="e10 static-weight fit")
    ap.add_argument("--only", action="append", default=None, help="candidate name(s)")
    ap.add_argument("--seasons", type=int, default=8)
    ap.add_argument("--season", type=int, default=2024)
    ap.add_argument("--seed", type=int, default=FIT_SEED)
    ap.add_argument("--out", type=Path, default=ROOT / "engine/experiments/static/results.json")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args(argv)

    cands = [c for c in CANDIDATES if not args.only or c.name in args.only]
    reports = []
    for c in cands:
        scores = score_candidate(c, n_seasons=args.seasons, season=args.season, seed=args.seed)
        rep = gate(c.name, scores)
        row = rep.as_dict() | {
            "rationale": c.rationale, "patch": c.patch,
            "season": args.season, "seed": args.seed, "n_seasons": args.seasons,
        }
        reports.append(row)
        print(json.dumps(row))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(reports, indent=2) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
