# Camera Daily Merger

MIT-licensed Home Assistant add-on, version **0.1.0**, maintained on **alpha**. Designed to
join each camera's previous local day at 00:15 Europe/Berlin using FFmpeg stream
copy. Original recordings must never be modified or deleted. No automatic
transcoding is planned.

## Development

Python 3.12 is the baseline (available on aarch64 Raspberry Pi 4 runtimes).

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[dev]'
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/python -m pytest
.venv/bin/python -m build
```

Use synthetic recordings and temporary mock NAS directories only. Never commit
recordings, credentials, private network details, logs or local databases.

See [specification](docs/SPECIFICATION.md), [implementation plan](docs/CODEX_IMPLEMENTATION_PLAN.md),
[architecture](docs/ARCHITECTURE.md) and [test report](docs/TEST_REPORT.md).
Synthetic end-to-end merging, scheduling and a protected web interface are implemented.
See [setup](docs/SETUP.md) and [0.1.0 release notes](docs/RELEASE_0.1.0.md).
The owner confirmed scheduled daily processing, multi-camera playback, app restart
recovery and unchanged originals on their live installation. Extended fault and
hardware qualification is incomplete; app metadata remains experimental.

## License

Project code and documentation use the [MIT license](LICENSE). Third-party
software retains its own licenses; see [dependency notices](docs/THIRD_PARTY.md).

Current source version: **0.1.0**. Install the alpha repository using
`https://github.com/karst3nl/camera-daily-merger#alpha`; see setup for verified
branch-selector behavior and device-test limitations. Configure sources in the
Home Assistant Configuration tab; empty defaults do not process media.

See [real-device acceptance](docs/ACCEPTANCE.md), [operations/recovery](docs/OPERATIONS.md)
and [security model](docs/SECURITY.md). Important initial limits include 256 clips
per job, conservative MP4 codec matching, and retained output versions consuming
extra storage. See the acceptance matrix for confirmed and outstanding device checks.

The camera view defaults to **2×2 for four cameras**, using equal windows that
fill the available viewport. Compact navigation and external wrapping playback
controls keep the normal view free of page/control scrolling. Digital zoom and
pan operate locally without changing recordings. **Layout** retains optional
manual columns/sizing.

**Latest per camera** and **All cameras by day** can also be embedded in a native
Home Assistant **Webpage** card. Open **Processing > Dashboard setup** for stable
URLs and follow the [dashboard guide](docs/DASHBOARD.md). No file copies, custom
resources or YAML are required. Home Assistant manages authenticated ingress;
recordings stream directly from existing exports. Setup is absent from camera views.
