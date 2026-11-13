# Changelog

## Unreleased — alpha

- Phase 0: Python 3.12 package bootstrap, pinned development tools, CI lint,
  formatting, smoke tests and package build checks.
- Documented architecture, safety policies and outstanding hardware verification.
- Phase 1 (gate blocked): aarch64 add-on skeleton, startup mount checks,
  heartbeat healthcheck, graceful shutdown and alpha local-install instructions.
- ARM64 execution and full Supervisor validation remain outstanding.
- Phase 1 gate completed: current add-on schema lint and emulated ARM64 service
  checks pass; added reusable native/emulated container validation and CI checks.
- Phase 2: explicit source mappings, configurable ISO timestamp adapter, safe
  read-only discovery snapshots, output/staging exclusion and JSON-lines dry-run.
- Added synthetic traversal/link/growing-file/midnight/DST tests; Reolink layout
  and timestamp semantics remain unverified.
- Phase 3: conservative ffprobe compatibility policy, cancellable stream-copy
  concatenation, source revalidation, disk-space checks, validated no-clobber
  publication and synthetic packet-order/source-hash tests.
- Explicit initial limits: 256 clips per export, MP4 H.264/H.265 with optional
  matching AAC; no transcoding or overwriting of existing output.
- Phase 4: durable SQLite manifests/state/history, atomic job claims, lifetime
  worker locking, interrupted-run recovery, five-attempt retry cap and immutable
  managed output versions preserving previous successful exports.
- Phase 5: 00:15 local calendar scheduling, bounded restart backfill, periodic
  reconciliation, manual historical enqueue, persistent scheduling metadata,
  scanner diagnostics blocking partial days and independent service heartbeat.
- Phase 6: responsive ingress-only UI with camera/date selection, current daily
  playback/download, history/diagnostics and CSRF-protected manual reprocessing.
- Bounded HTTP workers, safe output lookup, byte-range streaming and no public
  port mapping; desktop/mobile Chromium flow verified with synthetic H.264.
- Include MIT and third-party notices in the add-on build context/image.
- Robustness: discard unused media stderr, bound probe stream metadata, and avoid
  persistent startup-check markers blocking crash recovery.
- Alpha.2: source mappings, adapter and schedule settings are available in the
  Home Assistant Configuration tab; empty defaults safely disable processing.
