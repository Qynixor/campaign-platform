// sw.js - MUST be at root level (e.g., /sw.js)
const CACHE_NAME = 'rallynex-v3';
const STATIC_CACHE = 'rallynex-static-v3';

const STATIC_FILES = [
    '/',
    '/static/icons/icon-96x96.png',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png'
];

self.addEventListener('install', event => {
    console.log('[SW] Installing...');
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

self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);
    
    if (request.method !== 'GET') return;
    
    if (url.pathname.includes('/api/') || url.hostname !== self.location.hostname) {
        event.respondWith(fetch(request));
        return;
    }
    
    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then(response => {
                    const responseClone = response.clone();
                    caches.open(STATIC_CACHE).then(cache => {
                        cache.put(request, responseClone);
                    });
                    return response;
                })
                .catch(() => {
                    return caches.match(request).then(cached => cached || caches.match('/'));
                })
        );
        return;
    }
    
    event.respondWith(
        caches.match(request)
            .then(cached => {
                if (cached) return cached;
                
                return fetch(request)
                    .then(response => {
                        if (response && response.status === 200) {
                            const responseClone = response.clone();
                            caches.open(STATIC_CACHE).then(cache => {
                                cache.put(request, responseClone);
                            });
                        }
                        return response;
                    })
                    .catch(() => {
                        if (request.destination === 'image') {
                            return caches.match('/static/icons/icon-192x192.png');
                        }
                        throw error;
                    });
            })
    );
});

self.addEventListener('message', event => {
    if (event.data && event.data.type === 'SKIP_WAITING') {
        self.skipWaiting();
    }
});