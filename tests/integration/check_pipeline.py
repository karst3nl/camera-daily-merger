"""Native container synthetic scheduled merge/restart acceptance check."""

import argparse
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import time
import uuid
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--compact", action="store_true")
    parser.add_argument("--archived-dst", action="store_true")
    parser.add_argument("--mixed-rate", action="store_true")
    args = parser.parse_args()
    if args.mixed_rate and not args.compact:
        parser.error("--mixed-rate requires --compact")
    name = "merger-pipeline-" + uuid.uuid4().hex[:12]

    def docker(*command):
        return subprocess.run(
            ["docker", "--host=unix:///var/run/docker.sock", *command],
            check=True,
            capture_output=True,
            text=True,
        )

    with tempfile.TemporaryDirectory(dir=Path.cwd() / "work") as directory:
        root = Path(directory)
        data, media = root / "data", root / "media"
        data.mkdir()
        source_dir = media / "input"
        source_dir.mkdir(parents=True)
        day = (datetime.now(ZoneInfo("Europe/Berlin")) - timedelta(days=2)).date()
        source = source_dir / (
            f"synthetic_00_{day:%Y%m%d}100000.mp4"
            if args.compact
            else f"{day}T10:00:00+01:00.mp4"
        )
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=red:size=64x64:duration=0.5:rate=20"
                if args.mixed_rate
                else "color=red:size=64x64:duration=0.5:rate=10",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                *(
                    ["-bf", "0", "-video_track_timescale", "23900"]
                    if args.mixed_rate
                    else []
                ),
                str(source),
            ],
            check=True,
        )
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        second = None
        second_digest = None
        if args.mixed_rate:
            second = source_dir / f"synthetic_00_{day:%Y%m%d}120000.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-i",
                    str(source),
                    "-c",
                    "copy",
                    "-bsf:v",
                    "setts=time_base=1/23900:pts=N*1200:dts=N*1200:duration=1200",
                    "-video_track_timescale",
                    "23900",
                    str(second),
                ],
                check=True,
            )
            second_digest = hashlib.sha256(second.read_bytes()).hexdigest()
        archived = None
        if args.archived_dst:
            if not args.compact:
                parser.error("--archived-dst requires --compact")
            archived = source_dir / "synthetic_00_20261025020100.mp4"
            archived.write_bytes(source.read_bytes())
        (data / "options.json").write_text(
            json.dumps(
                {
                    "source_root": "/media",
                    "cameras": [{"id": "synthetic", "path": "input"}],
                    "timestamp_pattern": r"synthetic_00_(?P<start>\d{14})\.mp4"
                    if args.compact
                    else r"(?P<start>.+)\.mp4",
                    "timestamp_format": "%Y%m%d%H%M%S" if args.compact else "iso8601",
                    "minimum_age_seconds": 0,
                }
            )
        )
        try:
            docker(
                "run",
                "-d",
                "--name",
                name,
                "--mount",
                f"type=bind,src={data},dst=/data",
                "--mount",
                f"type=bind,src={media},dst=/media",
                args.image,
            )
            row = None
            for _ in range(80):
                if (data / "jobs.sqlite").exists():
                    with sqlite3.connect(data / "jobs.sqlite") as db:
                        try:
                            row = db.execute(
                                "SELECT status,output,attempts FROM jobs WHERE camera='synthetic'"
                            ).fetchone()
                        except sqlite3.OperationalError:
                            pass
                if row and row[0] == "success":
                    break
                time.sleep(0.25)
            assert row and row[0] == "success", docker("logs", name).stdout
            output = json.loads(row[1])
            docker(
                "exec",
                name,
                "python",
                "-c",
                "import os; from pathlib import Path; roots=[Path('/media/daily'),Path('/media/.staging')]; [(os.chmod(p,0o777) if p.is_dir() else None) for r in roots for p in [r,*r.rglob('*')]]",
            )
            assert (media / output["path"]).exists()
            docker("exec", name, "python", "-m", "app.main", "--healthcheck")
            if second is not None:

                def packet_hashes(relative):
                    raw = docker(
                        "exec",
                        name,
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
                        f"/media/{relative}",
                    ).stdout
                    return [
                        packet["data_hash"] for packet in json.loads(raw)["packets"]
                    ]

                assert packet_hashes(output["path"]) == packet_hashes(
                    "input/" + source.name
                ) + packet_hashes("input/" + second.name)
            docker("restart", name)
            time.sleep(1)
            docker("stop", "-t", "5", name)
            with sqlite3.connect(data / "jobs.sqlite") as db:
                after = db.execute(
                    "SELECT status,output,attempts FROM jobs WHERE camera='synthetic'"
                ).fetchone()
            assert row == after
            assert hashlib.sha256(source.read_bytes()).hexdigest() == digest
            if archived is not None:
                assert hashlib.sha256(archived.read_bytes()).hexdigest() == digest
            if second is not None:
                assert hashlib.sha256(second.read_bytes()).hexdigest() == second_digest
            assert (
                docker("inspect", "-f", "{{.State.ExitCode}}", name).stdout.strip()
                == "0"
            )
            print(
                "PASS: automatic merge, current output, restart idempotency, graceful shutdown, source hash"
            )
        finally:
            docker("rm", "-f", name)


if __name__ == "__main__":
    main()
