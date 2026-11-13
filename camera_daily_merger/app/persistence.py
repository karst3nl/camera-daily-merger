"""SQLite job transitions; each transaction uses its own bounded connection."""

from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import uuid

from .scanner import Clip, chronological


def manifest(clips: list[Clip]) -> str:
    return json.dumps(
        [asdict(c) for c in chronological(clips)], default=str, sort_keys=True
    )


def fingerprint(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def decode_manifest(value: str) -> list[Clip]:
    return [
        Clip(**{**row, "start": datetime.fromisoformat(row["start"])})
        for row in json.loads(value)
    ]


class Store:
    def __init__(self, path: Path):
        self.path = path
        with self.transaction() as db:
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1, 2):
                raise ValueError("Unsupported database schema version")
            db.execute("""CREATE TABLE IF NOT EXISTS jobs (
                camera TEXT NOT NULL, day TEXT NOT NULL, manifest TEXT NOT NULL,
                fingerprint TEXT NOT NULL, status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0, next_retry REAL NOT NULL DEFAULT 0,
                token TEXT, error TEXT, output TEXT, output_fingerprint TEXT,
                PRIMARY KEY(camera,day))""")
            db.execute("""CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY, camera TEXT, day TEXT, token TEXT,
                status TEXT, timestamp REAL, error TEXT)""")
            db.execute(
                "CREATE TABLE IF NOT EXISTS metadata (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            db.execute("PRAGMA user_version=2")

    @contextmanager
    def transaction(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def get(self, camera, day):
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE camera=? AND day=?", (camera, day)
            ).fetchone()
            return dict(row) if row else None

    def list(self):
        with self.transaction() as db:
            return [
                dict(row)
                for row in db.execute(
                    "SELECT camera,day,status,attempts,next_retry,error,output,output_fingerprint,fingerprint, (SELECT value FROM metadata WHERE key='media_diagnostics:' || jobs.camera || ':' || jobs.day) AS error_details FROM jobs ORDER BY day DESC,camera LIMIT 1000"
                )
            ]

    def enqueue(self, camera, day, clips, now, *, force=False, healthy=False):
        value = manifest(clips)
        digest = fingerprint(value)
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE camera=? AND day=?", (camera, day)
            ).fetchone()
            if row:
                if row["status"] in ("running", "queued"):
                    return False
                if not force and row["fingerprint"] == digest:
                    if row["status"] == "success" and healthy:
                        return False
                    if row["status"] == "failed" and (
                        row["attempts"] >= 5 or row["next_retry"] > now
                    ):
                        return False
                attempts = (
                    row["attempts"]
                    if not force
                    and row["fingerprint"] == digest
                    and row["status"] == "failed"
                    else 0
                )
                db.execute(
                    """UPDATE jobs SET manifest=?,fingerprint=?,status='queued',
                    attempts=?,next_retry=0,error=NULL WHERE camera=? AND day=?""",
                    (value, digest, attempts, camera, day),
                )
            else:
                db.execute(
                    "INSERT INTO jobs(camera,day,manifest,fingerprint,status) VALUES(?,?,?,?,'queued')",
                    (camera, day, value, digest),
                )
            db.execute(
                "DELETE FROM metadata WHERE key=?",
                (f"media_diagnostics:{camera}:{day}",),
            )
            db.execute(
                "INSERT INTO history(camera,day,status,timestamp) VALUES(?,?,'queued',?)",
                (camera, day, now),
            )
            return True

    def claim(self, now):
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE status='queued' ORDER BY day,camera LIMIT 1"
            ).fetchone()
            if not row:
                return None
            token = uuid.uuid4().hex
            db.execute(
                "UPDATE jobs SET status='running',attempts=attempts+1,token=? WHERE camera=? AND day=?",
                (token, row["camera"], row["day"]),
            )
            db.execute(
                "INSERT INTO history(camera,day,token,status,timestamp) VALUES(?,?,?,'running',?)",
                (row["camera"], row["day"], token, now),
            )
            return dict(
                db.execute("SELECT * FROM jobs WHERE token=?", (token,)).fetchone()
            )

    def finish(self, job, now, *, output=None, error=None, details=None):
        with self.transaction() as db:
            row = db.execute(
                "SELECT * FROM jobs WHERE camera=? AND day=? AND token=? AND status='running'",
                (job["camera"], job["day"], job["token"]),
            ).fetchone()
            if not row:
                raise ValueError("Stale job completion rejected")
            status = "failed" if error else "success"
            retry = now + min(3600, 30 * 2 ** min(row["attempts"] - 1, 7))
            db.execute(
                "UPDATE jobs SET status=?,error=?,next_retry=? WHERE camera=? AND day=?",
                (status, error, retry, job["camera"], job["day"]),
            )
            key = f"media_diagnostics:{job['camera']}:{job['day']}"
            if details:
                db.execute(
                    "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, json.dumps(details[:12])),
                )
            else:
                db.execute("DELETE FROM metadata WHERE key=?", (key,))
            if output:
                db.execute(
                    "UPDATE jobs SET output=?,output_fingerprint=? WHERE camera=? AND day=?",
                    (json.dumps(output), job["fingerprint"], job["camera"], job["day"]),
                )
            db.execute(
                "INSERT INTO history(camera,day,token,status,timestamp,error) VALUES(?,?,?,?,?,?)",
                (job["camera"], job["day"], job["token"], status, now, error),
            )

    def recover(self, now):
        """Caller must hold the exclusive worker lock for the entire worker lifetime."""
        with self.transaction() as db:
            rows = db.execute("SELECT * FROM jobs WHERE status='running'").fetchall()
            for row in rows:
                db.execute(
                    "UPDATE jobs SET status='failed',token=NULL,error='interrupted',next_retry=? WHERE camera=? AND day=?",
                    (now + 30, row["camera"], row["day"]),
                )
                db.execute(
                    "INSERT INTO history(camera,day,token,status,timestamp,error) VALUES(?,?,?,'failed',?,'interrupted')",
                    (row["camera"], row["day"], row["token"], now),
                )
            return len(rows)

    def metadata(self, key, value=None):
        with self.transaction() as db:
            if value is not None:
                db.execute(
                    "INSERT INTO metadata(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                    (key, json.dumps(value)),
                )
                return value
            row = db.execute(
                "SELECT value FROM metadata WHERE key=?", (key,)
            ).fetchone()
            return json.loads(row[0]) if row else None

    def cache_output(self, row, metadata):
        with self.transaction() as db:
            db.execute(
                "UPDATE jobs SET output=? WHERE camera=? AND day=? AND output=?",
                (json.dumps(metadata), row["camera"], row["day"], row["output"]),
            )
