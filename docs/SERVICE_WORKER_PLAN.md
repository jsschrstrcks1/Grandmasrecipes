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

**Requirement**: Users must pass a family challenge before the service worker activates or any content is served.

### Token-Based Access Control

```
┌─────────────────────────────────────────────────────────────────┐
│                     ACCESS FLOW                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   User visits site                                              │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────┐                                              │
│   │ Check for   │                                              │
│   │ family_token│                                              │
│   │ in storage  │                                              │
│   └──────┬──────┘                                              │
│          │                                                      │
│     ┌────┴────┐                                                │
│     │         │                                                │
│   Found    Not Found                                           │
│     │         │                                                │
│     │         ▼                                                │
│     │   ┌─────────────┐                                        │
│     │   │  Challenge  │                                        │
│     │   │    Page     │◄──── "What was Grandma's dog's name?"  │
│     │   └──────┬──────┘                                        │
│     │          │                                                │
│     │     ┌────┴────┐                                          │
│     │     │         │                                          │
│     │   Correct   Wrong                                        │
│     │     │         │                                          │
│     │     │         ▼                                          │
│     │     │   ┌─────────┐                                      │
│     │     │   │ Denied  │                                      │
│     │     │   │ (retry) │                                      │
│     │     │   └─────────┘                                      │
│     │     │                                                     │
│     │     ▼                                                     │
│     │   Set family_token                                       │
│     │   in localStorage                                        │
│     │     │                                                     │
│     └─────┴─────┐                                              │
│                 ▼                                                │
│   ┌─────────────────────┐                                      │
│   │  Register Service   │                                      │
│   │  Worker + Load Site │                                      │
│   └─────────────────────┘                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Token Configuration

```javascript
// family-gate.js - Loaded BEFORE any other scripts

const FAMILY_CONFIG = {
  tokenKey: 'grandmas_kitchen_family_token',
  tokenValue: 'blessed-baker-family-2024',  // Hash of correct answer

  // Challenge question(s) - family would know these
  challenges: [
    {
      question: "What Michigan city did Grandma grow up in?",
      answers: ["detroit", "flint", "lansing"],  // Accept multiple spellings
      hint: "It's known for cars..."
    },
    {
      question: "What was the name of Grandma's famous chocolate cake?",
      answers: ["jubilee", "jubilie"],  // Accept family spelling variant
      hint: "Check the recipe collection..."
    }
  ]
};

// Simple hash for answer validation (not cryptographically secure, just obfuscation)
function hashAnswer(answer) {
  let hash = 0;
  const str = answer.toLowerCase().trim();
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString(36);
}
```

### Challenge Page Implementation

```javascript
// gate.js - Shows challenge if no valid token

(function() {
  'use strict';

  const TOKEN_KEY = 'grandmas_kitchen_family_token';
  const VALID_HASHES = ['a7b3x2', 'k9m4p1'];  // Pre-computed hashes of valid answers

  // Check for existing valid token
  function hasValidToken() {
    const token = localStorage.getItem(TOKEN_KEY);
    return token && VALID_HASHES.includes(token);
  }

  // Show challenge modal
  function showChallenge() {
    // Block all content until challenge passed
    document.body.innerHTML = `
      <div id="family-gate" style="
        position: fixed; inset: 0;
        display: flex; align-items: center; justify-content: center;
        background: linear-gradient(135deg, #f5f0e6 0%, #e8dcc8 100%);
        font-family: Georgia, serif;
      ">
        <div style="
          background: white;
          padding: 2rem;
          border-radius: 12px;
          box-shadow: 0 4px 20px rgba(0,0,0,0.15);
          max-width: 400px;
          text-align: center;
        ">
          <h1 style="color: #8b4513; margin-bottom: 1rem;">
            🍪 Grandma's Kitchen
          </h1>
          <p style="color: #666; margin-bottom: 1.5rem;">
            This is a private family recipe archive.<br>
            Please answer the family question to enter.
          </p>
          <p style="font-weight: bold; color: #333; margin-bottom: 1rem;">
            What Michigan city did Grandma grow up in?
          </p>
          <input type="text" id="challenge-answer"
            placeholder="Your answer..."
            style="
              width: 100%; padding: 0.75rem;
              border: 2px solid #ddd; border-radius: 6px;
              font-size: 1rem; margin-bottom: 1rem;
            "
          >
          <button id="challenge-submit" style="
            width: 100%; padding: 0.75rem;
            background: #8b4513; color: white;
            border: none; border-radius: 6px;
            font-size: 1rem; cursor: pointer;
          ">
            Enter Kitchen
          </button>
          <p id="challenge-error" style="
            color: #c0392b; margin-top: 1rem; display: none;
          ">
            That's not quite right. Try again!
          </p>
          <p style="
            color: #999; font-size: 0.8rem; margin-top: 1.5rem;
            font-style: italic;
          ">
            "She looketh well to the ways of her household"<br>
            — Proverbs 31:27
          </p>
        </div>
      </div>
    `;

    // Handle submission
    const input = document.getElementById('challenge-answer');
    const submit = document.getElementById('challenge-submit');
    const error = document.getElementById('challenge-error');

    function checkAnswer() {
      const answer = input.value.toLowerCase().trim();
      const hash = hashAnswer(answer);

      if (VALID_HASHES.includes(hash)) {
        localStorage.setItem(TOKEN_KEY, hash);
        location.reload();  // Reload to register SW and show content
      } else {
        error.style.display = 'block';
        input.value = '';
        input.focus();
      }
    }

    submit.addEventListener('click', checkAnswer);
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') checkAnswer();
    });

    input.focus();
  }

  // Hash function (same as in config)
  function hashAnswer(answer) {
    let hash = 0;
    const str = answer.toLowerCase().trim();
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash;
    }
    return hash.toString(36);
  }

  // Main gate check - runs immediately
  if (!hasValidToken()) {
    // Prevent any content from showing
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', showChallenge);
    } else {
      showChallenge();
    }

    // Block service worker registration
    window.FAMILY_GATE_PASSED = false;
  } else {
    window.FAMILY_GATE_PASSED = true;
  }
})();
```

### Service Worker Token Check

The service worker itself checks for the token before caching or serving content:

```javascript
// sw.js - Token validation in fetch handler

