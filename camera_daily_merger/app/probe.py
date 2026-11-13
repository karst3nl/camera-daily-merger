"""Bounded subprocess execution and conservative MP4 stream compatibility."""

from dataclasses import dataclass
import json
import math
import subprocess
import threading
import time


class MediaError(RuntimeError):
    pass


def execute(
    arguments: list[str],
    *,
    descriptors=(),
    cancel: threading.Event | None = None,
    timeout=30,
) -> bytes:
    with subprocess.Popen(
        arguments, pass_fds=descriptors, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as process:
        deadline = time.monotonic() + timeout
        while True:
            if (cancel and cancel.is_set()) or time.monotonic() >= deadline:
                process.kill()
                process.communicate()
                raise MediaError("Media operation cancelled or timed out")
            try:
                stdout, _ = process.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                continue
        if process.returncode:
            # FFmpeg stderr can contain source names; never expose it to web/log callers.
            raise MediaError(
                f"Media process failed with exit code {process.returncode}"
            )
        return stdout


FIELDS = (
    "codec_type",
    "codec_name",
    "codec_tag_string",
    "profile",
    "level",
    "width",
    "height",
    "pix_fmt",
    "sample_aspect_ratio",
    "field_order",
    "r_frame_rate",
    "time_base",
    "sample_rate",
    "channels",
    "channel_layout",
    "extradata_hash",
    "color_range",
    "color_space",
    "color_transfer",
    "color_primaries",
)


@dataclass(frozen=True)
class Probe:
    duration: float
    streams: tuple[tuple, ...]


def probe(descriptor: int, *, cancel=None) -> Probe:
    raw = execute(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_streams",
            "-show_format",
            "-show_data_hash",
            "sha256",
            "-of",
            "json",
            f"/proc/self/fd/{descriptor}",
        ],
        descriptors=(descriptor,),
        cancel=cancel,
    )
    try:
        data = json.loads(raw)
        duration = float(data["format"]["duration"])
        if (
            not math.isfinite(duration)
            or duration <= 0
            or "mp4" not in data["format"]["format_name"].split(",")
        ):
            raise ValueError
        streams = data["streams"]
        if sum(stream["codec_type"] == "video" for stream in streams) != 1:
            raise ValueError
        for stream in streams:
            if (stream["codec_type"], stream["codec_name"]) not in {
                ("video", "h264"),
                ("video", "hevc"),
                ("audio", "aac"),
            }:
                raise ValueError
        return Probe(
            duration,
            tuple(tuple(stream.get(field) for field in FIELDS) for stream in streams),
        )
    except (KeyError, ValueError, TypeError) as error:
        raise MediaError("Unreadable or unsupported MP4 stream layout") from error
