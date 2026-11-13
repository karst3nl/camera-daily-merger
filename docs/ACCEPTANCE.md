# Phase 7 — Real-device acceptance

Status: **BLOCKED / NOT RUN**. Synthetic tests and ARM64 emulation are not evidence
of real Home Assistant OS, Pi 4, Synology, Reolink or ingress behavior. No release
or merge to main is approved. Run this protocol on alpha only.

One filename shape has now been supplied and reproduced using an anonymized
synthetic compact-timestamp adapter. Its actual camera name/date are not tracked.
The owner confirmed `_00_` has no application meaning and is treated literally.
Timestamp semantics, timezone, mount and codecs remain unverified.

## Required owner inputs

- An anonymized folder tree and 2–3 sample filename patterns per camera, preserving
  separators, timestamp representation and extensions. Remove camera serials,
  personal names and deployment details. Do not send/upload recordings.
- Codec metadata from representative daytime/nighttime/audio variants. A local
  `ffprobe -v error -show_entries format=format_name,duration:stream=codec_type,codec_name,profile,level,width,height,pix_fmt,time_base,r_frame_rate,sample_rate,channels,channel_layout -of json /LOCAL/CLIP`
  avoids filename/tag output. Replace the path locally; share only the sanitized
  metadata. Do not share credentials, original files or identifying logs.
- Confirmation of actual HA OS architecture/version, media mount path, SMB share
  permissions and whether dedicated output/staging hard-link publication works.
- Access to the target environment or owner-run results. No such access/evidence
  is currently available in the development workspace.

Before configuring the parser, verify what the filename timestamp actually means,
its timezone/offset, DST repeated-hour behavior, clips crossing midnight and how
long a recording may remain open. Never guess a Reolink convention. Grouping is by
clip start date; clips are not split at midnight. Confirm this policy matches the
real recording behavior before release.

## Device protocol

Record commit SHA, add-on version, HA OS/Supervisor version, architecture, Pi RAM,
FFmpeg version and redacted NAS/SMB configuration. Keep the raw audit data local.
Prepare backups before an alpha installation; never loosen original-file
permissions merely to make the add-on work.

| Check | Required evidence | Current result |
| --- | --- | --- |
| Alpha repository installation | #alpha selected, aarch64 image built, service healthy | NOT RUN |
| NAS mount | Actual /media path and share available after reboot | NOT RUN |
| Permissions | Source reads work; only dedicated output/staging writes allowed | NOT RUN |
| NAS publication primitives | Same filesystem, hard-link publication and fsync succeed | NOT RUN |
| Source adapter | Sanitized names mapped correctly, explicit timestamp semantics | NOT RUN |
| Multiple cameras | At least two cameras where available, no cross-camera mixing | NOT RUN |
| Full previous day | All eligible clips, correct start/middle/end ordering and duration | NOT RUN |
| Original preservation | Local before/after hashes and metadata audit unchanged | NOT RUN |
| Midnight and DST | Correct local date including repeated/gap timestamps | NOT RUN |
| Scheduler | Automatic 00:15 job uses previous calendar day | NOT RUN |
| Late arrival | New clip detected; new current version; previous valid version retained | NOT RUN |
| Incompatible/corrupt input | Explicit failure, no transcoding or partial final export | NOT RUN |
| Restart/interruption | Running state recovered; no duplicate active export | NOT RUN |
| Missing/corrupt output | Reconciliation handles missing/metadata-changed outputs; full integrity audit also checked | NOT RUN |
| Ingress access | Authenticated HA user allowed; direct peer rejected | NOT RUN |
| Manual reprocess | Valid date enqueued; invalid/future/unknown camera rejected | NOT RUN |
| Playback and seeking | H.264 and real supported codecs; beginning/middle/end viewed | NOT RUN |
| H.265 fallback | Browser support or accurate download/compatibility message | NOT RUN |
| Space exhaustion | No loss of originals or prior current export | NOT RUN |
| Backup/upgrade/recovery | Paired code/database backup restored successfully | NOT RUN |
| Pi performance | Wall time, peak RSS, CPU and NAS footprint recorded | NOT RUN |
| Dependency/licenses review | Exact binary/source notices and redistribution obligations complete | NOT RUN |
| Owner review | Evidence reviewed and explicit release/merge instruction | NOT GIVEN |

Start with a small synthetic NAS folder on the real device, then read-only real
inputs after their adapter is verified. Use a dedicated test output/staging area.
Do not run destructive fault injection against original recordings or remove any
source file. For original-preservation checks, take local source-only hashes
before/after (exclude output/staging), and retain those private lists outside Git.
To test failure safely, use copied synthetic media or a mock output filesystem.

For interruption, stop the app during a synthetic merge, restart it, inspect job
history/backoff and confirm the prior current output remains playable. A later
hardware power-loss test needs owner-controlled test storage and backups; it has
not been performed here.

## Capacity and benchmark sheet

Record per tested camera/day: source count and bytes, current-output bytes, total
retained-version/staging bytes, media duration, wall-clock job duration, peak RSS,
peak/average CPU, retry count and available NAS space before/after. SQLite history
contains running/completion timestamps; keep device metrics local and sanitize
summaries. Repeat with representative daytime/nighttime/audio codecs. Emulated
or workstation measurements must not be presented as Pi 4 benchmarks.

Initial limits to verify against the real workload:

- Maximum 256 clips/job. Larger days fail explicitly; if the actual workload
  exceeds this, safe bounded chunked processing must be implemented before release.
- MP4 with exactly one matching H.264/H.265 stream and optional matching AAC;
  other containers/stream layouts require a verified future adapter/policy.
- Stream parameters/extradata must match exactly; no automatic transcoding.
- One-hour FFmpeg timeout; sequential jobs only.
- Same-filesystem hard-link/fsync support required for publication.
- Retained immutable versions and orphan partials can consume additional NAS space.
- Six-hour reconciliation and seven-day initial recovery by default, bounded to
  366 dates / latest 1,000 job summaries per automatic pass; older backfill is manual.

## Release decision

Phase 7 can pass only after all required real-device evidence is filled in,
GitHub CI passes for the reviewed alpha SHA, release-critical findings are fixed,
license/source redistribution work is complete and the owner reviews the results.
A passing synthetic suite does not establish production readiness. Do not tag a
release or merge/push to main without the separate explicit owner instruction.
