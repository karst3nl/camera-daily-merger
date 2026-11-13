"""ISO timestamps from an explicitly configured filename regex."""

from datetime import UTC, datetime
import re
from typing import Protocol
from zoneinfo import ZoneInfo


class TimestampParser(Protocol):
    def parse(self, name: str) -> datetime: ...


class RegexTimestampParser:
    def __init__(self, pattern: str, timezone: str, timestamp_format: str = "iso8601"):
        self.pattern = re.compile(pattern)
        self.zone = ZoneInfo(timezone)
        self.timestamp_format = timestamp_format

    def parse(self, name: str) -> datetime:
        match = self.pattern.fullmatch(name)
        if not match:
            raise ValueError("Filename does not match configured timestamp adapter")
        value = match.group("start")
        if self.timestamp_format == "iso8601":
            if "T" not in value and " " not in value:
                raise ValueError("Recording timestamp requires a time component")
            start = datetime.fromisoformat(value)
        else:
            start = datetime.strptime(value, self.timestamp_format)
        if start.tzinfo is not None:
            return start.astimezone(self.zone)
        # Round-trip both folds. A gap has no valid instant; a repeated hour has two.
        candidates = {
            candidate.astimezone(UTC)
            for fold in (0, 1)
            if (candidate := start.replace(tzinfo=self.zone, fold=fold))
            .astimezone(UTC)
            .astimezone(self.zone)
            .replace(tzinfo=None)
            == start
        }
        if len(candidates) != 1:
            raise ValueError("Ambiguous or nonexistent local recording timestamp")
        return candidates.pop().astimezone(self.zone)
