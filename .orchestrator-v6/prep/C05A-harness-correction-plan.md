# C05A v4-harness authority/provenance correction — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans (inline) or
> superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Correct the five deterministic authority/provenance blockers the independent reviewer
raised at `6c63808` (BLOCK), as reusable harness infrastructure, without editing any frozen file
or running anything authoritative.

**Architecture:** Every correction lands in `engine/blitz_engine/promotion/harness_v4.py` plus new
test files. No frozen manifest, no accepted policy file, and none of `execution.py`, `runner.py`,
`manifest.py`, `season_eval.py` is modified — so req 8 (byte-for-byte preservation) holds by
construction. The reviewer probe from `6c63808` is copied in UNCHANGED and becomes the acceptance
gate; each refusal gets its own adversarial test.

**Tech Stack:** Python 3.12, pytest 9.1.1, numpy; engine venv at
`$HOME/Documents/GitHub/blitzboard/pipeline/.venv`.

## Global Constraints (verbatim, apply to every task)

- No authoritative run; no policy bridge; no new manifest/experiment version; no calibration
  reinterpretation; no push/merge/PR.
- Preserve every frozen file and accepted policy file byte-for-byte (manifests, `execution.py`,
  `runner.py`, `season_eval.py`, measurement-evaluator files, arm code).
- Run only non-authoritative tests/rehearsals. Stop at a clean immutable C05A checkpoint for
  re-review. C05 stays parked; v5 preserved regardless of C05A outcome.
- Interpreter/cwd (worktree gotcha): `cd engine && PYTHONPATH="$PWD"
  "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m pytest ...`.
- Frozen identities (already module constants): `BASELINE_SHA=01f01d3c…`,
  `CANDIDATE_SHA=7b3fd735…`; arm names `v5_shipped`/`v6_candidate` (exec-v2 `arms`).
- Reviewer probe (copy unchanged): `engine/tests/test_v6_c05_harness_authority_adversarial.py`
  from `v6/bench-portfolio-review` @ `6c63808` (blob sha256 `33e759b954799d112…`).

## File Structure

- Modify: `engine/blitz_engine/promotion/harness_v4.py` — all six enforcement changes + helpers.
- Create: `engine/tests/test_v6_c05_harness_authority_adversarial.py` — reviewer probe, UNCHANGED.
- Create: `engine/tests/test_v6_c05a_authority_correction.py` — one adversarial test per refusal.
- Create (checkpoint doc): `.orchestrator-v6/checkpoints/C05A-harness-correction.md`.

## New/changed public API in `harness_v4.py`

- `ARM_POLICY_SHAS: dict[str,str]` — `{"v5_shipped": BASELINE_SHA, "v6_candidate": CANDIDATE_SHA}`.
- `validate_draft_receipt(receipt, row, board_ids)` — **adds** unconditional arm↔policy_sha bind.
- `mandatory_league_ids(effective) -> frozenset[str]` — 216, asserted against manifest count.
- `recompute_seat_policy(eval_seed, teams, effective) -> list[str]`.
- `effective_v4_manifest_sha256(effective) -> str`.
- `validate_authoritative_draft_receipt(receipt, row, board_ids, effective, *, stage) -> None`.
- `write_fit_verdict(out_dir, *, effective, fit_measure_paths) -> Path`.
- `require_fit_verdict(out_dir, effective) -> dict`.
- `draft_arm(...)` / `measure_arm(...)` — authority-match, authoritative constraints, v4 binding,
  confirm-stage fit-verdict gate wired in.

---

### Task 0: Copy reviewer probe unchanged + record preservation baseline

**Files:**
- Create: `engine/tests/test_v6_c05_harness_authority_adversarial.py`
- Test: itself

- [ ] **Step 1: Copy the probe byte-for-byte from the review commit**

```bash
cd "$HOME/Documents/GitHub/blitzboard/.worktrees/v6-c05a-harness-correction"
git show v6/bench-portfolio-review:engine/tests/test_v6_c05_harness_authority_adversarial.py \
  > engine/tests/test_v6_c05_harness_authority_adversarial.py
shasum -a 256 engine/tests/test_v6_c05_harness_authority_adversarial.py
# expect 33e759b954799d112d88793c43cc1937b097a42ec92907ac7d42ff18909e3551
```

- [ ] **Step 2: Record frozen-file baseline hashes (req 8 guard)**

