"""Ingress-only HTTP, bounded request workers and descriptor-safe output streaming."""

from contextlib import contextmanager
from datetime import UTC, date, datetime
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import socket
import threading
from urllib.parse import parse_qs, urlsplit

from . import APP_VERSION
from .catalog import collection
from .persistence import Store
from .scheduler import Scheduler
from .settings import Settings
from .storage import open_export

STATIC = Path(__file__).parent / "static"


def ingress_peers() -> set[str]:
    # Supervisor's documented internal DNS name; fail closed if not available.
    try:
        return {
            address[4][0]
            for address in socket.getaddrinfo("supervisor", None, socket.AF_INET)
        }
    except OSError:
        return set()


class BoundedServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, *args):
        self.slots = threading.BoundedSemaphore(8)
        self.media_slots = threading.BoundedSemaphore(6)
        super().__init__(*args)

    def handle_error(self, request, client_address):
        pass  # Do not log untrusted paths or raw storage exceptions.

    def process_request(self, request, address):
        if not self.slots.acquire(blocking=False):
            request.close()
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self.slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self.slots.release()


def make_handler(store: Store, settings: Settings | None, allowed_peers: set[str]):
    csrf = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        server_version = "CameraDailyMerger"
        sys_version = ""

        def setup(self):
            super().setup()
            self.connection.settimeout(15)

        def log_message(self, *_):
            pass  # Request paths can contain user input and are not logged.

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; media-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'",
            )
            super().end_headers()

        def reply(
            self,
            status,
            body,
            content_type="application/json",
            *,
            download_filename=None,
        ):
            data = (
                json.dumps(body).encode()
                if content_type == "application/json"
                else body
            )
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            if download_filename:
                self.send_header(
                    "Content-Disposition", f'attachment; filename="{download_filename}"'
                )
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def authorized(self):
            if self.client_address[0] not in allowed_peers:
                self.reply(403, {"error": "Ingress access required"})
                return False
            return True

        def do_HEAD(self):
            self.do_GET()

        def do_GET(self):
            if not self.authorized():
                return
            parsed = urlsplit(self.path)
            path = parsed.path
            static = {
                "/": ("index.html", "text/html; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/dashboard-layout.js": (
                    "dashboard-layout.js",
                    "text/javascript; charset=utf-8",
                ),
                "/surveillance-player.js": (
                    "surveillance-player.js",
                    "text/javascript; charset=utf-8",
                ),
                "/native-dashboard.js": (
                    "native-dashboard.js",
                    "text/javascript; charset=utf-8",
                ),
                "/style.css": ("style.css", "text/css; charset=utf-8"),
                "/dashboard-card.js": (
                    "camera-daily-merger-card.js",
                    "text/javascript; charset=utf-8",
                ),
            }
            if path in static:
                name, content_type = static[path]
                self.reply(
                    200,
                    (STATIC / name).read_bytes(),
                    content_type,
                    download_filename="camera-daily-merger-card.js"
                    if path == "/dashboard-card.js"
                    and parse_qs(parsed.query).get("download") == ["1"]
                    else None,
                )
            elif path == "/api/status":
                self.reply(
                    200,
                    {
                        "configured": settings is not None,
                        "version": APP_VERSION,
                        "cameras": sorted(settings.cameras) if settings else [],
                        "csrf": csrf,
                        "verification": "Local processing; original recordings are retained",
                        "diagnostics": store.metadata("scan_diagnostics") or [],
                    },
                )
            elif path == "/api/videos":
                try:
                    query = parse_qs(parsed.query, keep_blank_values=True)
                    if set(query) - {"view", "day"} or any(
                        len(v) != 1 for v in query.values()
                    ):
                        raise ValueError
                    self.reply(
                        200,
                        collection(
                            store,
                            settings,
                            view=query.get("view", ["latest"])[0],
                            day=query.get("day", [None])[0],
                        ),
                    )
                except (ValueError, TypeError):
                    self.reply(400, {"error": "Invalid collection request"})
            elif path == "/api/jobs":
                rows = []
                for row in store.list():
                    if settings and row["camera"] in settings.cameras:
                        rows.append(
                            {
                                key: row[key]
                                for key in (
                                    "camera",
                                    "day",
                                    "status",
                                    "attempts",
                                    "error",
                                )
                            }
                            | {
                                "has_output": bool(row["output"]),
                                "details": json.loads(row["error_details"])
                                if row["status"] == "failed" and row["error_details"]
                                else [],
                            }
                        )
                self.reply(200, rows)
            elif path.startswith("/video/"):
                if not self.server.media_slots.acquire(blocking=False):
                    self.reply(503, {"error": "Too many simultaneous video streams"})
                else:
                    try:
                        self.video(path, parsed.query)
                    finally:
                        self.server.media_slots.release()
            else:
                self.reply(404, {"error": "Not found"})

        def do_POST(self):
            if not self.authorized():
                return
            if not hmac.compare_digest(self.headers.get("X-CSRF-Token", ""), csrf):
                self.reply(403, {"error": "CSRF token required"})
                return
            if self.path != "/api/reprocess" or not settings:
                self.reply(404, {"error": "Not available"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if (
                    self.headers.get("Content-Type") != "application/json"
                    or not 0 < length <= 4096
                ):
                    raise ValueError
                payload = json.loads(self.rfile.read(length))
                if set(payload) != {"camera", "day"} or not isinstance(
                    payload["camera"], str
                ):
                    raise ValueError
                day = date.fromisoformat(payload["day"])
                result = Scheduler(store, settings).reconcile(
                    {day}, datetime.now(UTC), camera=payload["camera"], force=True
                )
                self.reply(202, result)
            except (ValueError, TypeError, KeyError):
                self.reply(400, {"error": "Invalid camera/date request"})
            except OSError:
                self.reply(503, {"error": "Storage unavailable"})

        def video(self, path, query):
            match = re.fullmatch(
                r"/video/([A-Za-z0-9_-]{1,64})/(\d{4}-\d{2}-\d{2})", path
            )
            if not settings or not match or match[1] not in settings.cameras:
                self.reply(404, {"error": "Not found"})
                return
            sent_headers = False
            try:
                camera, day = match.groups()
                date.fromisoformat(day)
                row = store.get(camera, day)
                if not row or not row["output"]:
                    raise ValueError
                output = json.loads(row["output"])
                parameters = parse_qs(query, keep_blank_values=True)
                if set(parameters) - {"v", "download"} or (
                    "v" in parameters and parameters["v"] != [output["sha256"]]
                ):
                    raise ValueError
                with open_export(settings, camera, day, output) as source:
                    size = os.fstat(source).st_size
                    if size != output["size"]:
                        raise ValueError
                    start, end = 0, size - 1
                    etag = '"' + output["sha256"] + '"'
                    header = self.headers.get("Range")
                    if self.headers.get("If-Range") not in (None, etag):
                        header = None
                    if header:
                        requested = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
                        if not requested or not any(requested.groups()):
                            self.reply(416, {"error": "Invalid range"})
                            return
                        left, right = requested.groups()
                        if left:
                            start = int(left)
                            end = min(size - 1, int(right)) if right else size - 1
                        else:
                            start = max(0, size - int(right))
                        if not 0 <= start <= end < size:
                            self.reply(416, {"error": "Invalid range"})
                            return
                    sent_headers = True
                    self.send_response(206 if header else 200)
                    self.send_header("Content-Type", "video/mp4")
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("ETag", etag)
                    self.send_header("Content-Length", str(end - start + 1))
                    if header:
                        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                    if parse_qs(query).get("download") == ["1"]:
                        self.send_header(
                            "Content-Disposition",
                            f'attachment; filename="{camera}-{day}.mp4"',
                        )
                    self.end_headers()
                    if self.command == "HEAD":
                        return
                    os.lseek(source, start, os.SEEK_SET)
                    remaining = end - start + 1
                    while remaining:
                        chunk = os.read(source, min(65536, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (OSError, ValueError, KeyError, TypeError):
                if not sent_headers:
                    self.reply(404, {"error": "Output unavailable"})
                else:
                    self.close_connection = True

    return Handler


@contextmanager
def serve(
    store: Store, settings: Settings | None, *, host="0.0.0.0", port=8099, peers=None
):
    server = BoundedServer(
        (host, port),
        make_handler(store, settings, ingress_peers() if peers is None else peers),
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
