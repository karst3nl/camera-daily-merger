# Codex implementation handoff — Camera Daily Merger

Version: 1.0 | Status: implementation authorized on `alpha` | Date: 2026-11-13

## 0. Mission and constraints

Build an **MIT-licensed, open-source Home Assistant add-on** that reads motion-triggered video recordings from a network storage share, groups them by **camera and local calendar date**, and creates **one chronologically joined file per camera/day**. Empty periods are not represented. Use **FFmpeg stream copy**, preserving the original quality. The user does not want default transcoding.

Repository: https://github.com/karst3nl/camera-daily-merger

**Git rule: develop, test, commit and push only on branch `alpha`. Do not alter `main` or merge anything to it until the owner explicitly approves following real end-to-end acceptance.** Read `AGENTS.md` and `docs/SPECIFICATION.md`.

### Confirmed product requirements

- Daily scheduler: 00:15 Europe/Berlin by default; process the **previous** local day.
- Automatically process each camera; one daily output per camera/date.
- Video: lossless joining where compatible; incompatible clips cause an explicit job failure/report, not implicit re-encoding.
- Originals: permanently keep, never mutate/delete/move.
- Automatic daily processing enabled; reconcile/retry failed or incomplete dates, including late arrivals.
- Initial target: Home Assistant OS on Raspberry Pi 4, recording storage: Synology DS223 using SMB shared folder `reolink`.
- User's Synology-specific LAN IP must **not** appear in public configuration/commits. Synology internal directory is `/volume1/reolink`, while Home Assistant will mount an SMB media share (expected `/media/reolink`, validate in actual add-on).
- Output e.g. `daily/<camera-id>/YYYY-MM-DD.mp4` on the NAS share; persistent SQLite/job database/config inside add-on `/data`.
- Public-facing documentation in English, MIT license, safe config and GitHub-based development.

### Mandatory unknowns / don't invent

Actual Reolink **folder hierarchy, filename format, timestamp semantics, metadata, codecs**, clip behavior around midnight, source container formats and Home Assistant media-mount exposure have NOT yet been inspected. Design a configurable file-source adapter and synthetic fixtures first. Do not claim real recordings are supported until testing real anonymized samples. If unresolvable, mark the corresponding phase blocked and still deliver independently testable work.

## 1. Repository skeleton / intended architecture

```text
camera-daily-merger/
├── AGENTS.md
├── LICENSE
├── README.md
├── CHANGELOG.md
├── repository.yaml
├── .gitignore
├── .github/workflows/ci.yml
├── docs/
│   ├── SPECIFICATION.md
│   ├── CODEX_IMPLEMENTATION_PLAN.md
│   ├── ARCHITECTURE.md
│   ├── SETUP.md
│   └── TEST_REPORT.md
├── camera_daily_merger/
│   ├── config.yaml
│   ├── Dockerfile
│   ├── run.sh
│   ├── requirements.txt   # or pinned lockfile
│   └── app/
│       ├── main.py
│       ├── settings.py
│       ├── storage.py
│       ├── scanner.py
│       ├── timestamp_parser.py
│       ├── probe.py
│       ├── merger.py
│       ├── jobs.py
│       ├── scheduler.py
│       ├── persistence.py
│       ├── web.py
│       └── static/
└── tests/
    ├── fixtures/
    ├── unit/
    └── integration/
```

The layout is a proposal; keep modules small, avoid unnecessary dependencies, and justify any meaningful changes in `docs/ARCHITECTURE.md`.

Suggested stack: Python 3, ffmpeg/ffprobe, SQLite, a minimal HTTP app (FastAPI if justified), pytest, ruff. Verify current official Home Assistant add-on configuration specification and **ingress** support; don't rely on stale config settings. For volume mapping, use supported Home Assistant add-on media access and document required user setup. Verify architecture support for Pi 4 (aarch64 / possibly armv7 as appropriate).

## 2. Strict step-by-step phases and gates

