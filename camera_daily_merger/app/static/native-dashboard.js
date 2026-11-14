'use strict';
// Home Assistant's documented ingress properties protocol. No parent DOM access.
(() => {
  if (window.parent === window) return;
  let lastPath = null, kiosk = false;
  const send = value => window.parent.postMessage(value, location.origin);
  const subscribe = () => send({type:'home-assistant/subscribe-properties', kioskMode:kiosk});
  window.addEventListener('message', event => {
    if (event.source !== window.parent || event.origin !== location.origin) return;
    const data = event.data;
    if (!data || data.type !== 'home-assistant/properties') return;
    const route = data.route;
    if (!route || typeof route.prefix !== 'string' || typeof route.path !== 'string') return;
    if (!/^\/(?:app\/[a-z0-9_]+|hassio\/ingress\/[a-z0-9_]+|[a-z0-9_-]+)$/.test(route.prefix)) return;
    for (const view of ['latest','day']) document.getElementById(`native-${view}-url`).value = `${route.prefix}/dashboard/${view}`;
    document.getElementById('native-dashboard-status').textContent = 'Use these stable Home Assistant URLs. They contain no session token.';
    if (route.path === lastPath) return;
    lastPath = route.path;
    const match = /^\/dashboard\/(latest|day)(?:\/(\d{4}-\d{2}-\d{2}))?\/?$/.exec(route.path);
    if (!match || (match[1] === 'latest' && match[2])) return;
    const day = match[2] || null;
    if (day && (Number.isNaN(Date.parse(day)) || new Date(day).toISOString().slice(0,10) !== day)) return;
    nativeDashboardView(match[1], day);
    if (!kiosk) { kiosk=true;subscribe(); }
  });
  window.addEventListener('pagehide', () => send({type:'home-assistant/unsubscribe-properties'}));
  subscribe();
})();
