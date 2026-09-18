const CACHE_NAME = 'foodwise-static-v2';
const STATIC_ASSETS = [
    '/static/css/style.css',
    '/static/js/main.js',
    '/static/manifest.json',
    '/static/icons/icon-192.png',
    '/static/icons/icon-512.png',
    '/static/offline.html'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => {
            return cache.addAll(STATIC_ASSETS);
        })
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))
            );
        })
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    // Never cache POST, PUT, DELETE, PATCH requests
    if (event.request.method !== 'GET') {
        return;
    }

    const url = new URL(event.request.url);

    // List of private routes that should NEVER be cached
    const privateRoutes = [
    '/dashboard',
    '/food',
    '/meals',
    '/waste',
    '/login',
    '/register',
    '/logout',
    '/feedback',
    '/admin'
];
    const isPrivateRoute = privateRoutes.some(route => url.pathname === route || url.pathname.startsWith(route + '/'));

    if (isPrivateRoute) {
        // Navigation to private HTML pages: Network only, fallback to offline.html
        if (event.request.mode === 'navigate' || event.request.headers.get('accept').includes('text/html')) {
            event.respondWith(
                fetch(event.request).catch(() => caches.match('/static/offline.html'))
            );
        } else {
            // Other assets on private routes (if any API calls) - Network only
            event.respondWith(fetch(event.request));
        }
        return;
    }

    // Static assets (CSS, JS, Images, offline page)
    if (url.pathname.startsWith('/static/')) {
        event.respondWith(
            caches.match(event.request).then(response => {
                return response || fetch(event.request);
            })
        );
        return;
    }

    // Default HTML navigation for public pages (e.g. /, /tips): Network only, fallback to offline.html
    if (event.request.mode === 'navigate' || event.request.headers.get('accept').includes('text/html')) {
        event.respondWith(
            fetch(event.request).catch(() => caches.match('/static/offline.html'))
        );
        return;
    }

    // Default fetch for anything else
    event.respondWith(fetch(event.request));
});
