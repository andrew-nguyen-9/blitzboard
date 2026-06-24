# Versioning — `v[phase].[segment].[task]`

The project version is a three-part coordinate that doubles as a work-breakdown address.

```
v 2 . 3 . 2
  │   │   └── task     — one atomic, reviewable unit of work
  │   └────── segment  — a shippable slice of a phase (its own sub-branch)
  └────────── phase    — a major body of work (its own branch: v2, v3, …)
```

- **Phase** (`v2`) — a major release theme. Opens a long-lived branch off `main`.
- **Segment** (`v2.3`) — a coherent slice that can be built, tested, reviewed, and merged
  back to the phase branch on its own. Opens a sub-branch off the phase branch.
- **Task** (`v2.3.2`) — the smallest tracked unit. One commit (or a tight cluster), one
  clear acceptance criterion.

## Lineage

- **v1.0.0** = all pre-restructure work (P0–P7), now frozen in `docs/archive/v1/`.
- **v2.0.0** = the start of the new structure (this restructure + Foundation phase).
- Phases run `v2.0` … `v2.7` (see `docs/phases/v2/PHASES_OVERVIEW.md`). The next major
  release theme becomes `v3`.

## Tag / release mapping (SemVer-compatible)

We piggyback on SemVer so tooling and changelogs stay standard:

- Completing a **phase** → tag `v2.<phase>.0` and a GitHub Release (e.g. finishing the
  Scoring phase tags `v2.2.0`).
- A **patch** to a shipped phase → bump the third number (`v2.2.1`).
- The `v[p].[s].[t]` address is used in **branch names, commit scopes, task IDs, and PR
  titles**; the **git tag** uses the SemVer collapse at phase boundaries.

## Naming everywhere

| Artifact | Format | Example |
|----------|--------|---------|
| Phase branch | `v<phase>` | `v2` |
| Segment sub-branch | `v<phase>.<segment>-<slug>` | `v2.3-player-data` |
| Task commit | `v2.3.2 <scope>: <summary>` | `v2.3.2 players: keyset pagination` |
| Phase doc | `docs/phases/v<p>/v<p>.<s>-<slug>.md` | `docs/phases/v2/v2.3-player-data.md` |
| Release tag | `v<p>.<s>.0` | `v2.3.0` |

See `docs/workflow/GIT_WORKFLOW.md` for the branch/merge ritual.
