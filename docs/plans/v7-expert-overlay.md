# v7 expert overlay brief

## Outcome

Add the August 2026 Smores workbook consensus as a temporary, display-only supplement to the
manual draft board while v6 remains unlanded. VORP remains the default order and draftAI,
recommendations, simulations, and scoring are unchanged.

## Inputs and extraction

- `artifacts/Smores_2026_Live_Draft_Backup_11-Team.xlsx`
- `artifacts/Smores_2026_Live_Draft_Backup_12-Team.xlsx`
- One dependency-free OOXML extraction script writes a deterministic static JSON artifact keyed by
  team count. It reads only static Player Board cells; Excel live formulas are excluded.
- Preserve source date/provenance, model rank, tier, ESPN rank, market/FFPC/Sleeper ADP, market
  edge, risk, upside, injury/status, expert note, expert average, spread, rating, and confidence.

## Matching and UI

- Match by normalized player name plus normalized position (`DEF` and `DST` are equivalent).
- A key must resolve to exactly one BlitzBoard player. Missing and ambiguous names are surfaced in
  an overlay status line and never silently selected or discarded.
- Show a compact Expert chip with model rank, market ADP, risk, and upside on the Player Board.
- Highlight a disagreement when expert model rank and VORP rank differ by at least 24 overall
  places. Label whether experts are higher (`opportunity`) or the local model is higher (`landmine`).
- Missing/malformed overlay data is a no-op; the existing board remains fully usable.

## Explicit exclusions

- No changes to sort order, candidate pool, draftAI score, recommendations, simulation, persistence,
  or league configuration.
- No runtime workbook parser and no new dependency.

## Verification

- Extraction tests: static cells, both team counts, deterministic 300-row boards.
- Frontend tests: normalization, `DEF`/`DST`, missing and ambiguous matches, and the 24-rank signal.
- Frontend typecheck, lint, focused tests, production build, and repository diff review.

## Integration handoff

When this main-based unit merges into `v7-integration`, add the two source workbooks under the
main checkout's `artifacts/` directory to the draft runbook's laptop-failure fallback. The U4
runbook does not exist on this unit branch, so editing it here would create an add/add conflict.