Do not implement the entire application in one untested batch. At each gate: run actual commands, capture evidence, update `docs/TEST_REPORT.md`, commit and push to `alpha`, then proceed only if the gate passes. A test requiring unavailable real hardware must be labeled **NOT RUN / BLOCKED**, never PASS.

### Phase 0 — Repository bootstrap & policies

Deliver:
- Verify `alpha` is checked out; add `README.md`, `.gitignore`, `CHANGELOG.md`, architecture/plan docs.
- Keep `LICENSE` MIT; ensure no secrets or personal network addresses in tracked content.
- Set up Python packaging/dependencies and starter test infrastructure.
- Add a minimal GitHub Actions CI workflow for lint/unit tests; choose Pi-compatible runtime.

Tests / gate:
- Syntax and dependency install checks pass in a clean environment.
- At least one smoke test succeeds.
- Secret/file scanning check and git status review.
- Commit and push `alpha`.

### Phase 1 — Minimal installable Home Assistant add-on

Deliver:
- Home Assistant add-on repository metadata, add-on `config.yaml`, Dockerfile and service entrypoint.
- Persistent `/data` and supported `/media` mount configuration.
- Web/health endpoint or minimal log-only service; graceful shutdown, startup validation.
- Document adding a custom repository and installing an alpha build.

Tests / gate:
- Validate add-on metadata/config against current Home Assistant requirements.
- Build container for declared platform(s), launch it with a mock `/data` and `/media` and verify health/restart.
- Actual HA OS installation remains BLOCKED until run on user's HA machine.
- Commit/push `alpha`.

### Phase 2 — Storage access, discovery and safe timestamping

Deliver:
- Configurable root, output path, camera mappings, and scanner that excludes output/staging paths.
- Parser interface with explicit timestamp/zone policy; don't assume concrete Reolink naming until observed.
- Stable input snapshots: size, mtime, camera ID, extracted recording start; reject files still growing.
- Secure path validation (never traverse outside approved roots, follow unsafe symlinks or use file input in shell).
- Dry-run CLI/API to list detected clips without writing media.

Tests / gate:
- Synthetic nested camera folders, unsorted files, invalid files, symlink/traversal attempts, output-folder exclusion, files-in-progress, duplicate names.
- Tests across DST change, midnight boundary, timezone conversion and malformed timestamps.
- Mock NAS paths; mark real Reolink parsing unverified until sample structure arrives.
- Commit/push `alpha`.

### Phase 3 — Probe and concatenate

Deliver:
- ffprobe wrapper for stream metadata/duration/error results.
- Compatibility policy for container, video parameters, audio tracks, timestamp/timebase, stream layout; define what can be losslessly concatenated.
- FFmpeg concat demuxer or equivalent without transcoding, `-c copy`; use safe argument arrays and concat manifest escaping.
- Failure diagnostics for incompatible streams; zero original file writes.
- Build a temporary output under designated NAS staging folder on the same filesystem; validate before publishing. Never overwrite an existing valid output on failure.
- Check free disk space and FFmpeg exit status; handle signals and partial files.

Tests / gate:
- Create short **synthetic** video clips with ffmpeg; verify ascending order, expected duration within documented tolerance, stream metadata, and output playable by ffprobe.
- Incompatible codec/resolution/audio test case must fail safely without converting.
- Corrupted clip, zero clips, single clip, odd filenames, disk-write errors and interrupted run.
- Assert source file hashes before/after.
- Commit/push `alpha`.

### Phase 4 — Persistence, idempotency and retry

Deliver:
- SQLite schema for camera, day, job, source manifest, status, attempts, output metadata, error/log summary.
- Atomic job state transitions, crash restart recovery, per-camera/date lock, output version protection.
- Source change fingerprint including late-arriving clips; rebuild if changed without destroying previous working result prematurely.
- Explicit retry policy with capped backoff, avoiding unbounded busy retries.

Tests / gate:
- Restart mid-job; duplicate enqueue; scanner finds late clips; concurrent job attempts; DB migration smoke test.
- Tests establish no duplicate/corrupt output and reliable history.
- Commit/push `alpha`.

### Phase 5 — Scheduling and backfill

