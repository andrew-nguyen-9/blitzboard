# C02 remote reproduction commands

Commands were run from `$HOME/Documents/GitHub/blitzboard-c02-reproduction` unless noted. No external service or snapshot command was used.

| Command | Exit | Runtime/result |
|---|---:|---|
| `shasum -a 256 $HOME/Downloads/blitzboard-v6-20260826.bundle` | 0 | expected bundle hash |
| `git bundle verify $HOME/Downloads/blitzboard-v6-20260826.bundle` | 0 | complete history, five refs |
| `git rev-parse v6/bench-portfolio` | 0 | `edbcc4d743b447ebcbbfe84a0e1210380c6250d1` |
| `python3.12 -m venv pipeline/.venv` plus repository-declared pip installs | 0 | fresh worker environment |
| `pipeline/.venv/bin/python -m pytest engine/tests/test_v6_c02_remote_adversarial.py -q` | 1 | 3 failed, 3 passed in 1.44s |
| gzip content SHA-256 checks | 0 | all four hashes matched `promotion-v3.json` |
| offline v5 `cmd_boards` from baseline git archive | 0 | content hash `5898efdd…42e3` |
| offline v6 `cmd_boards` from production tree | 0 | content hash `0590fd2d…eff4` |
| offline `cmd_report` with redirected temporary output | 0 | normalized report identical |
| immutable manifest/amendment/promotion hash comparisons | 0 | all pairs byte-identical |
| `pytest tests/test_waiver_realism.py tests/test_league_sim.py tests/test_roster_shape.py -q` | 0 | 971 passed, 1 skipped; 14.40s wall |
| initial `pytest pipeline/tests -q` before frontend install | 2 | missing local `frontend/node_modules/.bin/tsx`; setup-only collection error |
| `npm ci` in `frontend` | 0 | 426 locked packages installed; 6 existing high-severity advisories reported |
| rerun `pytest pipeline/tests -q` | 0 | 157 passed; 3.79s wall |
| full engine suite including reviewer red tests | 1 | 3 failed, 4137 passed, 1 skipped; 192.44s wall |
| production-only full engine suite (`--ignore=tests/test_v6_c02_remote_adversarial.py`) | 0 | 4134 passed, 1 skipped; 176.35s wall |
| remote deterministic tie test | 0 | 1 passed in 1.56s |
| `ruff check engine/tests/test_v6_c02_remote_adversarial.py` | 0 | clean |
| `git diff --check` | 0 | clean at pre-record checkpoint |
| final focused remote adversarial suite | 1 | 3 failed, 4 passed in 1.58s; failures intentionally preserved |
