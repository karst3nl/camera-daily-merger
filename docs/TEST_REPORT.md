# Test report

## Phase 0 — Repository bootstrap (2026-11-13)

Branch: alpha. Runtime: Python 3.12.14, Linux. No media or NAS accessed.

Exact commands:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[dev]'
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python -m build
.venv/bin/python -m compileall -q camera_daily_merger
.venv/bin/python -m pip check
.venv/bin/python work/scan.py
git diff --check
git status --short
```

Results: 1 test passed, 0 failed. Lint, formatting, isolated wheel/sdist build,
syntax, dependency consistency and tracked/candidate file review passed. Initial
package installation rejected a license field incompatible with pinned
setuptools; corrected to reference LICENSE and installation/build rerun passed.
The local scan checks private IPv4, token/private-key patterns and prohibited
media/state file suffixes; this is a heuristic plus manual diff review, not proof
that arbitrary secrets cannot exist. The scan script is scratch tooling.
MIT license preserved. CI workflow created; hosted CI has not yet been observed.
Real Home Assistant/NAS tests NOT RUN; not applicable to bootstrap gate.
Next: Phase 1 add-on metadata, startup service and container validation.