Deliver:
- At 00:15 local time schedule the previous *calendar* day, not merely now minus 24 hours.
- Robust DST and missed-run recovery, daily reconcile schedule (configurable), manual run for camera/date and historical days.
- Limit concurrency to 1 on Pi 4 by default, adjustable if safe.

Tests / gate:
- Fake clock tests at DST transitions, system restart after scheduled time, two scheduling cycles, delayed arrivals, overlapping executions.
- Confirm existing healthy output isn't needlessly rebuilt with unchanged inputs.
- Commit/push `alpha`.

### Phase 6 — Web interface and Home Assistant integration

Deliver:
- Mobile/desktop-capable UI with camera/date chooser, list of daily videos, playable/downloadable output when browser codec supports it, job status, manual reprocess button, error diagnostics.
- Home Assistant ingress integration and local authentication strategy supported by add-on context; no public unauthenticated HTTP exposure by default.
- Show playback unsupported message for H.265/browser incompatibility instead of suggesting data is corrupt.
- Explicitly distinguish synthetic/mock successes from real NAS verification.

Tests / gate:
- API unit/integration tests for validation, enumeration and access permissions.
- Verify no arbitrary path access via URL/API, no exposure of SMB credentials or source paths to unauthorized requests.
- Browser UI manual tests; HA ingress on actual HA OS is BLOCKED until tested.
- Commit/push `alpha`.

### Phase 7 — Real NAS/Home Assistant acceptance, release readiness

Deliver:
- Instructions for binding NAS media share, permissions, camera folder mapping and output folder creation; troubleshooting.
- Run on actual Home Assistant OS Pi 4 and Synology DS223. Obtain **non-sensitive** sample folder structure/filenames and codec/ffprobe metadata from owner. Do not commit real footage or identifying filenames.
- Validate two or more cameras where available, real daytime/midnight boundaries, a complete previous day, delayed clips, incompatible formats, reboot recovery, playback and NAS storage footprint.
- Document benchmark on Pi 4, logging, backups, upgrade behavior, recovery, limitations and third-party license notices.
- Confirm output correctness via viewing segments from beginning, middle and end.

Tests / gate:
- End-to-end installation, storage mount, scheduled merge, playback, retry, restart/reconciliation and originals unchanged **all proven on real HA OS + NAS**.
- CI passing; no unresolved critical/high issues; `docs/TEST_REPORT.md` includes evidence, remaining known limitations and explicit owner review.
- Tag alpha/prerelease only on `alpha` if desired. **Do not merge or push to main**.
- Only after explicit owner approval may a separate release/merge action from `alpha` to `main` be performed.

## 3. Technical design invariants

- **No data loss:** read-only treatment of all original clips, including accidental colliding filenames. Destination confined to designated output/staging directory.
- **Correct grouping:** one day = midnight to next midnight in the configured local timezone. Handle daylight saving gaps/repeated hours using real timestamps when possible. If file timestamps are ambiguous, fail with clear error rather than silently misgroup.
- **Lossless output:** preserve video/audio streams by `-c copy`; concatenation alone cannot create true real-time blank intervals and must not.
- **Correctness over speed:** low-memory incremental enumeration, one merge at a time, bounded background jobs; no partial `.mp4` files published as success.
- **Observability:** detailed structured logs and a simple task history, without dumping sensitive full file paths.
- **Portability:** no hardcoded host IP, NAS volume path or camera names; setup via configuration.
- **Privacy:** no external uploads, no GitHub attachments of recordings, no cloud dependency at runtime.
- **Compatibility:** document codec/container limitations; MP4 and H.265 browser playback can vary.
- **Security:** no elevated host privileges beyond necessary Home Assistant mounts; minimize dependencies, pin versions, check licenses.

## 4. Required report after every phase

Use exactly this concise structure in Codex's final message for the phase:

```text
Phase: N — title
Branch: alpha
Commit: <SHA>
Pushed to origin/alpha: YES / NO (explain if no)
Files changed: ...
Implemented: ...
Tests run (exact commands): ...
Results: X passed, Y failed, Z not run/blocked
Actual Home Assistant/NAS verified: YES / NO
Open blockers: ...
Next phase: ...
```

