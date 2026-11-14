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
                "testsrc2=size=320x180:rate=10:duration=5",
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
            cameras={"a": "input_a", "b": "input_b", "c": "input_c", "d": "input_d"},
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
            initial_boxes = [
                tile.bounding_box() for tile in page.locator(".camera-tile").all()
            ]
            assert len(initial_boxes) == 4
            assert (
                max(b["height"] for b in initial_boxes)
                - min(b["height"] for b in initial_boxes)
                < 1
            )
            assert not media_requests, media_requests
            page.get_by_role("button", name="Play all", exact=True).click()
            expect(page.locator("#gallery-message")).to_have_text("")
            page.wait_for_function(
                "() => [...document.querySelectorAll('#gallery-grid video')].every(v=>v.readyState>=2 && !v.paused)"
            )
            tile = page.locator('.camera-tile[data-camera="a"]')
            other = page.locator('.camera-tile[data-camera="b"]')
            assert not tile.locator("video").evaluate("v=>v.controls")
            assert tile.locator("video").evaluate("v=>v.preload") == "none"
            assert tile.locator(".tile-meta").count() == 0
            assert tile.bounding_box()["y"] == other.bounding_box()["y"]
            viewport = tile.locator(".video-viewport")
            controls = tile.locator(".video-controls")
            assert (
                controls.bounding_box()["y"]
                >= viewport.bounding_box()["y"] + viewport.bounding_box()["height"]
            )
            tile.get_by_role("button", name="a: Pause", exact=True).click()
            assert tile.locator("video").evaluate("v=>v.paused")
            seek = tile.get_by_role("slider", name="a: Seek", exact=True)
            seek.fill("2")
            page.wait_for_function(
                "() => document.querySelector('.camera-tile video').currentTime >= 1.9"
            )
            for _ in range(6):
                tile.get_by_role("button", name="a: Zoom in", exact=True).click()
            expect(
                tile.get_by_role("button", name="a: Zoom in", exact=True)
            ).to_be_disabled()
            expect(
                tile.get_by_role("button", name="a: Reset zoom", exact=True)
            ).to_have_text("4×")
            before = tile.locator("video").evaluate("v=>v.style.transform")
            box = viewport.bounding_box()
            page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
            page.mouse.down()
            page.mouse.move(
                box["x"] + box["width"] / 2 + 35, box["y"] + box["height"] / 2 + 20
            )
            page.mouse.up()
            assert tile.locator("video").evaluate("v=>v.style.transform") != before
            assert "scale(4)" in tile.locator("video").evaluate("v=>v.style.transform")
            tile.get_by_role("button", name="a: Reset zoom", exact=True).click()
            expect(
                tile.get_by_role("button", name="a: Reset zoom", exact=True)
            ).to_have_text("1×")
            expect(
                tile.get_by_role("button", name="a: Zoom out", exact=True)
            ).to_be_disabled()
            tile.get_by_role("button", name="a: Unmute", exact=True).click()
            assert not tile.locator("video").evaluate("v=>v.muted")
            tile.get_by_role("button", name="a: Mute", exact=True).click()
            tile.get_by_role("button", name="a: Fullscreen", exact=True).click()
            page.wait_for_function(
                "() => document.fullscreenElement?.classList.contains('surveillance-player')"
            )
            assert (
                controls.bounding_box()["y"]
                >= viewport.bounding_box()["y"] + viewport.bounding_box()["height"] - 1
            )
            page.evaluate("document.exitFullscreen()")
            page.wait_for_function("() => !document.fullscreenElement")
            tile.get_by_role("button", name="a: Play", exact=True).click()
            page.wait_for_function(
                "() => !document.querySelector('.camera-tile video').paused"
            )
            page.screenshot(path="work/surveillance-playback.png", full_page=True)
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
            mobile_a = page.locator('.camera-tile[data-camera="a"]').bounding_box()
            mobile_b = page.locator('.camera-tile[data-camera="b"]').bounding_box()
            assert mobile_a["y"] == mobile_b["y"]
            assert mobile_b["x"] > mobile_a["x"]
            control_box = page.locator(
                '.camera-tile[data-camera="a"] .video-controls'
            ).bounding_box()
            assert control_box["x"] >= mobile_a["x"]
            assert (
                control_box["x"] + control_box["width"]
                <= mobile_a["x"] + mobile_a["width"] + 1
            )
            page.screenshot(path="work/gallery-mobile.png", full_page=True)
            page.goto(url + "/#view=day&day=2026-11-12&embed=1")
            expect(page.locator("#gallery-grid video")).to_have_count(2)
            assert not page.locator("header").is_visible()
            assert not page.locator("#management").is_visible()
            page.goto(url + "/#view=latest")
            expect(page.locator("#dashboard-help")).not_to_be_visible()
            expect(page.locator(".dashboard-setup")).not_to_be_visible()
            page.get_by_role(
                "button", name="Processing & single camera", exact=True
            ).click()
            page.get_by_role("button", name="Dashboard setup", exact=True).click()
            expect(page.locator("#native-dashboard-status")).to_contain_text(
                "Open this app"
            )
            # Mock the official HA app-panel properties bridge inside a native
            # Webpage frame. Authentication/session handling belongs to HA.
            page.route(
                "**/native-panel-test",
                lambda route: route.fulfill(
                    content_type="text/html",
                    body="""<!doctype html><body>
                <iframe src="/" width="1200" height="900"></iframe>
                <script>
                let kiosk=false;
                const properties={type:'home-assistant/properties',route:{
                  prefix:'/app/local_camera_daily_merger',path:'/dashboard/day/2026-11-11'}};
                addEventListener('message',e=>{
                  if(e.source!==document.querySelector('iframe').contentWindow || e.origin!==location.origin)return;
                  if(e.data.type==='home-assistant/subscribe-properties'){
                    kiosk=e.data.kioskMode===true;
                    e.source.postMessage(properties,location.origin);
                  }
                });
                </script></body>""",
                ),
            )
            page.goto(url + "/native-panel-test")
            frame = page.frame_locator("iframe")
            expect(frame.locator("#gallery-title")).to_have_text(
                "All cameras · 2026-11-11"
            )
            expect(frame.locator("header")).not_to_be_visible()
            expect(frame.locator("#native-latest-url")).to_have_value(
                "/app/local_camera_daily_merger/dashboard/latest"
            )
            page.wait_for_function("() => kiosk")
            frame.get_by_role("button", name="Play all", exact=True).click()
            page.wait_for_function(
                "() => [...document.querySelector('iframe').contentDocument.querySelectorAll('#gallery-grid video')].every(v=>v.readyState>=2 && !v.paused)"
            )
            frame.get_by_role("button", name="Pause all", exact=True).click()
            frame.locator("#gallery-day").fill("2026-11-12")
            frame.locator("#gallery-day").press("Tab")
            # Repeated properties (e.g. resize) must preserve the user's date.
            page.evaluate(
                "document.querySelector('iframe').contentWindow.postMessage(properties,location.origin)"
            )
            expect(frame.locator("#gallery-title")).to_have_text(
                "All cameras · 2026-11-12"
            )
            page.evaluate(
                "document.querySelector('iframe').contentWindow.postMessage({...properties,route:{prefix:'https://invalid.example',path:'/dashboard/latest'}},location.origin)"
            )
            expect(frame.locator("#gallery-title")).to_have_text(
                "All cameras · 2026-11-12"
            )
            # A same-origin child cannot impersonate the HA parent.
            frame.locator("body").evaluate(
                "body => window.dispatchEvent(new MessageEvent('message',{origin:location.origin,source:window,data:{type:'home-assistant/properties',route:{prefix:'/app/local_camera_daily_merger',path:'/dashboard/latest'}}}))"
            )
            expect(frame.locator("#gallery-title")).to_have_text(
                "All cameras · 2026-11-12"
            )
            page.evaluate(
                "properties.route.path='/dashboard/latest'; document.querySelector('iframe').contentWindow.postMessage(properties,location.origin)"
            )
            expect(frame.locator("#gallery-title")).to_have_text("Latest per camera")
            expect(frame.locator("#gallery-grid video")).to_have_count(2)
            # Actual nested card dimensions, independent of the physical screen.
            page.wait_for_function(
                "() => {const g=document.querySelector('iframe').contentDocument.querySelector('#gallery-grid'); return g.dataset.fitColumns && g.getBoundingClientRect().bottom <= 900;}"
            )
            page.locator("iframe").evaluate("f=>{f.width='720';f.height='430';}")
            page.wait_for_function(
                "() => {const doc=document.querySelector('iframe').contentDocument,g=doc.querySelector('#gallery-grid');return g.getBoundingClientRect().right<=720 && g.getBoundingClientRect().bottom<=430;}"
            )
            # Four equal windows, shared resizing and persisted layout preferences.
            published(store, root, "c", "2026-11-12", body=body, duration=5.0)
            published(store, root, "d", "2026-11-12", body=body, duration=5.0)
            page.set_viewport_size({"width": 1280, "height": 1000})
            page.goto(url)
            expect(page.locator("#gallery-grid video")).to_have_count(4)

            # Auto-fit maximizes common image size and keeps every tile visible.
            def assert_auto_fit(width, height):
                page.set_viewport_size({"width": width, "height": height})
                page.wait_for_function(
                    "() => {const g=document.querySelector('#gallery-grid'),b=g.getBoundingClientRect();return !galleryBusy && g.dataset.fitViewportWidth===String(innerWidth) && g.dataset.fitViewportHeight===String(innerHeight) && b.bottom<=innerHeight && b.right<=innerWidth;}"
                )
                tiles = [
                    tile.bounding_box() for tile in page.locator(".camera-tile").all()
                ]
                assert len(tiles) == 4
                assert (
                    max(t["width"] for t in tiles) - min(t["width"] for t in tiles) < 1
                )
                assert (
                    max(t["height"] for t in tiles) - min(t["height"] for t in tiles)
                    < 1
                )
                expect(page.locator("#dashboard-help")).not_to_be_visible()
                expect(page.locator(".dashboard-setup")).not_to_be_visible()
                actual = page.locator(".video-viewport").first.bounding_box()["width"]
                assert (
                    page.locator("#gallery-grid").get_attribute("data-fit-columns")
                    == "2"
                )
                assert (
                    page.locator("#gallery-grid").get_attribute("data-fit-rows") == "2"
                )
                assert page.evaluate(
                    "document.documentElement.scrollHeight<=innerHeight && document.documentElement.scrollWidth<=innerWidth"
                )
                for bar in page.locator(".video-controls").all():
                    assert bar.evaluate(
                        "b=>b.scrollWidth<=b.clientWidth && b.scrollHeight<=b.clientHeight"
                    )
                    bounds = bar.bounding_box()
                    tile_bounds = (
                        bar.locator("xpath=..").locator("xpath=..").bounding_box()
                    )
                    assert (
                        bounds["y"] + bounds["height"]
                        <= tile_bounds["y"] + tile_bounds["height"] + 1
                    )
                    assert bounds["y"] + bounds["height"] <= height + 1
                    for control in bar.locator("button,a,input").all():
                        box = control.bounding_box()
                        assert box["x"] >= bounds["x"] - 1
                        assert box["y"] >= bounds["y"] - 1
                        assert (
                            box["x"] + box["width"] <= bounds["x"] + bounds["width"] + 1
                        )
                        assert (
                            box["y"] + box["height"]
                            <= bounds["y"] + bounds["height"] + 1
                        )
                assert actual > 0
                for tile in tiles:
                    assert tile["x"] >= 0 and tile["y"] >= 0
                    assert tile["x"] + tile["width"] <= width + 1
                    assert tile["y"] + tile["height"] <= height + 1

            page.locator("#gallery-grid video").first.evaluate(
                "v=>window.autoFitPlayer=v"
            )
            for dimensions in [
                (1280, 1000),
                (1920, 1080),
                (844, 390),
                (390, 844),
                (800, 600),
            ]:
                assert_auto_fit(*dimensions)
            assert page.evaluate(
                "window.autoFitPlayer===document.querySelector('#gallery-grid video')"
            )
            page.get_by_role("button", name="All cameras by day", exact=True).click()
            expect(page.locator("#gallery-grid video")).to_have_count(4)
            assert_auto_fit(390, 844)
            assert_auto_fit(844, 390)
            page.get_by_role("button", name="Latest per camera", exact=True).click()
            expect(page.locator("#gallery-grid video")).to_have_count(4)
            assert_auto_fit(800, 600)
            page.screenshot(path="work/auto-fit-wall.png", full_page=True)
            # Camera-list mutations trigger fitting without a window resize.
            page.evaluate(
                "() => {const g=document.querySelector('#gallery-grid'),tile=g.firstElementChild; for(let i=0;i<2;i++){const extra=tile.cloneNode(true);extra.dataset.syntheticExtra='1';g.append(extra);}}"
            )
            page.wait_for_function(
                "() => {const g=document.querySelector('#gallery-grid');return g.dataset.fitColumns==='2' && g.dataset.fitRows==='3' && g.getBoundingClientRect().bottom<=innerHeight;}"
            )
            page.evaluate(
                "document.querySelectorAll('[data-synthetic-extra]').forEach(tile=>tile.remove())"
            )
            assert_auto_fit(1280, 1000)
            page.locator(".layout-settings summary").click()
            assert_auto_fit(1280, 1000)
            page.get_by_label("Columns", exact=True).select_option("2")

            def equal_windows():
                # A date/view fetch can replace all tiles between Playwright calls.
                # Wait for completion and read geometry in one browser task.
                page.wait_for_function(
                    "() => !galleryBusy && document.querySelectorAll('.camera-tile').length===4"
                )
                boxes = page.locator(".camera-tile").evaluate_all(
                    "tiles=>tiles.map(tile=>{const {x,y,width,height}=tile.getBoundingClientRect();return {x,y,width,height};})"
                )
                assert len(boxes) == 4
                assert (
                    max(b["width"] for b in boxes) - min(b["width"] for b in boxes) < 1
                )
                assert (
                    max(b["height"] for b in boxes) - min(b["height"] for b in boxes)
                    < 1
                )
                assert boxes[0]["y"] == boxes[1]["y"]
                assert boxes[2]["y"] == boxes[3]["y"] > boxes[0]["y"]
                return boxes

            page.wait_for_function(
                "() => !document.body.classList.contains('auto-fit') && document.querySelector('#gallery-grid').style.width==='100%'"
            )
            before = equal_windows()
            page.get_by_role("button", name="Play all", exact=True).click()
            page.wait_for_function(
                "() => [...document.querySelectorAll('#gallery-grid video')].every(v=>v.readyState>=2 && !v.paused)"
            )
            first_zoom = page.get_by_role("button", name="a: Zoom in", exact=True)
            first_zoom.click()
            first_zoom.click()
            page.locator("#gallery-grid video").first.evaluate(
                "v=>window.layoutPlayer=v"
            )
            page.get_by_role("slider", name="Window size", exact=False).fill("70")
            page.get_by_role("slider", name="Window size", exact=False).press("Tab")
            after = equal_windows()
            expect(
                page.get_by_role("button", name="a: Reset zoom", exact=True)
            ).to_have_text("2×")
            assert after[0]["width"] < before[0]["width"]
            assert page.evaluate(
                "window.layoutPlayer===document.querySelector('#gallery-grid video') && !window.layoutPlayer.paused"
            )
            page.screenshot(path="work/layout-2x2.png", full_page=True)
            page.reload()
            expect(page.locator("#gallery-grid video")).to_have_count(4)
            expect(page.locator("#layout-columns")).to_have_value("2")
            expect(page.locator("#layout-size")).to_have_value("70")
            equal_windows()
            page.get_by_role("button", name="All cameras by day", exact=True).click()
            expect(page.locator("#gallery-grid video")).to_have_count(4)
            equal_windows()
            page.set_viewport_size({"width": 390, "height": 844})
            equal_windows()
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.locator(".layout-settings summary").click()
            page.get_by_label("Columns", exact=True).select_option("4")
            page.get_by_role("slider", name="Window size", exact=False).fill("50")
            page.get_by_role("slider", name="Window size", exact=False).press("Tab")
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
            page.get_by_role("button", name="Reset layout", exact=True).click()
            expect(page.locator("#layout-columns")).to_have_value("auto")
            expect(page.locator("#layout-size")).to_have_value("100")
            page.evaluate(
                "localStorage.setItem('camera-daily-merger.layout.v3',JSON.stringify({columns:'999',size:-10}))"
            )
            page.reload()
            expect(page.locator("#layout-columns")).to_have_value("auto")
            expect(page.locator("#layout-size")).to_have_value("100")
            page.add_init_script(
                "Object.defineProperty(window,'localStorage',{get(){throw new DOMException('blocked','SecurityError')}})"
            )
            page.reload()
            expect(page.locator("#gallery-grid video")).to_have_count(4)
            page.locator(".layout-settings summary").click()
            page.get_by_label("Columns", exact=True).select_option("2")
            expect(page.locator("#layout-status")).to_contain_text(
                "storage unavailable"
            )
            equal_windows()
            assert not errors, errors
            browser.close()
            print(
                "PASS latest per camera, shared day, missing camera, play/pause all, non-disruptive refresh, mobile/embedded views, external controls, seeking, audio, fullscreen, zoom/pan, equal 2x2 sizing, browser preferences and automatic viewport fitting"
            )


if __name__ == "__main__":
    main()
