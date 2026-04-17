// sw.js - Rallynex PWA Service Worker
const CACHE_NAME = 'rallynex-v2';
const STATIC_CACHE = 'rallynex-static-v2';

// Files to cache immediately
const STATIC_FILES = [
    '/',
    '/static/icons/icon-96x96.png',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// Install event - cache static files
self.addEventListener('install', event => {
    console.log('[SW] Installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE).then(cache => {
            console.log('[SW] Caching static files');
            return cache.addAll(STATIC_FILES);
        }).then(() => {
            return self.skipWaiting();
        })
    );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
    console.log('[SW] Activating...');
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== STATIC_CACHE && key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            );
        }).then(() => {
            return self.clients.claim();
        })
    );
});

// Fetch event - simple cache-first strategy
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Skip non-GET requests
    if (request.method !== 'GET') {
        event.respondWith(fetch(request));
        return;
    }
    
    // Skip API calls
    if (url.pathname.includes('/api/')) {
        event.respondWith(fetch(request));
        return;
    }
    
    // For static assets and pages
    event.respondWith(
        caches.match(request).then(cachedResponse => {
            if (cachedResponse) {
                return cachedResponse;
            }
            return fetch(request).then(response => {
                // Cache valid responses
                if (response && response.status === 200) {
                    const responseClone = response.clone();
                    caches.open(STATIC_CACHE).then(cache => {
                        cache.put(request, responseClone);
                    });
                }
                return response;
            });
        }).catch(() => {
            // Fallback for offline
            if (url.pathname.includes('/static/icons/')) {
                return caches.match('/static/icons/icon-192x192.png');
            }
            return new Response('Offline - Rallynex', { status: 200 });
        })
    );
});