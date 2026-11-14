"""Mock HA WebSocket/session contract with real embedded gallery and playback."""

from pathlib import Path
import argparse
import tempfile
import subprocess
from urllib.parse import urlsplit

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
        store = Store(root / "jobs.sqlite")
        settings = Settings(
            root=root, cameras={"a": "input"}, timestamp_pattern=r"(?P<start>.+)\.mp4"
        )
        clip = root / "synthetic.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-v",
                "error",
                "-f",
                "lavfi",
                "-i",
                "color=blue:size=64x64:rate=10:duration=1",
                "-c:v",
                "libx264",
                "-threads",
                "1",
                str(clip),
            ],
            check=True,
        )
        published(store, root, "a", "2026-11-12", body=clip.read_bytes(), duration=1.0)
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
            context = browser.new_context(viewport={"width": 1100, "height": 900})
            page = context.new_page()
            base = f"http://127.0.0.1:{server.server_address[1]}"
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))

            def proxy(route):
                path = urlsplit(route.request.url).path
                suffix = path.split("/api/hassio_ingress/mock_ingress_token/", 1)[-1]
                response = route.fetch(
                    url=base
                    + "/"
                    + suffix
                    + (
                        "?" + urlsplit(route.request.url).query
                        if urlsplit(route.request.url).query
                        else ""
                    )
                )
                route.fulfill(response=response)

            page.route("**/api/hassio_ingress/mock_ingress_token/**", proxy)
            page.route(
                "**/dashboard-test",
                lambda route: route.fulfill(
                    content_type="text/html",
                    body='<html><body><script src="/dashboard-card.js"></script></body></html>',
                ),
            )
            page.goto(base + "/dashboard-test")
            page.wait_for_function(
                "() => !!customElements.get('camera-daily-merger-card')"
            )
            async_setup = """({legacy=false,denied=false,external=false,view='latest',date=null})=>{
              window.calls=[];window.card=document.createElement('camera-daily-merger-card');
              card.setConfig({addon:'local_camera_daily_merger',view,...(date?{date}:{}),height:640});
              card.hass={user:{id:'test-user'},connection:{},callWS:async request=>{
                calls.push(request);
                if(denied)throw {code:'unauthorized'};
                if(legacy && request.type!=='supervisor/api')throw {code:'unknown_command'};
                if(request.type==='supervisor/ingress/info' || request.endpoint?.endsWith('/info'))return {state:'started',ingress_url:external?'https://outside.invalid/api/hassio_ingress/token':'/api/hassio_ingress/mock_ingress_token'};
                if(request.type==='supervisor/ingress/validate_session' || request.endpoint==='/ingress/validate_session')return {};
                return {session:'mock_session_value_'+calls.filter(c=>c.type==='supervisor/ingress/session' || c.endpoint==='/ingress/session').length};
              }};document.body.append(card);
            }"""
            page.evaluate(async_setup, {})
            frame = page.frame_locator("camera-daily-merger-card iframe")
            expect(frame.locator("#gallery-title")).to_have_text("Latest per camera")
            expect(frame.locator(".camera-tile h3")).to_have_text("a")
            frame.get_by_role("button", name="Play all", exact=True).click()
            frame.locator("#gallery-grid video").evaluate("(video)=>video.play()")
            assert frame.locator("#gallery-grid video").evaluate(
                "(video)=>video.readyState>=2"
            )
            frame.locator("#gallery-grid video").evaluate(
                '(video)=>video.dataset.marker="stable"'
            )
            assert page.evaluate("calls.some(c=>c.type==='supervisor/ingress/session')")
            cookies = context.cookies()
            assert any(
                c["name"] == "ingress_session"
                and c["path"] == "/api/hassio_ingress/"
                and c["sameSite"] == "Strict"
                for c in cookies
            )
            src = page.locator("camera-daily-merger-card iframe").get_attribute("src")
            page.evaluate("() => card._authenticate()")
            assert (
                page.locator("camera-daily-merger-card iframe").get_attribute("src")
                == src
            )
            assert page.evaluate(
                "calls.some(c=>c.type==='supervisor/ingress/validate_session')"
            )
            assert (
                frame.locator("#gallery-grid video").get_attribute("data-marker")
                == "stable"
            )
            page.evaluate(
                """async()=>{const original=card._hass.callWS;card._hass.callWS=async request=>{if(request.type==='supervisor/ingress/validate_session')throw {code:'invalid_session'};return original(request);};await card._authenticate();card._hass.callWS=original;}"""
            )
            expect(frame.locator("#gallery-grid video")).not_to_have_attribute(
                "data-marker", "stable"
            )
            assert any(
                c["name"] == "ingress_session" and c["value"].endswith("_2")
                for c in context.cookies()
            )
            frame.get_by_role("button", name="All cameras on this day").click()
            expect(frame.locator("#gallery-title")).to_have_text(
                "All cameras · 2026-11-12"
            )
            frame.get_by_role("button", name="Latest per camera", exact=True).click()
            expect(frame.locator("#gallery-title")).to_have_text("Latest per camera")
            page.screenshot(path="work/dashboard-card-desktop.png", full_page=True)
            page.set_viewport_size({"width": 390, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
            page.screenshot(path="work/dashboard-card-mobile.png", full_page=True)
            page.evaluate("() => card.remove()")
            page.evaluate(
                async_setup, {"legacy": True, "view": "day", "date": "2026-11-12"}
            )
            expect(
                page.frame_locator("camera-daily-merger-card iframe").locator(
                    "#gallery-title"
                )
            ).to_have_text("All cameras · 2026-11-12")
            assert page.evaluate(
                "calls.some(c=>c.type==='supervisor/api' && c.endpoint==='/ingress/session')"
            )
            page.evaluate("() => card.remove()")
            page.evaluate(async_setup, {"denied": True})
            expect(page.locator("camera-daily-merger-card .message")).to_contain_text(
                "Cannot open app ingress"
            )
            assert (
                page.locator("camera-daily-merger-card iframe").get_attribute("src")
                is None
            )
            assert page.evaluate("calls.length===1")
            page.evaluate("() => card.remove()")
            page.evaluate(async_setup, {"external": True})
            expect(page.locator("camera-daily-merger-card .message")).to_contain_text(
                "Cannot open app ingress"
            )
            assert (
                page.locator("camera-daily-merger-card iframe").get_attribute("src")
                is None
            )
            assert page.evaluate(
                "!calls.some(c=>c.type==='supervisor/ingress/session')"
            )
            invalid = page.evaluate(
                """()=>{try{const item=document.createElement('camera-daily-merger-card');item.setConfig({addon:'../wrong'});return false;}catch{return true;}}"""
            )
            assert invalid
            assert not errors, errors
            browser.close()
            print(
                "PASS modern/legacy HA session contract, protected gallery iframe, latest/day, session validation, denied access, external URL rejection, mobile layout"
            )


if __name__ == "__main__":
    main()