```bash
for f in engine/blitz_engine/promotion/execution.py \
  engine/blitz_engine/promotion/runner.py engine/blitz_engine/promotion/manifest.py \
  engine/blitz_engine/simulation/season_eval.py \
  .orchestrator-v6/experiments/promotion-v3.json \
  .orchestrator-v6/experiments/promotion-v4.json \
  .orchestrator-v6/experiments/promotion-v4-exec-v2.json ; do shasum -a 256 "$f"; done \
  | tee /tmp/c05a-frozen-baseline.txt
```

- [ ] **Step 3: Run the probe — test 1 must FAIL (no arm↔policy bind yet), test 2 must PASS**

```
cd engine && PYTHONPATH="$PWD" "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  -m pytest tests/test_v6_c05_harness_authority_adversarial.py -q
```
Expected: `test_draft_receipt_refuses_arm_policy_identity_mismatch` FAILS (Failed: DID NOT RAISE);
`test_authoritative_constraints_are_frozen_in_effective_manifest` PASSES.

- [ ] **Step 4: Commit** — `test(c05a): import unchanged reviewer authority probe from 6c63808`

---

### Task 1: req 3 — bind arm → frozen policy SHA in `validate_draft_receipt`

**Files:** Modify `harness_v4.py`; Test: reviewer probe test 1 + new adversarial test.

**Interfaces:** Produces `ARM_POLICY_SHAS`; extends `validate_draft_receipt` (same 3-arg signature).

- [ ] **Step 1: Add the mapping + unconditional check** (after the `kind` check, before roster shape)

```python
ARM_POLICY_SHAS = {"v5_shipped": BASELINE_SHA, "v6_candidate": CANDIDATE_SHA}
```
Inside `validate_draft_receipt`, immediately after the `kind` guard:
```python
    want_sha = ARM_POLICY_SHAS.get(receipt.get("arm"))
    if want_sha is None:
        raise ExecutionError(f"draft receipt arm {receipt.get('arm')!r} is not a frozen arm name")
    if receipt.get("policy_sha") != want_sha:
        raise ExecutionError(
            f"arm {receipt['arm']!r} bound to policy_sha {receipt.get('policy_sha')!r} "
            f"does not match its frozen policy identity {want_sha}"
        )
```

- [ ] **Step 2: Run reviewer probe test 1 — now PASSES**

```
PYTHONPATH="$PWD" <venv> -m pytest \
  tests/test_v6_c05_harness_authority_adversarial.py::test_draft_receipt_refuses_arm_policy_identity_mismatch -q
```
Expected: PASS (raises ExecutionError matching `arm.*policy`).

- [ ] **Step 3: Run existing harness suite — 13/13 still green** (fixture is `v6_candidate/CANDIDATE`)

```
PYTHONPATH="$PWD" <venv> -m pytest tests/test_promotion_harness_v4.py -q
```
Expected: all pass (no existing test uses an inconsistent arm/policy pair).

- [ ] **Step 4: Commit** — `feat(c05a): bind draft-receipt arm to frozen policy SHA (blocker 3)`

---

### Task 2: req 1 — draft/measurement authority must match; reject authoritative use of non-authoritative input

**Files:** Modify `measure_arm` (and `draft_arm` symmetry); Test: new adversarial.

- [ ] **Step 1: Write failing test** in `test_v6_c05a_authority_correction.py`

```python
def test_measure_refuses_authoritative_on_nonauthoritative_draft(tmp_path):
    # a non-authoritative draft receipt cannot be laundered into an authoritative measurement
    receipt = _write_draft_receipt(tmp_path, authoritative=False)
    with pytest.raises(ExecutionError, match="authorit"):
        measure_arm(receipt, MEAS_CHECKOUT, effective=EFFECTIVE, n_seasons=8,
                    guard=GUARD, out_dir=tmp_path, tooling_root=REPO, authoritative=True)
```
(Uses a real fit draft receipt from `prep/c05-v4-rehearsal/draft/fit`, copied to tmp_path.)

- [ ] **Step 2: Run — FAILS** (currently no authority check). Expected: DID NOT RAISE.

- [ ] **Step 3: Implement** — at the top of `measure_arm`, after reading `receipt`:

```python
    if bool(authoritative) != bool(receipt.get("authoritative", False)):
        raise ExecutionError(
            "authority mismatch: draft receipt authoritative="
            f"{receipt.get('authoritative')} but measurement authoritative={authoritative}; "
            "draft and measurement authority must match and authoritative runs refuse "
            "non-authoritative input"
        )
```
Add the mirror guard in `draft_arm` is not needed (draft has no upstream receipt); document that.

- [ ] **Step 4: Run — PASSES**; re-run `test_promotion_harness_v4.py` — still green.

