# Alpha installation

This alpha implements synthetic-tested merging, scheduling and a web interface.
Real Home Assistant/NAS operation remains unverified. The interface uses ingress;
no host ports, privileged mode or Supervisor API access is enabled.

## Install from alpha

In Home Assistant, open Settings > Apps (Add-ons on older versions) > app store,
open the repositories menu and add:

```text
https://github.com/karst3nl/camera-daily-merger#alpha
```

Reload the store, select Camera Daily Merger and install the alpha build. Confirm
version 0.1.0-alpha.10 or newer from alpha. The `#alpha` selector is important:
without it the repository's default branch is used. Current Supervisor source
explicitly parses this selector and passes it as Git's clone branch; the actual
HA store installation flow still requires device acceptance. This corrects the
earlier bootstrap instructions that only described a local-copy installation.

If a local add-on installation is preferred, copy camera_daily_merger from an
alpha checkout into /addons/camera_daily_merger, reload the store and install
that local app. Never change main to make alpha discoverable. Builds need network
access to the Python/Alpine registries and signed Alpine package repositories.
Only aarch64 is declared; armv7 is not supported.

Verified Supervisor source reference (repository selector and clone behavior):
https://github.com/home-assistant/supervisor/blob/98a2322374ae3d0c248079d11f7435ad759935fa/supervisor/validate.py
and the same revision's supervisor/store/git.py.

Home Assistant provides persistent /data automatically. The supported media map
exposes /media read-write for future dedicated output/staging directories. Mount
NAS storage using Settings > System > Storage > Add network storage, select
Media usage and configure NAS_HOST/share/credentials locally. Expected source
path /media/reolink must be checked on the real installation; Synology internal
paths are not container paths. Restrict NAS credentials where possible; the
media mount itself is writable, so application path confinement remains essential.
This bootstrap never writes to media.

Check logs for “Worker ready” after source configuration; stop/restart and check
“Shutdown complete”. Without configuration the UI explains that setup is required.
Actual HA OS installation, mount exposure and Pi 4 operation are NOT VERIFIED.

Configuration reference checked 2026-11-13:
https://developers.home-assistant.io/docs/add-ons/configuration/

It documents aarch64, application startup, Docker init, automatic /data and
media map entries with read_only. Full Supervisor schema validation and actual
installation remain separate acceptance checks.

The current add-on linter and ARM64-emulated startup tests pass. Native Pi 4 and
Home Assistant OS installation are still unverified. Configuration omits default
startup/boot/init/options/schema values as required by the current linter.

## Synthetic discovery dry-run

Create a local JSON configuration (do not commit deployment-specific paths):

```json
{
  "root": "/media/reolink",
  "cameras": {"camera_a": "synthetic_input"},
  "timestamp_pattern": "(?P<start>.+)\\.mp4",
  "timezone": "Europe/Berlin",
  "output": "daily",
  "staging": ".staging",
  "minimum_age_seconds": 60
}
```

Run `python -m camera_daily_merger.app.discover /path/to/config.json` in the
checkout, or `python -m app.discover /data/discovery.json` inside the add-on.
Output is JSON lines with eligible Clip snapshots and rejection Diagnostics;
this command never creates output directories or writes media. Synthetic example
filename: 2026-11-12T12:00:00+01:00.mp4 (the file need not contain actual video
until probe/merge testing). This adapter is NOT a verified Reolink convention.
Use explicit offsets for repeated DST hours; naive ambiguous/gap times fail.
Camera mappings must not overlap. Symlinks/hardlinks are rejected. File age and
snapshot checks reduce incomplete input risk; actual writer behavior requires
real NAS testing. Store this configuration only locally under /data.

## Automatic processing and backfill

After installing alpha, enter source settings in the Home Assistant app Configuration
tab and restart. Set cameras to a list of `{id: camera_a, path: synthetic_input}`
mappings and timestamp_pattern to the verified adapter regex. The empty defaults
leave processing disabled. Advanced local users may instead provide
`/data/discovery.json` with the explicit JSON adapter above; that file overrides
source options, so remove that override before relying on the Configuration tab. Without complete source settings the service reports
processing disabled; once configured, automatic scheduling is enabled. The worker
runs one merge at a time. At 00:15 in the configured zone it considers the previous
calendar day. Startup recovers interrupted jobs and up to seven completed days;
reconciliation checks that same rolling window every six hours and also revisits
due failed historical jobs. Older healthy dates require manual backfill. These are
bounded recovery defaults, not unlimited automatic historical backfill.

