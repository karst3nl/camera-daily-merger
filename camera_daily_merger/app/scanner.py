"""Read-only snapshots and diagnostic dry-run discovery."""

from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import PurePosixPath
import stat
import time
from typing import Iterator

from .settings import Settings
from .storage import directory, open_relative
from .timestamp_parser import RegexTimestampParser, TimestampParser


@dataclass(frozen=True)
class Clip:
    camera: str
    path: str
    start: datetime
    size: int
    mtime_ns: int
    device: int
    inode: int


@dataclass(frozen=True)
class Diagnostic:
    camera: str
    path: str
    reason: str


def signature(info: os.stat_result) -> tuple[int, int, int, int]:
    return info.st_size, info.st_mtime_ns, info.st_dev, info.st_ino


def scan(
    settings: Settings,
    *,
    now: float | None = None,
    parser: TimestampParser | None = None,
) -> Iterator[Clip | Diagnostic]:
    now = time.time() if now is None else now
    parser = parser or RegexTimestampParser(
        settings.timestamp_pattern, settings.timezone
    )
    reserved = (PurePosixPath(settings.output), PurePosixPath(settings.staging))

    def walk(root_fd: int, camera: str, path: str):
        if any(PurePosixPath(path).is_relative_to(r) for r in reserved):
            return
        try:
            with open_relative(root_fd, path, is_directory=True) as folder:
                with os.scandir(folder) as entries:
                    for entry in entries:
                        relative = str(PurePosixPath(path) / entry.name)
                        try:
                            info = entry.stat(follow_symlinks=False)
                            if stat.S_ISLNK(info.st_mode):
                                yield Diagnostic(camera, relative, "symlink_rejected")
                            elif stat.S_ISDIR(info.st_mode):
                                yield from walk(root_fd, camera, relative)
                            elif (
                                PurePosixPath(entry.name).suffix.lower()
                                in settings.extensions
                            ):
                                with open_relative(root_fd, relative) as source:
                                    before = os.fstat(source)
                                    if before.st_nlink != 1:
                                        yield Diagnostic(
                                            camera, relative, "hardlink_rejected"
                                        )
                                        continue
                                    if (
                                        before.st_size == 0
                                        or now - before.st_mtime
                                        < settings.minimum_age_seconds
                                    ):
                                        yield Diagnostic(
                                            camera, relative, "empty_or_unsettled"
                                        )
                                        continue
                                    try:
                                        start = parser.parse(entry.name)
                                    except ValueError:
                                        yield Diagnostic(
                                            camera, relative, "invalid_timestamp"
                                        )
                                        continue
                                    if signature(info) != signature(
                                        before
                                    ) or signature(before) != signature(
                                        os.fstat(source)
                                    ):
                                        yield Diagnostic(
                                            camera, relative, "changed_during_scan"
                                        )
                                        continue
                                    yield Clip(
                                        camera, relative, start, *signature(before)
                                    )
                        except (OSError, ValueError):
                            yield Diagnostic(camera, relative, "unreadable_or_unsafe")
        except (OSError, ValueError):
            yield Diagnostic(camera, path, "unreadable_or_unsafe_directory")

    with directory(settings.root) as root_fd:
        for camera, path in settings.cameras.items():
            yield from walk(root_fd, camera, path)


def chronological(clips: list[Clip]) -> list[Clip]:
    return sorted(clips, key=lambda clip: (clip.start.astimezone(UTC), clip.path))
