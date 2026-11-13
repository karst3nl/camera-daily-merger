from datetime import date
import hashlib
import json
import os
import shutil
import subprocess
import threading

import pytest

from camera_daily_merger.app import merger
from camera_daily_merger.app.probe import MediaError
from camera_daily_merger.app.scanner import Clip, scan
from camera_daily_merger.app.settings import Settings

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg required")
DAY = date(2026, 11, 12)


def make_clip(root, hour, color="red", size="64x64", audio=False):
    folder = root / "input"
    folder.mkdir(exist_ok=True)
    path = folder / f"odd ' ; $ name_{DAY}T{hour:02}:00:00+01:00.mp4"
    args = [
        "ffmpeg",
        "-nostdin",
        "-v",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color={color}:size={size}:rate=10:duration=0.5",
    ]
    if audio:
        args += ["-f", "lavfi", "-i", "sine=frequency=440:duration=0.5", "-c:a", "aac"]
    subprocess.run(
        [
            *args,
            "-c:v",
            "libx264",
            "-threads",
            "1",
            "-pix_fmt",
            "yuv420p",
            "-y",
            str(path),
        ],
        check=True,
    )
    os.utime(path, (1, 1))
    return path


def config(root):
    return Settings(
        root=root,
        cameras={"a": "input"},
        timestamp_pattern=r"odd .*_(?P<start>.+)\.mp4",
        minimum_age_seconds=0,
    )


def clips(root):
    return [item for item in scan(config(root)) if isinstance(item, Clip)]


def hashes(paths):
    return {str(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}


def packets(path):
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v",
            "-show_packets",
            "-show_data_hash",
            "sha256",
            "-of",
            "json",
            str(path),
        ],
        check=True,
        capture_output=True,
    )
    return [p["data_hash"] for p in json.loads(result.stdout)["packets"]]


def test_stream_copy_order_duration_and_no_source_changes(tmp_path):
    later = make_clip(tmp_path, 12, "blue")
    earlier = make_clip(tmp_path, 10, "red")
    before = hashes([earlier, later])
    result = merger.merge(
        config(tmp_path), clips(tmp_path), DAY, temporary_directory=str(tmp_path)
    )
    output = tmp_path / result.path
    assert result.duration == pytest.approx(1, abs=0.1)
    assert packets(output) == packets(earlier) + packets(later)
    assert hashes([earlier, later]) == before
    assert list((tmp_path / ".staging").iterdir()) == []
    previous = output.read_bytes()
    with pytest.raises(FileExistsError):
        merger.merge(
            config(tmp_path), clips(tmp_path), DAY, temporary_directory=str(tmp_path)
        )
    assert output.read_bytes() == previous


def test_single_clip(tmp_path):
    source = make_clip(tmp_path, 10)
    result = merger.merge(
        config(tmp_path), clips(tmp_path), DAY, temporary_directory=str(tmp_path)
    )
    assert packets(tmp_path / result.path) == packets(source)


@pytest.mark.parametrize(
    "case",
    [
        "resolution",
        "audio",
        "corrupt",
        "zero",
        "cancel",
        "disk",
        "write",
        "changed",
        "codec",
    ],
)
def test_failures_preserve_sources_and_existing_output(tmp_path, monkeypatch, case):
    source = make_clip(tmp_path, 10)
    if case == "resolution":
        make_clip(tmp_path, 12, size="128x64")
    elif case == "audio":
        make_clip(tmp_path, 12, audio=True)
    elif case == "corrupt":
        (source.parent / f"odd bad_{DAY}T12:00:00+01:00.mp4").write_bytes(b"broken")
    elif case == "codec":
        other = make_clip(tmp_path, 12)
        temporary = tmp_path / "mpeg4.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-i",
                str(other),
                "-c:v",
                "mpeg4",
                str(temporary),
            ],
            check=True,
        )
        os.replace(temporary, other)
    originals = list(source.parent.iterdir())
    before = hashes(originals)
    selected = clips(tmp_path)
    cancel = threading.Event()
    if case == "zero":
        selected = []
    elif case == "cancel":
        cancel.set()
    elif case == "disk":

        class NoSpace:
            f_bavail = 0
            f_frsize = 4096

        monkeypatch.setattr(merger.os, "fstatvfs", lambda _: NoSpace())
    elif case == "write":

        def deny(*args, **kwargs):
            raise OSError("simulated publish error")

        monkeypatch.setattr(merger.os, "link", deny)
    elif case == "changed":
        source.touch()
    output = tmp_path / "daily/a/2026-11-12.mp4"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"previous successful export")
    with pytest.raises((MediaError, OSError)):
        merger.merge(
            config(tmp_path),
            selected,
            DAY,
            temporary_directory=str(tmp_path),
            cancel=cancel,
        )
    assert output.read_bytes() == b"previous successful export"
    assert hashes(originals) == before
    if (tmp_path / ".staging").exists():
        assert not list((tmp_path / ".staging").iterdir())


def test_snapshot_change_after_ffmpeg_prevents_publish(tmp_path, monkeypatch):
    source = make_clip(tmp_path, 10)
    selected = clips(tmp_path)
    execute = merger.execute

    def mutate(*args, **kwargs):
        result = execute(*args, **kwargs)
        source.touch()
        return result

    monkeypatch.setattr(merger, "execute", mutate)
    with pytest.raises(MediaError, match="snapshot changed"):
        merger.merge(config(tmp_path), selected, DAY, temporary_directory=str(tmp_path))
    assert not list((tmp_path / "daily/a").iterdir())


def test_compatible_audio(tmp_path):
    make_clip(tmp_path, 10, audio=True)
    make_clip(tmp_path, 12, audio=True)
    result = merger.merge(
        config(tmp_path), clips(tmp_path), DAY, temporary_directory=str(tmp_path)
    )
    assert result.duration == pytest.approx(1, abs=0.25)


def test_running_process_cancellation():
    import sys
    from camera_daily_merger.app.probe import execute

    cancel = threading.Event()
    timer = threading.Timer(0.1, cancel.set)
    timer.start()
    try:
        with pytest.raises(MediaError, match="cancelled"):
            execute(
                [sys.executable, "-c", "import time; time.sleep(20)"], cancel=cancel
            )
    finally:
        timer.cancel()
