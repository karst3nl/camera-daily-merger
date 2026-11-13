from contextlib import contextmanager
import json
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen


from camera_daily_merger.app.jobs import enqueue, run_one, worker_lock
from camera_daily_merger.app.persistence import Store
from camera_daily_merger.app.web import serve
from tests.integration.test_merge import DAY, clips, config, make_clip


@contextmanager
def application(tmp_path, *, peers=None, configured=True):
    settings = config(tmp_path)
    data = tmp_path / "data"
    data.mkdir(exist_ok=True)
    store = Store(data / "jobs.sqlite")
    with serve(
        store,
        settings if configured else None,
        host="127.0.0.1",
        port=0,
        peers={"127.0.0.1"} if peers is None else peers,
    ) as server:
        yield f"http://127.0.0.1:{server.server_address[1]}", store, settings, data


def request(url, *, body=None, token=None, headers=None, method=None):
    headers = headers or {}
    if body is not None:
        body = json.dumps(body).encode()
        headers["Content-Type"] = "application/json"
    if token:
        headers["X-CSRF-Token"] = token
    try:
        with urlopen(
            Request(url, data=body, headers=headers, method=method), timeout=5
        ) as response:
            return response.status, response.read(), response.headers
    except HTTPError as error:
        return error.code, error.read(), error.headers


def test_ingress_peer_required_even_with_forged_headers(tmp_path):
    with application(tmp_path, peers=set()) as (url, *_):
        for path in ("/", "/api/status", "/api/jobs", f"/video/a/{DAY}"):
            status, body, _ = request(
                url + path,
                headers={"X-Forwarded-For": "127.0.0.1", "X-Ingress-Path": "/"},
            )
            assert status == 403
            assert b"input" not in body


def test_setup_status_and_no_configuration_paths(tmp_path):
    with application(tmp_path, configured=False) as (url, *_):
        status, body, _ = request(url + "/api/status")
        assert status == 200
        assert json.loads(body)["configured"] is False
        assert str(tmp_path).encode() not in body
        assert request(url + "/api/jobs")[1] == b"[]"


def test_api_enumeration_csrf_validation_and_manual_run(tmp_path):
    make_clip(tmp_path, 10)
    with application(tmp_path) as (url, store, _, _):
        payload = {"camera": "a", "day": str(DAY)}
        assert request(url + "/api/reprocess", body=payload)[0] == 403
        token = json.loads(request(url + "/api/status")[1])["csrf"]
        for invalid in (
            {"camera": "../input", "day": str(DAY)},
            {"camera": "a", "day": "bad"},
            {"camera": "a", "day": "2999-01-01"},
            {"camera": "a", "day": str(DAY), "path": "/etc/passwd"},
        ):
            assert request(url + "/api/reprocess", body=invalid, token=token)[0] == 400
        assert request(url + "/api/reprocess", body=payload, token=token)[0] == 202
        assert store.get("a", str(DAY))["status"] == "queued"
        public = json.loads(request(url + "/api/jobs")[1])[0]
        assert set(public) == {
            "camera",
            "day",
            "status",
            "attempts",
            "error",
            "has_output",
        }
        assert public["camera"] == "a"
        for path in (
            "/../AGENTS.md",
            "/%2e%2e/AGENTS.md",
            "/api/manifest",
            "/video/../input",
            "/static/../main.py",
        ):
            assert request(url + path)[0] == 404


def test_video_ranges_download_missing_and_symlink(tmp_path):
    make_clip(tmp_path, 10)
    with application(tmp_path) as (url, store, settings, data):
        enqueue(store, settings, "a", DAY, clips(tmp_path))
        with worker_lock(data):
            run_one(store, settings, data, threading.Event())
        row = store.get("a", str(DAY))
        path = tmp_path / json.loads(row["output"])["path"]
        full = path.read_bytes()
        video = url + f"/video/a/{DAY}"
        assert request(video)[1] == full
        status, body, headers = request(video, headers={"Range": "bytes=0-31"})
        assert status == 206 and body == full[:32]
        assert headers["Content-Range"].startswith("bytes 0-31/")
        assert request(video, headers={"Range": "bytes=-10"})[1] == full[-10:]
        assert request(video, headers={"Range": "bytes=999999999-"})[0] == 416
        assert request(video, headers={"Range": "bytes=0-1,4-5"})[0] == 416
        assert request(video + "?download=1")[2]["Content-Disposition"].startswith(
            "attachment;"
        )
        assert request(video, method="HEAD")[1] == b""
        path.unlink()
        assert request(video)[0] == 404
        path.symlink_to(tmp_path / "input" / next((tmp_path / "input").iterdir()).name)
        assert request(video)[0] == 404


def test_diagnostic_basenames_visible_only_to_authorized_ingress(tmp_path):
    from camera_daily_merger.app.scheduler import Scheduler
    from datetime import UTC, datetime
    import os

    source = tmp_path / "input"
    source.mkdir()
    filename = "unmatched<img src=x onerror=alert(1)>.mp4"
    path = source / filename
    path.write_bytes(b"synthetic")
    os.utime(path, (1, 1))
    with application(tmp_path) as (url, store, settings, _):
        Scheduler(store, settings).reconcile(
            {DAY}, datetime(2026, 11, 13, 12, tzinfo=UTC)
        )
        status, body, _ = request(url + "/api/status")
        assert status == 200
        data = json.loads(body)
        assert data["diagnostics"][0]["examples"] == [filename]
        assert str(tmp_path).encode() not in body
    with application(tmp_path, peers=set()) as (url, *_):
        status, body, _ = request(url + "/api/status")
        assert status == 403
        assert filename.encode() not in body