Set reconcile_seconds/backfill_days in the Configuration tab. Optional advanced
`/data/schedule.json` overrides those two option values:

```json
{"reconcile_seconds": 21600, "backfill_days": 7}
```

Intervals must be 60..604800 seconds, backfill 1..366 days. Restart after changes.
Manual administrative enqueue (1..366 dates per call):

```sh
python -m app.backfill --config /data/discovery.json --data /data \
  --camera camera_a --start 2026-11-01 --end 2026-11-12
```

Use `camera_daily_merger.app.backfill` in a checkout. `--force` resets an exhausted
retry budget/reprocesses unchanged inputs. Pending/running jobs are never duplicated.
Only dates whose daily scheduled time has passed are accepted. The running service
processes enqueued work. Source diagnostics block affected days; fix mappings or
incomplete clips before retrying. The latest 1,000 job summaries and up to 366 dates
are included per automatic reconciliation; older history is available via manual
backfill. Earlier output versions remain on NAS. This storage cost has no automatic
retention policy. No original recordings are ever removed.

## Web interface and access

Open the installed app through Home Assistant's ingress panel. The image listens
on internal port 8099, with no host port mapping. The HTTP server accepts only the
Supervisor IPv4 addresses resolved through the documented internal `supervisor`
DNS name. If DNS is unavailable it accepts no HTTP peers. Forwarded IP/user
headers do not grant access. Authentication is delegated to Home Assistant ingress
and the default admin-only panel policy; direct network access is not supported.
Actual Supervisor proxy routing, peer identity and iframe behavior must still be
verified on HA OS. Do not add a public port mapping as a workaround.

The interface lists camera/date status, current daily playback/download, diagnostic
codes and a CSRF-protected reprocess action. It exposes no source manifests, full
NAS paths or credentials. Byte ranges support seeking. H.265 playback varies by
browser; the compatibility message offers a download without labeling the file
corrupt. The UI always distinguishes synthetic verification from actual NAS tests.

For local development only, set `MERGER_DEVELOPMENT=1` and optionally
`MERGER_WEB_PORT=8099`. This explicitly trusts loopback and binds only 127.0.0.1.
Keep that mode disabled in the add-on. Browser gate:

```sh
.venv/bin/python -m pip install '.[dev,browser]'
.venv/bin/python -m tests.integration.check_browser --chromium /usr/bin/chromium
```

Example Configuration tab YAML for **synthetic naming only**, to be replaced by
a verified adapter after inspecting owner-provided anonymized filename patterns:

```yaml
source_root: /media/reolink
cameras:
  - id: camera_a
    path: synthetic_input
timestamp_pattern: '(?P<start>.+)\.mp4'
timezone: Europe/Berlin
output: daily
staging: .staging
minimum_age_seconds: 60
reconcile_seconds: 21600
backfill_days: 7
```

The backfill CLI also accepts `--config /data/options.json` for normal add-on
options, provided source settings are complete. Do not configure credentials here;
network-storage credentials belong to Home Assistant's storage setup.

## Compact timestamp adapter candidate

An owner-provided example establishes this anonymized shape:
`<storage>/<camera>/YYYY/MM/DD/<camera>_00_YYYYMMDDHHMMSS.mp4`.
The scanner supports recursive calendar folders without assuming their exact root.
For a sanitized synthetic camera the candidate settings are:

```yaml
cameras:
  - id: camera_a
    path: camera_a
timestamp_pattern: '.+_00_(?P<start>\d{14})\.mp4'
timestamp_format: '%Y%m%d%H%M%S'
```

The actual source_root must be the verified HA mount containing the camera
folder. Camera IDs/prefixes are deployment-specific local settings, not source
code. Confirm that the timestamp is recording start time in the configured zone
before using this on real recordings. The owner confirmed `_00_` is a fixed
camera-generated filename component with no application meaning. The adapter
treats it literally and uses folder mappings for camera identity. The example
alone does not prove timezone or stream compatibility.
Offset-free repeated DST hours remain rejected. `timestamp_format: iso8601` keeps
the original ISO adapter behavior; date-only values are rejected.

