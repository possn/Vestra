/* Vestra Service Worker v10.73 — reliable portfolio sector classification. */
const CACHE_NAME = "vestra-cache-v186";
const NETWORK_TIMEOUT_MS = 5000;
const APP_SHELL = [
  "./", "./index.html", "./styles.css", "./market.css", "./app.js",
  "./app-utils.js", "./app-feedback.js", "./app-storage.js", "./app-asset-identity.js", "./app-ui-core.js", "./app-xlsx-loader.js",
  "./app-broker-normalization.js", "./app-xtb-normalization.js", "./app-broker-identity-data.js",
  "./app-broker-parsing-core.js", "./app-file-parsing.js", "./app-broker-import-loader.js", "./app-broker-workbook.js", "./app-broker-parsers.js",
  "./app-market-client.js", "./app-quote-errors.js", "./app-return-assumptions.js", "./app-financial-engine.js", "./app-export-runtime.js", "./app-runtime-bridge.js",
  "./market.js", "./market-runtime-loader.js", "./market-live-overlay.js", "./market-congress-live.js", "./market-portfolio-context.js",
  "./market-watch-snapshots.js", "./market-static-universe.js", "./market-scanner-data.js",
  "./market-analysis-tools-runtime.js", "./market-analysis-tools-runtime.css", "./market-etf-intelligence.js", "./dashboard-weekly-events.js",
  "./dashboard-weekly-events-navigation.js", "./dashboard-ui-refresh.js", "./dashboard-daily-news.js", "./dashboard-daily-news.css", "./ui-visual-polish.js", "./market-dossier-signals.js", "./market-search-suggestions.js",
  "./market-row-ui.js", "./market-data-loader.js", "./market-data-health.js", "./market-data-health.css", "./market-company-brief.js", "./market-company-brief.css",
  "./market-metric-cleanup.js", "./market-dossier-controls.js", "./market-dossier-controls.css", "./market-ui-polish.js", "./market-stock-themes-tools.js", "./portfolio-collapsibles.js", "./portfolio-collapsibles.css",
  "./portfolio-sheet-navigation.js", "./portfolio-sheet-navigation.css", "./portfolio-card-classifier.js", "./portfolio-card-classifier.css", "./market-opportunities.js", "./market-opportunities.css",
  "./market-metals.js", "./market-metals.css", "./market-model-validation.js", "./market-model-validation.css",
  "./quote-canonical-repair.js", "./market-global-search.js", "./market-learned-universe.js",
  "./vestra-portfolio-focus.js", "./vestra-portfolio-focus.css", "./vestra-portfolio-hierarchy.js", "./vestra-portfolio-hierarchy.css", "./vestra-swap-lab.js", "./vestra-swap-lab.css",
  "./market-opportunity-lenses.js", "./market-opportunity-lenses.css", "./mobile-ui-refresh.js", "./vestra-ai-brief.js", "./vestra-ai-brief.css", "./vestra-portfolio-ui.js", "./vestra-portfolio-ui.css",
  "./portfolio-diagnostics.js", "./portfolio-diagnostics.css", "./portfolio-dossier-routing.js", "./politicians.js", "./politicians.css", "./market-global-search.css", "./market-stock-themes-tools.css", "./data/executives.json",
  "./manifest.webmanifest", "./icon192.png", "./icon512.png", "./icon192-maskable.png", "./icon512-maskable.png",
  "./apple-touch-icon.png", "./apple-touch-icon-167.png", "./apple-touch-icon-152.png", "./apple-touch-icon-120.png",
  "./favicon-32.png", "./favicon-16.png", "./data/portfolio-sectors.json"
];

const BOOTSTRAP_NETWORK_FIRST = new Set([
  "app-utils.js", "app-feedback.js", "app-storage.js", "app-asset-identity.js", "app-ui-core.js", "app-xlsx-loader.js",
  "app-broker-normalization.js", "app-xtb-normalization.js", "app-broker-identity-data.js", "app-broker-parsing-core.js",
  "app-file-parsing.js", "app-broker-import-loader.js", "app-broker-workbook.js", "app-broker-parsers.js", "app-market-client.js", "app-quote-errors.js",
  "app-return-assumptions.js", "app-financial-engine.js", "app-export-runtime.js", "app.js", "market-runtime-loader.js", "market-live-overlay.js",
  "market-data-loader.js", "market-data-health.js", "market-portfolio-context.js", "market-static-universe.js",
  "market-scanner-data.js", "market-analysis-tools-runtime.js", "market-etf-intelligence.js", "dashboard-weekly-events.js",
  "dashboard-weekly-events-navigation.js", "dashboard-daily-news.js", "market-dossier-controls.js", "market-ui-polish.js", "market-opportunities.js",
  "market-opportunity-lenses.js", "mobile-ui-refresh.js", "vestra-ai-brief.js", "politicians.js"
]);

