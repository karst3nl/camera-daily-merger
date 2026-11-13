"""Single-worker service with calendar scheduling and independent heartbeat."""

import argparse
from datetime import UTC, datetime
import logging
import json
import os
from pathlib import Path
import signal
import threading
import tempfile
import time

from .backfill import load_settings
from .jobs import run_one, worker_lock
from .persistence import Store
from .scheduler import Schedule, Scheduler
from .web import serve


def validate_storage(data: Path, media: Path) -> None:
    if not data.is_dir() or not media.is_dir():
        raise ValueError("Required data/media mount is unavailable")
    # Anonymous state-only writeability check cannot leave a blocking startup marker.
    with tempfile.TemporaryFile(dir=data):
        pass


def healthy(data: Path) -> bool:
    try:
        age = time.time() - (data / "heartbeat").stat().st_mtime
        return 0 <= age < 90
    except OSError:
        return False


def run(data: Path, media: Path, stop: threading.Event) -> None:
    validate_storage(data, media)
    heartbeat = data / "heartbeat"

    def beat():
        while not stop.is_set():
            descriptor = os.open(
                heartbeat, os.O_WRONLY | os.O_CREAT | os.O_NOFOLLOW, 0o600
            )
            try:
                os.utime(descriptor)
            finally:
                os.close(descriptor)
            stop.wait(20)

    thread = threading.Thread(target=beat, daemon=True)
    thread.start()
    try:
        if stop.is_set():
            return
        config = Path(os.environ.get("MERGER_CONFIG", str(data / "discovery.json")))
        settings = load_settings(config) if config.exists() else None
        if settings and not settings.root.is_relative_to(media):
            raise ValueError("Configured source root must be within media mount")
        store = Store(data / "jobs.sqlite")
        development = os.environ.get("MERGER_DEVELOPMENT") == "1"
        with serve(
            store,
            settings,
            host="127.0.0.1" if development else "0.0.0.0",
            port=int(os.environ.get("MERGER_WEB_PORT", "8099")),
            peers={"127.0.0.1"} if development else None,
        ):
            if not settings:
                logging.info(
                    "No source configuration; processing disabled until configured and restarted"
                )
                stop.wait()
                return
            schedule_path = data / "schedule.json"
            values = (
                json.loads(schedule_path.read_text()) if schedule_path.exists() else {}
            )
            schedule = Schedule(
                reconcile_seconds=int(
                    os.environ.get(
                        "MERGER_RECONCILE_SECONDS",
                        values.get("reconcile_seconds", 21600),
                    )
                ),
                backfill_days=int(
                    os.environ.get(
                        "MERGER_BACKFILL_DAYS", values.get("backfill_days", 7)
                    )
                ),
            )
            with worker_lock(data):
                store.recover(time.time())
                scheduler = Scheduler(store, settings, schedule)
                logging.info(
                    "Worker ready; automatic scheduling enabled, concurrency=1"
                )
                next_scan = 0
                while not stop.is_set():
                    now = datetime.now(UTC)
                    if now.timestamp() >= next_scan:
                        try:
                            report = scheduler.tick(now)
                            if report["diagnostics"]:
                                logging.warning(
                                    "Discovery blocked %d camera/date diagnostics",
                                    len(report["diagnostics"]),
                                )
                        except OSError:
                            logging.error(
                                "Storage scan unavailable; retrying next minute"
                            )
                        next_scan = (int(now.timestamp()) // 60 + 1) * 60
                    if not run_one(store, settings, data, stop):
                        stop.wait(min(20, max(0.1, next_scan - time.time())))
    finally:
        stop.set()
        thread.join(timeout=21)
        heartbeat.unlink(missing_ok=True)
        logging.info("Shutdown complete")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    data = Path(os.environ.get("MERGER_DATA", "/data"))
    media = Path(os.environ.get("MERGER_MEDIA", "/media"))
    if args.healthcheck:
        return 0 if healthy(data) else 1
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    try:
        run(data, media, stop)
    except (OSError, ValueError):
        logging.error("Startup/storage validation failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
