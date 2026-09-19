/* Vestra Market Runtime Loader v1.0 — defer heavy market UI until first use. */
(() => {
  'use strict';

  const MODULE_TIMEOUT_MS = 8000;
  const MODULES = Object.freeze([
    'market-live-overlay.js?v=1.2',
    'market-congress-live.js?v=1.0',
    'market-portfolio-context.js?v=1.0',
    'market-watch-snapshots.js?v=1.0',
    'market-dossier-signals.js?v=1.0',
    'market-search-suggestions.js?v=1.2',
    'market-row-ui.js?v=1.0',
    'market.js?v=20260831v2',
    'market-metals.js?v=1.0',
    'market-data-loader.js?v=2.5',
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

  let runtimePromise = null;

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

  async function loadAll() {
    for (const src of MODULES) await loadModule(src);
    const api = window.VestraMarket;
    if (!api?.ensureLoaded || !api?.openTicker) throw new Error('Runtime de Mercado incompleto.');
    try { window.dispatchEvent(new CustomEvent('vestra:market-runtime-ready')); } catch (_) {}
    return api;
  }

  function ensure() {
    if (window.VestraMarket?.ensureLoaded && window.VestraMarket?.openTicker) {
      return Promise.resolve(window.VestraMarket);
    }
    if (!runtimePromise) {
      runtimePromise = loadAll().catch(error => {
        runtimePromise = null;
        throw error;
      });
    }
    return runtimePromise;
  }

  window.VestraMarketRuntime = Object.freeze({
    ensure,
    modules: MODULES,
    moduleTimeoutMs: MODULE_TIMEOUT_MS,
    version: '1.0',
  });
})();
