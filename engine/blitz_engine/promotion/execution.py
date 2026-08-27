"""C05 execution harness: the freeze-review corrections, mechanically enforced.

Answers the three deterministic blockers of `C05-exec-v1-freeze-review.md` without touching the
frozen files:

1. `load_execution_manifest` hash-verifies `promotion-v3.json` AND `promotion-v3-exec-v1.json`
   against their frozen sha256 pins, then builds an EFFECTIVE in-memory manifest that injects
   exactly two things: the frozen candidate SHA and the explicit `waiver_cost: 0.0` metric
   binding. Nothing on disk changes; any byte drift in either file refuses to load.
2. Arm receipts are produced from the ARM'S OWN CHECKOUT: `produce_arm_receipt` asserts the
   checkout's actual `git rev-parse HEAD` equals the arm's frozen SHA before anything runs, runs
   the evaluator inside that checkout via a subprocess whose `PYTHONPATH` is the checkout's
   `engine/`, and maps the accepted C02 paired playoff/championship samples into the receipt.
   The C05 tooling tree's own HEAD is not `7b3fd735…`, so it is mechanically refused as the
   candidate policy identity.
3. Receipts are WRITE-ONCE and stage-separated: fit receipts land under `<out>/fit/`, held-out
   confirm receipts under `<out>/confirm/`, an existing path refuses to be overwritten, and the
   `HeldOutGuard` year/stage check runs before any evaluator work.

No function here runs the authoritative experiment; `rehearse` is a deliberately tiny
two-checkout null run, labelled non-authoritative in its receipt.
"""
from __future__ import annotations

import copy
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np

from blitz_engine.promotion.manifest import ManifestError, load_manifest, sha256_file
from blitz_engine.promotion.runner import (
    ArmRun,
    HeldOutGuard,
    PromotionError,
    derive_eval_seed,
)

__all__ = [
    "BASELINE_SHA",
    "CANDIDATE_SHA",
    "EXEC_V1_SHA256",
    "MANIFEST_SHA256",
    "ExecutionError",
    "arm_command",
    "checkout_head",
    "load_execution_manifest",
    "produce_arm_receipt",
    "rehearse",
    "verify_arm_checkout",
]

#: Frozen identity pins. Changing any of these requires a new exec addendum version and a new
#: freeze review — they are the immutability check, not configuration.
MANIFEST_SHA256 = "bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab"
EXEC_V1_SHA256 = "24e5e50afdad75006ca3a1814317d9254ea98de25bbb97dba4b06bbee7c3b7ad"
BASELINE_SHA = "01f01d3c5f9c00a046edd43707db75ce1426c0e8"
CANDIDATE_SHA = "7b3fd73578943b992402ad693259a3e92358da69"


class ExecutionError(PromotionError):
    """A checkout, hash, binding, or write-once violation — execution refuses, never degrades."""


def load_execution_manifest(root: str | Path) -> dict[str, Any]:
    """Hash-load manifest + exec-v1 from `root` into the effective in-memory execution manifest."""
    root = Path(root)
    mp = root / ".orchestrator-v6" / "experiments" / "promotion-v3.json"
    ap = root / ".orchestrator-v6" / "experiments" / "promotion-v3-exec-v1.json"
    for path, want in ((mp, MANIFEST_SHA256), (ap, EXEC_V1_SHA256)):
        if not path.is_file():
            raise ManifestError(f"missing frozen file: {path}")
        if (got := sha256_file(path)) != want:
            raise ManifestError(f"{path.name}: sha256 {got} != frozen {want}")
    manifest = load_manifest(mp)
    addendum = json.loads(ap.read_text())
    if addendum["manifest_sha256"] != MANIFEST_SHA256:
        raise ManifestError("exec-v1 references a different manifest hash")
    sha = addendum["arms"]["candidate"]["combined_candidate_sha"]
    if sha != CANDIDATE_SHA:
        raise ManifestError(f"exec-v1 candidate SHA {sha!r} != frozen {CANDIDATE_SHA}")
    cost = float(addendum["metric_binding"]["waiver_cost"])
    if cost != 0.0:
        raise ManifestError(
            "metric binding must be waiver_cost = 0.0; any other value requires promotion-v4"
        )
    effective = copy.deepcopy(manifest)
    effective["arms"]["candidate"]["combined_candidate_sha"] = sha
    effective["arms"]["control"]["sha"] = addendum["arms"]["control"]["sha"]
    effective["evaluator"]["waiver_cost"] = cost
    effective["_exec_addendum_sha256"] = EXEC_V1_SHA256
    return effective


def checkout_head(checkout: str | Path) -> str:
    out = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return out.stdout.strip()


def verify_arm_checkout(checkout: str | Path, expected_sha: str) -> str:
    """The actual HEAD must equal the arm's frozen SHA — a later C05 tooling tree is refused."""
    head = checkout_head(checkout)
    if head != expected_sha:
        raise ExecutionError(
            f"checkout {checkout} HEAD {head} != required arm SHA {expected_sha}; "
            "arm receipts must come from the arm's own frozen checkout"
        )
    return head


