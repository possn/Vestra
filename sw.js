/* Vestra — Service Worker v6.8.0 + Politicians explorer */
const CACHE_NAME = "vestra-cache-v83";
const ASSETS = [
  "./", "./index.html", "./styles.css", "./market.css", "./app.js", "./market.js", "./market-hotfix.js", "./politicians.js", "./manifest.webmanifest",
  "./icon192.png", "./icon512.png", "./icon192-maskable.png", "./icon512-maskable.png",
  "./apple-touch-icon.png", "./apple-touch-icon-167.png", "./apple-touch-icon-152.png", "./apple-touch-icon-120.png",
  "./favicon-32.png", "./favicon-16.png"
];

const VESTRA_APP_HOTFIX = `\n;/* Vestra v6.7.8 targeted broker quantity repair */\n(function(){\n  try {\n    var originalSanity = (typeof quoteSanityCheck === 'function') ? quoteSanityCheck : null;\n    var strongIdentity = function(asset){ try { return typeof hasStrongQuoteIdentitySafe === 'function' && hasStrongQuoteIdentitySafe(asset); } catch (_) { return false; } };\n    if (originalSanity) {\n      quoteSanityCheck = function(asset, q, priceEur, rawTicker) {\n        var result = originalSanity(asset, q, priceEur, rawTicker);\n        if (!result || result.ok || !strongIdentity(asset)) return result;\n        var reason = String(result.reason || '');\n        if (/moeda\\s+[A-Z]{3}\\s+não coincide com\\s+[A-Z]{3}/i.test(reason)) return { ok:true, recovered:'cross-currency' };\n        if (/Cotação suspeita rejeitada/i.test(reason)) return { ok:true, recovered:'stale-baseline' };\n        return result;\n      };\n    }\n\n    var style = document.createElement('style');\n    style.id = 'vestra-v678-ios-quote-modal';\n    style.textContent = '.main{contain:none!important}#modalQuoteErrors{position:fixed!important;inset:0!important;overflow-y:auto!important;-webkit-overflow-scrolling:touch!important;touch-action:pan-y!important;overscroll-behavior:contain!important}#modalQuoteErrors .modal__box{height:auto!important;max-height:none!important;overflow:visible!important;margin:12px auto 40px!important}';\n    document.head.appendChild(style);\n\n    function isGlobalX(a){ var n=String((a&&a.name)||'').toUpperCase(); var i=String((a&&a.isin)||'').toUpperCase(); return i==='IE00BLCHJ534' || n.indexOf('GLOBAL X US INFRASTRUCTURE')>=0; }\n    function isSiemens(a){ var n=String((a&&a.name)||'').toUpperCase(); var i=String((a&&a.isin)||'').toUpperCase(); return i==='DE000SHL1006' || n.indexOf('SIEMENS HEALTHINEERS')>=0; }\n\n    async function repairTwoRemainingPositions(){\n      try {\n        if (typeof state === 'undefined' || !state) return;\n        if (!state.settings) state.settings = {};\n        if (state.settings.v678TwoQtyFixed) return;\n        var changed=false;\n\n        (state.assets||[]).forEach(function(a){\n          if (!a || (!isGlobalX(a) && !isSiemens(a))) return;\n          a.qty = 1;\n          if (a.notes) a.notes = String(a.notes).replace(/Qty=[\\d.,]+/i,'Qty=1');\n          if (isGlobalX(a)) { a.yahooTicker='94VE.DE'; }\n          if (isSiemens(a)) { a.yahooTicker='SHL.DE'; }\n          var lp = Number(a.lastPriceEur || 0);\n          var cb = Number(a.costBasis || 0);\n          if (lp > 0 && lp < 1000) a.value = lp;\n          else if (cb > 0 && cb < 1000) a.value = cb;\n          else a.value = 0;\n          delete a.valueLocal;\n          changed=true;\n        });\n\n        if (typeof ensureBrokerData === 'function') {\n          var bd=ensureBrokerData();\n          if (bd) (bd.positions||[]).forEach(function(p){\n            if (!p || (!isGlobalX(p) && !isSiemens(p))) return;\n            p.qty=1;\n            if (isGlobalX(p)) p.ticker='94VE.DE';\n            if (isSiemens(p)) p.ticker='SHL.DE';\n            var mv=Number(p.marketValueEUR||0), cb=Number(p.costBasisEUR||0);\n            if (mv>1000) p.marketValueEUR = (cb>0 && cb<1000) ? cb : 0;\n            changed=true;\n          });\n        }\n\n        state.settings.v678TwoQtyFixed=true;\n        if (changed) {\n          if (typeof saveStateAsync === 'function') await saveStateAsync(); else if (typeof saveState === 'function') saveState();\n          if (typeof renderAll === 'function') renderAll();\n        }\n      } catch(e){ console.error('[Vestra v6.7.8 targeted qty repair]',e); }\n    }\n\n    window.addEventListener('load', function(){ setTimeout(repairTwoRemainingPositions,500); }, {once:true});\n  } catch(e){ console.error('[Vestra v6.7.8 hotfix]',e); }\n})();\n`;

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
async function patchedDocument(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const fresh = await fetch(request, { cache: "no-store" });
    let text = await fresh.text();
    if (!text.includes('market-hotfix.js')) {
      text = text.replace(/<\/body>/i, '<script src="./market-hotfix.js?v=4.47"></script></body>');
    }
    if (!text.includes('politicians.js')) {
      text = text.replace(/<\/body>/i, '<script src="./politicians.js?v=1.0"></script></body>');
    }
    const headers = new Headers(fresh.headers);
    headers.set('content-type','text/html; charset=utf-8');
    headers.set('cache-control','no-store, max-age=0');
    const patched = new Response(text,{status:fresh.status,statusText:fresh.statusText,headers});
    cache.put(request,patched.clone()).catch(()=>{});
    return patched;
  } catch (_) {
    const cached=await cache.match(request);
    if(cached){
      let text=await cached.text();
      if(!text.includes('market-hotfix.js')) text=text.replace(/<\/body>/i,'<script src="./market-hotfix.js?v=4.47"></script></body>');
      if(!text.includes('politicians.js')) text=text.replace(/<\/body>/i,'<script src="./politicians.js?v=1.0"></script></body>');
      return new Response(text,{headers:{'content-type':'text/html; charset=utf-8','cache-control':'no-store'}});
    }
    return new Response('Offline',{status:503});
  }
}
async function patchedAppJs(request) {
  const cache = await caches.open(CACHE_NAME);
  try {
    const fresh = await fetch(request, { cache: "no-store" });
    let text = await fresh.text();
    if (!text.includes("Vestra v6.7.8 targeted broker quantity repair")) text += VESTRA_APP_HOTFIX;
    const headers = new Headers(fresh.headers);
    headers.set("content-type", "application/javascript; charset=utf-8");
    headers.set("cache-control", "no-store, max-age=0");
    const patched = new Response(text, { status:fresh.status, statusText:fresh.statusText, headers });
    cache.put(request, patched.clone()).catch(() => {});
    return patched;
  } catch (_) {
    const cached = await cache.match(request);
    if (cached) {
      let text = await cached.text();
      if (!text.includes("Vestra v6.7.8 targeted broker quantity repair")) text += VESTRA_APP_HOTFIX;
      return new Response(text, { headers:{"content-type":"application/javascript; charset=utf-8","cache-control":"no-store"} });
    }
    return new Response("/* Vestra app unavailable offline */", {status:503, headers:{"content-type":"application/javascript"}});
  }
}
async function staleWhileRevalidate(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  const fetchPromise = fetch(request, {cache:"no-store"}).then(resp => { cache.put(request, resp.clone()).catch(()=>{}); return resp; }).catch(() => cached || new Response("Offline", {status:503}));
  return cached || fetchPromise;
}
self.addEventListener("fetch", event => {
  const req=event.request;
  if (req.method!=="GET") return;
  const url=new URL(req.url);
  if (url.origin!==self.location.origin) return;
  if (url.pathname.endsWith("/app.js")) { event.respondWith(patchedAppJs(req)); return; }
  if (req.mode==="navigate" || req.destination==="document") { event.respondWith(patchedDocument(req)); return; }
  if (["script","style","worker","manifest"].includes(req.destination)) { event.respondWith(networkFirst(req)); return; }
  event.respondWith(staleWhileRevalidate(req));
});
