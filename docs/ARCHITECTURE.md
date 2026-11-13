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
