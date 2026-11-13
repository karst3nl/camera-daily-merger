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

## Phase 5 — Scheduling and backfill (2026-11-13)

Commands:

```sh
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python -m build
.venv/bin/python tests/integration/check_pipeline.py --image camera-daily-merger:test-amd64
docker --host=unix:///var/run/docker.sock build --platform linux/arm64 --secret id=proxy_ca,src=/etc/ssl/certs/ca-certificates.crt -t camera-daily-merger:alpha-arm64 camera_daily_merger
.venv/bin/python tests/integration/check_container.py --image camera-daily-merger:alpha-arm64 --qemu work/qemu-aarch64-static
```

Results: 54 tests passed, 0 failed. Fake-clock cases cover 00:15 boundaries around
both DST transitions, restart after a missed time, repeated scheduling cycles,
retry due time, delayed clips, healthy-output no-op, manual range validation and
current-day growing files not blocking yesterday. A native container with mock
NAS input automatically merged a historical synthetic day, recorded current output,
passed health, restarted without rebuilding, stopped gracefully and preserved
source SHA256. Initial harness could not inspect container-owned output directories
under rootless UID mapping; fixed test-only directory permissions before host
inspection/cleanup (production permissions unchanged). ARM64 build/service smoke
also passed. Early fake-clock tests used host-current fixture mtimes; fixed the
fixtures to deterministic old mtimes and retested.

Reconciliation defaults: six hours, seven-day initial backfill; maximum 366 dates
and latest 1,000 job summaries per pass. Older history requires explicit manual
backfill. Concurrency is one. Actual HA OS/NAS scheduling/reboot remains NOT RUN.
Next: Phase 6 ingress-only UI, validated manual actions and protected playback.

## Phase 6 — Web interface and ingress integration (2026-11-13)

Commands:

```sh
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python -m build
.venv/bin/python -m pip check
.venv/bin/python -m tests.integration.check_browser --chromium /usr/bin/chromium
.venv/bin/python tests/integration/check_pipeline.py --image camera-daily-merger:test-amd64
.venv/bin/python tests/integration/check_container.py --image camera-daily-merger:alpha-arm64 --qemu work/qemu-aarch64-static
docker --host=unix:///var/run/docker.sock run --rm -e INPUT_PATH=/repo/camera_daily_merger -e INPUT_COMMUNITY=false --mount type=bind,src=/workspace/camera-daily-merger,dst=/repo,readonly merger-addon-linter
```

Results: 59 tests passed, 0 failed; current add-on linter passed. New API integration
covers unauthorized peer denial even with forged forwarding headers, CSRF denial,
invalid/future camera/date, traversal attempts, safe summaries, no configuration
path disclosure, playback/download, HEAD, byte/suffix ranges, invalid ranges,
missing outputs and symlink rejection. MIT/third-party notices match the copies
included in the image; wheel inspection confirmed static assets and MIT license.

Playwright 1.57.0 with local Chromium passed desktop (1280x1100) and mobile
(390x844) checks: no horizontal overflow, synthetic H.264 playback, download,
manual reprocess enqueue, codec-compatibility error message and no JS errors.
Screenshots were visually reviewed locally; they contain synthetic content only
and are not tracked. H.265 decode is NOT VERIFIED: the error branch was simulated,
not a claim of real H.265 playback. Browser tooling is an optional dev dependency.
Native scheduled container merge/restart/source-hash checks and ARM64-emulated
service checks passed. Existing hosted GitHub CI runs through Phase 5 were
observed completed/success via the repository actions API.

Ingress is configured with no host port mapping; the server trusts only the
Supervisor DNS-resolved peer. Internal DNS behavior was checked against current
Home Assistant communication documentation. Actual ingress authentication,
Supervisor peer/iframe behavior and HA OS installation are NOT RUN / BLOCKED.
This explicitly permitted Phase 6 limitation transfers to real acceptance;
no production-ready claim. Next Phase 7 documentation and owner/device evidence.

