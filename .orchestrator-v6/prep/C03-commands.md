# C03 preparation commands and results

Run from the dedicated `v6/c03-prep` worktree at accepted base `b81541c226dd5aeeacbe9ed79df927853a4b8954`.

```sh
PYTHONPATH=engine "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m pytest \
  engine/tests/test_v6BenchPortfolio_adversarial.py \
  engine/tests/test_v6BenchShape_adversarial.py -q -rxX
```

Result: 22 passed, 4 strict expected failures in 11.25s (initial complete focused run).

```sh
"$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m ruff check \
  scripts/v6BenchPortfolioPrototype.py \
  engine/tests/test_v6BenchPortfolio_adversarial.py \
  engine/tests/test_v6BenchShape_adversarial.py
```

Result: all checks passed.

```sh
PYTHONPATH=engine "$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" -m pytest \
  engine/tests/test_league_matrix.py engine/tests/test_feasibility.py -q
```

Result: 29 passed in 17.27s.

```sh
C03_PYTHON="$HOME/Documents/GitHub/blitzboard/pipeline/.venv/bin/python" \
  bash scripts/v6-independent-c03-gate.sh
```

Final gate result: 22 passed, 4 strict expected failures in 6.65s. The generated synthetic receipt recorded 4.010411s enumeration/scoring time, 0.63419 MiB traced peak allocation, and 24.890625 MiB process peak RSS for all nine preregistered representative slices. This is synthetic engineering evidence only, not an authoritative promotion experiment.

Expected failures:

1. canonical fixture remains legacy schema v1;
2. browser-safe generated TypeScript artifact is absent;
3. exact generation/check drift gate is absent;
4. blocked 14-team 2QB slice lacks explicit `unsupported` status in the canonical fixture.

```sh
git diff --check
```

Result before commit: pass (no output).
