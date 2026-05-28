/* HiHi Labs — Service Worker */
const CACHE_VER    = 'hl-v3';
const STATIC_CACHE = `${CACHE_VER}-static`;
const API_CACHE    = `${CACHE_VER}-api`;

const PRECACHE_URLS = ['/offline/'];

const CDN_ORIGINS = [
  'fonts.googleapis.com',
  'fonts.gstatic.com',
  'cdnjs.cloudflare.com',
];

const SKIP_CACHE = ['/admin/', '/login/', '/logout/'];

// ── Install ───────────────────────────────────────────────────────────────────
self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(STATIC_CACHE)
      .then(c => c.addAll(PRECACHE_URLS).catch(() => {}))
      .then(() => self.skipWaiting())
  );
});

// ── Activate ─────────────────────────────────────────────────────────────────
self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys.filter(k => k.startsWith('hl-') && !k.startsWith(CACHE_VER))
            .map(k => caches.delete(k))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch ─────────────────────────────────────────────────────────────────────
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET') return;
  if (SKIP_CACHE.some(p => url.pathname.startsWith(p))) return;

  // CDN assets — cache-first
  if (CDN_ORIGINS.some(o => url.hostname.includes(o))) {
    e.respondWith(cacheFirst(e.request, STATIC_CACHE));
    return;
  }

  // Static files — cache-first
  if (url.pathname.startsWith('/static/')) {
    e.respondWith(cacheFirst(e.request, STATIC_CACHE));
    return;
  }

  // API / streaming — network only (never cache SSE/streams)
  if (url.pathname.includes('/stream/') || url.pathname.includes('/send/')) return;

  // API calls — network-first
  if (url.pathname.startsWith('/ai/') && e.request.headers.get('accept')?.includes('application/json')) {
    e.respondWith(networkFirst(e.request, API_CACHE, 8000));
    return;
  }

  // HTML pages — network-first, offline fallback
  if (e.request.headers.get('accept')?.includes('text/html')) {
    e.respondWith(
      fetch(e.request)
        .catch(() => caches.match('/offline/').then(r => r || new Response('Offline', {status: 503})))
    );
    return;
  }
});

// ── Push ─────────────────────────────────────────────────────────────────────
self.addEventListener('push', e => {
  let data = {};
  try { data = e.data?.json() || {}; } catch {}

  const title = data.title || 'HiHi Labs';
  const body  = data.body  || 'You have a new notification.';
  const tag   = data.tag   || 'hl-default';
  const url   = data.url   || '/';
  const icon  = data.icon  || '/static/icons/icon-192.png';
  const badge = data.badge || '/static/icons/badge-72.png';

  e.waitUntil(
    self.registration.showNotification(title, {
      body, tag, icon, badge,
      requireInteraction: data.urgent || false,
      data: { url },
      vibrate: data.urgent ? [200, 100, 200] : [100],
    })
  );
});

self.addEventListener('notificationclick', e => {
  e.notification.close();
  const url = e.notification.data?.url || '/';
  e.waitUntil(
    clients.matchAll({type: 'window', includeUncontrolled: true}).then(cs => {
      const existing = cs.find(c => c.url.includes(self.location.origin));
      if (existing) { existing.focus(); existing.navigate(url); }
      else           { clients.openWindow(url); }
    })
  );
});

// ── Helpers ───────────────────────────────────────────────────────────────────
async function cacheFirst(req, cacheName) {
  const cached = await caches.match(req);
  if (cached) return cached;
  try {
    const resp = await fetch(req);
    if (resp.ok) { const c = await caches.open(cacheName); c.put(req, resp.clone()); }
    return resp;
  } catch { return new Response('', {status: 503}); }
}

async function networkFirst(req, cacheName, timeoutMs = 5000) {
  const ctrl  = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), timeoutMs);
  try {
    const resp = await fetch(req, {signal: ctrl.signal});
    clearTimeout(timer);
    if (resp.ok) { const c = await caches.open(cacheName); c.put(req, resp.clone()); }
    return resp;
  } catch {
    clearTimeout(timer);
    return (await caches.match(req)) || new Response(JSON.stringify({error:'offline'}), {
      status: 503, headers: {'Content-Type': 'application/json'},
    });
  }
}