Phase 6 follow-up robustness review: discarded unused FFmpeg stderr instead of
buffering it, limited ffprobe to 32 streams and selected metadata fields, and used
an anonymous startup writeability check so an old bootstrap marker cannot prevent
restart. Added large-stderr and stale-marker regressions. Command
`.venv/bin/python -m pytest`: **61 passed, 0 failed**. Ruff checks and the rebuilt
native container pipeline passed. GitHub CI for Phase 6 commit 6ef2ca1 was observed
completed/success (run 43515122368). These checks do not change hardware limitations.

Phase 6 usability follow-up: added standard Home Assistant options/schema for
source root, camera mappings, timestamp adapter, zone, output/staging and schedule.
Empty mappings/adapter keep processing disabled. Advanced /data/discovery.json
remains an explicit source override. Alpha add-on version is 0.1.0-alpha.2.
62 tests passed plus current add-on linter; the native container pipeline now
uses options.json and passed automatic processing/restart/source-preservation.
Added v1-to-v2 migration preservation coverage before the final complete run.

## Phase 7 — Acceptance preparation and filename candidate (BLOCKED)

Prepared ACCEPTANCE.md, OPERATIONS.md and SECURITY.md, plus app-store README,
DOCS and changelog. Verified the current Supervisor repository URL regex and Git
clone code at revision 98a2322374ae3d0c248079d11f7435ad759935fa: #alpha is an
explicit supported branch selector. Updated setup accordingly; actual HA store
installation remains NOT RUN.

One owner-supplied filename/path shape was received. No actual camera name or
identifying filename is tracked. Added configurable timestamp_format (iso8601
or explicit strptime) with synthetic compact names under nested calendar folders.
Candidate format is %Y%m%d%H%M%S; its real time semantics/timezone
are still awaiting owner confirmation. The owner confirmed the `_00_` component
has no application meaning; it is matched literally, without inferring a codec
or camera identity from it. New tests cover the layout, malformed
compact dates, DST gaps/repeated hours and date-only ISO rejection.
No real recording was opened, modified or uploaded.

Commands:

```sh
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python -m build
.venv/bin/python -m pip check
.venv/bin/python work/scan.py
git diff --check
```

Results: 71 tests passed, 0 failed. Phase 7 real hardware, NAS, ingress,
full-day/multi-camera acceptance, Pi benchmarks, source/codec verification and
owner review remain NOT RUN / BLOCKED. Full release/license inventory is pending.
No release tag or merge/push to main is performed. See ACCEPTANCE.md for evidence
fields and known capacity/storage limits. Next action depends on sanitized codec
metadata, timestamp/mount confirmation and owner-run HA OS/Pi/NAS acceptance.

Phase 7 resource review: unchanged output snapshots now avoid full-video hashing.
Metadata changes trigger SHA256; verified snapshots are conditionally cached. A
regression test proves zero hash reads for unchanged output, one read after a
metadata-only change, subsequent cache reuse, and detection of same-size modified
content when mtime changes. Automatic lookback is bounded by backfill_days; due
failed historical jobs are revisited, older healthy dates remain manual. This
does not detect silent corruption that preserves all metadata; a separate audit
or explicit reprocess is needed for that case.

Additional commands: both architecture builds with the session CA secret,
`.venv/bin/python tests/integration/check_pipeline.py --image camera-daily-merger:test-amd64 --compact`,
and the ARM64-emulated container smoke test. The compact-name native scheduled
merge/restart/source-hash scenario passed; both images/service checks passed.

Final environment recovery: the development machine's 8 GiB filesystem filled
because repeated Docker VFS builds retained copied intermediate filesystems. A
native rerun passed after the first cache cleanup; the subsequent ARM build hit
ENOSPC again. Removed only this task's regenerable linter/old ARM test images and
all unused Docker build cache; free space increased to 5.8 GiB. Source/config/NAS
content was untouched. The final ARM build/smoke and package checks were rerun
successfully after cleanup. This development-host storage event is not a NAS
fault-injection success and is not counted as a passing device test.