- [ ] **Step 5: Commit** — `feat(c05a): require matching draft/measurement authority (blocker 1)`

---

### Task 3: req 2 — authoritative constraints derived exclusively from the frozen manifest

**Files:** Modify `harness_v4.py` (add `mandatory_league_ids`, arm-name/SHA from `_v4`, authoritative
constraint checks in `draft_arm`/`measure_arm`); Test: reviewer probe test 2 (already green) + new.

- [ ] **Step 1: Extend `_v4` overlay** in `load_execution_manifest_v4` with the exec-v2 arm map:

```python
    exec_v2_arms = {a["name"]: a.get("policy_sha") or a.get("combined_candidate_sha")
                    for a in exec_v2["arms"].values()}
    effective["_v4"]["arm_shas"] = exec_v2_arms      # {"v5_shipped": "01f01d3c…", "v6_candidate": "7b3fd735…"}
```

- [ ] **Step 2: Add `mandatory_league_ids`**

```python
def mandatory_league_ids(effective) -> frozenset[str]:
    from blitz_engine.testing import matrix
    ids = frozenset(r["id"] for r in matrix.all()
                    if int(r["teams"]) in (10, 12, 14) and int(r["bench_slots"]) in (4, 8))
    want = int(effective["league_configurations"]["mandatory_league_id_count"])
    if len(ids) != want:
        raise ExecutionError(f"derived {len(ids)} mandatory league ids != frozen {want}")
    return ids
```

- [ ] **Step 3: Write failing tests** (authoritative draft_arm refuses off-manifest caller args)

```python
def test_authoritative_refuses_nonframe_base_seed(): ...   # base_seed not in seed_derivation.base_seeds
def test_authoritative_refuses_nonmandatory_league(): ...  # e.g. a t8-* or bench6 id
def test_authoritative_measure_refuses_n_seasons_override(): ...  # n_seasons != 8
```
Each expects `ExecutionError` from an `authoritative=True` call with the offending value.

- [ ] **Step 4: Run — FAIL.**

- [ ] **Step 5: Implement `_check_authoritative_frame`** and call it in `draft_arm`/`measure_arm`
      when `authoritative`:

```python
def _check_authoritative_frame(effective, *, year, league_id, base_seed, arm,
                               expected_sha, stage, n_seasons=None) -> None:
    sd = effective["seed_derivation"]
    if int(base_seed) not in [int(s) for s in sd["base_seeds"]]:
        raise ExecutionError(f"authoritative base_seed {base_seed} not in frozen base_seeds")
    allowed_years = set(effective["seasons"]) if stage == "fit" else set(effective["held_out_seasons"])
    if int(year) not in allowed_years:
        raise ExecutionError(f"authoritative year {year} not frozen for stage {stage!r}")
    if str(league_id) not in mandatory_league_ids(effective):
        raise ExecutionError(f"authoritative league_id {league_id} not in the frozen 216-mandatory set")
    arm_shas = effective["_v4"]["arm_shas"]
    if arm not in arm_shas:
        raise ExecutionError(f"authoritative arm {arm!r} is not a frozen arm name")
    if expected_sha != arm_shas[arm]:
        raise ExecutionError(f"authoritative arm {arm!r} SHA {expected_sha} != frozen {arm_shas[arm]}")
    if n_seasons is not None and int(n_seasons) != int(effective["evaluator"]["n_seasons"]):
        raise ExecutionError(
            f"authoritative n_seasons {n_seasons} != frozen {effective['evaluator']['n_seasons']}")
```
Wire: `draft_arm` (authoritative) calls it with `stage`; `measure_arm` (authoritative) calls it with
`n_seasons` and the receipt's frame after reading it.

- [ ] **Step 6: Run — new tests PASS; reviewer probe test 2 PASS; existing suite green.**

- [ ] **Step 7: Commit** — `feat(c05a): derive authoritative frame from frozen manifest (blocker 2)`

---

### Task 4: req 4 — recompute and enforce deterministic seat-policy (authoritative)

**Files:** Modify `harness_v4.py`; Test: new adversarial.

- [ ] **Step 1: Add `recompute_seat_policy`**

```python
def recompute_seat_policy(eval_seed, teams, effective) -> list[str]:
    import numpy as np
    from blitz_engine.simulation.season_eval import DEFAULT_POLICY_MIX
    draft_stream = int(effective["seed_derivation"]["stream_offsets"]["draft"])   # 303
    rng = np.random.default_rng(int(eval_seed) + draft_stream)
    seats = [DEFAULT_POLICY_MIX[i % len(DEFAULT_POLICY_MIX)] for i in range(int(teams))]
    rng.shuffle(seats)
    return seats
```

