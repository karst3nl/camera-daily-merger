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
