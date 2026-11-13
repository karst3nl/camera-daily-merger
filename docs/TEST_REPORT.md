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

## Phase 1 — Gate completed with emulation (2026-11-13)

The previous ARM64 runtime blocker is resolved using QEMU user-mode 7.2.0,
mounted read-only into the ARM64 container and invoked explicitly (no host
binfmt/privileged changes). This tests ARM64 Python/service execution, not Pi
performance, the shell entrypoint under ARM, or actual Supervisor operation.
The native AMD64 test exercises the normal shell entrypoint.

Validated configuration against the current Home Assistant app linter schema,
upstream frenck/action-addon-linter commit
d51677290aef26cdfc835271dd3c7343ce502809. Removed five redundant defaults caught
by the first linter run; the repeated run passed. This replaces the outstanding
metadata validation gate; it is not an installation in a running Supervisor.
The linter image needed the session CA as a BuildKit secret for pip; TLS remained
enabled and the CA was not copied into the image. Reusable container checks and
CI linter/native container checks are now tracked.

Commands:

```sh
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/python -m pytest
docker --host=unix:///var/run/docker.sock run --rm -e INPUT_PATH=/repo/camera_daily_merger -e INPUT_COMMUNITY=false --mount type=bind,src=/workspace/camera-daily-merger,dst=/repo,readonly merger-addon-linter
.venv/bin/python tests/integration/check_container.py --image camera-daily-merger:alpha-arm64 --qemu work/qemu-aarch64-static
.venv/bin/python tests/integration/check_container.py --image camera-daily-merger:test-amd64
```

Results: 4 Python tests PASS, linter PASS, ARM64-emulated and AMD64-native
health/restart/shutdown/source-preservation checks PASS. Actual HA OS/NAS remains
NOT RUN / BLOCKED as explicitly permitted by the Phase 1 gate. No current
software gate failures. Proceed to Phase 2 with synthetic fixtures only.

## Phase 2 — Storage discovery and timestamping (2026-11-13)

Implemented configuration, parser protocol/ISO regex adapter, descriptor-relative
read-only source traversal, stable snapshots and JSON-lines dry-run. Original
media is not written. Reolink parsing remains UNVERIFIED; only synthetic naming
is supported by the tests. Snapshot checks cannot predict future NAS appends.

Commands:

```sh
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python -m build
.venv/bin/python -m pip check
docker --host=unix:///var/run/docker.sock build --platform linux/arm64 -t camera-daily-merger:alpha-arm64 camera_daily_merger
docker --host=unix:///var/run/docker.sock build --platform linux/amd64 -t camera-daily-merger:test-amd64 camera_daily_merger
.venv/bin/python tests/integration/check_container.py --image camera-daily-merger:alpha-arm64 --qemu work/qemu-aarch64-static
.venv/bin/python tests/integration/check_container.py --image camera-daily-merger:test-amd64
.venv/bin/python work/scan.py
git diff --check
```

Results: 25 tests passed, 0 failed (21 discovery/time/security tests plus 4
existing tests). Both images built; emulated ARM64/native AMD64 health, restart,
shutdown and original preservation passed. Lint/format/package/dependency checks
passed. Synthetic tests cover nested/unsorted/duplicate names, malformed timestamps,
source link escapes, traversal, output/staging exclusion, recent/empty/growing
files, midnight conversion and DST gaps/repeated hours. An unused test import
was fixed before tests. Actual HA OS/NAS NOT RUN. Gate passed for mock inputs;
next Phase 3 probing and stream-copy concatenation.

## Phase 3 — Probe and stream-copy merge (2026-11-13)

Commands:

```sh
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python -m build
docker --host=unix:///var/run/docker.sock build --platform linux/amd64 --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t camera-daily-merger:test-amd64 camera_daily_merger
docker --host=unix:///var/run/docker.sock build --platform linux/arm64 --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t camera-daily-merger:alpha-arm64 camera_daily_merger
.venv/bin/python tests/integration/check_container.py --image camera-daily-merger:alpha-arm64 --qemu work/qemu-aarch64-static
.venv/bin/python tests/integration/check_container.py --image camera-daily-merger:test-amd64
```

Results: 39 tests passed, 0 failed. Integration tests generate tiny synthetic
MP4 files and compare packet hashes in chronological order, duration, unchanged
source SHA256, staging cleanup and preservation of prior output. Covered single/
zero clips, odd filenames, codec/resolution/audio incompatibility, corruption,
space/write failures, snapshot changes and subprocess cancellation. Matching AAC
streams merge successfully. First packet-hash tests exposed concat auto_convert;
disabling it preserved packet hashes and passed retests. No re-encoding fallback.
Both architecture images built with pinned FFmpeg. Cross-architecture APK index
validation initially rejected missing ARM signing keys; copying keys from the
trusted target Alpine stage fixed it, with signature checks kept enabled.
ARM64-emulated FFmpeg generated a synthetic video and ffprobe reported 0.500000
seconds; native FFmpeg version/build flags inventoried locally. Container health/
restart/shutdown tests passed on both architectures. Emulation cannot execute
Python's ARM child processes automatically; full merger integration ran natively
on the host, while ARM media binaries were exercised explicitly via QEMU.

Limitations: 256 clips per export; one-hour FFmpeg timeout; conservative MP4
H.264/H.265 + AAC compatibility; hard-link publication requires same-filesystem
NAS support. Existing outputs are no-clobber; Phase 4 will manage safe versions.
True power loss can leave UUID.partial artifacts, never final success files.
Real HA OS/NAS/codecs/playback NOT RUN. Third-party redistribution inventory is
required before release. Next: Phase 4 durable jobs and immutable output versions.

## Phase 4 — Persistence and retry (2026-11-13)

Commands: `.venv/bin/ruff format .`, `.venv/bin/ruff check .`,
`.venv/bin/python -m pytest`, `.venv/bin/python -m build`,
`.venv/bin/python work/scan.py`, `git diff --check`.

Results: 43 tests passed, 0 failed. Added real synthetic-merge job integration
covering duplicate enqueue, durable success after reopening the DB, late clips,
cancelled rebuild retaining previous output, due retry, version promotion,
corrupted-output rebuild, concurrent claims, stale completion after simulated
crash/reopen, worker exclusion, retry exhaustion/new-manifest reset and migration
initialization/newer-schema rejection. Existing media/security tests still pass.

The process-kill/power-loss behavior on actual HA/NAS is NOT RUN. Recovery is
verified by persisted running-state simulation and store reopening. Immutable
versions avoid destructive replacement, but crashes can leave unreferenced
versions/partials; they are retained. SHA256 output integrity checks add bounded
sequential NAS I/O. No automatic cleanup/deletion. Actual HA OS/NAS NOT RUN.
Next: Phase 5 scheduler, missed-run recovery, reconciliation and manual backfill.
