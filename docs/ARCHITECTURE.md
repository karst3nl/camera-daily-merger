# Architecture

Implementation follows CODEX_IMPLEMENTATION_PLAN.md sequentially. Python 3.12
is the runtime baseline; target architecture is aarch64 for Raspberry Pi 4.
There are no runtime Python dependencies in the bootstrap.

The application package lives under camera_daily_merger/app so later add-on
packaging can use the proposed layout. Small modules will separate configuration,
read-only discovery, probing, merging, persistence, scheduling and HTTP access.
No processing or media access is implemented in Phase 0.

Invariants: untrusted input paths, no source writes, no implicit transcoding,
sequential merges by default, bounded work, temporary outputs separate from final
outputs, SQLite under /data and large staging files on the output filesystem.
Exact source filename semantics require real anonymized samples. Ambiguous local
timestamps must fail explicitly. Never infer a Reolink naming convention.

Only alpha receives commits/pushes. Main is reserved for explicit owner approval
after real Home Assistant OS, Raspberry Pi 4 and NAS acceptance.

Phase 1 adds a standard-library log-only service, avoiding HTTP/framework costs
until Phase 6. A pinned Python Alpine image replaces a Home Assistant base image
because no bashio/Supervisor API integration is needed yet. Docker init handles
process reaping; Python handles shutdown. Only aarch64 is declared. An auxiliary
amd64 build is for development validation only. No FFmpeg is bundled yet.

Phase 2 uses explicitly mapped camera folders and a regex adapter with a named
start group containing ISO-8601 timestamps. A parser protocol permits future
verified source adapters. Offset timestamps are converted into the configured
zone; naive timestamps use round-trip fold validation and reject DST gaps and
repeated hours. Sorting uses UTC, with relative path as a deterministic tie-break.
No inference from filesystem mtime is used for recording time.

Directory traversal uses descriptor-relative O_NOFOLLOW opens, including every
root component. Sources are opened read-only, nonblocking and must be regular,
single-link files. Output/staging subtrees are excluded. File size/mtime/device/
inode are captured and compared before/after timestamp extraction; recent/empty
files are excluded. This is an eligibility snapshot, not a guarantee that NAS
writers will never append later. Every future media-processing stage must reopen
and verify the snapshot and must reject changes before publishing. Directory
iteration is incremental; sorting is explicit and should be scoped to a day.
The dry-run is a local administrative CLI and reports relative source paths.

Phase 3 accepts MP4 with exactly one H.264/H.265 video stream and optional AAC
tracks; stream ordering and codec/profile/level/extradata, geometry, pixel format,
color metadata, frame rate/timebase and audio layout must match exactly. The
policy is deliberately conservative. Other layouts fail without conversion.
Concat uses -c copy and -auto_convert 0; filenames never enter its manifest,
only inherited read-only integer descriptors. Inputs are checked before/after
processing, including current path identity. Duration tolerance is 0.5 seconds
plus 0.25 seconds per clip to allow container/audio timestamp rounding.

Large temporary files live in the designated NAS staging directory; tiny concat
manifests use the explicit persistent-state temporary directory. Staging needs
110% of total input bytes plus 64 MiB reserve. Outputs are probed and fsynced
before atomic no-clobber hard-link publication on the same filesystem. NAS
hard-link/fsync support must be verified in acceptance. Existing outputs are never
overwritten in this phase. Exceptions remove this operation's partial file.
Hard power loss may leave an identifiable UUID.partial for later recovery.
At most 256 clips are accepted per job to bound descriptors; larger days fail
explicitly pending safe chunked concatenation. FFprobe timeout is 30 seconds and
FFmpeg timeout one hour. Real codec compatibility/playback remains unverified.

Phase 4 uses SQLite WAL/full synchronous transactions for queued/running/success/
failed state, attempts, manifests, errors and transition history. Atomic claims
use random attempt tokens; stale completions are rejected. The worker holds an
exclusive local flock for its entire lifetime, then recovers interrupted running
rows on startup. This prevents a second worker from declaring a live job crashed.
Retries are capped at five attempts with 30-second exponential backoff (maximum
one hour); explicit manual force or a changed manifest resets the budget.

Design refinement: managed exports use immutable YYYY-MM-DD-<attempt-token>.mp4
versions instead of replacing YYYY-MM-DD.mp4. The database points to exactly one
current daily export only after validation/publication. A failed rebuild retains
the previous pointer. This avoids overwriting unknown pre-existing files and
narrows the filesystem/SQLite crash window. A crash after publication but before
DB commit can leave an unreferenced valid version; it is never presented as a
success and is not automatically deleted. Older versions remain on NAS; no
retention/deletion policy is implemented. This costs space during retries, which
is preferable to risking original or previous-export loss. Legacy outputs are
not automatically adopted. Reconciliation checks size/mtime/device/inode first and hashes sequentially only
when that metadata changed or an older row lacks a verified snapshot. Successful
hash verification refreshes the snapshot with an atomic conditional DB update.
This avoids rereading unchanged videos on every cycle. Silent bit rot preserving
all metadata requires a separate full integrity audit or explicit rebuild.

Phase 5 adds a standard-library calendar scheduler. Persistent scheduling metadata
and schema v2 survive restart; v1 databases migrate by adding metadata. The latest
due date uses local calendar subtraction, including DST. A bounded historical
window covers missed runs and normal reconciliation; due failed historical jobs
are also revisited. Older healthy dates require manual backfill. Periodic cycles
and failed-job due times
trigger rescans. Repeated ticks/enqueues leave queued/running work intact. Invalid
source diagnostics block the affected camera/date; unknown timestamps block all
requested dates for that camera. Diagnostics are stored without source paths.
An independent heartbeat thread avoids false unhealthy status during long merges.
Concurrency remains fixed at one; increasing it is intentionally not exposed yet.

Phase 6 uses Python's small standard-library HTTP server with at most four active
request threads, 15-second socket timeouts and 64 KiB streaming chunks. Ingress
peers are resolved from the documented Supervisor hostname, with fail-closed DNS
handling and no trust in forwarding headers. HA ingress supplies user authentication;
there is no public standalone authentication mode. Administrative POST requires a
same-origin-readable random CSRF token and bounded JSON, then validates the camera/
calendar date. Static assets and API paths are allowlisted. Video lookup accepts
only camera/date identifiers and a DB-managed immutable filename under the output
root; safe descriptor opens reject symlinks. The interface never returns manifests,
full NAS paths or credentials. Browser assets use relative URLs for ingress prefixes,
external JS/CSS and a restrictive same-origin CSP. Local development requires an
explicit loopback-only override. Actual ingress remains an acceptance gate.

An owner-provided filename shape in Phase 7 justified adding explicit
`timestamp_format` configuration. `iso8601` remains the default; Python strptime
formats allow compact timestamps without hardcoding camera names or Reolink
semantics. Tests use anonymized synthetic YYYY/MM/DD directories and compact
names. Filename time remains authoritative for grouping, subject to confirming
its meaning/timezone with the owner. Calendar folder names do not override it.
