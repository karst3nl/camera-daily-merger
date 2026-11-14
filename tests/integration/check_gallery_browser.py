"""Desktop/mobile multi-camera gallery with real synthetic playback."""

from pathlib import Path
import argparse
import subprocess
import tempfile

from playwright.sync_api import expect, sync_playwright

from camera_daily_merger.app.persistence import Store
from camera_daily_merger.app.settings import Settings
from camera_daily_merger.app.web import serve
from tests.integration.test_catalog import published


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(dir=Path.cwd() / "work") as folder:
        root = Path(folder)
        base = root / "synthetic.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=blue:size=64x64:rate=10:duration=5",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                str(base),
            ],
            check=True,
        )
        body = base.read_bytes()
        store = Store(root / "jobs.sqlite")
        settings = Settings(
            root=root,
            cameras={"a": "input_a", "b": "input_b", "c": "input_c"},
            timestamp_pattern=r"(?P<start>.+)\.mp4",
        )
        published(store, root, "a", "2026-11-11", body=body, duration=5.0)
        published(store, root, "a", "2026-11-12", body=body, duration=5.0)
        published(store, root, "b", "2026-11-11", body=body, duration=5.0)
        with (
            serve(
                store, settings, host="127.0.0.1", port=0, peers={"127.0.0.1"}
            ) as server,
            sync_playwright() as pw,
        ):
            browser = pw.chromium.launch(
                executable_path=args.chromium,
                headless=True,
                args=["--no-sandbox"],
            )
            page = browser.new_page(viewport={"width": 1280, "height": 1000})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            media_requests = []
            page.on(
                "request",
                lambda req: media_requests.append(req.url)
                if "/video/" in req.url
                else None,
            )
            url = f"http://127.0.0.1:{server.server_address[1]}"
            page.goto(url)
            expect(
                page.locator('.camera-tile[data-camera="a"] .tile-date')
            ).to_have_text("2026-11-12")
            expect(
                page.locator('.camera-tile[data-camera="b"] .tile-date')
            ).to_have_text("2026-11-11")
            expect(page.locator("#gallery-grid video")).to_have_count(2)
            assert not media_requests, media_requests
            page.get_by_role("button", name="Play all", exact=True).click()
            expect(page.locator("#gallery-message")).to_have_text("")
            page.wait_for_function(
                "() => [...document.querySelectorAll('#gallery-grid video')].every(v=>v.readyState>=2 && !v.paused)"
            )
            published(store, root, "b", "2026-11-12", body=body, duration=5.0)
            page.evaluate("() => refreshGallery()")
            expect(page.locator("#gallery-message")).to_contain_text(
                "New exports are ready"
            )
            expect(
                page.locator('.camera-tile[data-camera="b"] .tile-date')
            ).to_have_text("2026-11-11")
            page.get_by_role("button", name="Pause all", exact=True).click()
            expect(
                page.locator('.camera-tile[data-camera="b"] .tile-date')
            ).to_have_text("2026-11-12")
            page.get_by_role("button", name="All cameras by day", exact=True).click()
            page.locator("#gallery-day").fill("2026-11-11")
            page.locator("#gallery-day").press("Tab")
            expect(page.locator("#gallery-title")).to_have_text(
                "All cameras · 2026-11-11"
            )
            expect(page.locator("#gallery-grid video")).to_have_count(2)
            page.screenshot(path="work/gallery-desktop.png", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path="work/gallery-mobile.png", full_page=True)
            page.goto(url + "/#view=day&day=2026-11-12&embed=1")
            expect(page.locator("#gallery-grid video")).to_have_count(2)
            assert not page.locator("header").is_visible()
            assert not page.locator("#management").is_visible()
            page.goto(url + "/#view=latest")
            page.get_by_role("button", name="Dashboard setup", exact=True).click()
            with page.expect_download() as download:
                page.get_by_role(
                    "link", name="Download dashboard card", exact=True
                ).click()
            assert download.value.suggested_filename == "camera-daily-merger-card.js"
            assert not errors, errors
            browser.close()
            print(
                "PASS latest per camera, shared day, missing camera, play/pause all, non-disruptive refresh, mobile and embedded views"
            )


if __name__ == "__main__":
    main()
