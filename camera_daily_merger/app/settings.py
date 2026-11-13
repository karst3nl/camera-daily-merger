"""Explicit synthetic source adapter configuration; no Reolink assumptions."""

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
from zoneinfo import ZoneInfo


class ConfigurationError(ValueError):
    """Controlled validation messages containing no deployment-specific values."""


def relative_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise ConfigurationError("Invalid relative path")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise ConfigurationError(
            "Camera/output/staging paths must be relative to source_root; absolute paths and parent traversal are not allowed"
        )
    return str(path)


@dataclass(frozen=True)
class Settings:
    root: Path
    cameras: dict[str, str]
    timestamp_pattern: str
    timestamp_format: str = "iso8601"
    timezone: str = "Europe/Berlin"
    output: str = "daily"
    staging: str = ".staging"
    minimum_age_seconds: int = 60
    extensions: tuple[str, ...] = (".mp4",)

    def __post_init__(self):
        if not self.root.is_absolute():
            raise ConfigurationError("Storage root must be absolute")
        if (
            not isinstance(self.timestamp_format, str)
            or not 1 <= len(self.timestamp_format) <= 128
        ):
            raise ConfigurationError("Explicit timestamp format required")
        ZoneInfo(self.timezone)
        pattern = re.compile(self.timestamp_pattern)
        if "start" not in pattern.groupindex:
            raise ConfigurationError("Timestamp pattern requires a named start group")
        if self.minimum_age_seconds < 0:
            raise ConfigurationError("Minimum age cannot be negative")
        for name in ("output", "staging"):
            value = relative_path(getattr(self, name))
            if value == ".":
                raise ConfigurationError(
                    "Reserved directories cannot be the storage root"
                )
            object.__setattr__(self, name, value)
        reserved = [PurePosixPath(self.output), PurePosixPath(self.staging)]
        if any(a.is_relative_to(b) for a, b in (reserved, reversed(reserved))):
            raise ConfigurationError("Output and staging must be separate")
        camera_paths = []
        for camera, path in self.cameras.items():
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", camera):
                raise ConfigurationError("Invalid camera ID")
            path = PurePosixPath(relative_path(path))
            if any(path.is_relative_to(r) for r in reserved):
                raise ConfigurationError("Camera cannot be inside output/staging")
            if any(
                path.is_relative_to(p) or p.is_relative_to(path) for p in camera_paths
            ):
                raise ConfigurationError("Camera mappings cannot overlap")
            camera_paths.append(path)
        if (
            not self.cameras
            or not self.extensions
            or any(
                not re.fullmatch(r"\.[A-Za-z0-9]+", extension)
                for extension in self.extensions
            )
        ):
            raise ConfigurationError(
                "Camera mappings and simple extensions are required"
            )


def from_addon_options(options: dict) -> Settings | None:
    """Empty alpha defaults require explicit adapter configuration before processing."""
    if not isinstance(options, dict):
        raise ConfigurationError("Add-on options must be an object")
    mappings = options.get("cameras", [])
    if not mappings or not options.get("timestamp_pattern"):
        return None
    try:
        cameras = {entry["id"]: entry["path"] for entry in mappings}
        if len(cameras) != len(mappings):
            raise ConfigurationError("Duplicate camera IDs")
        return Settings(
            root=Path(options["source_root"]),
            cameras=cameras,
            timestamp_pattern=options["timestamp_pattern"],
            timestamp_format=options.get("timestamp_format", "iso8601"),
            timezone=options.get("timezone", "Europe/Berlin"),
            output=options.get("output", "daily"),
            staging=options.get("staging", ".staging"),
            minimum_age_seconds=options.get("minimum_age_seconds", 60),
        )
    except (KeyError, TypeError) as error:
        raise ConfigurationError("Invalid add-on source configuration") from error
