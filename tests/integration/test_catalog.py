from contextlib import contextmanager
from datetime import date, timedelta
import hashlib
import json

from camera_daily_merger.app.persistence import Store
from camera_daily_merger.app.settings import Settings
from camera_daily_merger.app.web import serve
from tests.integration.test_web import request


def published(store, root, camera, day, token=1, body=b"synthetic export"):
    relative = f"daily/{camera}/{day}-{token:032x}.mp4"
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    store.enqueue(camera, day, [], 0, force=True)
    job = store.claim(0)
    store.finish(
        job,
        1,
        output={
            "path": relative,
            "duration": 1.5,
            "size": len(body),
            "sha256": hashlib.sha256(body).hexdigest(),
        },
    )
    return path


@contextmanager
def app(root, peers=None):
    settings = Settings(
        root=root,
        cameras={"a": "input_a", "b": "input_b", "c": "input_c"},
        timestamp_pattern=r"(?P<start>.+)\.mp4",
    )
    store = Store(root / "jobs.sqlite")
    with serve(
        store,
        settings,
        host="127.0.0.1",
        port=0,
        peers={"127.0.0.1"} if peers is None else peers,
    ) as server:
        yield f"http://127.0.0.1:{server.server_address[1]}", store


def test_latest_per_camera_and_shared_day_do_not_mix_dates(tmp_path):
    with app(tmp_path) as (url, store):
        published(store, tmp_path, "a", "2026-11-11")
        published(store, tmp_path, "a", "2026-11-12")
        published(store, tmp_path, "b", "2026-11-11")
        status, body, _ = request(url + "/api/videos")
        assert status == 200
        data = json.loads(body)
        assert [(v["camera"], v["day"], v["available"]) for v in data["videos"]] == [
            ("a", "2026-11-12", True),
            ("b", "2026-11-11", True),
            ("c", None, False),
        ]
        assert data["dates"] == ["2026-11-12", "2026-11-11"]
        assert str(tmp_path).encode() not in body and b'"path"' not in body
        data = json.loads(request(url + "/api/videos?view=day&day=2026-11-11")[1])
        assert all(v["day"] == "2026-11-11" for v in data["videos"])
        assert [v["available"] for v in data["videos"]] == [True, True, False]
        newest = json.loads(request(url + "/api/videos?view=day")[1])
        assert newest["day"] == "2026-11-12"
        assert [v["available"] for v in newest["videos"]] == [True, False, False]


def test_latest_preserves_previous_export_on_failed_retry_and_ignores_other_camera_history(
    tmp_path,
):
    with app(tmp_path) as (url, store):
        published(store, tmp_path, "a", "2026-11-12")
        store.enqueue("a", "2026-11-12", [], 2, force=True)
        store.finish(store.claim(2), 3, error="synthetic retry failure")
        with store.transaction() as db:
            db.executemany(
                "INSERT INTO jobs(camera,day,manifest,fingerprint,status) VALUES('removed',?,'[]','none','failed')",
                [
                    ((date(2030, 1, 1) + timedelta(days=n)).isoformat(),)
                    for n in range(1100)
                ],
            )
        data = json.loads(request(url + "/api/videos")[1])
        assert len(data["videos"]) == 3
        assert data["videos"][0]["available"] is True
        assert data["videos"][0]["previous_export"] is True
        assert data["dates"] == ["2026-11-12"]


def test_missing_or_linked_exports_are_unavailable_and_version_pins_fail_closed(
    tmp_path,
):
    with app(tmp_path) as (url, store):
        old = published(store, tmp_path, "a", "2026-11-12", 1)
        data = json.loads(request(url + "/api/videos")[1])["videos"][0]
        old_url = url + data["video_url"][1:]
        assert request(old_url)[1] == b"synthetic export"
        newer = published(
            store, tmp_path, "a", "2026-11-12", 2, b"new successful export"
        )
        assert request(old_url)[0] == 404
        current = json.loads(request(url + "/api/videos")[1])["videos"][0]
        current_url = url + current["video_url"][1:]
        assert request(current_url)[1] == b"new successful export"
        status, body, headers = request(
            url + "/video/a/2026-11-12",
            headers={"Range": "bytes=0-2", "If-Range": '"old-version"'},
        )
        assert status == 200 and body == b"new successful export"
        assert headers["ETag"]
        newer.unlink()
        unavailable = json.loads(request(url + "/api/videos")[1])["videos"][0]
        assert not unavailable["available"] and "video_url" not in unavailable
        newer.symlink_to(old)
        assert not json.loads(request(url + "/api/videos")[1])["videos"][0]["available"]


def test_catalog_access_and_query_validation(tmp_path):
    with app(tmp_path) as (url, _):
        for query in (
            "view=unknown",
            "view=day&day=2026-02-30",
            "view=day&day=../input",
            "view=latest&day=2026-11-12",
            "view=latest&view=day",
            "path=/data",
        ):
            assert request(url + "/api/videos?" + query)[0] == 400
    with app(tmp_path, peers=set()) as (url, _):
        assert request(url + "/api/videos")[0] == 403
