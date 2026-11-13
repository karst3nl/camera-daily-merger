from datetime import UTC, datetime
import json
import os
import subprocess
import sys

import pytest

from camera_daily_merger.app.scanner import Clip, Diagnostic, chronological, scan
from camera_daily_merger.app.settings import Settings
from camera_daily_merger.app.storage import directory, open_relative
from camera_daily_merger.app.timestamp_parser import RegexTimestampParser

PATTERN = r"(?P<start>.+)\.mp4"


def settings(root, **kwargs):
    return Settings(
        root=root, cameras={"camera_a": "input"}, timestamp_pattern=PATTERN, **kwargs
    )


def recording(root, name="2026-11-12T10:00:00+01:00.mp4", folder="input"):
    path = root / folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"synthetic")
    os.utime(path, (1, 1))
    return path


def test_nested_unsorted_duplicate_names_and_invalid(tmp_path):
    recording(tmp_path, "2026-11-12T12:00:00+01:00.mp4")
    recording(tmp_path, folder="input/nested")
    recording(tmp_path)
    recording(tmp_path, "bad.mp4")
    results = list(scan(settings(tmp_path)))
    clips = chronological([x for x in results if isinstance(x, Clip)])
    assert len(clips) == 3
    assert [c.start.hour for c in clips] == [10, 10, 12]
    assert len({c.path for c in clips}) == 3
    assert [x.reason for x in results if isinstance(x, Diagnostic)] == [
        "invalid_timestamp"
    ]


def test_exclusion_and_source_hashes(tmp_path):
    source = recording(tmp_path)
    recording(tmp_path, folder="daily")
    recording(tmp_path, folder=".staging")
    config = Settings(root=tmp_path, cameras={"a": "."}, timestamp_pattern=PATTERN)
    before = source.read_bytes(), source.stat().st_mtime_ns
    assert len(list(scan(config))) == 1
    assert (source.read_bytes(), source.stat().st_mtime_ns) == before


def test_symlinks_and_hardlinks(tmp_path):
    source = recording(tmp_path)
    (tmp_path / "input" / "link.mp4").symlink_to(source)
    (tmp_path / "input" / "escape").symlink_to(
        tmp_path.parent, target_is_directory=True
    )
    os.link(source, tmp_path / "input" / "hard.mp4")
    results = list(scan(settings(tmp_path)))
    assert all(isinstance(x, Diagnostic) for x in results)
    assert {x.reason for x in results} == {"symlink_rejected", "hardlink_rejected"}


def test_growing_recent_empty_and_changed_files(tmp_path):
    source = recording(tmp_path)
    assert list(scan(settings(tmp_path), now=10))[0].reason == "empty_or_unsettled"
    source.write_bytes(b"")
    assert list(scan(settings(tmp_path)))[0].reason == "empty_or_unsettled"
    recording(tmp_path)

    class GrowingParser:
        def parse(self, _):
            source.write_bytes(b"growing")
            return datetime.now(UTC)

    assert (
        list(scan(settings(tmp_path), parser=GrowingParser()))[0].reason
        == "changed_during_scan"
    )


@pytest.mark.parametrize("path", ["../escape", "/absolute", "a/../../escape", "a\\b"])
def test_traversal_rejected(tmp_path, path):
    with pytest.raises(ValueError):
        Settings(root=tmp_path, cameras={"a": path}, timestamp_pattern=PATTERN)
    with directory(tmp_path) as root:
        with pytest.raises(ValueError), open_relative(root, path):
            pass


@pytest.mark.parametrize(
    "kwargs",
    [
        {"output": "."},
        {"output": "daily", "staging": "daily/tmp"},
        {"output": "input"},
        {"timestamp_pattern": "no group"},
        {"minimum_age_seconds": -1},
        {"cameras": {"bad/id": "input"}},
        {"cameras": {"a": "input", "b": "input/nested"}},
    ],
)
def test_invalid_settings(tmp_path, kwargs):
    values = dict(root=tmp_path, cameras={"a": "input"}, timestamp_pattern=PATTERN)
    values.update(kwargs)
    with pytest.raises(ValueError):
        Settings(**values)


def test_root_and_intermediate_symlink_rejected(tmp_path):
    recording(tmp_path)
    (tmp_path / "alias").symlink_to(tmp_path / "input", target_is_directory=True)
    config = Settings(root=tmp_path, cameras={"a": "alias"}, timestamp_pattern=PATTERN)
    assert list(scan(config))[0].reason == "unreadable_or_unsafe_directory"
    with pytest.raises(OSError), directory(tmp_path / "alias"):
        pass


@pytest.mark.parametrize(
    "timestamp",
    [
        "2026-03-29T02:30:00",
        "2026-10-25T02:30:00",
        "nonsense",
    ],
)
def test_ambiguous_gap_malformed(timestamp):
    parser = RegexTimestampParser(PATTERN, "Europe/Berlin")
    with pytest.raises(ValueError):
        parser.parse(timestamp + ".mp4")


def test_midnight_offset_and_dst_order():
    parser = RegexTimestampParser(PATTERN, "Europe/Berlin")
    assert parser.parse("2026-11-12T23:30:00Z.mp4").date().isoformat() == "2026-11-13"
    assert parser.parse("2026-07-01T12:00:00.mp4").utcoffset().total_seconds() == 7200
    first = parser.parse("2026-10-25T02:45:00+02:00.mp4")
    second = parser.parse("2026-10-25T02:15:00+01:00.mp4")
    assert first.astimezone(UTC) < second.astimezone(UTC)
    clips = [
        Clip("a", "second", second, 1, 1, 1, 1),
        Clip("a", "first", first, 1, 1, 1, 1),
    ]
    assert [c.path for c in chronological(clips)] == ["first", "second"]


def test_dry_run_cli(tmp_path):
    recording(tmp_path)
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "root": str(tmp_path),
                "cameras": {"a": "input"},
                "timestamp_pattern": PATTERN,
            }
        )
    )
    result = subprocess.run(
        [sys.executable, "-m", "camera_daily_merger.app.discover", str(config)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert json.loads(result.stdout)["type"] == "Clip"
    assert not (tmp_path / "daily").exists()
