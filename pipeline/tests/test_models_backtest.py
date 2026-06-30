"""Self-check for the model-backtest metric helpers (v3 Epic 12).

The metric math (Spearman on ranks, the season-0 summary shape) must be right offline —
the full 2015-2025 run pulls nflverse and is exercised locally / by the manual workflow.

    python tests/test_models_backtest.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backtest.models_backtest import _spearman, _summary, _parse_seasons  # noqa: E402


def test_spearman_monotonic():
    """Perfectly monotone (even if non-linear) ⇒ ρ≈1; reversed ⇒ ρ≈−1."""
    xs = [1, 2, 3, 4, 5]
    assert _spearman(xs, [1, 4, 9, 16, 25]) > 0.999
    assert _spearman(xs, [25, 16, 9, 4, 1]) < -0.999
    print("✓ spearman: monotone=+1, reversed=−1")


def test_spearman_guards():
    assert _spearman([1, 2], [1, 2]) == 0.0           # too few points
    assert _spearman([1, 1, 1, 1], [1, 2, 3, 4]) == 0.0  # zero-variance input
    print("✓ spearman guards small / constant inputs")


def test_summary_averages_seasons():
    rows = [{"season": 2016, "coverage": 0.80, "mae": 30.0},
            {"season": 2017, "coverage": 0.78, "mae": 40.0}]
    s = _summary("monte_carlo", rows, ("coverage", "mae"))
    assert s == {"model": "monte_carlo", "season": 0,
                 "metrics": {"seasons": [2016, 2017], "coverage": 0.79, "mae": 35.0}}, s
    print("✓ summary averages metrics across seasons")


def test_parse_seasons():
    assert _parse_seasons("2015-2018") == [2015, 2016, 2017, 2018]
    assert _parse_seasons("2015 2016") == [2015, 2016]
    print("✓ season spec parses range + list")


def main():
    test_spearman_monotonic()
    test_spearman_guards()
    test_summary_averages_seasons()
    test_parse_seasons()
    print("\nALL MODELS-BACKTEST TESTS PASSED ✅")


if __name__ == "__main__":
    main()
