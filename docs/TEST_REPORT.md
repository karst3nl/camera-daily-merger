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

## Phase 1 — Add-on bootstrap (partial; gate BLOCKED)

Implemented repository/add-on metadata, aarch64 image, persistent /data,
read-write media map, log-only service with storage validation, Docker healthcheck
and SIGTERM/SIGINT shutdown. No media discovery/processing or network listener.
Current official configuration documentation reviewed on 2026-11-13 (SETUP.md).
Full Supervisor schema validation NOT RUN; metadata review is not that test.

Commands (all from repository root):

```sh
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
sh -n camera_daily_merger/run.sh
docker --host=unix:///var/run/docker.sock build --platform linux/arm64 -t camera-daily-merger:alpha-arm64 camera_daily_merger
docker --host=unix:///var/run/docker.sock build --platform linux/amd64 -t camera-daily-merger:test-amd64 camera_daily_merger
.venv/bin/python work/container_check.py
.venv/bin/python -m build
.venv/bin/python -m pip check
.venv/bin/python work/scan.py
git diff --check
```

Results: 4 Python tests passed, 0 failed; lint/format/shell syntax/build/dependency
checks passed. Both ARM64 and auxiliary AMD64 images built. Initial ARM64 build
failed executing chmod without emulation; fixed with COPY --chmod so cross-build
requires no ARM execution. AMD64 container passed health, restart and graceful
stop against mock data and read-only mock media mounts. ARM64 launch FAILED:
container exited before healthcheck (host is x86_64, no ARM execution support).
The scratch harness reports each platform separately; its exit code alone is
not a success criterion. ARM64 runtime gate remains BLOCKED, along with full
Supervisor schema validation. Actual HA OS / Pi 4 / Synology tests NOT RUN.
No subsequent phases started. No original recordings were used or changed.

Next: validate metadata with Supervisor tooling and run the ARM64 container on
an ARM64-capable environment; then finish Phase 1 and proceed to Phase 2.

Post-review: git diff --check caught trailing Markdown whitespace on the updated
specification status line. Removed it and reran git diff --check successfully;
this documentation-only correction is recorded in a follow-up commit.
