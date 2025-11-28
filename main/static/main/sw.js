// RallyNex Service Worker
const CACHE_NAME = 'rallynex-v2.0.0';
const STATIC_CACHE = 'rallynex-static-v2.0.0';
const DYNAMIC_CACHE = 'rallynex-dynamic-v2.0.0';

// Assets to cache immediately
const STATIC_ASSETS = [
    '/',
    '/static/css/main.css',
    '/static/main/js/pwa.js',
    '/static/manifest.json',
    // Add other critical assets
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('RallyNex SW installing...');
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                console.log('RallyNex SW installed');
                return self.skipWaiting();
            })
    );
});

// Activate event - cleanup old caches
self.addEventListener('activate', event => {
    console.log('RallyNex SW activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cacheName => {
                    if (cacheName !== STATIC_CACHE && cacheName !== DYNAMIC_CACHE && cacheName !== CACHE_NAME) {
                        console.log('Deleting old cache:', cacheName);
                        return caches.delete(cacheName);
                    }
                })
            );
        }).then(() => {
            console.log('RallyNex SW activated');
            return self.clients.claim();
        })
    );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Skip Chrome extensions
    if (event.request.url.indexOf('chrome-extension') !== -1) return;

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached version
                if (response) {
                    return response;
                }

                // Clone the request
                const fetchRequest = event.request.clone();

                return fetch(fetchRequest).then(response => {
                    // Check if valid response
                    if (!response || response.status !== 200 || response.type !== 'basic') {
                        return response;
                    }

                    // Clone the response
                    const responseToCache = response.clone();

                    // Cache dynamic requests
                    caches.open(DYNAMIC_CACHE)
                        .then(cache => {
                            cache.put(event.request, responseToCache);
                        });

                    return response;
                }).catch(error => {
                    console.log('Fetch failed; returning offline page:', error);
                    // You could return a custom offline page here
                });
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        console.log('Background sync triggered');
        event.waitUntil(doBackgroundSync());
    }
});

async function doBackgroundSync() {
    // Implement background sync for critical actions
    // Like syncing donations, messages, etc. when online
}