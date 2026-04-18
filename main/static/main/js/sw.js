// Service Worker for Rallynex PWA
const CACHE_NAME = 'rallynex-v2';
const STATIC_CACHE = 'rallynex-static-v2';

// Files to cache on install - UPDATED PATHS
const STATIC_FILES = [
    '/',
    '/offline/',
    '/manifest.json',
    '/static/icons/icon-96x96.png',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('[SW] Installing...');
    
    // Force activation without waiting
    self.skipWaiting();
    
    event.waitUntil(
        caches.open(STATIC_CACHE)
            .then(cache => {
                console.log('[SW] Caching static files');
                return cache.addAll(STATIC_FILES);
            })
            .catch(err => {
                console.error('[SW] Cache error:', err);
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
            // Take control of all clients immediately
            return self.clients.claim();
        })
    );
});

// Fetch event - network first, fallback to cache
self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    // Only handle GET requests
    if (request.method !== 'GET') return;
    
    // Skip cross-origin requests
    if (url.origin !== self.location.origin) return;
    
    // Skip API requests
    if (url.pathname.includes('/api/')) return;
    
    // Skip admin requests
    if (url.pathname.includes('/admin/')) return;
    
    // For navigation requests (HTML pages)
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then(response => {
                    // Cache the latest version
                    const responseClone = response.clone();
                    caches.open(STATIC_CACHE).then(cache => {
                        cache.put(request, responseClone);
                    });
                    return response;
                })
                .catch(() => {
                    // If offline, try to serve from cache
                    return caches.match(request)
                        .then(cached => {
                            if (cached) return cached;
                            // Fallback to offline page
                            return caches.match('/offline/');
                        });
                })
        );
        return;
    }
    
    // For all other requests (images, CSS, JS, etc.)
    event.respondWith(
        caches.match(request)
            .then(cached => {
                if (cached) {
                    // Return cached version immediately
                    return cached;
                }
                
                // Not in cache, fetch from network
                return fetch(request)
                    .then(response => {
                        // Cache successful responses
                        if (response && response.status === 200) {
                            const responseClone = response.clone();
                            caches.open(STATIC_CACHE).then(cache => {
                                cache.put(request, responseClone);
                            });
                        }
                        return response;
                    })
                    .catch(() => {
                        // If image request fails, return fallback icon
                        if (request.destination === 'image') {
                            return caches.match('/static/icons/icon-192x192.png');
                        }
                        // For other requests, just fail
                        throw new Error('Network request failed');
                    });
            })
    );
});

// Handle messages from clients
self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});

// Periodic sync for content updates (if supported)
self.addEventListener('periodicsync', event => {
    if (event.tag === 'update-content') {
        event.waitUntil(updateContent());
    }
});

async function updateContent() {
    try {
        const cache = await caches.open(STATIC_CACHE);
        // Refresh cached pages
        await Promise.all(
            STATIC_FILES.map(url => 
                fetch(url)
                    .then(response => {
                        if (response.ok) {
                            return cache.put(url, response);
                        }
                    })
                    .catch(err => console.log('Update failed for', url, err))
            )
        );
        console.log('[SW] Content updated');
    } catch (err) {
        console.error('[SW] Update error:', err);
    }
}