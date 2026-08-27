# C05 promotion-v4 independent freeze review

Verdict: **BLOCK**

- reviewed C05 head: `b556d3db41d1ec303044b188855605e62a77204e`
- candidate policy SHA: `7b3fd73578943b992402ad693259a3e92358da69`
- promotion-v4 SHA-256: `47af290506a2aa9e66add39b62125c12341927814d3cbc660426cc767e32569a`
- promotion-v4-exec-v1 SHA-256: `41e33538c87cadacde3165ea05c7ceb6f42004bda8f992864c9cfa826220c208`
- preserved v3 hashes: `bbb241603a33697bff376b21a2e57e7e066c3c85186eaaab120485ec6bd941ab`,
  `24e5e50afdad75006ca3a1814317d9254ea98de25bbb97dba4b06bbee7c3b7ad`

## Accepted design

The append-only v4 design correctly separates policy identity from measurement identity. Each arm
drafts in its frozen checkout, while both roster outputs are evaluated by the same hash-pinned
accepted C02 evaluator. This makes the required paired playoff/championship evidence computable
without changing either policy arm. V3 statistics, thresholds, held-out isolation, failure
interpretations, and the failed accepted calibration disposition remain intact. The candidate and
v3 files are unchanged. The v4 manifest and addendum were committed separately, and no v4 harness
or authoritative run exists.

The mechanical provenance correction is sound: it derives HEAD, rejects tracked dirt, proves HEAD
contains the harness, and records module/effective-manifest hashes. Both prior reviewer probes pass;
the focused suite passes 47/47. Ruff passes over production/C05-owned files and the formatted first
probe. The immutable second reviewer probe retains its known E501 and must be explicitly excluded,
not described as part of a clean all-files Ruff run.

## Freeze blockers

1. `promotion-v4-exec-v1.json` freezes tooling head `bc11f54...` and calls it the receipts-
   regeneration head. Both regenerated arm receipts mechanically record `278f50e...`. The latter is
   the clean commit from which the receipts were actually generated; `bc11f54` is the subsequent
   commit that added them. The addendum therefore contradicts the evidence it purports to freeze.
2. Stage 2 requires drafted rosters to “partition the same board.” A draft consumes only
   `teams * (starter slots + bench slots)` players, leaving a shared free-agent complement, so the
   rosters cannot partition the entire board as written. The frozen validation must instead require
   expected per-seat roster sizes, globally unique drafted IDs all present on the hashed board, and
   define the undrafted board complement as the common initial free-agent pool.
3. The producer's unqualified “Ruff clean/full command passes” statement is false if the copied
   immutable second reviewer probe is included: it deterministically raises E501. This is not a
   production defect, but the executable gate scope must be frozen honestly and reproducibly.

## Required append-only correction

Preserve promotion-v4 and exec-v1 byte-for-byte. Add `promotion-v4-exec-v2.json`, committed alone,
that supersedes exec-v1 by hash and:

- records the actual rehearsal tooling head `278f50e...` separately from the later receipt commit;
- clarifies roster validation and the shared undrafted free-agent complement exactly as above;
- freezes the exact Ruff command/scope, explicitly excluding the byte-identical reviewer-owned
  second probe or recording its expected E501 separately;
- retains all v4 identities, hashes, gates, and the requirement for a passing calibration report.

Do not implement the v4 harness or execute any authoritative arm before exec-v2 receives PASS. Do
not edit immutable manifests/evidence, push, merge, or open a PR.