Update `docs/TEST_REPORT.md` accordingly.

## 5. Initial Codex assignment

1. Check repository, `alpha` branch, `AGENTS.md`, `docs/SPECIFICATION.md` and this plan.
2. Implement **Phase 0 only**, verify tests, commit and push **to `alpha` only**.
3. Report the gate results and continue to Phase 1 if Phase 0 genuinely passed. Continue phases sequentially, always test before commits/pushes.
4. Do not claim the app is production-ready or merge into `main` in this session.

## 6. Inputs still needed from the owner for real-device verification

- Example sanitized folder tree and 2–3 anonymized recording filenames per camera.
- `ffprobe` output from a few representative clips, if available.
- Confirmation of NAS share permissions and actual HA OS media mounting.
- Access to actual HA OS environment, or owner-provided manual test results with logs.

## Implementation refinements

Phase 4: use immutable attempt-token output filenames with a SQLite current-output
pointer, rather than overwriting the date-only pathname. This preserves unknown
colliding files and previous successful exports across crashes. Only one version
is current per camera/date; older/orphan versions remain until an explicitly
approved future cleanup policy. See ARCHITECTURE.md for tradeoffs.

Phase 7 / alpha.8: classify derived video r_frame_rate as informational after
synthetic packet/frame/timing-preservation evidence for matching codec headers
and timebases with different frame-rate estimates. Apply the same comparison at
input and output validation. All other required stream fields remain strict.

## Authorized dashboard extension

After owner-reported successful alpha.8 processing, add (1) latest-per-camera and
same-date multi-camera views with read-only collection APIs, then (2) a local
Lovelace card using authenticated Home Assistant ingress sessions. Test/commit
these independently on alpha. Multi-player controls do not imply wall-clock
synchronization because motion-free periods are absent from the exports. Preserve
no-public-port access, source immutability and bounded Raspberry Pi resources.

## Native dashboard simplification (owner requested)

Alpha.10 replaces the primary custom-resource setup with the built-in Webpage
card. Reuse the HA app panel route and official ingress properties protocol for
compact views and installation-specific stable URLs. Keep the earlier resource
available for existing users. Verify protocol, playback, date preservation and
existing regression suites with synthetic exports; real HA acceptance remains open.

## Surveillance dashboard refinement (owner requested)

Alpha.11 adds a full-width, adjacent camera grid with name/date metadata only,
external playback controls and bounded client-side zoom/pan. Test playback, seek,
audio, fullscreen geometry, zoom limits/reset/panning and desktop/mobile layouts
with synthetic video before committing. Preserve the native dashboard bridge,
processing UI and all source/storage safety invariants.

## Equal adjustable camera windows (owner requested)

Alpha.12 adds graphical automatic/1–4 column selection and a shared 50–100% width
control. Four cameras in two columns form 2×2. Preserve equal tile dimensions,
playback and zoom while resizing; store only validated browser-local preferences.
Test four synthetic cameras, missing tiles, view changes/reload, mobile layout,
blocked/corrupt storage and existing pipeline/browser gates before commit/push.

## Automatic viewport fit (owner requested)

Alpha.13 defaults to height-and-width-aware layout, maximizing equal camera image
size while reserving labels/control rows. Recompute using event-driven viewport,
chrome and camera-count observers. Preserve optional manual sizing, playback and
zoom. Validate desktop, portrait, landscape and nested card resize plus existing
browser/pipeline checks before publishing on alpha.

## Fixed 2×2 compact camera view (owner requested)

Alpha.14 replaces variable automatic column selection with two columns, always
2×2 for four cameras. Fit equal windows to remaining viewport height/width, retain
image aspect ratio and wrap external controls without horizontal scrolling. Move
setup out of camera views and compact navigation. Verify latest/day desktop,
portrait, landscape and embedded layouts with page/control scroll dimensions and
visible control bounds, plus existing regression/pipeline gates before publishing.
