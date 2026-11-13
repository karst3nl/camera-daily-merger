"""Single-worker lifetime lock, crash recovery and immutable managed outputs."""

from contextlib import contextmanager
from dataclasses import asdict
from datetime import date
import fcntl
import hashlib
import json
import os
from pathlib import Path
import threading
import time

from .merger import merge
from .persistence import Store, decode_manifest
from .probe import MediaError
from .settings import Settings
from .storage import directory, open_relative


@contextmanager
def worker_lock(data: Path):
    descriptor = os.open(
        data / "worker.lock", os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield
    finally:
        os.close(descriptor)


def output_healthy(
    settings: Settings, row: dict | None, *, store: Store | None = None
) -> bool:
    if not row or not row["output"]:
        return False
    try:
        metadata = json.loads(row["output"])
        with (
            directory(settings.root) as root,
            open_relative(root, metadata["path"]) as descriptor,
        ):
            info = os.fstat(descriptor)
            if info.st_size != metadata["size"]:
                return False
            snapshot = {
                "mtime_ns": info.st_mtime_ns,
                "device": info.st_dev,
                "inode": info.st_ino,
            }
            if all(metadata.get(key) == value for key, value in snapshot.items()):
                return True
            with os.fdopen(os.dup(descriptor), "rb") as source:
                valid = (
                    hashlib.file_digest(source, "sha256").hexdigest()
                    == metadata["sha256"]
                )
            if valid and store is not None:
                store.cache_output(row, metadata | snapshot)
            return valid

    except (OSError, ValueError, KeyError):
        return False


def enqueue(
    store: Store,
    settings: Settings,
    camera: str,
    day: date,
    clips,
    *,
    now=None,
    force=False,
):
    if camera not in settings.cameras or any(
        c.camera != camera or c.start.date() != day for c in clips
    ):
        raise ValueError("Camera/date does not match manifest")
    row = store.get(camera, day.isoformat())
    return store.enqueue(
        camera,
        day.isoformat(),
        clips,
        time.time() if now is None else now,
        force=force,
        healthy=output_healthy(settings, row, store=store),
    )


def run_one(
    store: Store, settings: Settings, data: Path, cancel: threading.Event, *, now=None
):
    """Must be called under worker_lock; DB claim also prevents duplicate job claims."""
    fixed_now = now
    now = time.time() if now is None else now
    job = store.claim(now)
    if not job:
        return False
    try:
        result = merge(
            settings,
            decode_manifest(job["manifest"]),
            date.fromisoformat(job["day"]),
            temporary_directory=str(data),
            cancel=cancel,
            output_token=job["token"],
        )
        store.finish(
            job, time.time() if fixed_now is None else now, output=asdict(result)
        )
    except MediaError as error:
        store.finish(
            job, time.time() if fixed_now is None else now, error=str(error)[:200]
        )
    except (OSError, ValueError):
        store.finish(
            job,
            time.time() if fixed_now is None else now,
            error="storage_or_validation_failure",
        )
    return True
