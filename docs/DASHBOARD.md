# Native Home Assistant dashboard

Available in **0.1.0-alpha.10**. No recording copies, JavaScript installation,
custom resources or YAML are required.

1. Update and restart the add-on, then open its web UI through Home Assistant.
2. Open **Dashboard setup**. The app displays two installation-specific URLs.
3. Edit your normal dashboard, select **Add card > Webpage**, and enter the
   **Latest per camera** URL in the graphical URL field. Adjust the card aspect
   ratio to provide enough height for the camera grid.
4. Optionally add another Webpage card with the **All cameras by day** URL.

The stable URLs normally look like `/app/ADDON_SLUG/dashboard/latest` and
`/app/ADDON_SLUG/dashboard/day`. Use the detected links for your installation;
older Home Assistant installations can use a different app route prefix.
Append `/YYYY-MM-DD` to the day URL to open a particular date.
Never paste `/api/hassio_ingress/...` session URLs into a dashboard.

Home Assistant's own app panel creates and renews the ingress session. The
add-on uses the supported `home-assistant/subscribe-properties` message protocol
to read the route and request compact kiosk mode inside the Webpage card.
Messages must come from the same-origin parent window. No new public port,
Supervisor permission, parent DOM access or authentication bypass is introduced.
The existing administrator access policy still applies. This requires a Home
Assistant frontend supporting ingress properties and kiosk mode. The protocol
was checked against upstream `src/panels/app/ha-panel-app.ts`; actual Home
Assistant dashboard acceptance remains an owner-device test.

Latest shows each camera's latest published day; dates may differ. The day view
shows one common date with placeholders for missing exports. The date selector
and previous/next buttons browse published days. Videos play directly from
existing exports with `preload=none`; nothing is copied for the dashboard.
Visible views refresh every 60 seconds, preserving active playback until paused
or explicitly refreshed. Play all/Pause all control up to six streams. Motion
clips have gaps removed, so playback is not synchronized to real-world time.
H.265 browser support varies.

If links are blank, open the add-on through Home Assistant rather than a direct
server address. If the dashboard shows an access error, first check that the app
is running and opens normally for the same user. If a video cannot play, check
codec support and the six-stream limit. Choose a taller card if controls are cut
off. The previous custom Lovelace resource remains served for existing alpha.9
installations, but is unnecessary for the native setup.

## Surveillance view (alpha.11)

The add-on opens as a full-width camera wall. Camera tiles sit directly beside
each other, with only the camera name and export date above each image. Desktop
columns adapt to available width; narrow screens retain two columns. Processing
and installation remain accessible through their separate controls.

Each tile has playback controls **below** the image: play/pause, seek, audio,
zoom out/in, reset and fullscreen where supported. Native video controls are
disabled in the camera wall so their overlay cannot hide recorded details.
Fullscreen expands the complete player, keeping the controls outside the image.
The separate processing/single-camera view retains its original native player.

Use **+ / −** for digital zoom from 1× to 4× in half steps; the magnification
button resets to 1×. Drag a zoomed image with a mouse or finger to inspect its
edges. Zoom is local to that player and resets when a view is rebuilt. It does
not move the physical camera, add detail, copy recordings or transcode media.
Only actual playback/export errors add diagnostic text to a tile. The date always
identifies the displayed export, including a retained prior successful export.

## Adjustable layout (alpha.12)

Open **Layout** above the camera wall. Choose **2 columns** for four cameras in a
2×2 arrangement, or choose automatic, one, three or four columns. All configured
cameras remain present; additional cameras continue onto further rows. Fixed
column choices also apply on mobile and inside the Home Assistant dashboard.

Use **Window size** (50–100%) to resize every camera window together. The value
sets the wall's width relative to the available space; 100% fills that space.
All tiles keep equal widths and heights, with the same 16:9 video viewport and
external controls. Videos with a different aspect ratio are letterboxed. Missing
exports retain equal-sized tiles. Long camera names are shortened visually.
Layout changes preserve the existing players, playback positions and zoom.

Preferences apply to latest/day and embedded views and are saved for this browser
on the same Home Assistant origin. A different device/browser has its own settings.
Only column count and size are stored, never recordings or credentials. If browser
storage is blocked, changes work for the current page and a status explains that
they cannot persist. **Reset layout** restores automatic columns and 100% width.
The six-simultaneous-stream limit is unchanged.

## Automatic fit to the available display (alpha.13)

**Automatic · fit all cameras** is now the default. It reads the actual browser
or embedded card viewport, subtracts navigation/toolbar space, and selects the
row/column arrangement with the largest equal 16:9 camera images that fit both
width and height. The device's physical screen resolution is not used: a dashboard
card can be much smaller than that screen. The wall adapts to window resizing,
rotation, browser viewport changes, changed camera counts and expanded controls.
Playback elements and zoom remain intact. Missing exports count as camera tiles.

Labels and playback controls stay outside each image. In automatic mode controls
use a fixed-height row; swipe/scroll that row horizontally on small tiles to reach
all buttons. The normal six-stream limit remains. Very short cards or very large
camera lists can lack even enough room for labels and controls; the Layout status
then asks for a taller panel rather than hiding cameras or controls.

Automatic mode controls size itself, so the manual size slider is disabled. Manual
1–4-column selection and shared sizing remain available. **Reset layout** restores
automatic fitting. Alpha.13 starts with automatic fitting even if alpha.12 had a
saved layout; subsequent choices use the new browser preference version. No screen
permission, new media processing, file copy or server-side polling is required.
