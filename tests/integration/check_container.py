"""Run explicitly against a built image; no Docker dependency for unit tests."""

import argparse
from pathlib import Path
import subprocess
import tempfile
import time
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--qemu", type=Path)
    args = parser.parse_args()
    name = "merger-test-" + uuid.uuid4().hex[:12]

    def docker(*command, check=True):
        return subprocess.run(
            ["docker", "--host=unix:///var/run/docker.sock", *command],
            check=check,
            capture_output=True,
            text=True,
        )

    with tempfile.TemporaryDirectory(dir=Path.cwd() / "work") as directory:
        root = Path(directory)
        data, media = root / "data", root / "media"
        data.mkdir()
        media.mkdir()
        original = media / "synthetic.txt"
        original.write_bytes(b"untouched")
        extra, entry, executable = [], [], ["python"]
        if args.qemu:
            extra = [
                "--mount",
                f"type=bind,src={args.qemu.resolve()},dst=/qemu,readonly",
                "--entrypoint",
                "/qemu",
            ]
            executable = ["/qemu", "/usr/local/bin/python"]
            entry = ["/usr/local/bin/python", "-m", "app.main"]

        def wait_healthy():
            for _ in range(40):
                result = docker(
                    "exec",
                    name,
                    *executable,
                    "-m",
                    "app.main",
                    "--healthcheck",
                    check=False,
                )
                if result.returncode == 0:
                    return
                time.sleep(0.25)
            raise AssertionError("Container did not become healthy")

        try:
            docker(
                "run",
                "-d",
                "--name",
                name,
                *extra,
                "--mount",
                f"type=bind,src={data},dst=/data",
                "--mount",
                f"type=bind,src={media},dst=/media,readonly",
                args.image,
                *entry,
            )
            wait_healthy()
            docker("restart", name)
            wait_healthy()
            docker("stop", "-t", "5", name)
            assert (
                docker("inspect", "-f", "{{.State.ExitCode}}", name).stdout.strip()
                == "0"
            )
            assert not (data / "heartbeat").exists()
            assert original.read_bytes() == b"untouched"
            print("PASS: health, restart, shutdown, original unchanged")
        finally:
            docker("rm", "-f", name, check=False)


if __name__ == "__main__":
    main()
