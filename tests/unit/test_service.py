import os
import threading
import time

import pytest

from camera_daily_merger.app.main import healthy, run, validate_storage


def test_missing_mount(tmp_path):
    with pytest.raises(ValueError):
        validate_storage(tmp_path, tmp_path / "missing")


def test_health_age_and_missing(tmp_path):
    assert not healthy(tmp_path)
    heartbeat = tmp_path / "heartbeat"
    heartbeat.touch()
    assert healthy(tmp_path)
    old = time.time() - 100
    os.utime(heartbeat, (old, old))
    assert not healthy(tmp_path)


def test_shutdown_preserves_media(tmp_path):
    data, media = tmp_path / "data", tmp_path / "media"
    data.mkdir()
    media.mkdir()
    source = media / "original"
    source.write_bytes(b"synthetic original")
    stop = threading.Event()
    stop.set()
    run(data, media, stop)
    assert not list(data.iterdir())
    assert source.read_bytes() == b"synthetic original"


def test_stale_bootstrap_marker_does_not_block_restart(tmp_path):
    data, media = tmp_path / "data", tmp_path / "media"
    data.mkdir()
    media.mkdir()
    marker = data / "bootstrap-check"
    marker.write_bytes(b"left by old bootstrap")
    validate_storage(data, media)
    assert marker.read_bytes() == b"left by old bootstrap"


def test_absolute_camera_path_reports_actionable_error_without_private_values(
    tmp_path, monkeypatch, caplog
):
    import json
    from camera_daily_merger.app.main import main

    data, media = tmp_path / "data", tmp_path / "media"
    data.mkdir()
    media.mkdir()
    private_path = str(media / "private_camera")
    (data / "options.json").write_text(
        json.dumps(
            {
                "source_root": str(media),
                "cameras": [{"id": "a", "path": private_path}],
                "timestamp_pattern": r"(?P<start>.+)\.mp4",
            }
        )
    )
    monkeypatch.setenv("MERGER_DATA", str(data))
    monkeypatch.setenv("MERGER_MEDIA", str(media))
    monkeypatch.setattr("sys.argv", ["merger"])
    monkeypatch.setattr("signal.signal", lambda *_: None)
    assert main() == 1
    assert "must be relative to source_root" in caplog.text
    assert private_path not in caplog.text
    assert not (media / "daily").exists()


def test_invalid_regex_does_not_log_raw_configuration(tmp_path, monkeypatch, caplog):
    import json
    from camera_daily_merger.app.main import main

    data, media = tmp_path / "data", tmp_path / "media"
    data.mkdir()
    media.mkdir()
    (data / "options.json").write_text(
        json.dumps(
            {
                "source_root": str(media),
                "cameras": [{"id": "a", "path": "input"}],
                "timestamp_pattern": "private_camera([",
            }
        )
    )
    monkeypatch.setenv("MERGER_DATA", str(data))
    monkeypatch.setenv("MERGER_MEDIA", str(media))
    monkeypatch.setattr("sys.argv", ["merger"])
    monkeypatch.setattr("signal.signal", lambda *_: None)
    assert main() == 1
    assert "invalid timestamp_pattern regex" in caplog.text
    assert "private_camera" not in caplog.text
