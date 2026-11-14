"""Read-only current-export collections; no source scans or full-video hashing."""

from datetime import date
import json
import math
import re

from .storage import open_export


def collection(store, settings, *, view="latest", day=None):
    if view not in ("latest", "day") or (view == "latest" and day is not None):
        raise ValueError("Invalid collection view")
    if day is not None and date.fromisoformat(day).isoformat() != day:
        raise ValueError("Invalid collection date")
    cameras = sorted(settings.cameras) if settings else []
    rows, dates = store.gallery_rows(cameras, day if view == "day" else None)
    if view == "day" and day is None:
        day = dates[0] if dates else None
        rows, _ = store.gallery_rows(cameras, day) if day else ([], [])
    videos = []
    for row in rows:
        entry = {
            "camera": row["camera"],
            "day": row["day"],
            "available": False,
            "job_status": row["status"],
            "previous_export": bool(row["output"]) and row["status"] != "success",
        }
        if row["output"]:
            try:
                metadata = json.loads(row["output"])
                digest = metadata["sha256"]
                duration = float(metadata["duration"])
                if (
                    not re.fullmatch(r"[0-9a-f]{64}", digest)
                    or not math.isfinite(duration)
                    or duration <= 0
                ):
                    raise ValueError
                with open_export(settings, row["camera"], row["day"], metadata):
                    pass
                url = f"./video/{row['camera']}/{row['day']}?v={digest}"
                entry.update(
                    available=True,
                    duration=duration,
                    size=metadata["size"],
                    version=digest,
                    video_url=url,
                    download_url=url + "&download=1",
                )
            except (OSError, ValueError, TypeError, KeyError):
                entry["unavailable_reason"] = (
                    "Latest export unavailable; check storage or reprocess this day."
                )
        videos.append(entry)
    if view == "day" and not rows:
        videos = [
            {
                "camera": camera,
                "day": day,
                "available": False,
                "job_status": None,
                "previous_export": False,
            }
            for camera in cameras
        ]
    return {"view": view, "day": day, "dates": dates, "videos": videos}