#: Runs INSIDE the arm checkout, so the evaluator is provably the arm's code. The venv's editable
#: blitz_engine install registers a meta-path finder that OVERRIDES PYTHONPATH (the CLAUDE.md
#: worktree trap — the rehearsal caught it resolving a baseline arm to the tooling tree), so the
#: payload strips editable finders, pins the checkout's engine/ first, purges any preloaded
#: modules, and HARD-ASSERTS `blitz_engine.__file__` lives inside the checkout before running.
#: Emits raw arrays as JSON on stdout; `getattr` keeps it runnable on the v5 baseline, which
#: predates the C02 proxy fields.
_ARM_PAYLOAD = r"""
import json, sys

year, league_id, eval_seed, n_seasons, waiver_cost, engine_path = json.loads(sys.argv[1])
sys.path.insert(0, engine_path)
sys.meta_path = [
    f for f in sys.meta_path
    if "editable" not in (type(f).__module__ + type(f).__name__).lower()
]
for name in [m for m in list(sys.modules) if m == "blitz_engine" or m.startswith("blitz_engine.")]:
    del sys.modules[name]
import blitz_engine
if not str(blitz_engine.__file__).startswith(engine_path):
    raise SystemExit(
        f"blitz_engine resolved OUTSIDE the arm checkout: {blitz_engine.__file__} "
        f"(required prefix {engine_path}) - refusing to produce a receipt"
    )
import numpy as np
from blitz_engine.simulation import season_eval as se

try:
    from blitz_engine.testing import matrix
    row = next(r for r in matrix.all() if r["id"] == league_id)
except Exception as e:  # pragma: no cover - matrix loader is present in every supported checkout
    raise SystemExit(f"cannot load league row: {e}")
pool = se.build_players(year, league_id)
import hashlib
rows = [(p.player_id, p.position, float(p.projection))
        for p in sorted(pool, key=lambda p: (-p.projection, p.player_id))]
board_hash = hashlib.sha256(json.dumps(rows).encode()).hexdigest()
cfg_kwargs = {"n_seasons": int(n_seasons), "seed": int(eval_seed)}
import dataclasses
if any(f.name == "waiver_cost" for f in dataclasses.fields(se.EvalConfig)):
    cfg_kwargs["waiver_cost"] = float(waiver_cost)
elif float(waiver_cost) != 0.0:
    raise SystemExit("this checkout cannot honour a nonzero waiver_cost binding")
res = se.evaluate_season(year, row, config=se.EvalConfig(**cfg_kwargs))
def arr(name):
    a = np.asarray(getattr(res, name, np.empty((0, 0))), dtype=float)
    return a.tolist() if a.size else None
print(json.dumps({
    "board_hash": board_hash,
    "seat_policy": list(res.seat_policy),
    "per_season": np.asarray(res.per_season, dtype=float).tolist(),
    "h2h_win_rate": np.asarray(res.h2h_win_rate, dtype=float).tolist(),
    "per_season_playoff": arr("per_season_playoff"),
    "per_season_champ": arr("per_season_champ"),
}))
"""


def arm_command(
    checkout: str | Path, python: str, year: int, league_id: str, eval_seed: int,
    n_seasons: int, waiver_cost: float = 0.0,
) -> tuple[list[str], dict[str, str]]:
    """The exact (argv, extra_env) that runs one arm slice inside `checkout`."""
    engine_path = str(Path(checkout) / "engine")
    args = json.dumps([year, league_id, eval_seed, n_seasons, waiver_cost, engine_path])
    argv = [python, "-c", _ARM_PAYLOAD, args]
    env = {"PYTHONPATH": engine_path}
    return argv, env


