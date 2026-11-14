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

The camera view defaults to a fixed **2×2 wall for four cameras**, compact
navigation and external wrapping playback controls. Equal windows fit the actual
viewport without normal page/control scrolling. Digital zoom/pan and optional
manual layouts remain available; recordings are never copied for the dashboard.

For a native Home Assistant Webpage card, open **Processing > Dashboard setup**;
see the [dashboard guide](https://github.com/karst3nl/camera-daily-merger/blob/alpha/docs/DASHBOARD.md).
No custom resources or YAML are required. Existing authenticated app access applies.
