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
