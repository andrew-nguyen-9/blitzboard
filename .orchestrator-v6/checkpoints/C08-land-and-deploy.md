# C08 land and deploy

Disposition: **PASS — DEPLOYED AND VERIFIED**

- pull request: `#113` (`v6/bench-portfolio-land` → `main`)
- reviewed producer: `ea706a393d50fbb328131cea5ec532436303e922`
- landing cleanup: `61fa20fa42a54ef36abcded14b15fc6c52f6c924`
- merge commit: `f26a6838ddc83e5780980fb464d67a526d8efdf1`
- production deployment: Vercel `6149025208`
- canonical production URL: `https://blitzboard.an9.dev`
- deployment window: Friday, 2026-08-28 04:38:12–04:49:40 PM CDT (`-0500`)

## Landing evidence

The real merge reproduced the C07 rehearsed tree before cleanup. A base-to-head `git diff --check`
then exposed three historical whitespace-only defects across three v6-added files. C07's clean diff
claim was therefore inaccurate. The landing branch removed only those trailing/terminal blank lines,
the focused C05 freeze probe passed 2/2 with `C05_PROD_ROOT` bound, and the corrected base-to-head
diff check passed before push.

PR checks passed: Vercel preview, frontend build/typecheck/lint/tests, the personal-identity scan,
and Playwright axe smoke. GitHub merged PR #113 at 04:44:56 PM CDT. The post-merge `main` CI run
`33213896564` independently passed the same build/typecheck/lint/tests, identity scan, and axe smoke.
The only annotations were GitHub action-runtime Node 20 deprecation notices.

## Runtime and production evidence

The exact landing branch ran locally with Next.js 15.5.19 in no-key offline mode. `/`, `/draft`, and
`/players` returned 200; the browser rendered the home page with real empty-state content and zero
console errors. The local `/rankings` probe returned the expected 404 because no such route exists.

Vercel reported the production deployment successful for the exact merge SHA. On the canonical
domain, `/`, `/draft`, `/players`, `/league`, `/waivers`, `/trades`, `/about`, `/privacy`, and `/terms`
all returned 200. Browser canaries rendered Home, Draft Board, Player Explorer, the authenticated
League redirect, Waiver Wire, and Trade Calculator with main content and zero console errors. Browser
navigation completed in 0.26–1.93 seconds for the checked product surfaces.

The GitHub repository homepage had remained set to stale `https://draft.an9.dev`, which returned
Vercel `DEPLOYMENT_NOT_FOUND`. Repository docs, metadata, sitemap, and robots all identify
`https://blitzboard.an9.dev` as canonical. The GitHub homepage setting was corrected to that URL;
no code change or Vercel-domain mutation was necessary.

## Authority and remaining limitations

C05 promotion remains excluded and parked. Shipped v5 remains production authority. This landing
does not reinterpret the absent C05 auxiliary evidence or promote the v6 candidate path.

The primary checkout remains deliberately untouched at `9192163b5be121e645e5574d7e04855725b4895f`
with its pre-existing user-owned changes. The landing evidence branch remains available because the
GitHub CLI could not perform local branch cleanup while that checkout owned `main`; no force or
destructive cleanup was attempted.
