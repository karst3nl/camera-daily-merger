"""Enqueue a bounded historical range; the service worker processes it sequentially."""

import argparse
from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path

from .persistence import Store
from .scheduler import Scheduler
from .settings import Settings, from_addon_options


def load_settings(path: Path) -> Settings:
    values = json.loads(path.read_text())
    if "source_root" in values:
        settings = from_addon_options(values)
        if settings is None:
            raise ValueError("Source configuration is incomplete")
        return settings
    values["root"] = Path(values["root"])
    return Settings(**values)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--camera", required=True)
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    count = (args.end - args.start).days + 1
    if not 1 <= count <= 366:
        parser.error("Backfill must cover 1..366 days")
    settings = load_settings(args.config)
    store = Store(args.data / "jobs.sqlite")
    result = Scheduler(store, settings).reconcile(
        {args.start + timedelta(days=n) for n in range(count)},
        datetime.now(UTC),
        camera=args.camera,
        force=args.force,
    )
    print(json.dumps(result))


if __name__ == "__main__":
    main()
