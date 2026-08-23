/* Vestra — Service Worker v6.6.6 hotfix */
const CACHE_NAME = "vestra-cache-v70";
const ASSETS = [
  "./", "./index.html", "./styles.css", "./market.css", "./app.js", "./market.js", "./manifest.webmanifest",
  "./icon192.png", "./icon512.png",
  "./icon192-maskable.png", "./icon512-maskable.png",
  "./apple-touch-icon.png", "./apple-touch-icon-167.png",
  "./apple-touch-icon-152.png", "./apple-touch-icon-120.png",
  "./favicon-32.png", "./favicon-16.png"
];

/*
  v6.6.6 runtime repair.
  The current app build contains two over-aggressive safeguards:
  1) it treats a Yahoo trading currency different from the broker/portfolio currency as a collision;
  2) it permanently rejects a correct quote when the previously cached baseline is already corrupted.
  Both are false for strong ticker/ISIN identities (US equities and USD LSE ETF listings are real examples).

  The quote-error modal also sits inside .main, whose CSS layout containment makes long position:fixed
  descendants unreliable/unscrollable on iOS Safari. Until the source bundle is rebuilt, this service
  worker appends a tiny runtime hotfix to app.js and injects the iOS-safe CSS.
*/
const VESTRA_APP_HOTFIX = `\n;/* Vestra v6.6.6 runtime quote/modal hotfix */\n(function(){\n  try {\n    var original = (typeof quoteSanityCheck === 'function') ? quoteSanityCheck : null;\n    var strong = function(asset){\n      try { return typeof hasStrongQuoteIdentitySafe === 'function' && hasStrongQuoteIdentitySafe(asset); } catch (_) { return false; }\n    };\n    if (original) {\n      quoteSanityCheck = function(asset, q, priceEur, rawTicker) {\n        var result = original(asset, q, priceEur, rawTicker);\n        if (!result || result.ok || !strong(asset)) return result;\n        var reason = String(result.reason || '');\n        if (/moeda\\s+[A-Z]{3}\\s+não coincide com\\s+[A-Z]{3}/i.test(reason)) {\n          console.warn('[Vestra v6.6.6] accepted legitimate cross-currency quote', asset && (asset.name || asset.ticker), q && q.currency);\n          return { ok:true, recovered:'cross-currency' };\n        }\n        if (/Cotação suspeita rejeitada/i.test(reason)) {\n          console.warn('[Vestra v6.6.6] accepted strong-identity quote over stale baseline', asset && (asset.name || asset.ticker));\n          return { ok:true, recovered:'stale-baseline' };\n        }\n        return result;\n      };\n    }\n\n    var style = document.createElement('style');\n    style.id = 'vestra-v666-ios-modal-hotfix';\n    style.textContent = '.main{contain:none!important}#modalQuoteErrors .modal__box{overflow-y:auto!important;-webkit-overflow-scrolling:touch!important;overscroll-behavior:contain!important;touch-action:pan-y!important;max-height:calc(100dvh - 28px)!important}';\n    document.head.appendChild(style);\n  } catch (e) { console.error('[Vestra v6.6.6 hotfix]', e); }\n})();\n`;

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)).catch(() => {})
  );
});

self.addEventListener("activate", event => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.map(k => k !== CACHE_NAME ? caches.delete(k) : Promise.resolve()));
    await self.clients.claim();
  })());
});

async function networkFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const fresh = await fetch(request);
    cache.put(request, fresh.clone()).catch(() => {});
    return fresh;
  } catch {
    const cached = await cache.match(request);
    return cached || new Response("Offline", { status: 503 });
  }
}

async function patchedAppJs(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const fresh = await fetch(request, { cache: "no-store" });
    let text = await fresh.text();
    if (!text.includes("Vestra v6.6.6 runtime quote/modal hotfix")) text += VESTRA_APP_HOTFIX;
    const headers = new Headers(fresh.headers);
    headers.set("content-type", "application/javascript; charset=utf-8");
    headers.set("cache-control", "no-store, max-age=0");
    const patched = new Response(text, { status: fresh.status, statusText: fresh.statusText, headers });
    cache.put(request, patched.clone()).catch(() => {});
    return patched;
  } catch (_) {
    const cached = await cache.match(request);
    if (cached) {
      let text = await cached.text();
      if (!text.includes("Vestra v6.6.6 runtime quote/modal hotfix")) text += VESTRA_APP_HOTFIX;
      return new Response(text, { headers: { "content-type": "application/javascript; charset=utf-8", "cache-control": "no-store" } });
    }
    return new Response("/* Vestra app unavailable offline */", { status: 503, headers: { "content-type": "application/javascript" } });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request).then(resp => {
    cache.put(request, resp.clone()).catch(() => {});
    return resp;
  }).catch(() => cached || new Response("Offline", { status: 503 }));
  return cached || fetchPromise;
}

self.addEventListener("fetch", event => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  if (url.pathname.endsWith("/app.js")) {
    event.respondWith(patchedAppJs(req));
    return;
  }

  if (req.mode === "navigate" || req.destination === "document") {
    event.respondWith(networkFirst(req));
    return;
  }

  if (["script", "style", "worker", "manifest"].includes(req.destination)) {
    event.respondWith(networkFirst(req));
    return;
  }

  event.respondWith(staleWhileRevalidate(req));
});
