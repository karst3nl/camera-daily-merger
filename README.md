# Camera Daily Merger

MIT-licensed Home Assistant add-on under development on **alpha**. Intended to
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
See [alpha setup](docs/SETUP.md) and the test report before installing. Real Reolink layouts, Home Assistant OS and NAS
operation remain unverified. This is not a production-ready add-on.

## License

Project code and documentation use the [MIT license](LICENSE). Third-party
software retains its own licenses; see [dependency notices](docs/THIRD_PARTY.md).

Current add-on snapshot: **0.1.0-alpha.5**. Install the alpha repository using
`https://github.com/karst3nl/camera-daily-merger#alpha`; see setup for verified
branch-selector behavior and device-test limitations. Configure sources in the
Home Assistant Configuration tab; empty defaults do not process media.

See [real-device acceptance](docs/ACCEPTANCE.md), [operations/recovery](docs/OPERATIONS.md)
and [security model](docs/SECURITY.md). Important initial limits include 256 clips
per job, conservative MP4 codec matching, and retained output versions consuming
extra storage. Real-device acceptance is blocked pending owner input/results.
