"""Calendar scheduling and bounded reconciliation; no timezone arithmetic shortcuts."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import PurePosixPath
from zoneinfo import ZoneInfo

from .jobs import enqueue
from .persistence import Store
from .scanner import Clip, scan
from .settings import Settings
from .timestamp_parser import RegexTimestampParser


@dataclass(frozen=True)
class Schedule:
    reconcile_seconds: int = 21600
    backfill_days: int = 7

    def __post_init__(self):
        if (
            not 60 <= self.reconcile_seconds <= 604800
            or not 1 <= self.backfill_days <= 366
        ):
            raise ValueError("Invalid reconciliation interval/backfill bound")


def latest_due_day(now: datetime, timezone: str) -> date:
    if now.tzinfo is None:
        raise ValueError("Scheduler requires an aware clock")
    local = now.astimezone(ZoneInfo(timezone))
    return local.date() - timedelta(days=1 if local.time() >= time(0, 15) else 2)


class Scheduler:
    def __init__(
        self, store: Store, settings: Settings, schedule: Schedule | None = None
    ):
        self.store, self.settings = store, settings
        self.schedule = schedule or Schedule()

    def reconcile(self, days: set[date], now: datetime, *, camera=None, force=False):
        if now.tzinfo is None or not days or len(days) > 366:
            raise ValueError("Expected aware clock and 1..366 dates")
        if camera is not None and camera not in self.settings.cameras:
            raise ValueError("Unknown camera")
        if any(day > latest_due_day(now, self.settings.timezone) for day in days):
            raise ValueError("Only completed scheduled calendar days may be processed")
        cameras = [camera] if camera else list(self.settings.cameras)
        grouped = {(name, day): [] for name in cameras for day in days}
        blocked = set()
        parser = RegexTimestampParser(
            self.settings.timestamp_pattern, self.settings.timezone
        )
        for item in scan(self.settings, now=now.timestamp()):
            if item.camera not in cameras:
                continue
            if isinstance(item, Clip):
                key = item.camera, item.start.date()
                if key in grouped and len(grouped[key]) <= 256:
                    grouped[key].append(item)
            else:
                try:
                    affected = {
                        parser.parse(PurePosixPath(item.path).name).date()
                    } & days
                except ValueError:
                    affected = days
                for day in affected:
                    blocked.add((item.camera, day, item.reason))
        queued = 0
        for (name, day), selected in grouped.items():
            if any(c == name and d == day for c, d, _ in blocked):
                continue
            if selected:
                queued += enqueue(
                    self.store,
                    self.settings,
                    name,
                    day,
                    selected,
                    now=now.timestamp(),
                    force=force,
                )
        errors = [
            {"camera": name, "day": day.isoformat(), "reason": reason}
            for name, day, reason in sorted(blocked)
        ]
        self.store.metadata("scan_diagnostics", errors)
        return {"queued": queued, "diagnostics": errors}

    def tick(self, now: datetime):
        due = latest_due_day(now, self.settings.timezone)
        previous = self.store.metadata("last_scan")
        rows = self.store.list()
        retry_due = any(
            row["status"] == "failed"
            and row["attempts"] < 5
            and row["next_retry"] <= now.timestamp()
            for row in rows
        )
        if (
            previous
            and previous["due"] == due.isoformat()
            and 0
            <= now.timestamp() - previous["timestamp"]
            < self.schedule.reconcile_seconds
            and not retry_due
        ):
            return {"queued": 0, "diagnostics": []}
        days = {due - timedelta(days=n) for n in range(self.schedule.backfill_days)}
        # Previously requested historical jobs are revisited within the bounded listing.
        days.update(
            date.fromisoformat(row["day"])
            for row in rows
            if row["day"] <= due.isoformat()
        )
        # Bound one reconciliation pass. Older ranges remain available via manual backfill.
        days = set(sorted(days, reverse=True)[:366])
        result = self.reconcile(days, now)
        self.store.metadata(
            "last_scan", {"due": due.isoformat(), "timestamp": now.timestamp()}
        )
        return result
