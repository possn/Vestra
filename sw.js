/* Vestra — Service Worker v6.7.5 closed-position repair */
const CACHE_NAME = "vestra-cache-v76";
const ASSETS = [
  "./", "./index.html", "./styles.css", "./market.css", "./app.js", "./market.js", "./manifest.webmanifest",
  "./icon192.png", "./icon512.png",
  "./icon192-maskable.png", "./icon512-maskable.png",
  "./apple-touch-icon.png", "./apple-touch-icon-167.png",
  "./apple-touch-icon-152.png", "./apple-touch-icon-120.png",
  "./favicon-32.png", "./favicon-16.png"
];

const VESTRA_APP_HOTFIX = `\n;/* Vestra v6.7.5 runtime closed-position repair */\n(function(){\n  try {\n    var style = document.createElement('style');\n    style.id = 'vestra-v675-ios-modal-hotfix';\n    style.textContent = '.main{contain:none!important}#modalQuoteErrors .modal__box{overflow-y:auto!important;-webkit-overflow-scrolling:touch!important;overscroll-behavior:contain!important;touch-action:pan-y!important;max-height:calc(100dvh - 28px)!important}';\n    document.head.appendChild(style);\n\n    async function repairClosedWTI(){\n      try {\n        if (typeof state === 'undefined' || !state) return;\n        if (!state.settings) state.settings = {};\n        var changed = false;\n\n        // The supplied XTB statement proves OD7F.DE / WTI Crude Oil has no current open position.\n        // Remove any stale generated mirror regardless of which old ticker alias it carries.\n        var before = (state.assets || []).length;\n        state.assets = (state.assets || []).filter(function(a){\n          if (!a || !a.generatedFromBroker) return true;\n          var nm = String(a.name || '').trim().toUpperCase();\n          var tk = String(a.ticker || '').trim().toUpperCase();\n          var yt = String(a.yahooTicker || '').trim().toUpperCase();\n          var notes = String(a.notes || '').toUpperCase();\n          var isWTI = nm.indexOf('WTI CRUDE OIL') >= 0 || tk === 'OD7F.DE' || tk === 'OD7F' || yt === 'OD7F.DE' || yt === 'OD7F' || notes.indexOf('OD7F.DE') >= 0;\n          if (isWTI) { changed = true; return false; }\n          return true;\n        });\n        if ((state.assets || []).length !== before) changed = true;\n\n        // Remove any persisted broker position mirror for the same closed instrument so rebuilds cannot resurrect it.\n        if (typeof ensureBrokerData === 'function') {\n          var bd = ensureBrokerData();\n          if (bd) {\n            var pb = (bd.positions || []).length;\n            bd.positions = (bd.positions || []).filter(function(p){\n              var nm = String((p && p.name) || '').toUpperCase();\n              var tk = String((p && p.ticker) || '').toUpperCase();\n              return !(nm.indexOf('WTI CRUDE OIL') >= 0 || tk === 'OD7F.DE' || tk === 'OD7F');\n            });\n            if ((bd.positions || []).length !== pb) changed = true;\n          }\n        }\n\n        state.settings.v675ClosedWtiRepaired = true;\n        if (changed) {\n          if (typeof saveStateAsync === 'function') await saveStateAsync();\n          else if (typeof saveState === 'function') saveState();\n          if (typeof renderAll === 'function') renderAll();\n        }\n      } catch (e) { console.error('[Vestra v6.7.5 WTI repair]', e); }\n    }\n\n    // Do not force a quote refresh here. The app's normal 30-minute stale policy owns refresh cadence.\n    window.addEventListener('load', function(){ setTimeout(repairClosedWTI, 500); }, { once:true });\n  } catch (e) { console.error('[Vestra v6.7.5 hotfix]', e); }\n})();\n`;

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
    const fresh = await fetch(request, { cache: "no-store" });
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
    if (!text.includes("Vestra v6.7.5 runtime closed-position repair")) text += VESTRA_APP_HOTFIX;
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
      if (!text.includes("Vestra v6.7.5 runtime closed-position repair")) text += VESTRA_APP_HOTFIX;
      return new Response(text, { headers: { "content-type": "application/javascript; charset=utf-8", "cache-control":"no-store" } });
    }
    return new Response("/* Vestra app unavailable offline */", { status: 503, headers: { "content-type":"application/javascript" } });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request, { cache: "no-store" }).then(resp => {
    cache.put(request, resp.clone()).catch(() => {});
    return resp;
  }).catch(() => cached || new Response("Offline", { status:503 }));
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
