# C03 producer-blind findings

Frozen before reading `.orchestrator-v6/checkpoints/C03-claude.md`.

- reviewed production head: `573e9ab2e127b6be79937c2c6cd32b5fc7227f3d`
- accepted base: `417af276dd4438d8a35f38d08bfc26206044925e`
- reconciled interface: `a3394b0a6c72174894bd8a44b33c702372903d11`
- experiment implementation head: `cde6518facef12fa483cadbcd684f9281a8c0745`

## Blind deterministic finding

The authoritative receipt records `do_not_promote`, all nine mandatory slices fail at least one
frozen superiority threshold, and the known 14-team 2QB slice remains red. The cumulative v1/v2
failure interpretation requires `DO_NOT_PROMOTE_PRESERVE_C02C_BEHAVIOR`.

The canonical source nevertheless labels eight failed candidate selections `measured`; the
generator publishes those selections plus 207 interpolations as supported schema-v2 soft costs.
On that schema, `roster_shape.to_requirements` also removes the accepted C02C independent bench
bounds. Thus integration would replace accepted behavior with failed candidate guidance instead
of retaining the candidate only as negative experimental evidence.

The reviewer-owned adversarial test requires every failed-candidate source/artifact row to remain
unsupported. It is expected to fail against this checkpoint. This is a deterministic promotion-
disposition contradiction, not a numerical disagreement.

No producer rationale was consulted before freezing this finding.
