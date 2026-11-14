# Camera Daily Merger — Project Specification

**Specification version:** 1.4
**Status:** Alpha development; Phases 0–6 synthetic validation complete, real acceptance pending
**License:** MIT (see [LICENSE](../LICENSE))  
**Project:** https://github.com/karst3nl/camera-daily-merger

## 1. Purpose

Camera Daily Merger is an open-source Home Assistant add-on (Home Assistant App) that combines the motion-triggered camera recordings belonging to one camera and one calendar day into one chronologically ordered daily video. Periods without recorded motion are not filled with artificial footage. The resulting videos can be browsed without opening each individual clip.

## 2. Confirmed requirements

- Process the **previous local calendar day** automatically every day at **00:15**, timezone **Europe/Berlin** by default (configurable for other users).
- Produce **one daily video per camera per date**, provided compatible recordings exist.
- Keep the **original video quality** by using lossless stream copying whenever the source streams are compatible; **do not automatically re-encode** incompatible recordings.
- **Permanently retain all original recording files**: the add-on must never delete or modify source recordings.
- Enable **automatic daily processing**.
- Enable **reconciliation/retry** of failed, missing, or incomplete daily exports, including detection of late-arriving source clips.
- Preserve chronological order using reliable recording timestamps derived from file naming and/or metadata after the actual camera file layout is verified.
- Log processing status and errors; avoid replacing a valid output with an incomplete or failed export.
- Be suitable for a Raspberry Pi 4 running Home Assistant OS, with FFmpeg processing sequentially by default.

## 3. Storage design

The initial installation uses a Synology DS223 NAS with the camera recordings in the Synology shared folder named `reolink`.

- The user-specific Synology host address and credentials belong **only in local configuration**, never in version-controlled source files or examples with real values.
- The Synology internal path is `/volume1/reolink`; it is **not** a Home Assistant container path.
- Mount the SMB share through Home Assistant's supported **network storage / media** facility (share name `reolink`), then expose it to the add-on via the Home Assistant media mount (planned path `/media/reolink`; verify at implementation).
- Read source recordings from camera-specific directories, whose actual layout remains **to be inspected**.
- Write daily outputs to a dedicated `daily/` subdirectory, e.g. `daily/<camera-id>/YYYY-MM-DD.mp4`; do not scan this directory as input.
- Keep processing configuration, task state, SQLite metadata and small temporary files under the persistent add-on `/data` path.
- Keep large temporary output files on the NAS in a dedicated staging area on the same share as final outputs, with sufficient free-space checks.
- Restrict writes in application logic to designated output/staging directories. Explore separate read-only and writable SMB shares for stronger NAS-level protection of originals.

## 4. Processing pipeline

1. Schedule and enqueue the previous day's jobs at 00:15 local time.
2. Find eligible camera files without modifying the originals.
3. Determine camera, local recording date, and clip order; exclude ongoing/incomplete recordings.
4. Probe inputs with ffprobe for readability and stream compatibility.
5. Concatenate compatible clips with FFmpeg using stream copy, avoiding quality loss.
6. Write to a temporary output and validate the result before atomically replacing/promoting the daily output where supported.
7. Record source manifest, completion state, diagnostics and output metadata in SQLite.
8. Reconcile previously processed days to detect late clips or failed jobs; rebuild safely if the source set changed.

The actual camera filename conventions, date-boundary behavior (including daylight saving transitions), timestamp priority, compatibility of source video/audio streams, browser playback limitations (especially H.265), and exact validation criteria must be specified after inspecting sample files.

### Derived frame-rate policy

FFprobe's video `r_frame_rate` is a guessed base rate, not a decoder-configuration
invariant. Matching MP4 video streams may therefore be copied with different
reported base rates when all other required stream fields (including codec
headers, geometry, timebase and audio layout) match. Input packet timing is
preserved; the application does not set an output frame rate, duplicate/drop
frames or transcode to normalize these estimates. Output validation uses the
same compatibility policy and duration checks. Actual device acceptance remains
required even after packet/frame/timing-preservation tests pass synthetically.

## 5. Proposed implementation

- Python for orchestration and job scheduling.
- FFmpeg and ffprobe for analysis and concatenation.
- SQLite for job state and source manifests.
- FastAPI with a lightweight HTML/CSS/JavaScript web interface, subject to confirming Home Assistant ingress requirements.
- Add-on image/configuration, build tests, and documentation in the same repository.
- Do not use hardware-intensive re-encoding as an implicit fallback.

## 6. Open-source governance

**License decision: MIT, confirmed 2026-11-13.**

- The repository root **LICENSE** file contains the full MIT License text.
- All source code and documentation contributed to this repository are intended for distribution under the MIT License unless a specific file or dependency states otherwise.
- Include the required copyright and permission notices in substantial redistributions of the software.
- Document bundled third-party dependencies and their applicable licenses; the MIT project license does not override those third-party terms.
- Publish public documentation primarily in English, including installation, configuration, contribution, troubleshooting, and security guidance.
- Do not commit NAS credentials, tokens, private recordings, IP addresses tied to personal deployments, logs with sensitive data, or the local SQLite database.
- Maintain a README, changelog, technical specification, and a suitable .gitignore.
- Use GitHub Issues and, later, CI workflows for tests/builds.
- Coding-agent workflow: implement and test changes, create descriptive Git commits, and push completed reviewed work to GitHub; develop larger changes on feature branches. Secrets must never be committed.

**Repository visibility:** Public is the project goal. Visibility is a GitHub repository setting and is separate from adding an MIT license.

## 7. Open decisions before implementation

1. Inspect actual Reolink folder hierarchy and sample filenames.
2. Identify supported container, video and audio codecs (H.264/H.265, MP4 or other formats).
3. Decide camera discovery versus manual mapping.
4. Decide historical backfill range and manual reprocessing interface.
5. Confirm daily video playback method and browser compatibility requirements.
6. Define retention of daily exports, storage alerts, and exact reconciliation frequency.
7. Confirm NAS share mounting and least-privilege access strategy.

## 8. Non-goals for v1

- No automatic deletion of original recordings.
- No automatic video transcoding for incompatible source recordings.
- No uploading camera recordings to GitHub or external cloud services.
