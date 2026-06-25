"""
calibration_check.py — reliability of the projection distributions (v2.2.3.2).

Validates the v2.2.3 claim: feeding *predictability-aware* σ into Monte Carlo makes
volatile players' boom/bust ranges honest, not just wide. We measure honesty with a
reliability diagram (Probability Integral Transform; see `models/calibration.py`):
for a calibrated forecaster, realized outcomes are Uniform across the predicted
percentiles, so the diagram is flat and the calibration error → 0.

Offline + self-validating (no DB, no network): we synthesize a world where low-ρ
players are *truly* more volatile than the base projector's σ implies, then compare
two forecasters on the same realized outcomes —
  • naive            : emits the base σ for everyone (the v1 bug — booms underestimated)
  • predictability-aware : widens σ by 1 + MC_VOL_GAIN·(1−ρ)  (v2.2.3.1)
and assert the aware model is better calibrated on the volatile cohort.

Run:  python calibration_check.py
"""
from __future__ import annotations

import random

from models.calibration import pit_values, calibration_error, reliability_table
from models.value_engine import MC_VOL_GAIN

# The real world is more volatile for low-ρ players than the base σ admits. We don't
# know this gain exactly (the backtest tunes MC_VOL_GAIN, v2.4.3); pick a true gain in
# the same ballpark to show directional improvement, not a fit-to-self.
TRUE_VOL_GAIN = 0.7
N = 6000


def _world(seed: int = 5):
    """Synthesize (mean, base_sigma, rho, realized) for a population of players."""
    rng = random.Random(seed)
    rows = []
    for _ in range(N):
        mean = rng.uniform(60, 320)
        base_sigma = mean * rng.uniform(0.20, 0.30)
        rho = rng.betavariate(2, 2)                       # spread of predictabilities
        true_sigma = base_sigma * (1 + TRUE_VOL_GAIN * (1 - rho))
        realized = rng.gauss(mean, true_sigma)
        rows.append((mean, base_sigma, rho, realized))
    return rows


def _print_diagram(label: str, pit: list[float]) -> None:
    print(f"\n{label}  (error={calibration_error(pit):.3f})")
    for lo, hi, frac in reliability_table(pit, bins=10):
        bar = "█" * round(frac * 100)
        flag = "" if abs(frac - 0.1) < 0.03 else "  ←"
        print(f"  [{lo:.1f},{hi:.1f})  {frac:5.1%} {bar}{flag}")


def main() -> None:
    rows = _world()
    means = [r[0] for r in rows]
    realized = [r[3] for r in rows]

    naive_sigma = [r[1] for r in rows]
    aware_sigma = [r[1] * (1 + MC_VOL_GAIN * (1 - r[2])) for r in rows]

    pit_naive = pit_values(means, naive_sigma, realized)
    pit_aware = pit_values(means, aware_sigma, realized)
    _print_diagram("naive (base σ for everyone)", pit_naive)
    _print_diagram("predictability-aware σ", pit_aware)

    err_naive, err_aware = calibration_error(pit_naive), calibration_error(pit_aware)
    assert err_aware < err_naive, f"widening did not improve calibration ({err_aware} vs {err_naive})"

    # Focus on the volatile cohort (ρ < 0.4) — the players the fix targets.
    vol_rows = [r for r in rows if r[2] < 0.4]
    vm = [r[0] for r in vol_rows]
    vr = [r[3] for r in vol_rows]
    vpn = pit_values(vm, [r[1] for r in vol_rows], vr)
    vpa = pit_values(vm, [r[1] * (1 + MC_VOL_GAIN * (1 - r[2])) for r in vol_rows], vr)
    print(f"\nvolatile cohort (ρ<0.4, n={len(vol_rows)}): "
          f"naive error={calibration_error(vpn):.3f} → aware error={calibration_error(vpa):.3f}")
    assert calibration_error(vpa) < calibration_error(vpn)

    print(f"\n✓ predictability-aware σ improves calibration "
          f"(overall {err_naive:.3f}→{err_aware:.3f}); volatile booms no longer underestimated.")


if __name__ == "__main__":
    main()