- [ ] **Step 2: Write failing test** — an authoritative receipt with a tampered `seat_policy` is refused;
      an untampered real receipt passes the seat-policy check.

```python
def test_authoritative_refuses_tampered_seat_policy(tmp_path):
    receipt = _real_authoritative_like_receipt(tmp_path)         # real seat_policy
    receipt["seat_policy"] = list(reversed(receipt["seat_policy"]))
    with pytest.raises(ExecutionError, match="seat.policy|seat_policy"):
        validate_authoritative_draft_receipt(receipt, ROW, BOARD, EFFECTIVE, stage="fit")
```

- [ ] **Step 3: Run — FAIL.**

- [ ] **Step 4: Implement `validate_authoritative_draft_receipt`** (calls `validate_draft_receipt`
      first, then the authoritative-only checks incl. seat-policy + frame + v4 binding):

```python
def validate_authoritative_draft_receipt(receipt, row, board_ids, effective, *, stage) -> None:
    validate_draft_receipt(receipt, row, board_ids)                    # shape + arm↔policy
    _check_authoritative_frame(effective, year=receipt["year"], league_id=receipt["league_id"],
        base_seed=receipt["base_seed"], arm=receipt["arm"], expected_sha=receipt["policy_sha"],
        stage=stage)
    want = recompute_seat_policy(receipt["eval_seed"], int(row["teams"]), effective)
    if list(receipt["seat_policy"]) != want:
        raise ExecutionError("draft receipt seat_policy does not match the deterministic assignment")
    _require_v4_binding(receipt, effective)                            # Task 5
```
Wire `measure_arm(authoritative=True)` to call this instead of the plain validator.

- [ ] **Step 5: Run — PASS; existing suite green** (plain `validate_draft_receipt` unchanged for
      non-authoritative synthetic fixtures).

- [ ] **Step 6: Commit** — `feat(c05a): enforce deterministic seat-policy on authoritative receipts (req 4)`

---

### Task 5: req 6 — bind every draft receipt to v4 + exec-v2 + effective-v4-manifest hash

**Files:** Modify `draft_arm` (emit binding) + add `effective_v4_manifest_sha256` + `_require_v4_binding`.

- [ ] **Step 1: Add the deterministic effective-v4 hash + binding checker**

```python
def effective_v4_manifest_sha256(effective) -> str:
    import hashlib, json
    return hashlib.sha256(
        json.dumps(effective, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()

def _require_v4_binding(receipt, effective) -> None:
    if receipt.get("manifest_sha256") != V4_MANIFEST_SHA256:
        raise ExecutionError("draft receipt not bound to promotion-v4 manifest hash")
    if receipt.get("exec_addendum_sha256") != EXEC_V2_SHA256:
        raise ExecutionError("draft receipt not bound to exec-v2 addendum hash")
    if receipt.get("effective_v4_manifest_sha256") != effective_v4_manifest_sha256(effective):
        raise ExecutionError("draft receipt effective-v4-manifest hash mismatch")
```

- [ ] **Step 2: Write failing test** — a draft receipt missing v4 binding is refused by
      `validate_authoritative_draft_receipt`; `draft_arm` output includes all three fields.

- [ ] **Step 3: Run — FAIL.**

- [ ] **Step 4: Emit the binding in `draft_arm`'s receipt dict**

```python
        "manifest_sha256": V4_MANIFEST_SHA256,
        "exec_addendum_sha256": EXEC_V2_SHA256,
        "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
```

- [ ] **Step 5: Run — PASS; existing suite green.**

- [ ] **Step 6: Commit** — `feat(c05a): bind draft receipts to v4/exec-v2/effective-v4 hash (blocker 5)`

---

### Task 6: req 5 — write-once hash-pinned passing fit-verdict gate before confirmation

**Files:** Modify `harness_v4.py` (`write_fit_verdict`, `require_fit_verdict`, wire confirm gate).

- [ ] **Step 1: Add producer + gate**

