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
- Phase 7 preparation: real-device acceptance protocol, operations/backup/recovery,
  security guidance and verified #alpha repository installation instructions.
- Real Pi 4 / HA OS / Synology acceptance, benchmarks, source-adapter verification
  and release/license review remain blocked; no release tag or main merge.
- Added configurable compact timestamp formats after one owner-provided filename
  shape; anonymized nested-calendar fixtures pass. Actual timezone/channel/codec
  semantics remain unverified; date-only ISO timestamps are rejected.
- Reduce NAS I/O with cached output identity/mtime/size and SHA256 checks after
  metadata changes; bound normal reconciliation to the configured lookback plus
  due failed historical jobs. Full metadata-preserving bit-rot audit is separate.
- Alpha.3 includes the compact filename adapter candidate and output integrity
  cache; real-device acceptance remains blocked.
- Alpha.4: actionable startup configuration diagnostics for absolute camera paths,
  invalid regex/JSON/timezone and mount failures, without logging private values.
- Clarified relative, case-sensitive camera folder paths versus logical camera IDs.
- Scanner diagnostics now distinguish missing folders, permission denial, unsafe
  directory/link paths and NAS I/O errors without exposing raw exception paths.
- Alpha.5: discovery diagnostics distinguish filename-pattern, timestamp-format
  and DST errors and show up to three offending basenames in the authenticated UI.
- Reprocess results show the actual first diagnostic instead of only a generic
  blocked message; the UI displays its backend version for upgrade verification.
- Alpha.6: retain the known local recording date when rejecting an ambiguous or
  nonexistent DST time, so archival transition-day clips cannot block unrelated
  dates. The affected DST day still fails closed without guessing an offset.
- Alpha.7: incompatible-stream failures identify the first differing chronological
  clip and show bounded field/value comparisons in job history. The conservative
  compatibility policy and no-transcoding behavior remain unchanged.
- Alpha.8: accept differing derived video r_frame_rate estimates when required
  stream configuration matches; preserve source packet timing with stream copy.
- Added exact 20/1 versus 239/12 and irregular-cadence regressions proving encoded
  packets, decoded frames, timing/order, duration and source hashes are preserved.
- Dashboard extension, step 1: latest published day per camera and shared-date
  multi-camera galleries, play/pause controls, missing-export states and automatic
  refresh that preserves active playback.
- Added read-only collection API and version-pinned video URLs; six media streams
  and eight total HTTP workers keep metadata requests available during playback.
- Alpha.9: local Lovelace card for latest-per-camera and shared-day collections,
  using authenticated HA ingress sessions with modern/legacy WS support, renewal
  and same-origin validation. Added in-app resource download/setup and documentation.

## 0.1.0-alpha.10

- Native Home Assistant Webpage card setup: no copied files, resource or YAML.
- Stable latest/day links, official ingress properties bridge and compact mode.
- Existing recording exports stream directly; source recordings stay untouched.

## 0.1.0-alpha.11

- Full-width surveillance grid with adjacent cameras and name/date-only metadata.
- External playback, seeking and audio controls leave the video image unobscured.
- Client-side 1–4× digital zoom, reset, mouse/touch pan and wrapper fullscreen.
- Preserve native dashboard embedding and original recordings without copying.

## 0.1.0-alpha.12

- Graphical dashboard layout: automatic or 1–4 columns, including four-camera 2×2.
- Shared window-size control keeps camera tiles equal and preserves playback.
- Validated browser-local layout preferences, reset and blocked-storage fallback.
- Clamp zoom/pan during window resizing without reloading video streams.
