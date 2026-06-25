"""
Unit tests for the reliability / calibration check (v2.2.3.2).

A projection's distribution is *calibrated* if realized outcomes fall inside its
predicted percentiles at the right rate — e.g. ~10% of outcomes below the emitted
10th percentile. We test via the Probability Integral Transform (PIT): for a
calibrated forecaster the PIT values are Uniform(0,1).

Plain asserts (no pytest in the venv):  python tests/test_calibration.py
"""
from __future__ import annotations

import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.calibration import pit_values, calibration_error, reliability_table  # noqa: E402


def test_pit_values_bounded_and_centered():
    """PIT of a realized value equal to the mean is 0.5; PIT ∈ [0,1] always."""
    pit = pit_values(means=[100, 100, 100], stdevs=[20, 20, 20], realized=[100, 60, 140])
    assert all(0.0 <= x <= 1.0 for x in pit)
    assert abs(pit[0] - 0.5) < 1e-6
    assert pit[1] < 0.5 < pit[2]
    print(f"✓ PIT bounded & centered: {[round(x,2) for x in pit]}")


def test_calibrated_forecaster_has_low_error():
    """When realized ~ N(mean, stdev) exactly, PIT is ~uniform → low calibration error."""
    random.seed(11)
    means = [random.uniform(50, 300) for _ in range(4000)]
    stdevs = [m * 0.35 for m in means]
    realized = [random.gauss(m, s) for m, s in zip(means, stdevs)]
    err = calibration_error(pit_values(means, stdevs, realized))
    assert err < 0.05, err
    print(f"✓ calibrated forecaster: error={err:.3f} (< 0.05)")


def test_overconfident_forecaster_is_flagged():
    """Predicted σ too small (realized truly twice as volatile) → PIT piles up at the
    extremes → large calibration error, which the metric must surface."""
    random.seed(12)
    means = [random.uniform(50, 300) for _ in range(4000)]
    pred_stdevs = [m * 0.20 for m in means]
    realized = [random.gauss(m, m * 0.40) for m in means]  # twice as wide as predicted
    err = calibration_error(pit_values(means, pred_stdevs, realized))
    assert err > 0.15, err
    print(f"✓ overconfident forecaster flagged: error={err:.3f} (> 0.15)")


def test_reliability_table_sums_to_one():
    """The reliability table partitions the PIT mass; bins cover [0,1] and sum to 1."""
    random.seed(13)
    pit = [random.random() for _ in range(1000)]
    table = reliability_table(pit, bins=10)
    assert len(table) == 10
    assert abs(sum(frac for *_, frac in table) - 1.0) < 1e-9
    assert math.isclose(table[0][0], 0.0) and math.isclose(table[-1][1], 1.0)
    print(f"✓ reliability table partitions PIT mass across {len(table)} bins")


def main():
    test_pit_values_bounded_and_centered()
    test_calibrated_forecaster_has_low_error()
    test_overconfident_forecaster_is_flagged()
    test_reliability_table_sums_to_one()
    print("\nALL CALIBRATION TESTS PASSED ✅")


if __name__ == "__main__":
    main()
