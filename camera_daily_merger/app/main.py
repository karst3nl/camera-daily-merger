"""Log-only bootstrap service. Does not scan or modify media."""

import argparse
import logging
import os
from pathlib import Path
import signal
import threading
import time


def validate_storage(data: Path, media: Path) -> None:
    if not data.is_dir() or not media.is_dir():
        raise ValueError("Required data/media mount is unavailable")
    # Only the dedicated application state mount may be written in this phase.
    marker = data / "bootstrap-check"
    with marker.open("x"):
        pass
    marker.unlink()


def healthy(data: Path) -> bool:
    try:
        age = time.time() - (data / "heartbeat").stat().st_mtime
        return 0 <= age < 90
    except OSError:
        return False


def run(data: Path, media: Path, stop: threading.Event) -> None:
    validate_storage(data, media)
    logging.info("Bootstrap ready; media processing is not implemented")
    heartbeat = data / "heartbeat"
    try:
        while not stop.is_set():
            heartbeat.touch()
            stop.wait(20)
    finally:
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
