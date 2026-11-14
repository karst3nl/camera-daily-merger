# Home Assistant dashboard and multi-camera views

Available in add-on **0.1.0-alpha.9**. The app now opens on **Latest per camera**.
Each camera shows its most recent published daily export, with its actual date;
dates can differ when a camera has no newer recordings. **All cameras by day**
shows exactly one selected calendar date, with placeholders for missing exports.
It never substitutes a different camera/date to fill a missing tile. The last
successful export remains viewable during a failed rebuild, labeled accordingly.

The view refreshes every 60 seconds while visible. New results wait until active
playback is paused or explicitly refreshed. Videos have preload=none and do not
autoplay. Play all/Pause all operate the players together; they do not synchronize
real-world recording times because motion-free gaps have been removed. Up to six
streams can be served simultaneously across clients/cards. Larger camera lists
remain browsable and playable individually; browser H.265 support still varies.

## 1. Install the local Lovelace resource

1. Upgrade/restart the add-on and refresh its web UI. Verify alpha.9 in the banner.
2. Click **Dashboard setup**, then **Download dashboard card**.
3. Using File Editor, Studio Code Server or another local file-management method,
   create `/config/www` if needed and copy the downloaded file there as
   `/config/www/camera-daily-merger-card.js`. This is the Home Assistant config
   directory, not the add-on's private /data directory.
4. In Home Assistant, open **Settings > Dashboards > Resources** (advanced mode
   may need to be enabled in your profile). Add this resource once:

   ```yaml
   url: /local/camera-daily-merger-card.js?v=0.1.0-alpha.9
   type: module
   ```

5. Reload the browser/dashboard. When upgrading the card later, replace the local
   JS file and change the resource's version query to avoid a cached old copy.

No HACS package or internet-hosted runtime resource is required. The resource
contains no session token. No new HA configuration-directory mount, public port
or Supervisor API permission is granted to the add-on.

## 2. Add a latest-per-camera card

Edit the desired dashboard, add a **Manual** card and use:

```yaml
type: custom:camera-daily-merger-card
addon: ADDON_SLUG
title: Latest daily recordings
view: latest
height: 640
```

Replace ADDON_SLUG with the installed app's exact slug, including the repository
prefix, for example `local_camera_daily_merger` for a local installation. It is
shown in the app's HA URL or installation information. Do not use an ingress token
or derive a slug from camera names. The card resolves the real ingress URL through
the authenticated Home Assistant API. Height can be 300..1600 pixels.

## 3. Add the shared-day card

```yaml
type: custom:camera-daily-merger-card
addon: ADDON_SLUG
title: All cameras by day
view: day
height: 900
```

With no date configured, the view follows the newest published date across
cameras. Its date selector and previous/next controls browse exports (up to 366
recent dates in navigation; any explicit historical date can be entered).
To pin one date, add `date: '2026-11-12'`. A manually selected date remains pinned
within that iframe until navigation/reload; changing it does not edit dashboard
YAML. **All cameras on this day** from a latest tile opens the shared-day view;
**Latest per camera** returns from it in embedded mode.

## Authentication and compatibility

The card requests an ingress session through the existing authenticated `hass`
WebSocket connection, sets the standard scoped ingress cookie and embeds only a
same-origin `/api/hassio_ingress/.../` URL returned by HA. The session is kept in
memory/the standard cookie, never dashboard YAML or localStorage. It validates
every minute while visible and when the dashboard becomes visible; an expired
session is recreated and the iframe reloaded. Valid sessions do not reload active
playback. Disconnecting the card releases its timer/listener. Permission errors do
not trigger a weaker authentication path or a public video URL.

The default app policy requires an administrator. Non-admin user access is not
enabled by this feature; keep the app's existing HA access policy. The card uses
current `supervisor/ingress/info`, `/session`, `/validate_session` WS commands, with
an older `supervisor/api` fallback **only** for `unknown_command`. The current and
older contracts were checked against upstream frontend/core source and exercised
with a mocked HA bridge; actual owner dashboard/session behavior still requires
verification. Direct iframe cards containing copied session URLs are not supported.

Source references used for interoperability:

- Current frontend, revision 2706bd89a12c96e4df0268f2b0584c10e557ce1b,
  `src/data/hassio/ingress.ts`.
- Older frontend, revision 0fe80ef5f991, same file and
  `src/data/supervisor/supervisor.ts`.
- Current Core `homeassistant/components/hassio/websocket_api.py` and Supervisor
  session handling (15-minute session lifetime, extended by validation).

## Troubleshooting

- **Custom element doesn't exist**: check the local JS path, module resource type
  and browser cache/reload. The www folder maps to /local in HA.
- **Cannot open app ingress**: verify the full app slug, running app, HA connection
  and user permissions. Open the app normally once to check access.
- **Empty camera tile**: verify that camera has a published successful export.
  A pending/failed job without a prior export is not a playable result.
- **Latest export unavailable**: the metadata exists but the managed output is
  missing, unsafe or has a changed size; reconcile/reprocess and check NAS access.
- **Playback error**: check browser codec support, simultaneous-stream limit and
  whether a retry published a newer version. Refresh or use the download link.
- **Different camera dates in latest view**: expected. Use the shared-day view to
  compare one exact date across cameras.
