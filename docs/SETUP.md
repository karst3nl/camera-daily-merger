# Alpha installation

This alpha implements synthetic-tested merging, scheduling and a web interface.
Real Home Assistant/NAS operation remains unverified. The interface uses ingress;
no host ports, privileged mode or Supervisor API access is enabled.

Home Assistant's repository installer reads the default branch. Until release,
use a local add-on checkout of **alpha**, rather than expecting the repository
URL alone to install alpha. With supported access to the HA /addons directory,
copy only camera_daily_merger from the alpha checkout into
/addons/camera_daily_merger, then reload the app store, install the local app and
start it. Never change main to make alpha discoverable. Local builds require
network access to the Python base image registry. Only aarch64 is declared;
armv7 is not supported by this bootstrap image.

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
reconciliation runs every six hours and also revisits due failed jobs. These are
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
