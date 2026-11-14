"""Explicit Playwright browser gate; requires playwright and a local Chromium."""

import argparse
import os
from pathlib import Path
import tempfile
import threading

from playwright.sync_api import expect, sync_playwright

from camera_daily_merger.app.jobs import enqueue, run_one, worker_lock
from camera_daily_merger.app.persistence import Store
from camera_daily_merger.app.web import serve
from tests.integration.test_merge import DAY, clips, config, make_clip


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chromium", default="/usr/bin/chromium")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(dir=Path.cwd() / "work") as folder:
        root = Path(folder)
        make_clip(root, 10)
        data = root / "data"
        data.mkdir()
        settings = config(root)
        store = Store(data / "jobs.sqlite")
        enqueue(store, settings, "a", DAY, clips(root))
        with worker_lock(data):
            run_one(store, settings, data, threading.Event())
        with (
            serve(
                store, settings, host="127.0.0.1", port=0, peers={"127.0.0.1"}
            ) as server,
            sync_playwright() as playwright,
        ):
            browser = playwright.chromium.launch(
                executable_path=args.chromium, headless=True, args=["--no-sandbox"]
            )
            page = browser.new_page(viewport={"width": 1280, "height": 1100})
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(f"http://127.0.0.1:{server.server_address[1]}/")
            page.get_by_role("button", name="Processing & single camera").click()
            page.get_by_text("a · 2026-11-12", exact=True).wait_for()
            page.locator("#camera").select_option("a")
            page.locator("#day").fill(str(DAY))
            page.get_by_role("button", name="Show recording").click()
            page.locator("#video").evaluate("e=>{e.muted=true;return e.play();}")
            page.wait_for_function("document.getElementById('video').readyState >= 2")
            page.screenshot(path="work/browser-desktop.png", full_page=True)
            with page.expect_download() as download:
                page.get_by_role("link", name="Download MP4").click()
            assert download.value.suggested_filename == f"a-{DAY}.mp4"
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            page.screenshot(path="work/browser-mobile.png", full_page=True)
            page.locator("#video").evaluate("e=>e.dispatchEvent(new Event('error'))")
            assert page.locator("#playback").is_visible()
            page.get_by_role("button", name="Reprocess day").click()
            page.get_by_text(
                "Day queued for sequential processing.", exact=True
            ).wait_for()
            assert store.get("a", str(DAY))["status"] == "queued"
            bad_name = "unmatched<img src=x onerror=alert(1)>.mp4"
            bad_path = root / "input" / bad_name
            bad_path.write_bytes(b"synthetic")
            os.utime(bad_path, (1, 1))
            page.get_by_role("button", name="Reprocess day").click()
            expect(page.locator("#message")).to_contain_text(
                "filename_pattern_mismatch"
            )
            assert bad_name in page.locator("#message").inner_text()
            assert bad_name in page.locator("#diagnostics").inner_text()
            assert page.locator("#diagnostics img").count() == 0
            assert page.evaluate(
                "document.documentElement.scrollWidth <= window.innerWidth"
            )
            pending = store.claim(0)
            store.finish(pending, 0, error="synthetic retry setup")
            make_clip(root, 12, size="128x64")
            enqueue(store, settings, "a", DAY, clips(root), force=True)
            with worker_lock(data):
                run_one(store, settings, data, threading.Event())
            page.get_by_role("button", name="Refresh", exact=True).click()
            expect(page.locator("#jobs")).to_contain_text("width: 128 vs 64")
            assert str(root) not in page.locator("#jobs").inner_text()
            assert not errors, errors
            browser.close()
            print(
                "PASS: desktop/mobile layout, playback, download, compatibility message, manual reprocess, no JS errors"
            )


if __name__ == "__main__":
    main()
