"""Read-only snapshots and diagnostic dry-run discovery."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
import os
import errno
from pathlib import PurePosixPath
import stat
import time
from typing import Iterator

from .settings import Settings
from .storage import directory, open_relative
from .timestamp_parser import RegexTimestampParser, TimestampError, TimestampParser


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
    detail: str | None = None
    recording_date: date | None = None


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
        settings.timestamp_pattern, settings.timezone, settings.timestamp_format
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
                                    except TimestampError as error:
                                        yield Diagnostic(
                                            camera,
                                            relative,
                                            "invalid_timestamp",
                                            error.code,
                                            error.recording_date,
                                        )
                                        continue
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
        except OSError as error:
            reason = {
                errno.ENOENT: "source_directory_not_found",
                errno.EACCES: "source_directory_permission_denied",
                errno.EPERM: "source_directory_permission_denied",
                errno.ENOTDIR: "source_directory_not_directory_or_symlink",
                errno.ELOOP: "source_directory_symlink_rejected",
                errno.EIO: "source_directory_io_error",
                errno.ESTALE: "source_directory_io_error",
            }.get(error.errno, "unreadable_or_unsafe_directory")
            yield Diagnostic(camera, path, reason)
        except ValueError:
            yield Diagnostic(camera, path, "source_directory_invalid_path")

    with directory(settings.root) as root_fd:
        for camera, path in settings.cameras.items():
            yield from walk(root_fd, camera, path)


def chronological(clips: list[Clip]) -> list[Clip]:
    return sorted(clips, key=lambda clip: (clip.start.astimezone(UTC), clip.path))
