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
