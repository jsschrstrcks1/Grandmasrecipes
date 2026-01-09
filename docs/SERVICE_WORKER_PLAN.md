# Service Worker Plan: Family Recipe Archive

> **Status**: Planning
> **Author**: Claude
> **Date**: January 2026

## Overview

This document outlines the architecture for a service worker that "transcends" the four family recipe repositories, enabling offline access, faster loads, and a true Progressive Web App experience.

---

## Repository Topology

| Repository | URL | Role |
|------------|-----|------|
| **Grandmasrecipes** | `jsschrstrcks1.github.io/Grandmasrecipes/` | Hub + Local collection |
| **MomsRecipes** | `jsschrstrcks1.github.io/MomsRecipes/` | Remote collection |
| **Grannysrecipes** | `jsschrstrcks1.github.io/Grannysrecipes/` | Remote collection |
| **Allrecipes** | `jsschrstrcks1.github.io/Allrecipes/` | Remote collection |

All four repositories are served from the same GitHub Pages domain (`jsschrstrcks1.github.io`), which simplifies cross-origin concerns.

---

## Key Challenges

1. **Same-origin policy**: Service workers can only intercept requests within their registered scope
2. **Cross-origin caching**: Remote collections are on different paths but same domain
3. **Image-heavy content**: Recipe scans (handwritten cards) need efficient caching
4. **Offline-first**: Site should work at Grandma's house with spotty WiFi
5. **Cache invalidation**: Recipe data should stay fresh while enabling offline use
6. **Family-only access**: Prevent random visitors from accessing/caching family recipes

---

## Family Access Gate (Authentication)

**Status**: ✅ Already implemented in `index.html` and `recipe.html`

The site uses a localStorage-based authentication gate that must be passed before viewing recipes.

### Existing Implementation

**Location**: Inline script in `index.html` and `recipe.html`

```javascript
// Authentication gate (ALREADY IN CODEBASE)
const AUTH_KEY = 'grandmas-kitchen-auth';
const CORRECT_ANSWER = 'Baker';  // Grandma's last name

function checkAuth() {
  return localStorage.getItem(AUTH_KEY) === 'true';
}

// On successful auth:
localStorage.setItem(AUTH_KEY, 'true');
```

**HTML Structure**:
- `#auth-gate` - Full-screen challenge modal (visible by default)
- `#site-content` - Main content wrapper (hidden until authenticated)
- Challenge question: "What is Grandma's last name?"

### Service Worker Integration

The service worker MUST check for the `grandmas-kitchen-auth` token before caching or serving any content.

**Challenge**: Service workers cannot directly access `localStorage`. Solutions:

#### Option 1: IndexedDB Mirror (Recommended)

When the page sets `localStorage`, also mirror to IndexedDB (accessible from SW):

```javascript
// In page script - after successful auth
localStorage.setItem(AUTH_KEY, 'true');

// Also mirror to IndexedDB for service worker access
const db = await openDB('FamilyAuth', 1, {
  upgrade(db) { db.createObjectStore('auth'); }
});
await db.put('auth', 'true', 'grandmas-kitchen-auth');
```

```javascript
// In sw.js - check IndexedDB before caching
async function isAuthenticated() {
  try {
    const db = await openDB('FamilyAuth', 1);
    const value = await db.get('auth', 'grandmas-kitchen-auth');
    return value === 'true';
  } catch {
    return false;
  }
}

self.addEventListener('fetch', event => {
  event.respondWith(
    (async () => {
      if (!await isAuthenticated()) {
        // Don't cache anything - return network only
        return fetch(event.request);
      }
      // Proceed with normal caching strategies
      return handleAuthenticatedFetch(event.request);
    })()
  );
});
```

#### Option 2: Skip SW Registration Until Authenticated

Simpler approach - only register service worker after auth passes:

```javascript
// In index.html - register SW only after authentication
if (checkAuth()) {
  showSite();
  // Only register SW for authenticated users
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/Grandmasrecipes/sw.js');
  }
} else {
  showGate();
  // No SW registration for unauthenticated users
}
```

