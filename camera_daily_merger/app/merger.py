"""Stream copy through stable read-only descriptors, then no-clobber publication."""

from contextlib import ExitStack
from dataclasses import dataclass
from datetime import date
import hashlib
import os
import tempfile
import threading
import uuid

from .probe import MediaError, compatibility_differences, execute, probe
from .scanner import Clip, chronological, signature
from .settings import Settings
from .storage import directory, open_relative, writable_directory


@dataclass(frozen=True)
class Output:
    path: str
    duration: float
    size: int
    sha256: str
    mtime_ns: int = 0
    device: int = 0
    inode: int = 0


def merge(
    settings: Settings,
    clips: list[Clip],
    day: date,
    *,
    temporary_directory: str,
    cancel: threading.Event | None = None,
    reserve_bytes: int = 64 * 1024 * 1024,
    output_token: str | None = None,
) -> Output:
    if not clips or len(clips) > 256:
        raise MediaError("Expected 1..256 clips per export")
    clips = chronological(clips)
    camera = clips[0].camera
    if camera not in settings.cameras or any(
        c.camera != camera or c.start.date() != day for c in clips
    ):
        raise MediaError("Mixed camera/day source set")
    if len({c.path for c in clips}) != len(clips):
        raise MediaError("Duplicate source")
    mapped = settings.cameras[camera]
    from pathlib import PurePosixPath

    reserved = [PurePosixPath(settings.output), PurePosixPath(settings.staging)]
    if any(
        not PurePosixPath(c.path).is_relative_to(mapped)
        or any(PurePosixPath(c.path).is_relative_to(r) for r in reserved)
        for c in clips
    ):
        raise MediaError("Source outside camera mapping")
    with ExitStack() as stack:
        root = stack.enter_context(directory(settings.root))
        sources = [stack.enter_context(open_relative(root, c.path)) for c in clips]

        def unchanged():
            for clip, descriptor in zip(clips, sources, strict=True):
                info = os.fstat(descriptor)
                if info.st_nlink != 1 or signature(info) != (
                    clip.size,
                    clip.mtime_ns,
                    clip.device,
                    clip.inode,
                ):
                    raise MediaError("Source snapshot changed; rescan required")
                # Verify that the current name still points at the same inode.
                with open_relative(root, clip.path) as current:
                    if signature(os.fstat(current)) != signature(info):
                        raise MediaError("Source path changed; rescan required")

        unchanged()
        probes = [probe(source, cancel=cancel) for source in sources]
        for index, candidate in enumerate(probes[1:], start=2):
            differences = compatibility_differences(probes[0], candidate)
            if differences:
                fields = ", ".join(
                    dict.fromkeys(item["field"] for item in differences)
                )[:90]
                details = [
                    {**item, "reference_clip": 1, "clip": index} for item in differences
                ]
                raise MediaError(
                    f"Incompatible streams: clip {index} vs 1 ({fields}); no transcoding performed",
                    details=details,
                )
        staging = stack.enter_context(writable_directory(root, settings.staging))
        destination = stack.enter_context(
            writable_directory(root, f"{settings.output}/{camera}")
        )
        if os.fstat(staging).st_dev != os.fstat(destination).st_dev:
            raise MediaError("Staging and output must share a filesystem")
        space = os.fstatvfs(staging)
        if (
            space.f_bavail * space.f_frsize
            < sum(c.size for c in clips) * 1.1 + reserve_bytes
        ):
            raise MediaError("Insufficient staging space")
        name = uuid.uuid4().hex + ".partial"
        output_fd = os.open(
            name,
            os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o640,
            dir_fd=staging,
        )
        try:
            with tempfile.TemporaryFile(mode="w+", dir=temporary_directory) as manifest:
                # Filenames never enter the manifest: only our integer descriptors do.
                manifest.write("ffconcat version 1.0\n")
                for source in sources:
                    manifest.write(f"file '/proc/self/fd/{source}'\n")
                manifest.flush()
                execute(
                    [
                        "ffmpeg",
                        "-nostdin",
                        "-v",
                        "error",
                        "-y",
                        "-protocol_whitelist",
                        "file,pipe",
                        "-f",
                        "concat",
                        "-auto_convert",
                        "0",
                        "-safe",
                        "0",
                        "-i",
                        f"/proc/self/fd/{manifest.fileno()}",
                        "-map",
                        "0",
                        "-c",
                        "copy",
                        "-f",
                        "mp4",
                        f"/proc/self/fd/{output_fd}",
                    ],
                    descriptors=(*sources, manifest.fileno(), output_fd),
                    cancel=cancel,
                    timeout=3600,
                )
            result = probe(output_fd, cancel=cancel)
            expected = sum(item.duration for item in probes)
            if (
                result.streams != probes[0].streams
                or abs(result.duration - expected) > 0.25 * len(clips) + 0.5
            ):
                raise MediaError("Output stream/duration validation failed")
            unchanged()
            if cancel and cancel.is_set():
                raise MediaError("Cancelled before publication")
            os.fsync(output_fd)
            os.lseek(output_fd, 0, os.SEEK_SET)
            with os.fdopen(os.dup(output_fd), "rb") as readable:
                digest = hashlib.file_digest(readable, "sha256").hexdigest()
            if output_token is not None:
                if len(output_token) != 32 or any(
                    c not in "0123456789abcdef" for c in output_token
                ):
                    raise ValueError("Invalid output version token")
            suffix = "-" + output_token if output_token else ""
            final = f"{day.isoformat()}{suffix}.mp4"
            # Hard-link publication is atomic and cannot overwrite an existing output.
            os.link(
                name,
                final,
                src_dir_fd=staging,
                dst_dir_fd=destination,
                follow_symlinks=False,
            )
            os.fsync(destination)
            published = os.fstat(output_fd)
            return Output(
                f"{settings.output}/{camera}/{final}",
                result.duration,
                os.fstat(output_fd).st_size,
                digest,
                mtime_ns=published.st_mtime_ns,
                device=published.st_dev,
                inode=published.st_ino,
            )
        finally:
            os.close(output_fd)
            os.unlink(name, dir_fd=staging)