## Startup configuration errors

Camera `path` is relative to `source_root`. For source_root `/media/NAS_SHARE`
and a folder `/media/NAS_SHARE/CameraA`, use `id: cameraa` and `path: CameraA`.
An absolute camera path is rejected. Match the actual folder's capitalization;
the logical ID may use a different case. After saving options, restart the app.
Alpha.4 reports this constraint explicitly instead of the earlier generic startup
failure. Regex, JSON, timezone, mount/OS and database failures also get safe
category-level diagnostics; raw configuration and paths are not printed.

Alpha.4 scanner codes distinguish `source_directory_not_found` (check relative
folder spelling/case), `source_directory_permission_denied` (read permissions),
`source_directory_not_directory_or_symlink` and `source_directory_io_error`.
The same directory problem may appear for every date in the recovery window;
this does not establish that seven separate date folders are missing.

## Finding the recording that blocks a day

Alpha.5 shows the backend version beside verification status. After upgrading,
restart and refresh the UI, then reprocess the requested date. Invalid timestamp
rows include a controlled detail code, the number of affected entries and up to
three example basenames (no source directories). Examples appear only through
authenticated ingress and are rendered as text, including unusual filenames.

- `filename_pattern_mismatch`: inspect timestamp_pattern and unintended escaping.
- `timestamp_format_mismatch`: compact 14-digit names need `%Y%m%d%H%M%S`, not
  the ISO adapter. Confirm the effective saved configuration and restart.
- `ambiguous_or_nonexistent_local_time`: resolve DST timestamp ambiguity using a
  reliable explicit-offset source adapter; do not guess an offset.

Unknown timestamps still block requested dates; the app does not silently skip
potential recordings. Recursive discovery can find a mismatching MP4 outside the
selected calendar folder. Never delete or rename originals to bypass diagnostics.
Do not publish private example names or the local database in bug reports.

## DST errors belonging to another day

Alpha.6 scopes ambiguous/nonexistent local times to their parsed local calendar
date. For example, an offset-free 02:xx clip on the Berlin fall-back date cannot
be ordered reliably, but its recording date is still known. It blocks that date,
not every requested historical day. No offset is guessed and no original is
changed. Truly unparseable filenames with unknown dates still block the requested
camera dates. After upgrading, restart and reprocess to refresh old diagnostics.

## Incompatible stream diagnostics

Alpha.7 adds comparison lines to failed job history. Upgrade, restart, reprocess
and refresh history after the worker finishes. Each line identifies a one-based
chronological clip number versus reference clip 1, a zero-based stream index
(or layout), the field and the two values. Examples include width/height, codec,
timebase, audio layout and codec-header hash. A mismatch reports up to
12 fields from the first incompatible clip; absence is shown explicitly.

The message alone does not establish whether the recordings require conversion
or whether a future verified remux policy can handle a particular difference.
The current exact compatibility rules still reject the mismatch, perform no
transcoding, publish no failed output and retain any previous current export.
Share only non-sensitive comparison values when requesting help; no recordings
or full ffprobe dumps are needed for this diagnostic step.

## Different reported video frame rates

Alpha.8 accepts differences in FFprobe's derived video r_frame_rate when the
other required stream fields match. An estimate such as 239/12 versus 20/1 alone
no longer rejects an export. The merger preserves packet timing with -c copy;
it does not force 20 fps or re-encode. Codec headers, dimensions, timebase and
audio compatibility are still checked. After updating/restarting, manually
reprocess a previously failed day to reset its retry budget, then refresh history.
If another field differs, the field comparison remains the next diagnostic.

## Dashboard views

Alpha.10 supports the normal Home Assistant Webpage card. Open **Dashboard setup**
in the app, then enter its latest/day URL in the card's graphical URL field.
No file copies, custom resources or YAML are required. Follow the
[dashboard guide](https://github.com/karst3nl/camera-daily-merger/blob/alpha/docs/DASHBOARD.md).
Home Assistant manages ingress authentication. Actual owner-device dashboard
acceptance remains to be verified.
