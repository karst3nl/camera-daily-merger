"""Bounded subprocess execution and conservative MP4 stream compatibility."""

from dataclasses import dataclass
import json
import math
import subprocess
import threading
import time


class MediaError(RuntimeError):
    def __init__(self, message: str, *, details: list[dict] | None = None):
        super().__init__(message)
        self.details = details or []


def execute(
    arguments: list[str],
    *,
    descriptors=(),
    cancel: threading.Event | None = None,
    timeout=30,
) -> bytes:
    with subprocess.Popen(
        arguments,
        pass_fds=descriptors,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
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
            "-max_streams",
            "32",
            "-show_entries",
            "format=format_name,duration:stream=" + ",".join(FIELDS),
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


def compatibility_differences(reference: Probe, candidate: Probe) -> list[dict]:
    """Bounded field comparisons; no filenames, tags or raw codec headers."""

    def display(value):
        if value is None:
            return "absent"
        if not isinstance(value, (str, int, float)):
            return "unavailable"
        return "".join(
            c if c.isascii() and c.isprintable() else "?" for c in str(value)
        )[:40]

    if len(reference.streams) != len(candidate.streams):
        return [
            {
                "stream": "layout",
                "field": "stream_count",
                "expected": str(len(reference.streams)),
                "actual": str(len(candidate.streams)),
            }
        ]
    changes = []
    for stream_index, (expected, actual) in enumerate(
        zip(reference.streams, candidate.streams, strict=True)
    ):
        for field, left, right in zip(FIELDS, expected, actual, strict=True):
            # FFprobe's guessed base rate is not decoder configuration. VFR
            # timestamps can differ while encoded packets and headers match.
            if field == "r_frame_rate" and expected[0] == actual[0] == "video":
                continue
            if left != right:
                changes.append(
                    {
                        "stream": stream_index,
                        "field": field,
                        "expected": display(left),
                        "actual": display(right),
                    }
                )
                if len(changes) == 12:
                    return changes
    return changes
