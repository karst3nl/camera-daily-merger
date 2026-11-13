"""ISO timestamps from an explicitly configured filename regex."""

from datetime import UTC, date, datetime
import re
from typing import Protocol
from zoneinfo import ZoneInfo


class TimestampError(ValueError):
    """Controlled diagnostic code without recording metadata."""

    def __init__(self, code: str, *, recording_date: date | None = None):
        super().__init__(code)
        self.code = code
        self.recording_date = recording_date


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
            raise TimestampError("filename_pattern_mismatch")
        value = match.group("start")
        try:
            if self.timestamp_format == "iso8601":
                if "T" not in value and " " not in value:
                    raise ValueError("Missing time component")
                start = datetime.fromisoformat(value)
            else:
                start = datetime.strptime(value, self.timestamp_format)
        except ValueError as error:
            raise TimestampError("timestamp_format_mismatch") from error
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
            raise TimestampError(
                "ambiguous_or_nonexistent_local_time", recording_date=start.date()
            )
        return candidates.pop().astimezone(self.zone)
