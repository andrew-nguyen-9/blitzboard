"""Independent C05 execution-freeze probes."""

from __future__ import annotations

import os
from pathlib import Path


def _root() -> Path:
    value = os.environ.get("C05_PROD_ROOT")
    assert value, "C05_PROD_ROOT must name the C05 execution worktree"
    return Path(value)


def test_execution_loader_applies_frozen_addendum_and_metric_binding() -> None:
    from blitz_engine.promotion.execution import load_execution_manifest

    effective = load_execution_manifest(_root())
    assert effective["arms"]["candidate"]["combined_candidate_sha"] == (
        "7b3fd73578943b992402ad693259a3e92358da69"
    )
    assert effective["evaluator"]["waiver_cost"] == 0.0


def test_arm_runner_emits_accepted_c02_proxy_metrics() -> None:
    from blitz_engine.promotion.runner import HeldOutGuard, run_arm

    from blitz_engine.testing import matrix

    row = matrix.by_id("t10-1qb-std-te0.0-b4-ir0")
    run = run_arm(
        "v6_candidate",
        "7b3fd73578943b992402ad693259a3e92358da69",
        2021,
        row,
        2026082601,
        n_seasons=1,
        guard=HeldOutGuard([2021], [2018]),
        stage="fit",
    )
    assert run.playoff_proxy is not None
    assert run.championship_proxy is not None
    assert len(run.playoff_proxy) == row["teams"]
    assert len(run.championship_proxy) == row["teams"]

