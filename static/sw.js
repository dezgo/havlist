const CACHE_NAME = 'havlist-v1';
const PRECACHE = ['/', '/static/style.css', '/static/form.js'];

self.addEventListener('install', (e) => {
    e.waitUntil(
        caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE))
    );
    self.skipWaiting();
});

self.addEventListener('activate', (e) => {
    e.waitUntil(
        caches.keys().then((keys) =>
            Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', (e) => {
    // Network-first for API/dynamic, cache-first for static assets
    if (e.request.url.includes('/api/') || e.request.url.includes('/uploads/')) {
        e.respondWith(fetch(e.request).catch(() => caches.match(e.request)));
    } else {
        e.respondWith(
            caches.match(e.request).then((cached) => cached || fetch(e.request))
        );
    }
});