## Phase 7 owner feedback — startup diagnostics (alpha.4)

Owner reports successful installation and initial UI opening. Configured startup
then failed with a generic validation error. The supplied configuration used an
absolute camera path; camera mappings require paths relative to source_root.
Actual names/paths are not copied into tracked tests or documentation. Correcting
the relative path and matching folder capitalization is the user-side remedy;
its success on the device is not yet confirmed. Full real acceptance stays blocked.

Added controlled ConfigurationError messages, category-only regex/JSON/timezone/
OS/database diagnostics, and no raw exception/configuration path logging. Synthetic
regressions reproduce absolute-path startup failure, verify the actionable message
without private values, reject malformed regex without logging its contents, and
support logical camera IDs differing from case-sensitive source folder names.

Commands: `.venv/bin/ruff format .`, `.venv/bin/ruff check .`,
`.venv/bin/ruff format --check .`, `.venv/bin/python -m pytest`,
`.venv/bin/python -m build`, `.venv/bin/python -m pip check`,
`.venv/bin/python work/scan.py`, `git diff --check`.
Results: 74 tests passed, 0 failed. Device restart after correction NOT RUN.

Further owner feedback: configured startup now succeeds, but discovery reports
the same generic directory error for the recovery window. The owner confirmed a
lowercase relative folder value differing from the original supplied folder's
capitalization; advised matching the actual folder name. Actual corrected scan
success remains unconfirmed. Added missing/permission/not-directory-or-link/I/O
scanner categories. Tests use synthetic names and simulated permission denial.
Final full-suite result: 76 passed, 0 failed. Native compact-name container pipeline
passed before this classification-only scanner change; no media write behavior
was changed. Real-device full acceptance remains blocked.

## Phase 7 owner feedback — actionable discovery diagnostics (alpha.5)

Owner still encounters blocked discovery after providing seven syntactically
valid compact filename examples. The earlier summary did not identify the bad
entry or distinguish regex mismatch from timestamp-format/DST failure. Actual
NAS root cause remains UNCONFIRMED; no real source was opened or modified here.

Added controlled parser detail codes and bounded local basename examples (three
per diagnostic group), counts, UI hints and a visible backend version. Full source
directories, raw configuration and private exception strings remain absent from
HTTP output/logging. Access remains restricted to authenticated ingress peers.
Potential unknown recordings still block the requested day; no skip policy was
introduced. Tracked tests use anonymized synthetic names only.

Commands:

```sh
.venv/bin/ruff format .
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python -m tests.integration.check_browser --chromium /usr/bin/chromium
.venv/bin/python -m build
.venv/bin/python -m pip check
.venv/bin/python work/scan.py
git diff --check
```

Results: 80 tests passed, 0 failed. New regressions distinguish overescaped regex
from ISO/compact format mismatch, bound samples while preserving blocking, and
verify basenames/full-path exclusion and denied-peer privacy. Browser flow passed
with an HTML-looking synthetic filename shown as plain text in the blocking
message/diagnostics, no injected image, no horizontal overflow or JS errors.
The first new browser assertion used a string wait_for_function rejected by CSP;
replaced the test assertion with Playwright's locator expectation and reran it
successfully. CSP was not relaxed. Existing playback/download/reprocess checks
also passed. Real NAS reprocess after upgrading remains NOT RUN / BLOCKED.

Alpha.5 native image build and compact-name scheduled container pipeline also
passed: automatic merge, current output, restart idempotency, graceful shutdown
and unchanged synthetic source hash. Commands: native Docker build with the
session CA secret, then `.venv/bin/python tests/integration/check_pipeline.py
--image camera-daily-merger:test-amd64 --compact`.
