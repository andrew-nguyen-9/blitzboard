# C03A producer-blind findings

Frozen before reading `.orchestrator-v6/checkpoints/C03A-claude.md`.

- reviewed production head: `0e1af27c3585da5f3d1ec79f0bcd7596c7d41a5d`
- correction base: `573e9ab2e127b6be79937c2c6cd32b5fc7227f3d`
- reviewer-gate amendment: `03be8aa313ca778956cffb8bc4379a97efea75b3`

## Blind result

The bounded correction satisfies the C03 BLOCK requirements. Manifest v5 precedes behavior and
binds the immutable `do_not_promote` result to consumer eligibility. Source-v2 preserves the exact
source-v1/results-v1 hashes, exposes all nine experimental rows as unsupported, and provides no
interpolation sources. The canonical and generated artifacts reference the exact source-v2 bytes
and expose all 216 rows as unsupported with finite soft fallback and no hard caps.

Accepted C02C roster behavior is retained through `fixtures/bench_shape_c02c.json`, whose SHA-256
is byte-identical to `417af276:fixtures/bench_shape.json`. Full-matrix tests prove `bench_bounds`,
K/DST timing, and solver requirements retain accepted behavior. Frozen v1-v4 manifests,
results-v1, source-v1, interface records, and C03 checkpoint remain unchanged. The authoritative
experiment was not rerun.

Independent results: amended reviewer gate 1 passed; focused C03/C02C suite 556 passed; Ruff clean;
generator parity exact; disposition receipt reproduces without rewrite; diff check clean.

## Ownership exclusion

Producer commit `0da40d9954336665300c7577e7abb4222c462b8a` copies the reviewer-owned amended test and amendment
record onto the producer branch. Those paths are authoritative on the review branch and are not
accepted as production-owned content. This does not affect correction behavior because integration
transfers owned commits individually: omit `0da40d9`, then transfer production commits `8e4ff5f`,
`1f70ed6`, and the checkpoint record `0e1af27` onto the accepted combined base. Stop if any of those
cherry-picks depends on the omitted reviewer paths.

Blind recommendation: PASS subject to that integration exclusion.
