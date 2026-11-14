# Camera Daily Merger 0.1.0

## Delivered behavior

- Daily previous-calendar-day exports at 00:15 in the configured timezone.
- Lossless compatible MP4 joining, sequential processing, persisted retries and
  reconciliation; originals are never modified, moved or deleted.
- Fixed automatic 2×2 view for four cameras, equal viewport-fitting windows,
  compact navigation and controls outside video images, with digital zoom/pan.
- Latest-per-camera and shared-day views; native Home Assistant Webpage embedding
  without copied recordings, custom resources or YAML.
- A single authoritative version for installed package, app API and add-on options.

## Live confirmation and qualification boundary

After reporting alpha.14 working, the owner requested this version and affirmed
four bundled live checks: automatic 00:15 processing, complete multi-camera video
playback at beginning/middle/end, app restart with continued processing, and
unchanged originals. No private recordings or deployment credentials were collected.
No direct access, hash lists, metrics or device logs were supplied to the workspace.

This is the requested **0.1.0 source version on alpha** for that confirmed normal
workflow. Experimental app metadata remains intentional: the extended acceptance
matrix still lacks hardware measurements, full power-loss/NAS-outage behavior,
paired backup restore, source-hash audit details and real DST/codec variant checks.
These are not represented as passed. No software can promise perfect operation
under all storage/hardware conditions. See ACCEPTANCE.md and TEST_REPORT.md.

No main merge, release tag, published binary image or automatic deployment is part
of this delivery. The existing alpha repository remains the installation source.

## Upgrade and rollback

Update the existing app from alpha after saving paired code/state backups. Do not
uninstall or delete its database. Options, camera mappings, schema v2, outputs and
browser layout v3 remain unchanged. Restart the app, refresh the browser, confirm
version 0.1.0 in Processing, and check the next scheduled run. NAS recordings need
separate backup; Home Assistant app backup does not back up the media share.
Rollback requires the matching app/state backup described in OPERATIONS.md.

## Known operating bounds

- aarch64 only; no armv7 support. One merge at a time; up to 256 clips per job.
- Matching MP4 H.264/H.265 and optional matching AAC. No implicit transcoding.
  Browser H.265 support varies. Derived r_frame_rate differences alone are allowed.
- Default recovery covers seven days with six-hour reconciliation. Older backfill
  is manual; source timestamp ambiguity is reported rather than guessed.
- Output/staging must support same-filesystem hard-link publication and fsync.
  Retained output versions/partials consume NAS space; no automatic deletion.
- Up to six simultaneous streams across clients. Normal four-camera automatic
  layout was tested without scrolling; unusually small cards still need physical
  space for readable controls.
- Ingress access uses the existing Home Assistant policy; no public video port.

Project source remains MIT. Base images, Python, FFmpeg and codec libraries retain
their own licenses; this source delivery publishes no binary images. Consult
THIRD_PARTY.md before redistributing a self-built image.