```python
def write_fit_verdict(out_dir, *, effective, fit_measure_paths) -> Path:
    from blitz_engine.promotion.manifest import sha256_file
    pins = {str(p): sha256_file(p) for p in sorted(map(str, fit_measure_paths))}
    doc = {"kind": "fit_verdict", "verdict": "pass",
           "manifest_sha256": V4_MANIFEST_SHA256, "exec_addendum_sha256": EXEC_V2_SHA256,
           "effective_v4_manifest_sha256": effective_v4_manifest_sha256(effective),
           "fit_receipt_sha256": pins}
    return _write_once(Path(out_dir) / "fit-verdict.json", doc)

def require_fit_verdict(out_dir, effective) -> dict:
    from blitz_engine.promotion.manifest import sha256_file
    p = Path(out_dir) / "fit-verdict.json"
    if not p.is_file():
        raise ExecutionError("confirmation blocked: no fit-verdict receipt exists")
    doc = json.loads(p.read_text())
    if doc.get("verdict") != "pass":
        raise ExecutionError(f"confirmation blocked: fit verdict is {doc.get('verdict')!r}")
    if doc.get("effective_v4_manifest_sha256") != effective_v4_manifest_sha256(effective):
        raise ExecutionError("fit-verdict effective-v4-manifest hash mismatch")
    for rel, want in doc["fit_receipt_sha256"].items():
        if not Path(rel).is_file() or sha256_file(rel) != want:
            raise ExecutionError(f"fit-verdict pinned receipt drift or missing: {rel}")
    return doc
```

- [ ] **Step 2: Write failing tests** — confirm-stage `draft_arm`/`measure_arm` refuse when no
      fit-verdict; refuse a tampered/failed verdict; a valid verdict passes the gate.

- [ ] **Step 3: Run — FAIL.**

- [ ] **Step 4: Wire the gate** — in `draft_arm` and `measure_arm`, when `stage == "confirm"`:
      `require_fit_verdict(out_dir, effective)` immediately after the stage guard, before any work.

- [ ] **Step 5: Run — PASS; existing suite green** (`test_confirm_stage_refuses_fit_year` uses the
      guard which fires on the fit-year before the gate matters; verify ordering keeps it green).

- [ ] **Step 6: Commit** — `feat(c05a): require passing fit-verdict before confirmation (blocker 4)`

---

### Task 7: req 7/8/9 — full adversarial suite green, frozen-file preservation, C05A checkpoint

**Files:** finalize `test_v6_c05a_authority_correction.py`; create checkpoint doc.

- [ ] **Step 1: Full non-authoritative engine suite from the worktree**

```
cd engine && PYTHONPATH="$PWD" "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  -m pytest tests/test_promotion.py tests/test_promotion_adapter.py \
  tests/test_promotion_execution.py tests/test_promotion_harness_v4.py \
  tests/test_v6_c05_harness_authority_adversarial.py \
  tests/test_v6_c05a_authority_correction.py -q
```
Expected: all pass (reviewer probe 2/2 green).

- [ ] **Step 2: Frozen ruff scope** (exec-v2 gate) + `harness_v4.py`

```
PYTHONPATH="$PWD" <venv> -m ruff check blitz_engine/promotion tests/test_v6_c05a_authority_correction.py
```

- [ ] **Step 3: Prove frozen files unchanged (req 8)**

```bash
shasum -a 256 -c /tmp/c05a-frozen-baseline.txt   # every line: OK
git status --porcelain   # only NEW files: harness edits, 2 test files, plan, checkpoint
git diff --stat af24062 -- engine/blitz_engine/promotion/execution.py \
  engine/blitz_engine/promotion/runner.py engine/blitz_engine/simulation/season_eval.py \
  '.orchestrator-v6/experiments/*.json'   # empty
```

- [ ] **Step 4: Write `.orchestrator-v6/checkpoints/C05A-harness-correction.md`** — append-only
      record: reviewed BLOCK `6c63808`, each blocker→fix→test, reviewer probe copied unchanged
      (sha `33e759b9…`), frozen-file preservation proof, "C05 parked / v5 preserved / no
      authoritative run", stop-for-re-review.

- [ ] **Step 5: Commit** — `docs(c05a): immutable C05A checkpoint for independent re-review`

## Self-Review

- **Spec coverage:** req1→Task2, req2→Task3, req3→Task1, req4→Task4, req5→Task6, req6→Task5,
  req7→Task0+each task's adversarial test+Task7, req8→Task7 Step3 (and by construction), req9→Task7.
- **Placeholder scan:** fixtures marked `...` in Tasks 3/4/6 are the only stubs — each is expanded
  to a concrete receipt during execution (real receipt copied from `prep/c05-v4-rehearsal`).
- **Type consistency:** `validate_authoritative_draft_receipt`, `_check_authoritative_frame`,
  `recompute_seat_policy`, `effective_v4_manifest_sha256`, `mandatory_league_ids`,
  `require_fit_verdict` names are used identically across Tasks 3–6.
