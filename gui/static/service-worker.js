/**
 * LNDg Service Worker – Phase-6F PWA offline support
 *
 * Strategy:
 *  - Static assets: cache-first with network fallback
 *  - API calls (/api/): network-first, no caching (live data)
 *  - Navigation (HTML pages): network-first, offline fallback to cached shell
 */

const CACHE_NAME = 'lndg-v1';
const OFFLINE_URL = '/';

const STATIC_ASSETS = [
  '/static/w3style.css',
  '/static/api.js',
  '/static/helpers.js',
  '/static/sort_table.js',
  '/static/charts.js',
  '/static/favicon.ico',
  '/static/manifest.json',
];

// ── Install: pre-cache static assets ─────────────────────────────────────────
self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(STATIC_ASSETS).catch(function(err) {
        console.warn('[SW] Pre-cache partial failure:', err);
      });
    })
  );
  self.skipWaiting();
});

// ── Activate: clean up old caches ────────────────────────────────────────────
self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(key) { return key !== CACHE_NAME; })
            .map(function(key) { return caches.delete(key); })
      );
    })
  );
  self.clients.claim();
});

// ── Fetch: routing strategy ───────────────────────────────────────────────────
self.addEventListener('fetch', function(event) {
  var url = new URL(event.request.url);

  // Skip non-GET and cross-origin requests
  if (event.request.method !== 'GET' || url.origin !== self.location.origin) {
    return;
  }

  // API calls: network-only (never cache live data).
  // Early return without event.respondWith() delegates to default browser fetch behavior.
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // SSE events stream: network-only, never cache streaming connections
  if (url.pathname.startsWith('/api/v2/events/')) {
    return;
  }

  // Static assets: cache-first
  if (url.pathname.startsWith('/static/')) {
    event.respondWith(
      caches.match(event.request).then(function(cached) {
        if (cached) {
          return cached;
        }
        return fetch(event.request).then(function(response) {
          if (response && response.status === 200) {
            var cloned = response.clone();
            caches.open(CACHE_NAME).then(function(cache) {
              cache.put(event.request, cloned);
            });
          }
          return response;
        });
      })
    );
    return;
  }

  // Navigation (HTML): network-first with offline fallback
  event.respondWith(
    fetch(event.request).then(function(response) {
      if (response && response.status === 200) {
        var cloned = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, cloned);
        });
      }
      return response;
    }).catch(function() {
      return caches.match(event.request).then(function(cached) {
        return cached || caches.match(OFFLINE_URL);
      });
    })
  );
});
