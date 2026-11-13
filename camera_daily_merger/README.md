# Camera Daily Merger — Alpha

Join each camera's previous local day using FFmpeg stream copy. Original
recordings stay untouched. Configure camera folders and a verified timestamp
adapter before enabling processing; empty defaults do not process media.

Synthetic merging, scheduling, retry and browser tests pass. Real Home Assistant
OS, Raspberry Pi 4, Synology storage and Reolink codec/filename semantics remain
unverified. This alpha is not a production release.

Initial limits: MP4 H.264/H.265 with matching optional AAC, 256 clips per job,
sequential processing, and same-filesystem hard-link publication. Immutable output
versions remain on NAS; no automatic retention/deletion is implemented.

Open the UI through HA ingress. No public host port is mapped. See the
Documentation tab for setup, and the project's
[acceptance protocol](https://github.com/karst3nl/camera-daily-merger/blob/alpha/docs/ACCEPTANCE.md)
and [operations guide](https://github.com/karst3nl/camera-daily-merger/blob/alpha/docs/OPERATIONS.md).

Project code is MIT-licensed. Bundled FFmpeg and other libraries retain their own
license terms; see THIRD_PARTY.md. Develop and test alpha only; main requires
separate owner approval after real-device acceptance.
