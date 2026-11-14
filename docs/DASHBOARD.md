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
