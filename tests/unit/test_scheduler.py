from datetime import UTC, date, datetime, timedelta
import os

import pytest

from camera_daily_merger.app.persistence import Store
from camera_daily_merger.app.scheduler import Schedule, Scheduler, latest_due_day
from camera_daily_merger.app.settings import Settings
from tests.integration.test_merge import DAY, make_clip


@pytest.mark.parametrize(
    "instant,expected",
    [
        ("2026-03-28T23:14:59+00:00", "2026-03-27"),
        ("2026-03-28T23:15:00+00:00", "2026-03-28"),
        ("2026-03-29T22:15:00+00:00", "2026-03-29"),
        ("2026-10-24T22:15:00+00:00", "2026-10-24"),
        ("2026-10-25T23:15:00+00:00", "2026-10-25"),
    ],
)
def test_calendar_dates_across_dst(instant, expected):
    assert (
        latest_due_day(datetime.fromisoformat(instant), "Europe/Berlin").isoformat()
        == expected
    )


def test_clock_and_config_validation():
    with pytest.raises(ValueError):
        latest_due_day(datetime.now(), "Europe/Berlin")
    with pytest.raises(ValueError):
        Schedule(backfill_days=0)
    with pytest.raises(ValueError):
        Schedule(reconcile_seconds=1)


def test_missed_run_restart_cycles_and_delayed_clip(tmp_path):
    make_clip(tmp_path, 10)
    from tests.integration.test_merge import config

    store = Store(tmp_path / "jobs.sqlite")
    scheduler = Scheduler(store, config(tmp_path))
    now = datetime(2026, 11, 13, 9, tzinfo=UTC)
    assert scheduler.tick(now)["queued"] == 1
    assert Scheduler(Store(store.path), config(tmp_path)).tick(now)["queued"] == 0
    job = store.claim(now.timestamp())
    store.finish(job, now.timestamp(), error="interrupted mock")
    assert scheduler.tick(now + timedelta(seconds=29))["queued"] == 0
    assert scheduler.tick(now + timedelta(seconds=30))["queued"] == 1
    assert (
        scheduler.tick(now + timedelta(days=1))["queued"] == 0
    )  # pending job is never duplicated


def test_diagnostics_block_partial_day(tmp_path):
    make_clip(tmp_path, 10)
    (tmp_path / "input" / "invalid.mp4").write_bytes(b"broken")
    os.utime(tmp_path / "input" / "invalid.mp4", (1, 1))
    from tests.integration.test_merge import config

    store = Store(tmp_path / "jobs.sqlite")
    scheduler = Scheduler(store, config(tmp_path))
    result = scheduler.reconcile({DAY}, datetime(2026, 11, 13, 9, tzinfo=UTC))
    assert result["queued"] == 0
    assert result["diagnostics"][0]["reason"] == "invalid_timestamp"
    assert not store.list()


def test_current_day_unsettled_does_not_block_previous_day(tmp_path):
    import os

    root = tmp_path / "input"
    root.mkdir()
    old = root / "2026-11-12T10:00:00+01:00.mp4"
    old.write_bytes(b"old")
    os.utime(old, (1, 1))
    current = root / "2026-11-13T10:00:00+01:00.mp4"
    current.write_bytes(b"recent")
    now = datetime(2026, 11, 13, 9, tzinfo=UTC)
    os.utime(current, (now.timestamp(), now.timestamp()))
    settings = Settings(
        root=tmp_path, cameras={"a": "input"}, timestamp_pattern=r"(?P<start>.+)\.mp4"
    )
    store = Store(tmp_path / "jobs.sqlite")
    assert Scheduler(store, settings).reconcile({DAY}, now)["queued"] == 1