const TOKEN_KEY = 'grandmas_kitchen_family_token';
const VALID_HASHES = ['a7b3x2', 'k9m4p1'];

self.addEventListener('fetch', event => {
  // For navigation requests, check token via message channel
  if (event.request.mode === 'navigate') {
    event.respondWith(
      (async () => {
        // Ask the client if they have a valid token
        const clients = await self.clients.matchAll();
        let hasToken = false;

        for (const client of clients) {
          // Use postMessage to check token
          // Client-side script responds with token status
        }

        // If no token, serve challenge page instead
        if (!hasToken) {
          return new Response(CHALLENGE_PAGE_HTML, {
            headers: { 'Content-Type': 'text/html' }
          });
        }

        // Normal fetch handling for authenticated users
        return normalFetchHandler(event.request);
      })()
    );
    return;
  }

  // ... rest of fetch handling
});
```

### Alternative: Simpler IndexedDB Check in SW

```javascript
// sw.js - Check IndexedDB for token (works in SW context)

async function hasValidFamilyToken() {
  return new Promise((resolve) => {
    const request = indexedDB.open('FamilyGate', 1);

    request.onerror = () => resolve(false);

    request.onupgradeneeded = (event) => {
      event.target.result.createObjectStore('auth', { keyPath: 'id' });
    };

    request.onsuccess = (event) => {
      const db = event.target.result;
      const tx = db.transaction('auth', 'readonly');
      const store = tx.objectStore('auth');
      const get = store.get('family_token');

      get.onsuccess = () => {
        const result = get.result;
        resolve(result && VALID_HASHES.includes(result.value));
      };

      get.onerror = () => resolve(false);
    };
  });
}

// In fetch handler
self.addEventListener('fetch', event => {
  event.respondWith(
    (async () => {
      const hasToken = await hasValidFamilyToken();

      if (!hasToken) {
        // Return challenge page or 403
        return new Response('Family access required', {
          status: 403,
          headers: { 'Content-Type': 'text/plain' }
        });
      }

      // Proceed with normal caching/fetching
      return normalFetchHandler(event.request);
    })()
  );
});
```

### HTML Integration

```html
<!-- index.html - Gate script loads FIRST -->
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <!-- Gate script blocks everything until authenticated -->
  <script src="gate.js"></script>

  <!-- Rest of head only executes after gate passes -->
  <title>Grandma's Kitchen</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
  <!-- Content hidden until gate passes (CSS backup) -->
  <style>
    body:not(.authenticated) > *:not(#family-gate) {
      display: none !important;
    }
  </style>

  <!-- Normal content -->
  <header class="site-header">...</header>

  <!-- SW registration only after gate passes -->
  <script>
    if (window.FAMILY_GATE_PASSED) {
      document.body.classList.add('authenticated');
      // Register service worker
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/Grandmasrecipes/sw.js');
      }
    }
  </script>
  <script src="script.js"></script>
</body>
</html>
```

### Security Considerations

| Aspect | Reality | Mitigation |
|--------|---------|------------|
| Client-side only | Determined users can bypass | Acceptable for family site (not banking) |
| Hashes visible | In JS source code | Obfuscation, not security |
| Token in localStorage | Can be copied | Family trust model |
| No server validation | GitHub Pages limitation | Accept trade-off |

**This is "keep honest people honest" security**, not Fort Knox. The goal is:
1. Discourage casual visitors from accessing family content
2. Prevent search engine indexing of recipes
3. Make it clear this is a private family site
4. Keep the service worker from caching content for unauthorized users

For true security, you'd need a backend with proper authentication. This solution fits the GitHub Pages static site constraint.

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
