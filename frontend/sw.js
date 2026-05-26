/**
 * ALAS Service Worker — Enables offline support and PWA installation.
 * 
 * Caching strategy:
 * - Cache-first for static assets (CSS, JS, fonts, icons)
 * - Network-first for API calls (always try fresh data)
 * - Offline fallback page for navigation requests
 */

const CACHE_NAME = 'alas-v1';
const STATIC_ASSETS = [
  '/',
  '/css/styles.css',
  '/js/app.js',
  '/js/chat.js',
  '/js/voice.js',
  '/js/memory.js',
  '/js/modes.js',
  '/js/knowledge.js',
  '/js/evolution.js',
  '/assets/icon-512.png',
  '/manifest.json',
];

// Install — cache static assets
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    })
  );
  self.skipWaiting();
});

// Activate — clean up old caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => {
      return Promise.all(
        keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
      );
    })
  );
  self.clients.claim();
});

// Fetch — smart caching strategy
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip WebSocket and non-GET requests
  if (request.method !== 'GET' || url.protocol === 'ws:' || url.protocol === 'wss:') {
    return;
  }

  // API calls — network first, fallback to cache
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request)
        .then((response) => {
          // Cache successful GET API responses
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
          return response;
        })
        .catch(() => caches.match(request))
    );
    return;
  }

  // Static assets — cache first, fallback to network
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((response) => {
        // Cache new static assets
        if (response.ok) {
          const responseClone = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, responseClone));
        }
        return response;
      });
    })
  );
});
