/* Vestra Service Worker v7.5 — cache/offline infrastructure only. */
const CACHE_NAME = "vestra-cache-v89";
const APP_SHELL = [
  "./",
  "./index.html",
  "./styles.css",
  "./market.css",
  "./app.js",
  "./app-utils.js",
  "./market.js",
  "./market-hotfix.js",
  "./market-data-loader.js",
  "./market-opportunity-lenses.js",
  "./vestra-portfolio-ui.js",
  "./market-close-controller.js",
  "./politicians.js",
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
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(APP_SHELL))
      .catch(() => {})
  );
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

self.addEventListener("fetch", event => {
  const request = event.request;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;

  if (request.mode === "navigate" || request.destination === "document") {
    event.respondWith(networkFirst(request));
    return;
  }

  if (["script", "style", "worker", "manifest"].includes(request.destination)) {
    event.respondWith(networkFirst(request));
    return;
  }

  if (/\/data\/.*\.(json|txt)$/i.test(url.pathname)) {
    event.respondWith(networkFirst(request));
    return;
  }

  if (request.destination === "image" || /\.(png|jpg|jpeg|webp|svg|ico)$/i.test(url.pathname)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  event.respondWith(networkFirst(request));
});
