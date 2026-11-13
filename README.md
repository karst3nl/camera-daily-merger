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
A log-only alpha installation skeleton is described in [setup](docs/SETUP.md). Real Reolink layouts, Home Assistant OS and NAS
operation remain unverified. This is not a production-ready add-on.

## License

Project code and documentation use the [MIT license](LICENSE). Third-party
software retains its own licenses; see [dependency notices](docs/THIRD_PARTY.md).