async function precacheAsset(cache, asset) {
  const fresh = await fetchWithTimeout(asset, { cache: "no-store" });
  if (!fresh || !fresh.ok) throw new Error(`Precache failed: ${asset}`);
  await cache.put(asset, fresh.clone());
}

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await Promise.all(APP_SHELL.map(asset => precacheAsset(cache, asset)));
  })());
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map(key => key === CACHE_NAME ? Promise.resolve() : caches.delete(key)));
    await self.clients.claim();
  })());
});

async function matchCached(cache, request) {
  const exact = await cache.match(request);
  if (exact) return exact;
  return cache.match(request, { ignoreSearch: true });
}

async function fetchWithTimeout(request, options = {}, timeoutMs = NETWORK_TIMEOUT_MS) {
  const controller = typeof AbortController === "function" ? new AbortController() : null;
  const fetchOptions = { ...options };
  if (controller) fetchOptions.signal = controller.signal;
  let timeoutId = null;
  const timeout = new Promise((_, reject) => {
    timeoutId = setTimeout(() => {
      try { if (controller) controller.abort(); } catch (_) {}
      reject(new Error("Network timeout"));
    }, Math.max(1, Number(timeoutMs) || NETWORK_TIMEOUT_MS));
  });
  try {
    return await Promise.race([fetch(request, fetchOptions), timeout]);
  } finally {
    if (timeoutId !== null) clearTimeout(timeoutId);
  }
}

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const fresh = await fetchWithTimeout(request, { cache: "no-store" });
    if (fresh && fresh.ok) {
      try { await cache.put(request, fresh.clone()); } catch (_) {}
      return fresh;
    }
    const cached = await matchCached(cache, request);
    return cached || fresh || new Response("Offline", { status: 503 });
  } catch (_) {
    const cached = await matchCached(cache, request);
    return cached || new Response("Offline", { status: 503 });
  }
}

async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await matchCached(cache, request);
  if (cached) return cached;
  try {
    const fresh = await fetchWithTimeout(request);
    if (fresh && fresh.ok) cache.put(request, fresh.clone()).catch(() => {});
    return fresh;
  } catch (_) {
    return new Response("Offline", { status: 503 });
  }
}

async function staleWhileRevalidate(request, event) {
  const cache = await caches.open(CACHE_NAME);
  const exact = await cache.match(request);
  const hasVersionQuery = (() => {
    try { return new URL(request.url).search.length > 0; } catch (_) { return false; }
  })();
  const refresh = fetchWithTimeout(request, { cache: "no-store" })
    .then(fresh => {
      if (fresh && fresh.ok) cache.put(request, fresh.clone()).catch(() => {});
      return fresh;
    }).catch(() => null);

  if (exact) {
    if (event && typeof event.waitUntil === "function") event.waitUntil(refresh.then(() => {}));
    return exact;
  }

  // A versioned runtime URL is an explicit request for a new generation.
  // Do not satisfy it immediately from an older ignoreSearch cache entry.
  // Try the network first; only fall back to the unversioned precache offline.
  if (hasVersionQuery) {
    const fresh = await refresh;
    if (fresh) return fresh;
    const fallback = await cache.match(request, { ignoreSearch: true });
    return fallback || new Response("Offline", { status: 503 });
  }

  const cached = await matchCached(cache, request);
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
    event.respondWith(networkFirst(request)); return;
  }
  const assetName = url.pathname.split("/").filter(Boolean).pop() || "";
  if (request.destination === "style") {
    // Layout regressions are particularly visible in installed iOS PWAs. CSS
    // version query strings must not be satisfied from an older ignoreSearch
    // cache entry before the network has had a chance to return the new file.
    // networkFirst still preserves full offline fallback through matchCached().
    event.respondWith(networkFirst(request)); return;
  }
  if (request.destination === "script" && BOOTSTRAP_NETWORK_FIRST.has(assetName)) {
    event.respondWith(networkFirst(request)); return;
  }
  if (["script", "worker", "manifest"].includes(request.destination)) {
    event.respondWith(staleWhileRevalidate(request, event)); return;
  }
  if (/\/data\/.*\.(json|txt)$/i.test(url.pathname)) {
    event.respondWith(networkFirst(request)); return;
  }
  if (request.destination === "image") event.respondWith(cacheFirst(request));
});
