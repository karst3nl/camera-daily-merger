# Operations and recovery

## Storage and least privilege

Mount network storage using Home Assistant's supported Media network-storage
facility. Credentials remain in HA's local setup. Verify the actual container
mount before configuring source_root. Synology internal volume paths are not
container paths. Use dedicated output and staging directories excluded from
source discovery; they must be on the same writable filesystem. Prefer NAS ACLs
that allow reads of source folders and writes only to those dedicated directories.
Do not change permissions/ownership of original recordings. Separate read-only
source and writable output shares would strengthen protection but require a
future configuration design; the current app uses one root and application-level
confinement plus any NAS ACLs available.

## State, logs and backups

Persistent /data contains options, optional advanced configuration, SQLite state,
worker lock and heartbeat. Job summaries expose only controlled diagnostic codes;
source manifests/paths remain local in SQLite. Logs suppress raw FFmpeg stderr
because filenames can contain private information. Never publish a DB or raw
configuration/logs. Back up /data using HA's app backup facilities and verify the
restore on a test environment. Stop the app for a manual cold backup and include
the entire state directory, including any SQLite WAL/SHM files. Keep a matching
alpha source commit/image reference with the backup. Back up NAS storage separately;
HA app backups do not imply that media/originals are backed up.

## Upgrades and rollback

Update alpha only after saving paired code/state backups. Schema v1 migrates to v2
without losing queued work; unknown/newer schema versions fail closed. A code
rollback may require the corresponding pre-upgrade state backup; do not delete
the DB or force an older app to write a newer schema. Confirm mount paths, parser,
health and current-output playback after every change. No automatic source or
export cleanup is implemented.

## Output integrity and NAS load

Routine reconciliation uses cached size/mtime/device/inode to avoid rereading
unchanged videos. Changed metadata or legacy output records trigger a full SHA256
comparison; valid results refresh the cached snapshot. Missing/truncated/changed
outputs fail this check. Silent corruption preserving every metadata field needs
a separate full integrity audit or explicit reprocess; routine checks are not a
cryptographic scrub of all historical data. Automatic lookback is seven days by
default, plus due failed historical jobs; older healthy dates use manual backfill.

## Interrupted jobs and failed exports

A lifetime worker lock prevents two service workers. Restart marks persisted
running jobs interrupted; retries wait for backoff and stop after five attempts.
A changed manifest starts a new budget, or the user may explicitly reprocess a
completed historical date. The old current export stays referenced on failure.
Successful exports use immutable versions; the SQLite pointer selects the current
one. A crash between filesystem publication and DB commit can leave an orphan
version. A hard stop can leave a UUID.partial staging file. They are not presented
as success and are never automatically removed. Review recovery/cleanup locally;
no destructive cleanup command is provided in this alpha.

If storage is full, the export fails safely; make space through owner-controlled
management of designated output/staging storage or expand capacity. Never remove
original clips as a recovery step. SQLite corruption requires restoring the paired
backup and reconciling outputs, not adopting arbitrary files as completed exports.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Processing disabled | Complete camera mappings and verified adapter in HA Configuration; restart; advanced discovery.json overrides options |
| Storage scan unavailable | HA Media mount, share reachability and read permissions; do not bypass safe path checks |
| invalid_timestamp | Filename/zone policy, malformed date or ambiguous/nonexistent DST hour |
| empty_or_unsettled | File still recent/growing/empty or device clock incorrect; retry after recording completes |
| symlink/hardlink rejection | Explicit regular source paths are required; do not follow links to bypass confinement |
| Incompatible streams | Compare safe codec metadata; no implicit re-encode will occur |
| Publication error | Same filesystem, hard-link support, output/staging permissions, available space |
| Retry exhausted | Correct the cause, then use explicit reprocess; avoid repeated busy retries |
| UI forbidden | Open through HA ingress; verify Supervisor DNS/peer; do not expose a host port |
| Player error | Check browser codec support, especially H.265; try download in a compatible player |
| More than 256 clips | Current capacity limit; requires a future bounded merge extension before release |

Report bugs with alpha SHA, sanitized diagnostic codes, minimal synthetic
reproduction and safe codec metadata. No original footage, credentials, private
network addresses or identifying filenames should be attached.
