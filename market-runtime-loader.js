/* Vestra Market Runtime Loader v1.1 — defer heavy market UI until first use. */
(() => {
  'use strict';

  const MODULE_TIMEOUT_MS = 8000;
  const CORE_MODULES = Object.freeze([
    'market-live-overlay.js?v=1.2',
    'market-congress-live.js?v=1.0',
    'market-portfolio-context.js?v=1.0',
    'market-watch-snapshots.js?v=1.0',
    'market-dossier-signals.js?v=1.0',
    'market-search-suggestions.js?v=1.2',
    'market-row-ui.js?v=1.0',
    'market.js?v=20260831v2',
    'market-data-loader.js?v=2.5',
  ]);
  const ENHANCEMENT_MODULES = Object.freeze([
    'market-metals.js?v=1.0',
    'market-company-brief.js?v=1.0',
    'market-metric-cleanup.js?v=1.0',
    'portfolio-collapsibles.js?v=1.2',
    'portfolio-card-classifier.js?v=1.2',
    'market-opportunities.js?v=1.1',
    'vestra-portfolio-focus.js?v=1.0',
    'vestra-portfolio-hierarchy.js?v=1.3',
    'vestra-swap-lab.js?v=1.0',
    'market-opportunity-lenses.js?v=1.0',
    'vestra-ai-brief.js?v=1.0',
    'vestra-portfolio-ui.js?v=1.1',
    'portfolio-diagnostics.js?v=1.0',
    'portfolio-dossier-routing.js?v=1.0',
    'politicians.js?v=2.1',
  ]);
  const MODULES = Object.freeze([...CORE_MODULES, ...ENHANCEMENT_MODULES]);

  let runtimePromise = null;
  let enhancementsPromise = null;

  function modulePath(src) {
    return String(src || '').split('?')[0];
  }

  function existingModule(src) {
    const path = modulePath(src);
    return [...document.scripts].find(script => {
      try {
        const url = new URL(script.src, document.baseURI);
        return url.pathname.endsWith('/' + path) || url.pathname === '/' + path;
      } catch (_) {
        return false;
      }
    }) || null;
  }

  function loadModule(src) {
    if (typeof document === 'undefined') return Promise.reject(new Error('Market runtime sem DOM.'));
    if (existingModule(src)) return Promise.resolve();

    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      let settled = false;
      let timeoutId = null;
      const cleanup = () => {
        if (timeoutId !== null) clearTimeout(timeoutId);
        script.removeEventListener('load', onLoad);
        script.removeEventListener('error', onError);
      };
      const finish = error => {
        if (settled) return;
        settled = true;
        cleanup();
        if (error) {
          if (script.isConnected) script.remove();
          reject(error);
          return;
        }
        script.dataset.vestraMarketRuntimeLoaded = '1';
        resolve();
      };
      const onLoad = () => finish(null);
      const onError = () => finish(new Error('Falha a carregar ' + src));

      script.src = src;
      script.async = false;
      script.dataset.vestraMarketRuntimeModule = modulePath(src);
      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      timeoutId = setTimeout(() => finish(new Error('Timeout a carregar ' + src)), MODULE_TIMEOUT_MS);
      document.head.appendChild(script);
    });
  }

  async function loadSequence(modules) {
    for (const src of modules) await loadModule(src);
  }

  function ensureEnhancements() {
    if (!enhancementsPromise) {
      enhancementsPromise = loadSequence(ENHANCEMENT_MODULES).catch(error => {
        enhancementsPromise = null;
        console.warn('[MarketRuntime] enhancement load failed', error);
        return false;
      });
    }
    return enhancementsPromise;
  }

  async function loadCore() {
    await loadSequence(CORE_MODULES);
    const api = window.VestraMarket;
    if (!api?.ensureLoaded || !api?.openTicker) throw new Error('Runtime de Mercado incompleto.');
    try { window.dispatchEvent(new CustomEvent('vestra:market-runtime-ready')); } catch (_) {}
    // Decorations are intentionally not on the critical path. Every enhancement
    // is late-load safe and repairs the current DOM when it starts.
    setTimeout(() => { void ensureEnhancements(); }, 0);
    return api;
  }

  function readyApi() {
    const api = window.VestraMarket;
    return api && api.__lazyRuntimeFacade !== true && api.ensureLoaded && api.openTicker ? api : null;
  }

  function ensure() {
    const ready = readyApi();
    if (ready) {
      void ensureEnhancements();
      return Promise.resolve(ready);
    }
    if (!runtimePromise) {
      runtimePromise = loadCore().catch(error => {
        runtimePromise = null;
        throw error;
      });
    }
    return runtimePromise;
  }

  const lazyFacade = Object.freeze({
    __lazyRuntimeFacade: true,
    ensureLoaded: (...args) => ensure().then(api => api.ensureLoaded?.(...args)),
    openTicker: (...args) => ensure().then(api => api.openTicker?.(...args)),
    openPortfolioAsset: (...args) => ensure().then(api => api.openPortfolioAsset?.(...args)),
    upsertRemoteStock: (...args) => ensure().then(api => api.upsertRemoteStock?.(...args)),
    toggleWatch: (...args) => ensure().then(api => api.toggleWatch?.(...args)),
    resolvePortfolioStock: (...args) => readyApi()?.resolvePortfolioStock?.(...args) || null,
  });
  if (!window.VestraMarket) window.VestraMarket = lazyFacade;

  window.VestraMarketRuntime = Object.freeze({
    ensure,
    ensureEnhancements,
    modules: MODULES,
    coreModules: CORE_MODULES,
    enhancementModules: ENHANCEMENT_MODULES,
    moduleTimeoutMs: MODULE_TIMEOUT_MS,
    version: '1.1',
  });
})();
