// HokieMacros service worker: works offline, stays fresh online.
const V = 'hm-v1';
const SHELL = ['./', './index.html', './manifest.webmanifest', './icons/icon-192.png', './icons/apple-touch-icon.png', './campus-clean.webp'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(V).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== V).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

const put = (req, res) => { if (res && res.ok) { const c = res.clone(); caches.open(V).then(x => x.put(req, c)); } return res; };
// Network first, cached copy when offline (the app itself, menus and hours)
const networkFirst = req => fetch(req).then(r => put(req, r)).catch(() => caches.match(req, { ignoreSearch: true }));
// Cached copy right away, refreshed in the background (food database, fonts)
const staleWhileRevalidate = req => caches.match(req).then(hit => { const net = fetch(req).then(r => put(req, r)).catch(() => hit); return hit || net; });
// Cached forever once fetched (map tiles and images never change)
const cacheFirst = req => caches.match(req).then(hit => hit || fetch(req).then(r => put(req, r)));

self.addEventListener('fetch', e => {
  const req = e.request; if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin === location.origin) {
    if (req.mode === 'navigate' || url.pathname.endsWith('/') || url.pathname.endsWith('.html') || url.pathname.endsWith('dining.json')) return e.respondWith(networkFirst(req));
    if (/\/(t1|t2|icons)\/|\.(webp|jpg|png)$/.test(url.pathname) || url.pathname.endsWith('walk.json')) return e.respondWith(cacheFirst(req));
    return e.respondWith(staleWhileRevalidate(req));
  }
  if (/fonts\.(googleapis|gstatic)\.com$/.test(url.hostname)) return e.respondWith(staleWhileRevalidate(req));
  // everything else (the price/occupancy script) goes straight to the network
});
