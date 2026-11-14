"""Linux descriptor-relative read-only access; never follow source symlinks."""

from contextlib import contextmanager
import os
from pathlib import Path
import stat

from .settings import relative_path


@contextmanager
def directory(path: Path):
    """Open every root component without symlink traversal."""
    if not path.is_absolute():
        raise ValueError("Absolute root required")
    descriptor = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        for component in path.parts[1:]:
            if component in (".", ".."):
                raise ValueError("Invalid root component")
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def open_relative(root_fd: int, path: str, *, is_directory: bool = False):
    parts = relative_path(path).split("/")
    descriptor = os.dup(root_fd)
    try:
        for index, component in enumerate(parts):
            flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
            if index < len(parts) - 1 or is_directory:
                flags |= os.O_DIRECTORY
            child = os.open(component, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        if not is_directory and not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ValueError("Only regular source files are accepted")
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def writable_directory(root_fd: int, path: str):
    """Create/open only explicitly designated output directories, no symlinks."""
    descriptor = os.dup(root_fd)
    try:
        for component in relative_path(path).split("/"):
            try:
                os.mkdir(component, mode=0o750, dir_fd=descriptor)
            except FileExistsError:
                pass
            child = os.open(
                component,
                os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                dir_fd=descriptor,
            )
            os.close(descriptor)
            descriptor = child
        yield descriptor
    finally:
        os.close(descriptor)


@contextmanager
def open_export(settings, camera: str, day: str, metadata: dict):
    """Open only a DB-managed immutable export, with matching size."""
    from datetime import date
    from pathlib import PurePosixPath
    import re

    if (
        not isinstance(metadata, dict)
        or not isinstance(metadata.get("sha256"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"])
    ):
        raise ValueError("Invalid export version")
    if date.fromisoformat(day).isoformat() != day:
        raise ValueError("Invalid export date")
    relative = PurePosixPath(metadata["path"])
    if relative.parent != PurePosixPath(settings.output) / camera or not re.fullmatch(
        re.escape(day) + r"-[0-9a-f]{32}\.mp4", relative.name
    ):
        raise ValueError("Invalid managed export")
    if not isinstance(metadata["size"], int) or metadata["size"] <= 0:
        raise ValueError("Invalid export size")
    with (
        directory(settings.root) as root,
        open_relative(root, metadata["path"]) as source,
    ):
        if os.fstat(source).st_size != metadata["size"]:
            raise ValueError("Output size changed")
        yield source
