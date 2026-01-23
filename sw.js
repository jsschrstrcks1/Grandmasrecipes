/**
 * Service Worker for Grandma's Kitchen Family Recipe Archive
 *
 * Provides offline support and caching for:
 * - Local static assets (HTML, CSS, JS)
 * - Local recipe data (JSON shards)
 * - Cross-origin family recipe repositories
 * - Cheese builder tools from Allrecipes
 *
 * Caching Strategies:
 * - Static assets: Cache-first (fast loads)
 * - Recipe data: Network-first with cache fallback (fresh data)
 * - Cross-origin: Stale-while-revalidate (balance of speed and freshness)
 */

const CACHE_VERSION = 'v1.0.0';
const CACHE_NAME = `grandmas-kitchen-${CACHE_VERSION}`;

// Family recipe repository domains (allowed for cross-origin caching)
const FAMILY_DOMAINS = [
  'jsschrstrcks1.github.io'
];

// Static assets to precache on install
const PRECACHE_ASSETS = [
  '/',
  '/index.html',
  '/recipe.html',
  '/styles.min.css',
  '/script.js',
  '/data/collections.json',
  '/data/recipes_index.json',
  '/data/ingredient-index.json',
  '/data/health-considerations.json'
];

// Cross-origin resources to prefetch (cheese builder tools)
const CROSS_ORIGIN_PREFETCH = [
  'https://jsschrstrcks1.github.io/Allrecipes/cheese-builder.html',
  'https://jsschrstrcks1.github.io/Allrecipes/cheese-builder.js',
  'https://jsschrstrcks1.github.io/Allrecipes/adulterant-companion.js',
  'https://jsschrstrcks1.github.io/Allrecipes/data/adulterants.json',
  'https://jsschrstrcks1.github.io/Allrecipes/milk-substitution.js',
  'https://jsschrstrcks1.github.io/Allrecipes/data/milk-substitution.json'
];

// Install event - precache static assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');

  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Precaching static assets');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => {
        // Prefetch cross-origin resources (don't fail install if these fail)
        return caches.open(CACHE_NAME).then((cache) => {
          const crossOriginPromises = CROSS_ORIGIN_PREFETCH.map((url) => {
            return fetch(url, { mode: 'cors', credentials: 'omit' })
              .then((response) => {
                if (response.ok) {
                  return cache.put(url, response);
                }
              })
              .catch((err) => {
                console.log(`[SW] Failed to prefetch ${url}:`, err.message);
              });
          });
          return Promise.allSettled(crossOriginPromises);
        });
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');

  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name.startsWith('grandmas-kitchen-') && name !== CACHE_NAME)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache or network
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') {
    return;
  }

  // Skip chrome-extension and other non-http(s) protocols
  if (!url.protocol.startsWith('http')) {
    return;
  }

  // Determine caching strategy based on request type
  if (isStaticAsset(url)) {
    // Cache-first for static assets
    event.respondWith(cacheFirst(event.request));
  } else if (isRecipeData(url)) {
    // Network-first for recipe data (want fresh data)
    event.respondWith(networkFirst(event.request));
  } else if (isFamilyDomain(url)) {
    // Stale-while-revalidate for cross-origin family resources
    event.respondWith(staleWhileRevalidate(event.request));
  } else {
    // Network-only for other requests
    return;
  }
});

// Helper: Check if URL is a static asset
function isStaticAsset(url) {
  const staticExtensions = ['.html', '.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.woff', '.woff2'];
  const isLocal = url.origin === self.location.origin;
  const isStatic = staticExtensions.some(ext => url.pathname.endsWith(ext));
  return isLocal && isStatic;
}

// Helper: Check if URL is recipe data
function isRecipeData(url) {
  const isLocal = url.origin === self.location.origin;
  const isJson = url.pathname.endsWith('.json');
  const isDataFolder = url.pathname.includes('/data/');
  return isLocal && isJson && isDataFolder;
}

// Helper: Check if URL is from a family domain
function isFamilyDomain(url) {
  return FAMILY_DOMAINS.some(domain => url.hostname === domain || url.hostname.endsWith('.' + domain));
}

// Strategy: Cache-first (fast, serves from cache if available)
async function cacheFirst(request) {
  const cachedResponse = await caches.match(request);
  if (cachedResponse) {
    return cachedResponse;
  }

  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Cache-first fetch failed:', error.message);
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

// Strategy: Network-first (fresh data, falls back to cache)
async function networkFirst(request) {
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, networkResponse.clone());
    }
    return networkResponse;
  } catch (error) {
    console.log('[SW] Network-first falling back to cache:', request.url);
    const cachedResponse = await caches.match(request);
    if (cachedResponse) {
      return cachedResponse;
    }
    return new Response(JSON.stringify({ error: 'Offline', cached: false }), {
      status: 503,
      headers: { 'Content-Type': 'application/json' }
    });
  }
}

// Strategy: Stale-while-revalidate (serve cached, update in background)
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cachedResponse = await cache.match(request);

  // Fetch fresh version in background
  const fetchPromise = fetch(request, { mode: 'cors', credentials: 'omit' })
    .then((networkResponse) => {
      if (networkResponse.ok) {
        cache.put(request, networkResponse.clone());
      }
      return networkResponse;
    })
    .catch((error) => {
      console.log('[SW] Background revalidation failed:', error.message);
      return null;
    });

  // Return cached response immediately if available, otherwise wait for network
  if (cachedResponse) {
    return cachedResponse;
  }

  const networkResponse = await fetchPromise;
  if (networkResponse) {
    return networkResponse;
  }

  return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
}

// Message handler for manual cache operations
self.addEventListener('message', (event) => {
  if (event.data && event.data.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data && event.data.type === 'CACHE_URLS') {
    const urls = event.data.urls || [];
    event.waitUntil(
      caches.open(CACHE_NAME).then((cache) => {
        return Promise.allSettled(
          urls.map((url) => {
            return fetch(url, { mode: 'cors', credentials: 'omit' })
              .then((response) => {
                if (response.ok) {
                  return cache.put(url, response);
                }
              })
              .catch((err) => {
                console.log(`[SW] Failed to cache ${url}:`, err.message);
              });
          })
        );
      })
    );
  }

  if (event.data && event.data.type === 'GET_CACHE_STATUS') {
    caches.open(CACHE_NAME).then((cache) => {
      cache.keys().then((keys) => {
        event.ports[0].postMessage({
          cacheVersion: CACHE_VERSION,
          cachedUrls: keys.map(req => req.url),
          count: keys.length
        });
      });
    });
  }
});

console.log('[SW] Service worker loaded');
