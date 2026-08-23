/* Vestra — Service Worker v6.7.0 broker rebuild hotfix */
const CACHE_NAME = "vestra-cache-v72";
const ASSETS = [
  "./", "./index.html", "./styles.css", "./market.css", "./app.js", "./market.js", "./manifest.webmanifest",
  "./icon192.png", "./icon512.png",
  "./icon192-maskable.png", "./icon512-maskable.png",
  "./apple-touch-icon.png", "./apple-touch-icon-167.png",
  "./apple-touch-icon-152.png", "./apple-touch-icon-120.png",
  "./favicon-32.png", "./favicon-16.png"
];

const VESTRA_APP_HOTFIX = `\n;/* Vestra v6.7.0 runtime hotfix */\n(function(){\n  try {\n    var original = (typeof quoteSanityCheck === 'function') ? quoteSanityCheck : null;\n    var strong = function(asset){\n      try { return typeof hasStrongQuoteIdentitySafe === 'function' && hasStrongQuoteIdentitySafe(asset); } catch (_) { return false; }\n    };\n    if (original) {\n      quoteSanityCheck = function(asset, q, priceEur, rawTicker) {\n        var result = original(asset, q, priceEur, rawTicker);\n        if (!result || result.ok || !strong(asset)) return result;\n        var reason = String(result.reason || '');\n        if (/moeda\\s+[A-Z]{3}\\s+não coincide com\\s+[A-Z]{3}/i.test(reason)) return { ok:true, recovered:'cross-currency' };\n        if (/Cotação suspeita rejeitada/i.test(reason)) return { ok:true, recovered:'stale-baseline' };\n        return result;\n      };\n    }\n\n    var style = document.createElement('style');\n    style.id = 'vestra-v670-ios-modal-hotfix';\n    style.textContent = '.main{contain:none!important}#modalQuoteErrors .modal__box{overflow-y:auto!important;-webkit-overflow-scrolling:touch!important;overscroll-behavior:contain!important;touch-action:pan-y!important;max-height:calc(100dvh - 28px)!important}';\n    document.head.appendChild(style);\n\n    // v6.7.0: v6.6.9 changed broker reconstruction logic but did not bump the\n    // persisted rebuild schema. Existing devices therefore kept the corrupted\n    // generated mirror and never executed the repaired rebuild. Force it once.\n    window.addEventListener('load', function(){\n      setTimeout(async function(){\n        try {\n          if (typeof state === 'undefined' || !state) return;\n          if (!state.settings) state.settings = {};\n          if (state.settings.v670BrokerMirrorRebuilt) return;\n          if (typeof ensureBrokerData !== 'function' || typeof rebuildBrokerGeneratedData !== 'function') return;\n          var bd = ensureBrokerData();\n          if (!bd || (!((bd.events||[]).length) && !((bd.positions||[]).length))) return;\n          rebuildBrokerGeneratedData();\n          state.settings.v670BrokerMirrorRebuilt = true;\n          state.settings.brokerRebuildSchemaVersion = 45;\n          try { state.settings.brokerRebuildSig = typeof getBrokerDataSignature === 'function' ? getBrokerDataSignature() : state.settings.brokerRebuildSig; } catch (_) {}\n          if (typeof saveStateAsync === 'function') await saveStateAsync();\n          else if (typeof saveState === 'function') saveState();\n          if (typeof renderAll === 'function') renderAll();\n          console.warn('[Vestra v6.7.0] broker mirror rebuilt from stored source data');\n        } catch (e) { console.error('[Vestra v6.7.0 broker rebuild]', e); }\n      }, 1400);\n    }, { once:true });\n  } catch (e) { console.error('[Vestra v6.7.0 hotfix]', e); }\n})();\n`;

self.addEventListener("install", event => {
  self.skipWaiting();
  event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS)).catch(() => {}));
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
    if (!text.includes("Vestra v6.7.0 runtime hotfix")) text += VESTRA_APP_HOTFIX;
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
      if (!text.includes("Vestra v6.7.0 runtime hotfix")) text += VESTRA_APP_HOTFIX;
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