def test_manual_backfill_validation_and_bounds(tmp_path):
    (tmp_path / "input").mkdir()
    settings = Settings(
        root=tmp_path, cameras={"a": "input"}, timestamp_pattern=r"(?P<start>.+)\.mp4"
    )
    scheduler = Scheduler(Store(tmp_path / "jobs.sqlite"), settings)
    now = datetime(2026, 11, 13, 9, tzinfo=UTC)
    for days, camera in [
        ({date(2026, 11, 13)}, None),
        ({DAY}, "unknown"),
        (set(), None),
        ({DAY - timedelta(days=n) for n in range(367)}, None),
    ]:
        with pytest.raises(ValueError):
            scheduler.reconcile(days, now, camera=camera)


def test_reconciliation_late_arrival_and_healthy_skip(tmp_path):
    import threading
    from camera_daily_merger.app.jobs import run_one, worker_lock
    from tests.integration.test_merge import config

    make_clip(tmp_path, 10)
    data = tmp_path / "data"
    data.mkdir()
    store = Store(data / "jobs.sqlite")
    scheduler = Scheduler(store, config(tmp_path), Schedule(reconcile_seconds=60))
    now = datetime(2026, 11, 13, 9, tzinfo=UTC)
    with worker_lock(data):
        assert scheduler.tick(now)["queued"] == 1
        run_one(store, config(tmp_path), data, threading.Event(), now=now.timestamp())
        assert scheduler.tick(now + timedelta(seconds=60))["queued"] == 0
        make_clip(tmp_path, 12)
        assert scheduler.tick(now + timedelta(seconds=120))["queued"] == 1
        run_one(
            store, config(tmp_path), data, threading.Event(), now=now.timestamp() + 120
        )
        assert scheduler.tick(now + timedelta(days=1))["queued"] == 0
        assert store.get("a", DAY.isoformat())["attempts"] == 1


@pytest.mark.parametrize(
    "pattern,format,detail",
    [
        (
            r".+_00_(?P<start>\\d{14})\\.mp4",
            "%Y%m%d%H%M%S",
            "filename_pattern_mismatch",
        ),
        (r".+_00_(?P<start>\d{14})\.mp4", "iso8601", "timestamp_format_mismatch"),
    ],
)
def test_compact_diagnostics_identify_adapter_problem(
    tmp_path, pattern, format, detail
):
    source = tmp_path / "input"
    source.mkdir()
    filename = "camera_a_00_20260101120000.mp4"
    path = source / filename
    path.write_bytes(b"synthetic")
    os.utime(path, (1, 1))
    settings = Settings(
        root=tmp_path,
        cameras={"a": "input"},
        timestamp_pattern=pattern,
        timestamp_format=format,
    )
    store = Store(tmp_path / "jobs.sqlite")
    result = Scheduler(store, settings).reconcile(
        {date(2026, 1, 1)}, datetime(2026, 1, 2, 12, tzinfo=UTC)
    )
    diagnostic = result["diagnostics"][0]
    assert diagnostic["reason"] == "invalid_timestamp"
    assert diagnostic["detail"] == detail
    assert diagnostic["examples"] == [filename]
    assert diagnostic["count"] == 1
    assert result["queued"] == 0
    assert str(tmp_path) not in str(diagnostic)


def test_diagnostic_examples_are_bounded_and_keep_blocking_unknown_files(tmp_path):
    root = tmp_path / "input"
    root.mkdir()
    for n in range(10):
        path = root / f"unknown_{n}.mp4"
        path.write_bytes(b"synthetic")
        os.utime(path, (1, 1))
    settings = Settings(
        root=tmp_path,
        cameras={"a": "input"},
        timestamp_pattern=r"camera_00_(?P<start>\d{14})\.mp4",
        timestamp_format="%Y%m%d%H%M%S",
    )
    store = Store(tmp_path / "jobs.sqlite")
    result = Scheduler(store, settings).reconcile(
        {DAY}, datetime(2026, 11, 13, 12, tzinfo=UTC)
    )
    assert result["queued"] == 0
    assert len(result["diagnostics"]) == 1
    assert result["diagnostics"][0]["count"] == 10
    assert len(result["diagnostics"][0]["examples"]) == 3
