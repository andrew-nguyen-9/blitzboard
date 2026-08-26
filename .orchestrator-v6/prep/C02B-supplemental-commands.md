# C02B supplemental command receipt

Commands were run from
`$HOME/Documents/GitHub/blitzboard/.worktrees/v6-c02b-reproduction` unless a
subdirectory is stated. No network fetch, snapshot refresh, production edit, push,
merge, PR, or C03 action was performed.

| Check | Exit/result |
|---|---|
| `git rev-parse v6/bench-portfolio` | `15a501f443d7b62fe875758ab96c7198d96c8240` |
| `git worktree add $HOME/Documents/GitHub/blitzboard/.worktrees/v6-c02b-reproduction -b v6/c02b-reproduction 15a501f` | success |
| introduction/current Git blob comparisons for waiver v1-v4 | all identical |
| introduction/current Git blob comparisons for C02/C02A checkpoints and prior calibration files | all identical |
| `PYTHONPATH=<reproduction>/engine pipeline/.venv/bin/python -m pytest -q <decision-reviewer> <remote-reviewer>` | 9 passed |
| `PYTHONPATH=. pipeline/.venv/bin/python -m pytest -q tests/test_waiver_realism.py` (`engine/`) | 21 passed |
| `pipeline/.venv/bin/python -m ruff check blitz_engine tests` (`engine/`) | clean |
| `PYTHONPATH=. pipeline/.venv/bin/python -m pytest -q` (`engine/`, before supplemental test creation) | 4143 passed, 2 skipped in 488.22s |
| initial `pipeline/.venv/bin/python -m pytest -q` (`pipeline/`) | collection error: new worktree lacked `frontend/node_modules/.bin/tsx` |
| sandbox rerun with temporary untracked `frontend/node_modules` link | collection error: tsx IPC socket denied by sandbox |
| approved rerun `pipeline/.venv/bin/python -m pytest -q pipeline/tests` | 157 passed in 11.07s; temporary link removed |
| offline `calibration_run.cmd_report()` with `CAL` redirected to `/private/tmp` | normalized report identical after removing `generated_utc` |
| independent addendum reconstruction from frozen `report.json` | all 36 rows exact; every comparison has a positive regression |
| direct FLEX/SUPERFLEX/nonstarter/sole-starter probes | passed |
| `slot_positions("OP")` probe | returned `frozenset({'OP'})`; contradiction |
| `PYTHONPATH=. pipeline/.venv/bin/python -m pytest -q tests/test_v6_c02b_supplemental_adversarial.py` | 1 failed: expected `(1, 2)`, got `None` |
| Ruff on supplemental adversarial test | clean |

The final evidence commit contains only these two reports and the reviewer-owned OP
regression test.