This prevents any caching for unauthenticated visitors, but means the SW never installs until they authenticate.

#### Option 3: Message Channel Validation

Use postMessage to verify auth status with active clients:

```javascript
// sw.js
self.addEventListener('fetch', event => {
  if (event.request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        const clients = await self.clients.matchAll({ type: 'window' });
        if (clients.length === 0) {
          // No active clients - can't verify, pass through
          return fetch(event.request);
        }

        // Ask client to verify auth
        const authStatus = await new Promise(resolve => {
          const channel = new MessageChannel();
          channel.port1.onmessage = e => resolve(e.data.authenticated);
          clients[0].postMessage({ type: 'AUTH_CHECK' }, [channel.port2]);
        });

        if (!authStatus) {
          return fetch(event.request); // Don't cache
        }
        return handleAuthenticatedFetch(event.request);
      })()
    );
  }
});
```

### Recommended Approach

**Use Option 2** (conditional SW registration) for simplicity:

1. Keep existing localStorage auth gate unchanged
2. Only register service worker after `checkAuth()` returns true
3. Service worker assumes all requests are from authenticated users
4. Unauthenticated visitors never get SW installed = no caching

This requires minimal changes to the existing auth system while ensuring the SW only operates for family members

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SERVICE WORKER (sw.js)                       │
│                  Installed on Hub Site Only                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │ APP SHELL   │  │ RECIPE DATA │  │ IMAGES                  │ │
│  │ CACHE       │  │ CACHE       │  │ CACHE                   │ │
│  │             │  │             │  │                         │ │
│  │ - HTML      │  │ - Local JSON│  │ - data/*.jpeg (local)   │ │
│  │ - CSS       │  │ - Remote    │  │ - Remote images         │ │
│  │ - JS        │  │   JSONs     │  │   (cross-origin)        │ │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘ │
│                                                                 │
│  Strategy: Cache-first for static, Network-first for JSON      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
   ┌──────────┐      ┌─────────────────┐     ┌──────────────┐
   │ Local    │      │ MomsRecipes     │     │ Grannysrecipes│
   │ /data/   │      │ /data/recipes   │     │ /data/recipes │
   └──────────┘      │ .json           │     │ .json         │
                     └─────────────────┘     └──────────────┘
```

---

## Caching Strategies by Resource Type

| Resource Type | Strategy | TTL | Rationale |
|---------------|----------|-----|-----------|
| **App Shell** (HTML, CSS, JS) | Cache-first with background update | 24h | Fast loads, auto-refresh |
| **Local Recipe JSON** | Network-first with cache fallback | 1h | Data freshness matters |
| **Remote Recipe JSONs** | Stale-while-revalidate | 4h | Balance freshness/speed |
| **Recipe Images (local)** | Cache-first | 30 days | Images rarely change |
| **Handwritten Scans** | Cache-first, permanent | Never expire | Sacred family heirlooms |

---

## Implementation Details

### 1. Service Worker Registration

Add to `index.html` and `recipe.html`:

```javascript
// Register SW only on production (GitHub Pages)
if ('serviceWorker' in navigator && location.hostname.includes('github.io')) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/Grandmasrecipes/sw.js', {
      scope: '/Grandmasrecipes/'
    }).then(registration => {
      console.log('SW registered:', registration.scope);

      // Check for updates periodically
      setInterval(() => registration.update(), 60 * 60 * 1000); // hourly
    }).catch(error => {
      console.log('SW registration failed:', error);
    });
  });
}
```

### 2. Cache Names (versioned)

```javascript
const CACHE_VERSION = 'v1';
const CACHES = {
  shell: `grandmas-shell-${CACHE_VERSION}`,
  data: `grandmas-data-${CACHE_VERSION}`,
  images: `grandmas-images-${CACHE_VERSION}`
};
```

### 3. App Shell Precaching

```javascript
const APP_SHELL = [
  '/Grandmasrecipes/',
  '/Grandmasrecipes/index.html',
  '/Grandmasrecipes/recipe.html',
  '/Grandmasrecipes/styles.css',
  '/Grandmasrecipes/script.js',
  '/Grandmasrecipes/data/recipes_master.json',
  '/Grandmasrecipes/data/collections.json',
  '/Grandmasrecipes/offline.html'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHES.shell)
      .then(cache => cache.addAll(APP_SHELL))
      .then(() => self.skipWaiting())
  );
});
```

### 4. Fetch Event Routing

```javascript
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // Skip non-GET requests
  if (event.request.method !== 'GET') return;

  // Route based on request type
  if (isAppShell(url)) {
    event.respondWith(cacheFirst(event.request, CACHES.shell));
  }
  else if (isRecipeJSON(url)) {
    event.respondWith(networkFirst(event.request, CACHES.data));
  }
  else if (isImage(url)) {
    event.respondWith(cacheFirst(event.request, CACHES.images));
  }
  else if (isRemoteCollection(url)) {
    event.respondWith(staleWhileRevalidate(event.request, CACHES.data));
  }
});

// Helper functions
function isAppShell(url) {
  return APP_SHELL.some(path => url.pathname.endsWith(path.replace('/Grandmasrecipes', '')));
}

function isRecipeJSON(url) {
  return url.pathname.endsWith('.json');
}

function isImage(url) {
  return /\.(jpeg|jpg|png|gif|webp)$/i.test(url.pathname);
}
```

### 5. Cross-Origin Collection Handling

```javascript
const FAMILY_ORIGINS = [
  'https://jsschrstrcks1.github.io/MomsRecipes/',
  'https://jsschrstrcks1.github.io/Grannysrecipes/',
  'https://jsschrstrcks1.github.io/Allrecipes/'
];

function isRemoteCollection(url) {
  return FAMILY_ORIGINS.some(origin => url.href.startsWith(origin));
}

// Stale-while-revalidate for remote collections
async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  const fetchPromise = fetch(request).then(response => {
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  }).catch(() => cachedResponse);

  return cachedResponse || fetchPromise;
}
```

### 6. Caching Strategy Functions

```javascript
// Cache-first: Return cached version, fallback to network
async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  if (cached) {
    // Background update for shell assets
    if (cacheName === CACHES.shell) {
      fetch(request).then(response => {
        if (response.ok) cache.put(request, response);
      });
    }
    return cached;
  }

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    return offlineFallback(request);
  }
}

// Network-first: Try network, fallback to cache
async function networkFirst(request, cacheName) {
  const cache = await caches.open(cacheName);

  try {
    const response = await fetch(request);
    if (response.ok) {
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await cache.match(request);
    return cached || offlineFallback(request);
  }
}
```

### 7. Offline Fallback

```javascript
async function offlineFallback(request) {
  // For navigation requests, show offline page
  if (request.mode === 'navigate') {
    const cache = await caches.open(CACHES.shell);
    return cache.match('/Grandmasrecipes/offline.html');
  }

  // For images, return a placeholder
  if (/\.(jpeg|jpg|png|gif|webp)$/i.test(request.url)) {
    return new Response(
      '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="150"><rect fill="#f5f0e6" width="200" height="150"/><text x="50%" y="50%" text-anchor="middle" fill="#8b4513">Offline</text></svg>',
      { headers: { 'Content-Type': 'image/svg+xml' }}
    );
  }

  return new Response('Offline', { status: 503 });
}
```

### 8. Cache Cleanup on Activation

```javascript
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames
          .filter(name => !Object.values(CACHES).includes(name))
          .map(name => caches.delete(name))
      );
    }).then(() => self.clients.claim())
  );
});
```

### 9. Background Sync (Optional)

```javascript
// Register sync when online
self.addEventListener('sync', event => {
  if (event.tag === 'sync-remote-recipes') {
    event.waitUntil(syncRemoteCollections());
  }
});

async function syncRemoteCollections() {
  const cache = await caches.open(CACHES.data);

  for (const origin of FAMILY_ORIGINS) {
    try {
      const url = origin + 'data/recipes.json';
      const response = await fetch(url);
      if (response.ok) {
        await cache.put(url, response);
        console.log(`Synced: ${url}`);
      }
    } catch (e) {
      console.log(`Sync failed for ${origin}, will retry`);
    }
  }
}
```

---

## File Structure

```
Grandmasrecipes/
├── sw.js                    # Main service worker
├── offline.html             # Graceful offline fallback page
├── manifest.json            # PWA manifest (optional)
└── docs/
    └── SERVICE_WORKER_PLAN.md  # This document
```

---

## PWA Manifest (Optional)

```json
{
  "name": "Grandma's Kitchen - Family Recipe Archive",
  "short_name": "Grandma's Kitchen",
  "description": "Four generations of family recipes, preserved with love",
  "start_url": "/Grandmasrecipes/",
  "scope": "/Grandmasrecipes/",
  "display": "standalone",
  "background_color": "#f5f0e6",
  "theme_color": "#8b4513",
  "icons": [
    {
      "src": "data/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "data/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

---

## Implementation Phases

### Phase 1: Core Service Worker
- [ ] App shell caching (HTML, CSS, JS)
- [ ] Local recipe JSON caching
- [ ] Basic offline fallback page
- [ ] Service worker registration

### Phase 2: Cross-Origin Support
- [ ] Remote collection JSON caching
- [ ] Remote image caching
- [ ] Stale-while-revalidate for remote data

### Phase 3: PWA Features
- [ ] Web app manifest
- [ ] Install prompt handling
- [ ] "Add to Home Screen" support
- [ ] Update notification toast

### Phase 4: Advanced Features
- [ ] IndexedDB for full offline search
- [ ] Image lazy-loading optimization
- [ ] Prefetch linked recipes
- [ ] Explicit "Save for Offline" feature
- [ ] Push notifications (recipe updates)

---

## Important Considerations

### GitHub Pages Limitations
- No server-side logic (pure static hosting)
- All repos share domain `jsschrstrcks1.github.io`
- CORS headers are permissive by default
- No custom HTTP headers possible

### Cache Size Management
```javascript
// Implement LRU eviction for images
const MAX_IMAGE_CACHE_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_DATA_CACHE_SIZE = 5 * 1024 * 1024;   // 5MB

async function trimCache(cacheName, maxSize) {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();

  let totalSize = 0;
  const entries = [];

  for (const request of keys) {
    const response = await cache.match(request);
    const size = (await response.clone().blob()).size;
    entries.push({ request, size, url: request.url });
    totalSize += size;
  }

  // Remove oldest entries until under limit
  while (totalSize > maxSize && entries.length > 0) {
    const oldest = entries.shift();
    await cache.delete(oldest.request);
    totalSize -= oldest.size;
  }
}
```

### Update Flow
1. New SW detected → Install new version
2. Old SW still controls page until refresh
3. `skipWaiting()` forces immediate activation
4. `clients.claim()` takes control of open tabs
5. Show toast: "Recipes updated! Refresh to see changes."

### Testing Checklist
- [ ] Chrome DevTools → Application → Service Workers
- [ ] Test with "Offline" checkbox enabled
- [ ] Verify Cache Storage contents
- [ ] Test on actual mobile device
- [ ] Test with slow 3G throttling
- [ ] Verify cross-origin collection loading
- [ ] Test update flow (change version, reload)

---

## Security Notes

1. **HTTPS Required**: Service workers only work over HTTPS (or localhost)
2. **No Sensitive Data**: Recipe data is family-friendly, no auth required
3. **Cache Poisoning**: Only cache responses with `response.ok === true`
4. **Scope Restriction**: SW can only intercept within its registered scope

---

## References

- [Service Worker API (MDN)](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API)
- [The Offline Cookbook (Google)](https://web.dev/offline-cookbook/)
- [Workbox (Google's SW library)](https://developer.chrome.com/docs/workbox/)

---

*"She looketh well to the ways of her household, and eateth not the bread of idleness."*
— Proverbs 31:27
