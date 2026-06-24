# Branch Protection — `main`

`main` is protected so it can only receive **finished, reviewed phases** through a pull
request — never a direct push. This enforces the rule in `GIT_WORKFLOW.md` ("Never commit
to `main` directly") at the platform level, not just by convention.

## The rule (as applied)

| Setting | Value | Why |
|---------|-------|-----|
| Require a pull request before merging | **on** | All changes to `main` arrive via PR (`v2` → `main` at phase finish). |
| Required approving reviews | **0** | Solo maintainer can merge their own reviewed PR; raise this when collaborators join. |
| Include administrators (`enforce_admins`) | **on** | A direct `git push origin main` is rejected even for repo admins — this is what makes the rule real. |
| Allow force pushes | **off** | History on `main` is append-only. |
| Allow deletions | **off** | `main` cannot be deleted. |
| Required status checks | _added in v2.0.1.3_ | Once CI exists, the build/typecheck/lint/axe job becomes a required check. |

## Apply / update (repo admin)

```bash
gh api -X PUT repos/<owner>/<repo>/branches/main/protection \
  --input docs/workflow/branch-protection.json
```

The request body lives in `branch-protection.json` (next to this doc) so it is reviewable
and reproducible. To add the CI check once it exists, set `required_status_checks.contexts`
to the CI job name and re-PUT.

## Verify

A direct push to `main` must be rejected:

```bash
git switch main && git commit --allow-empty -m "probe" && git push origin main
# expected: remote rejects with "protected branch hook declined" / GH006
git reset --hard HEAD~1   # undo the local probe commit
```

## Temporarily lifting it

If you ever need to bypass (rare), turn off **Include administrators** in
*Settings → Branches → main* (or set `enforce_admins:false` via the API), do the operation,
then turn it back on. Prefer a PR.
