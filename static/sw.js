// sw.js - Service Worker for Rallynex PWA

const CACHE_NAME = 'rallynex-v1.0.0';
const DYNAMIC_CACHE = 'rallynex-dynamic-v1';

// Assets to cache on install
const STATIC_ASSETS = [
    '/',
    '/static/css/',
    '/static/js/',
    '/static/images/',
    '/static/icons/icon-96x96.png',
    '/static/icons/icon-192x192.png',
    '/static/icons/favicon.svg',
    '/offline/'
];

// Install event - cache static assets
self.addEventListener('install', event => {
    console.log('[Service Worker] Installing...');
    
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('[Service Worker] Caching static assets');
                return cache.addAll(STATIC_ASSETS);
            })
            .then(() => {
                return self.skipWaiting();
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('[Service Worker] Activating...');
    
    event.waitUntil(
        caches.keys()
            .then(cacheNames => {
                return Promise.all(
                    cacheNames.map(cache => {
                        if (cache !== CACHE_NAME && cache !== DYNAMIC_CACHE) {
                            console.log('[Service Worker] Deleting old cache:', cache);
                            return caches.delete(cache);
                        }
                    })
                );
            })
            .then(() => {
                return self.clients.claim();
            })
    );
});

// Fetch event - network first with cache fallback
self.addEventListener('fetch', event => {
    const { request } = event;
    const url = new URL(request.url);
    
    // Skip cross-origin requests
    if (!url.origin.includes(self.location.origin)) {
        return;
    }
    
    // HTML - Network first, fallback to cache, then offline page
    if (request.mode === 'navigate' || 
        (request.method === 'GET' && request.headers.get('accept').includes('text/html'))) {
        
        event.respondWith(
            fetch(request)
                .then(response => {
                    const clonedResponse = response.clone();
                    caches.open(DYNAMIC_CACHE).then(cache => {
                        cache.put(request, clonedResponse);
                    });
                    return response;
                })
                .catch(() => {
                    return caches.match(request)
                        .then(cachedResponse => {
                            return cachedResponse || caches.match('/offline/');
                        });
                })
        );
        return;
    }
    
    // Static assets - Cache first, network fallback
    if (request.url.includes('/static/') || 
        request.url.includes('/media/') ||
        request.destination === 'image' ||
        request.destination === 'font' ||
        request.destination === 'style' ||
        request.destination === 'script') {
        
        event.respondWith(
            caches.match(request)
                .then(cachedResponse => {
                    if (cachedResponse) {
                        return cachedResponse;
                    }
                    
                    return fetch(request)
                        .then(response => {
                            const clonedResponse = response.clone();
                            caches.open(DYNAMIC_CACHE).then(cache => {
                                cache.put(request, clonedResponse);
                            });
                            return response;
                        })
                        .catch(error => {
                            if (request.destination === 'image') {
                                return caches.match('/static/images/fallback-image.png');
                            }
                            throw error;
                        });
                })
        );
        return;
    }
    
    // API calls - Network only
    if (url.pathname.includes('/api/')) {
        event.respondWith(fetch(request));
        return;
    }
    
    // Default - Network first with cache fallback
    event.respondWith(
        fetch(request)
            .then(response => {
                const clonedResponse = response.clone();
                caches.open(DYNAMIC_CACHE).then(cache => {
                    cache.put(request, clonedResponse);
                });
                return response;
            })
            .catch(() => {
                return caches.match(request);
            })
    );
});

// Push notification event
self.addEventListener('push', event => {
    let data = { title: 'Rallynex', body: 'New update available!' };
    
    if (event.data) {
        try {
            data = event.data.json();
        } catch (e) {
            data.body = event.data.text();
        }
    }
    
    const options = {
        body: data.body,
        icon: '/static/icons/icon-192x192.png',
        badge: '/static/icons/icon-96x96.png',
        vibrate: [200, 100, 200],
        data: {
            url: data.url || '/',
            dateOfArrival: Date.now()
        },
        actions: [
            {
                action: 'open',
                title: 'Open'
            },
            {
                action: 'close',
                title: 'Close'
            }
        ]
    };
    
    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Notification click event
self.addEventListener('notificationclick', event => {
    event.notification.close();
    
    if (event.action === 'close') {
        return;
    }
    
    const urlToOpen = event.notification.data.url || '/';
    
    event.waitUntil(
        clients.matchAll({ type: 'window' })
            .then(windowClients => {
                for (let client of windowClients) {
                    if (client.url.includes(urlToOpen) && 'focus' in client) {
                        return client.focus();
                    }
                }
                if (clients.openWindow) {
                    return clients.openWindow(urlToOpen);
                }
            })
    );
});

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'sync-posts') {
        event.waitUntil(syncPosts());
    }
});

async function syncPosts() {
    try {
        const cache = await caches.open(DYNAMIC_CACHE);
        const requests = await cache.keys();
        const offlineActions = requests.filter(req => req.url.includes('/api/offline-actions'));
        
        for (const request of offlineActions) {
            const response = await cache.match(request);
            const data = await response.json();
            
            await fetch('/api/sync/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            
            await cache.delete(request);
        }
    } catch (error) {
        console.error('Background sync failed:', error);
    }
}