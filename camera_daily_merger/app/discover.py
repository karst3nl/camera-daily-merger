"""Explicit read-only JSON-lines dry run: python -m app.discover config.json."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path

from .scanner import scan
from .settings import Settings


def main():
    parser = argparse.ArgumentParser(description="Read-only discovery; no media output")
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    config["root"] = Path(config["root"])
    settings = Settings(**config)
    for result in scan(settings):
        print(
            json.dumps({"type": type(result).__name__, **asdict(result)}, default=str)
        )


if __name__ == "__main__":
    main()
