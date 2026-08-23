/* Vestra — Service Worker v6.7.3 broker truth runtime repair */
const CACHE_NAME = "vestra-cache-v74";
const ASSETS = [
  "./", "./index.html", "./styles.css", "./market.css", "./app.js", "./market.js", "./manifest.webmanifest",
  "./icon192.png", "./icon512.png",
  "./icon192-maskable.png", "./icon512-maskable.png",
  "./apple-touch-icon.png", "./apple-touch-icon-167.png",
  "./apple-touch-icon-152.png", "./apple-touch-icon-120.png",
  "./favicon-32.png", "./favicon-16.png"
];

const VESTRA_APP_HOTFIX = `\n;/* Vestra v6.7.3 runtime broker-truth hotfix */\n(function(){\n  try {\n    var originalSanity = (typeof quoteSanityCheck === 'function') ? quoteSanityCheck : null;\n    var strong = function(asset){\n      try { return typeof hasStrongQuoteIdentitySafe === 'function' && hasStrongQuoteIdentitySafe(asset); } catch (_) { return false; }\n    };\n    if (originalSanity) {\n      quoteSanityCheck = function(asset, q, priceEur, rawTicker) {\n        var result = originalSanity(asset, q, priceEur, rawTicker);\n        if (!result || result.ok || !strong(asset)) return result;\n        var reason = String(result.reason || '');\n        if (/moeda\\s+[A-Z]{3}\\s+não coincide com\\s+[A-Z]{3}/i.test(reason)) return { ok:true, recovered:'cross-currency' };\n        if (/Cotação suspeita rejeitada/i.test(reason)) return { ok:true, recovered:'stale-baseline' };\n        return result;\n      };\n    }\n\n    // Proven broker identities from the actual imported statements.\n    if (typeof getKnownBrokerYahooOverride === 'function') {\n      var oldOverride = getKnownBrokerYahooOverride;\n      getKnownBrokerYahooOverride = function(x) {\n        x = x || {};\n        var i = String(x.isin || '').trim().toUpperCase();\n        var t = String(x.ticker || '').trim().toUpperCase();\n        if (i === 'IE00BLCHJ534') return '94VE.DE';\n        if (i === 'DE000SHL1006') return 'SHL.DE';\n        if (i === 'US58463J3041' || t === 'MPT') return 'MPW';\n        return oldOverride(x);\n      };\n    }\n\n    var style = document.createElement('style');\n    style.id = 'vestra-v673-ios-modal-hotfix';\n    style.textContent = '.main{contain:none!important}#modalQuoteErrors .modal__box{overflow-y:auto!important;-webkit-overflow-scrolling:touch!important;overscroll-behavior:contain!important;touch-action:pan-y!important;max-height:calc(100dvh - 28px)!important}';\n    document.head.appendChild(style);\n\n    function baseTicker(x){\n      var t = String((x && (x.ticker || x.yahooTicker)) || '').trim().toUpperCase();\n      if (!t) return '';\n      return t.replace(/\\.(US|DE|L|PA|AS|MC|MI|SW|TO|CO|ST|LS|HE|BR|AX|F|VI|WA|OL|SG|IR)$/,'');\n    }\n\n    async function repairBrokerTruth(){\n      try {\n        if (typeof state === 'undefined' || !state) return;\n        if (!state.settings) state.settings = {};\n        if (state.settings.v673BrokerTruthRepaired) return;\n        if (typeof ensureBrokerData !== 'function') return;\n        var bd = ensureBrokerData();\n        if (!bd || (!((bd.events||[]).length) && !((bd.positions||[]).length))) return;\n\n        // Rebuild the generated broker mirror once from the stored source ledger.\n        if (typeof rebuildBrokerGeneratedData === 'function') rebuildBrokerGeneratedData();\n\n        var snapshotBases = new Set();\n        (bd.positions || []).forEach(function(p){\n          if (!p || !(p.positionKind === 'market_snapshot' || p.positionKind === 'cost_snapshot')) return;\n          var k = baseTicker(p); if (k) snapshotBases.add(k);\n        });\n\n        var net = new Map(), hasLedger = new Set();\n        (bd.events || []).forEach(function(e){\n          if (!e || (e.type !== 'BUY' && e.type !== 'SELL')) return;\n          var k = baseTicker(e); if (!k) return;\n          var q = Math.abs(typeof parseQty === 'function' ? parseQty(e.qty) : (typeof parseNum === 'function' ? parseNum(e.qty) : Number(e.qty||0)));\n          if (!Number.isFinite(q)) q = 0;\n          hasLedger.add(k);\n          net.set(k, (net.get(k)||0) + (e.type === 'BUY' ? q : -q));\n        });\n\n        // A security with a complete BUY/SELL ledger netting to zero and no current snapshot\n        // is closed. It must not survive as a portfolio asset (e.g. OD7F.DE / WTI).\n        state.assets = (state.assets || []).filter(function(a){\n          if (!a || !a.generatedFromBroker) return true;\n          var k = baseTicker(a);\n          if (!k || snapshotBases.has(k) || !hasLedger.has(k)) return true;\n          return Math.abs(net.get(k)||0) > 1e-8;\n        });\n\n        // Repair the three identities proven by the supplied broker files.\n        (state.assets || []).forEach(function(a){\n          if (!a || !a.generatedFromBroker) return;\n          var isin = String(a.isin || '').toUpperCase();\n          var nm = String(a.name || '').toUpperCase();\n          if (isin === 'IE00BLCHJ534' || nm.indexOf('GLOBAL X US INFRASTRUCTURE') >= 0) { a.yahooTicker='94VE.DE'; a.ticker=a.ticker || 'PAVE'; }\n          if (isin === 'DE000SHL1006' || nm.indexOf('SIEMENS HEALTHINEERS') >= 0) { a.yahooTicker='SHL.DE'; a.ticker=a.ticker || 'SHL'; }\n          if (isin === 'US58463J3041' || nm.indexOf('MEDICAL PROPERTIES') >= 0) { a.yahooTicker='MPW'; }\n\n          // Catastrophic valuation guard. A quote collision must never turn a €30–€100\n          // holding into tens of thousands. Reset to broker cost until a valid quote lands.\n          var cb = typeof parseNum === 'function' ? parseNum(a.costBasis || 0) : Number(a.costBasis||0);\n          var v = typeof parseNum === 'function' ? parseNum(a.value || 0) : Number(a.value||0);\n          if (cb > 1 && v > cb * 100) {\n            a.value = cb;\n            delete a.valueLocal;\n            delete a.lastPriceEur;\n          }\n        });\n\n        state.settings.v673BrokerTruthRepaired = true;\n        state.settings.brokerRebuildSchemaVersion = 47;\n        try { if (typeof getBrokerDataSignature === 'function') state.settings.brokerRebuildSig = getBrokerDataSignature(); } catch (_) {}\n        if (typeof saveStateAsync === 'function') await saveStateAsync();\n        else if (typeof saveState === 'function') saveState();\n        if (typeof renderAll === 'function') renderAll();\n\n        // Refresh after the mirror is sane; identity overrides above are already active.\n        setTimeout(function(){ try { if (typeof refreshLiveQuotes === 'function') refreshLiveQuotes(); } catch (_) {} }, 700);\n      } catch (e) { console.error('[Vestra v6.7.3 broker truth repair]', e); }\n    }\n\n    window.addEventListener('load', function(){ setTimeout(repairBrokerTruth, 900); }, { once:true });\n  } catch (e) { console.error('[Vestra v6.7.3 hotfix]', e); }\n})();\n`;

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
    if (!text.includes("Vestra v6.7.3 runtime broker-truth hotfix")) text += VESTRA_APP_HOTFIX;
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
      if (!text.includes("Vestra v6.7.3 runtime broker-truth hotfix")) text += VESTRA_APP_HOTFIX;
      return new Response(text, { headers: { "content-type": "application/javascript; charset=utf-8", "cache-control": "no-store" } });
    }
    return new Response("/* Vestra app unavailable offline */", { status: 503, headers: { "content-type": "application/javascript" } });
  }
}

async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request, { cache: "no-store" }).then(resp => {
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
