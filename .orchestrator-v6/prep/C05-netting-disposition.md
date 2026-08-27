# C05 — started-points transaction-netting disposition (2026-08-27, pre-freeze)

Append-only resolution of `C05-c02-interface-mismatches.md` item 2, checked at the accepted
combined C02–C04 head `7b3fd73578943b992402ad693259a3e92358da69` BEFORE candidate identity is
frozen. `promotion-v3.json` was not edited (byte-verified sha256
`bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab`).

## Finding

At the combined head, `season_eval.py` still computes
`per_season[s] = season_pts − waiver_cost × (emergency + upside claims)` — but
`EvalConfig.waiver_cost` defaults to **0.0** and the frozen manifest `evaluator` block
(`n_seasons: 8, waivers: true, waiver_moves_per_week: 1`) does not set `waiver_cost`. Under the
preregistered configuration the netting term is therefore **exactly zero**: the frozen
`metric_definition` wording ("mean locked-lineup regular-season points") is numerically exact for
the authoritative run as preregistered. `waiver_cost` also acts as a claim decision gate; at 0.0
that gate is inert as well.

## Disposition

- **No promotion-v4 amendment is required** for the authoritative run as preregistered: wording
  and computation coincide when `waiver_cost = 0.0`, which is both the code default and the
  manifest's (implicit) frozen configuration.
- **Binding constraint recorded:** the authoritative run MUST leave `waiver_cost` at 0.0. Running
  it with any nonzero `waiver_cost` changes the primary metric's semantics and is prohibited
  without a promotion-v4 amendment that freezes the value and rewrites `metric_definition`.
- `adapter.INTERFACE_MISMATCHES` item 2 stays in the code as the historical record; this file is
  its disposition. Mismatch item 2 is now CLOSED (conditionally: closed for waiver_cost = 0.0).

## Gate evidence on the combined head (all non-authoritative)

- 37/37 tests pass (`tests/test_promotion.py` + `tests/test_promotion_adapter.py`, worktree
  PYTHONPATH form); ruff clean on the promotion package and both test files.
- Fresh dry-run receipt at `prep/c04-accepted/C05-dryrun-receipt.json` (new subdir — the
  cherry-picked accepted-C02 receipt is preserved untouched): board-corpus hashes verified
  against the manifest; synthetic run promote/byte-stable and stamped non-authoritative; real
  null run (identical arms, CRN) → all paired deltas exactly zero, determinism proven by double
  execution, leak guard live, verdict `preserve_v5`.
- Canonical C03 artifacts unchanged at the combined head: `fixtures/bench_shape.json`
  `96cabb5f…cdde8`, `frontend/lib/generated/benchShape.generated.ts` `208ecb38…2ab0eb` (match
  the accepted-C03 reconciliation record).
