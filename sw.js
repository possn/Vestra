/* Vestra Service Worker v10.13 — fast static shell + fresh market data. */
const CACHE_NAME = "vestra-cache-v127";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./market.css",
  "./app.js",
  "./app-utils.js",
  "./app-feedback.js",
  "./app-storage.js",
  "./app-asset-identity.js",
  "./app-ui-core.js",
  "./app-broker-normalization.js",
  "./app-xtb-normalization.js",
  "./app-broker-identity-data.js",
  "./app-broker-parsing-core.js",
  "./app-file-parsing.js",
  "./app-broker-workbook.js",
  "./app-broker-parsers.js",
  "./app-market-client.js",
  "./app-quote-errors.js",
  "./app-return-assumptions.js",
  "./app-financial-engine.js",
  "./market.js",
  "./market-live-overlay.js",
  "./market-congress-live.js",
  "./market-portfolio-context.js",
  "./market-watch-snapshots.js",
  "./market-static-universe.js",
  "./market-dossier-signals.js",
  "./market-search-suggestions.js",
  "./market-row-ui.js",
  "./market-data-loader.js",
  "./market-company-brief.js",
  "./market-metric-cleanup.js",
  "./portfolio-collapsibles.js",
  "./portfolio-sheet-navigation.js",
  "./portfolio-card-classifier.js",
  "./market-opportunities.js",
  "./vestra-portfolio-focus.js",
  "./vestra-portfolio-hierarchy.js",
  "./vestra-swap-lab.js",
  "./market-opportunity-lenses.js",
  "./vestra-ai-brief.js",
  "./vestra-portfolio-ui.js",
  "./portfolio-diagnostics.js",
  "./portfolio-dossier-routing.js",
  "./politicians.js",
  "./data/executives.json",
  "./manifest.webmanifest",
  "./icon192.png",
  "./icon512.png",
  "./icon192-maskable.png",
  "./icon512-maskable.png",
  "./apple-touch-icon.png",
  "./apple-touch-icon-167.png",
  "./apple-touch-icon-152.png",
  "./apple-touch-icon-120.png",
  "./favicon-32.png",
  "./favicon-16.png"
];

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    // One optional/missing shell file must not make the whole offline shell empty.
    await Promise.allSettled(APP_SHELL.map(asset => cache.add(asset)));
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map(key => key === CACHE_NAME ? Promise.resolve() : caches.delete(key)));
    await self.clients.claim();
  })());
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const fresh = await fetch(request, { cache: "no-store" });
    if (fresh && fresh.ok) cache.put(request, fresh.clone()).catch(() => {});
    return fresh;
  } catch (_) {
    const cached = await cache.match(request);
    return cached || new Response("Offline", { status: 503 });
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  if (cached) return cached;
  try {
    const fresh = await fetch(request);
    if (fresh && fresh.ok) cache.put(request, fresh.clone()).catch(() => {});
    return fresh;
  } catch (_) {
    return new Response("Offline", { status: 503 });
  }
}

async function staleWhileRevalidate(request, event) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const refresh = fetch(request, { cache: "no-store" })
    .then(fresh => {
      if (fresh && fresh.ok) cache.put(request, fresh.clone()).catch(() => {});
      return fresh;
    })
    .catch(() => null);

  if (cached) {
    if (event && typeof event.waitUntil === "function") event.waitUntil(refresh.then(() => {}));
    return cached;
  }

  const fresh = await refresh;
  return fresh || new Response("Offline", { status: 503 });
}

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate" || request.destination === "document") {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static code is versioned by the app shell URLs. Serve an already-cached copy
  // immediately on repeat launches and refresh it in the background. This avoids
  // making iOS standalone startup wait for GitHub Pages/network latency every time.
  if (["script", "style", "worker", "manifest"].includes(request.destination)) {
    event.respondWith(staleWhileRevalidate(request, event));
    return;
  }

  // Market payloads intentionally remain network-first: freshness is more
  // important than shaving a few ms and offline still falls back to the cache.
  if (/\/data\/.*\.(json|txt)$/i.test(url.pathname)) {
    event.respondWith(networkFirst(request));
    return;
  }

  if (request.destination === "image") {
    event.respondWith(cacheFirst(request));
  }
});