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
