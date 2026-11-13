# Alpha installation

This version is a log-only bootstrap, not a recording merger. Do not rely on it
for daily exports. No web server, ingress, host ports, privileged mode or
Supervisor API access is enabled. Ingress is deferred to Phase 6.

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

Check logs for “Bootstrap ready”; stop/restart and check “Shutdown complete”.
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