def produce_arm_receipt(
    arm: str,
    checkout: str | Path,
    expected_sha: str,
    *,
    effective: dict[str, Any],
    year: int,
    league_id: str,
    base_seed: int,
    n_seasons: int,
    stage: str,
    guard: HeldOutGuard,
    out_dir: str | Path,
    tooling_head: str,
    python: str = sys.executable,
    authoritative: bool = False,
) -> Path:
    """Verify the checkout, run the arm inside it, write a write-once stage-separated receipt."""
    if stage not in ("fit", "confirm"):
        raise ExecutionError(f"unknown stage {stage!r}")
    guard.check(year, stage=stage)
    head = verify_arm_checkout(checkout, expected_sha)
    out = Path(out_dir) / stage / f"{arm}-{year}-{league_id}-{base_seed}.json"
    if out.exists():
        raise ExecutionError(f"write-once violation: {out} already exists")
    eval_seed = derive_eval_seed(base_seed, year, league_id)
    argv, extra_env = arm_command(
        checkout, python, year, league_id, eval_seed, n_seasons,
        float(effective["evaluator"]["waiver_cost"]),
    )
    proc = subprocess.run(
        argv, env={**os.environ, **extra_env}, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise ExecutionError(f"arm payload failed in {checkout}: {proc.stderr[-800:]}")
    payload = json.loads(proc.stdout.strip().splitlines()[-1])

    def _proxy(name: str) -> tuple[float, ...] | None:
        a = payload.get(name)
        if a is None:
            return None
        return tuple(float(v) for v in np.asarray(a, dtype=float).mean(axis=0))

    run = ArmRun(
        arm=arm,
        policy_sha=head,
        year=int(year),
        league_id=str(league_id),
        base_seed=int(base_seed),
        eval_seed=eval_seed,
        board_hash=str(payload["board_hash"]),
        seat_policy=tuple(payload["seat_policy"]),
        per_season=tuple(tuple(float(v) for v in r) for r in payload["per_season"]),
        h2h_win_rate=tuple(float(v) for v in payload["h2h_win_rate"]),
        playoff_proxy=_proxy("per_season_playoff"),
        championship_proxy=_proxy("per_season_champ"),
        synthetic=not authoritative,
    )
    receipt = {
        "authoritative": bool(authoritative),
        "label": None if authoritative else "NON-AUTHORITATIVE rehearsal/probe receipt",
        "arm_checkout_head": head,
        "produced_by_tooling_head": tooling_head,
        "manifest_sha256": MANIFEST_SHA256,
        "exec_addendum_sha256": EXEC_V1_SHA256,
        "stage": stage,
        "arm_run": run.to_dict(),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return out


def rehearse(
    repo_root: str | Path,
    scratch: str | Path,
    out_dir: str | Path,
    *,
    tooling_head: str,
    league_id: str = "t10-1qb-std-te0.0-b4-ir0",
    year: int = 2021,
    base_seed: int = 2026082601,
) -> dict[str, Any]:
    """Cheap NON-AUTHORITATIVE two-checkout rehearsal: baseline vs candidate, one slice, 1 season.

    Creates two detached throwaway checkouts at the frozen arm SHAs, produces one receipt from
    each through the full verify-head → subprocess-evaluator → write-once path, then pairs them.
    A pairing failure here is a REAL finding to report, not to resolve.
    """
    from blitz_engine.promotion.runner import PairingError, pair_slice

    root, scratch = Path(repo_root), Path(scratch)
    effective = load_execution_manifest(root)
    guard = HeldOutGuard(list(effective["seasons"]), list(effective["held_out_seasons"]))
    checkouts = {"v5_shipped": (scratch / "arm-v5", BASELINE_SHA),
                 "v6_candidate": (scratch / "arm-v6", CANDIDATE_SHA)}
    runs: dict[str, ArmRun] = {}
    finding = None
    try:
        for arm, (co, sha) in checkouts.items():
            subprocess.run(
                ["git", "-C", str(root), "worktree", "add", "--detach", str(co), sha],
                capture_output=True, text=True, check=True,
            )
            path = produce_arm_receipt(
                arm, co, sha, effective=effective, year=year, league_id=league_id,
                base_seed=base_seed, n_seasons=1, stage="fit", guard=guard,
                out_dir=out_dir, tooling_head=tooling_head, authoritative=False,
            )
            runs[arm] = ArmRun.from_dict(json.loads(path.read_text())["arm_run"])
        try:
            s = pair_slice(runs["v6_candidate"], runs["v5_shipped"])
            paired = {
                "paired": True,
                "started_points_delta_mean": float(np.mean(s["started_points"])),
                "h2h_delta_mean": float(np.mean(s["h2h_win_rate"])),
                "playoff_proxy_available_both_arms": s["playoff_proxy"] is not None,
                "championship_proxy_available_both_arms": s["championship_proxy"] is not None,
            }
        except PairingError as e:
            paired = {"paired": False}
            finding = f"PairingError: {e}"
    finally:
        for co, _ in checkouts.values():
            subprocess.run(
                ["git", "-C", str(root), "worktree", "remove", "--force", str(co)],
                capture_output=True, text=True,
            )
    summary = {
        "label": "NON-AUTHORITATIVE two-checkout rehearsal — justifies nothing",
        "slice": {"year": year, "league_id": league_id, "base_seed": base_seed, "n_seasons": 1},
        "arm_heads": {a: runs[a].policy_sha for a in runs},
        "board_hashes": {a: runs[a].board_hash for a in runs},
        "candidate_proxies_present": runs.get("v6_candidate") is not None
        and runs["v6_candidate"].playoff_proxy is not None,
        "control_proxies_present": runs.get("v5_shipped") is not None
        and runs["v5_shipped"].playoff_proxy is not None,
        "pairing": paired,
        "finding": finding,
    }
    p = Path(out_dir) / "rehearsal-summary.json"
    p.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary
