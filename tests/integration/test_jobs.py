from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import json
import sqlite3
import threading

import pytest

from camera_daily_merger.app.jobs import enqueue, output_healthy, run_one, worker_lock
from camera_daily_merger.app.persistence import Store
from tests.integration.test_merge import DAY, clips, config, make_clip


def test_durable_success_idempotency_late_arrival_and_retry(tmp_path):
    make_clip(tmp_path, 10)
    data = tmp_path / "data"
    data.mkdir()
    store = Store(data / "jobs.sqlite")
    settings = config(tmp_path)
    with worker_lock(data):
        assert enqueue(store, settings, "a", DAY, clips(tmp_path))
        assert not enqueue(store, settings, "a", DAY, clips(tmp_path))
        assert run_one(store, settings, data, threading.Event())
        row = store.get("a", DAY.isoformat())
        assert row["status"] == "success"
        old = json.loads(row["output"])
        assert output_healthy(settings, row)
        assert not enqueue(store, settings, "a", DAY, clips(tmp_path))
        make_clip(tmp_path, 12, "blue")
        assert enqueue(store, settings, "a", DAY, clips(tmp_path))
        cancel = threading.Event()
        cancel.set()
        assert run_one(store, settings, data, cancel)
        row = store.get("a", DAY.isoformat())
        assert row["status"] == "failed"
        assert json.loads(row["output"]) == old
        assert output_healthy(settings, row)
        assert not enqueue(store, settings, "a", DAY, clips(tmp_path), now=0)
        assert enqueue(
            store, settings, "a", DAY, clips(tmp_path), now=row["next_retry"]
        )
        assert run_one(store, settings, data, threading.Event())
        row = Store(data / "jobs.sqlite").get("a", DAY.isoformat())
        assert row["status"] == "success"
        assert json.loads(row["output"])["path"] != old["path"]
        assert (tmp_path / old["path"]).exists()
        assert output_healthy(settings, row)
        (tmp_path / json.loads(row["output"])["path"]).write_bytes(b"incomplete")
        assert enqueue(store, settings, "a", DAY, clips(tmp_path))
        assert run_one(store, settings, data, threading.Event())
        assert output_healthy(settings, store.get("a", DAY.isoformat()))


def test_concurrent_claims_and_stale_completion(tmp_path):
    store = Store(tmp_path / "jobs.sqlite")
    assert store.enqueue("a", DAY.isoformat(), [], 0)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: store.claim(0), range(4)))
    claimed = [r for r in results if r]
    assert len(claimed) == 1
    assert Store(store.path).get("a", DAY.isoformat())["status"] == "running"
    store.recover(10)
    assert store.get("a", DAY.isoformat())["status"] == "failed"
    with pytest.raises(ValueError, match="Stale"):
        store.finish(claimed[0], 11, error="old worker")
    assert not store.enqueue("a", DAY.isoformat(), [], 39)
    assert store.enqueue("a", DAY.isoformat(), [], 40)


def test_capped_retry_and_new_manifest(tmp_path):
    make_clip(tmp_path, 10)
    selected = clips(tmp_path)
    store = Store(tmp_path / "jobs.sqlite")
    clock = 0
    for attempt in range(5):
        assert store.enqueue("a", DAY.isoformat(), selected, clock)
        job = store.claim(clock)
        store.finish(job, clock, error="synthetic failure")
        row = store.get("a", DAY.isoformat())
        assert row["attempts"] == attempt + 1
        clock = row["next_retry"]
    assert not store.enqueue("a", DAY.isoformat(), selected, clock + 100000)
    assert store.enqueue("a", DAY.isoformat(), [replace(selected[0], size=123)], clock)
    assert store.get("a", DAY.isoformat())["attempts"] == 0


def test_worker_lock_and_migration(tmp_path):
    with worker_lock(tmp_path):
        with pytest.raises(BlockingIOError), worker_lock(tmp_path):
            pass
    path = tmp_path / "jobs.sqlite"
    Store(path)
    Store(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        db.execute("PRAGMA user_version=999")
    with pytest.raises(ValueError, match="schema"):
        Store(path)


def test_v1_migration_preserves_queued_work(tmp_path):
    path = tmp_path / "jobs.sqlite"
    store = Store(path)
    store.enqueue("a", str(DAY), [], 0)
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE metadata")
        db.execute("PRAGMA user_version=1")
    migrated = Store(path)
    assert migrated.get("a", str(DAY))["status"] == "queued"
    assert migrated.metadata("cursor") is None
    migrated.metadata("cursor", {"day": str(DAY)})
    assert Store(path).metadata("cursor") == {"day": str(DAY)}


def test_output_integrity_cache_bounds_unchanged_nas_reads(tmp_path, monkeypatch):
    from camera_daily_merger.app import jobs

    make_clip(tmp_path, 10)
    data = tmp_path / "data"
    data.mkdir()
    store = Store(data / "jobs.sqlite")
    settings = config(tmp_path)
    enqueue(store, settings, "a", DAY, clips(tmp_path))
    with worker_lock(data):
        run_one(store, settings, data, threading.Event())
    digest = jobs.hashlib.file_digest
    calls = []

    def counted(*args, **kwargs):
        calls.append(1)
        return digest(*args, **kwargs)

    monkeypatch.setattr(jobs.hashlib, "file_digest", counted)
    row = store.get("a", str(DAY))
    assert output_healthy(settings, row, store=store)
    assert not calls
    path = tmp_path / json.loads(row["output"])["path"]
    path.touch()
    assert output_healthy(settings, row, store=store)
    assert len(calls) == 1
    assert output_healthy(settings, store.get("a", str(DAY)), store=store)
    assert len(calls) == 1
    content = bytearray(path.read_bytes())
    content[0] ^= 1
    path.write_bytes(content)
    assert not output_healthy(settings, store.get("a", str(DAY)), store=store)
