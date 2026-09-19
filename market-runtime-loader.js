/* Vestra Market runtime loader v1.2 — defer market core, pure helpers and dossier enhancements until first use. */
(() => {
  'use strict';

  const SRC = 'market.js?v=20260831v2';
  const TIMEOUT_MS = 12000;
  let helpersPromise = null;
  let enhancementsPromise = null;
  let loadPromise = null;

  function loadHelper(globalName, src) {
    if (window[globalName]) return Promise.resolve(window[globalName]);
    return new Promise((resolve, reject) => {
      if (typeof document === 'undefined') {
        reject(new Error(`Helper de Mercado indisponível: ${globalName}`));
        return;
      }
      const selector = `script[data-vestra-market-helper="${globalName}"]`;
      const existing = document.querySelector(selector);
      const script = existing || document.createElement('script');
      let settled = false;
      let timeoutId = null;

      const cleanup = () => {
        if (timeoutId !== null) clearTimeout(timeoutId);
        script.removeEventListener('load', onLoad);
        script.removeEventListener('error', onError);
      };
      const finish = (error = null) => {
        if (settled) return;
        settled = true;
        cleanup();
        if (error) {
          if (script.isConnected && !window[globalName]) script.remove();
          reject(error);
          return;
        }
        resolve(window[globalName]);
      };
      const onLoad = () => {
        if (!window[globalName]) {
          finish(new Error(`Helper de Mercado carregou sem API: ${globalName}`));
          return;
        }
        finish();
      };
      const onError = () => finish(new Error(`Não foi possível carregar ${globalName}.`));

      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      timeoutId = setTimeout(
        () => finish(new Error(`Tempo esgotado a carregar ${globalName}.`)),
        TIMEOUT_MS
      );

      if (!existing) {
        script.src = src;
        script.async = true;
        script.dataset.vestraMarketHelper = globalName;
        document.head.appendChild(script);
      }
    });
  }

  function ensureHelpers() {
    if (
      window.VestraMarketLiveOverlay &&
      window.VestraMarketCongressLive &&
      window.VestraMarketPortfolioContext &&
      window.VestraMarketWatchSnapshots &&
      window.VestraMarketDossierSignals &&
      window.VestraMarketSearchSuggestions &&
      window.VestraMarketRowUI
    ) return Promise.resolve();

    if (!helpersPromise) {
      helpersPromise = Promise.all([
        loadHelper('VestraMarketLiveOverlay', 'market-live-overlay.js?v=1.2'),
        loadHelper('VestraMarketCongressLive', 'market-congress-live.js?v=1.0'),
        loadHelper('VestraMarketPortfolioContext', 'market-portfolio-context.js?v=1.0'),
        loadHelper('VestraMarketWatchSnapshots', 'market-watch-snapshots.js?v=1.0'),
        loadHelper('VestraMarketDossierSignals', 'market-dossier-signals.js?v=1.0'),
        loadHelper('VestraMarketSearchSuggestions', 'market-search-suggestions.js?v=1.2'),
        loadHelper('VestraMarketRowUI', 'market-row-ui.js?v=1.0'),
      ]).catch(err => {
        helpersPromise = null;
        throw err;
      });
    }
    return helpersPromise;
  }

  function ensureDossierEnhancements() {
    if (window.VestraMarketMetricCleanup && window.VestraMarketCompanyBrief) {
      return Promise.resolve(window.VestraMarketCompanyBrief);
    }
    if (!enhancementsPromise) {
      enhancementsPromise = loadHelper('VestraMarketMetricCleanup', 'market-metric-cleanup.js?v=1.0').then(metric => {
        if (!metric) return null;
        return loadHelper('VestraMarketCompanyBrief', 'market-company-brief.js?v=1.0');
      }).catch(err => {
        enhancementsPromise = null;
        throw err;
      });
    }
    return enhancementsPromise;
  }

  function loadCore() {
    if (window.VestraMarket?.ensureLoaded) return Promise.resolve(window.VestraMarket);
    return new Promise((resolve, reject) => {
      if (typeof document === 'undefined') {
        reject(new Error('Runtime de Mercado indisponível neste ambiente.'));
        return;
      }
      const existing = document.querySelector('script[data-vestra-market-core]');
      const script = existing || document.createElement('script');
      let settled = false;
      let timeoutId = null;

      const cleanup = () => {
        if (timeoutId !== null) clearTimeout(timeoutId);
        script.removeEventListener('load', onLoad);
        script.removeEventListener('error', onError);
      };
      const finish = (error = null) => {
        if (settled) return;
        settled = true;
        cleanup();
        if (error) {
          if (script.isConnected && !window.VestraMarket) script.remove();
          reject(error);
          return;
        }
        try {
          window.dispatchEvent(new CustomEvent('vestra:market-core-ready', { detail: { version: '1.2' } }));
        } catch (_) {}
        resolve(window.VestraMarket);
      };
      const onLoad = () => {
        if (!window.VestraMarket?.ensureLoaded) {
          finish(new Error('Runtime de Mercado carregou sem API VestraMarket.'));
          return;
        }
        finish();
      };
      const onError = () => finish(new Error('Não foi possível carregar o runtime de Mercado.'));

      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      timeoutId = setTimeout(
        () => finish(new Error('Tempo esgotado a carregar o runtime de Mercado.')),
        TIMEOUT_MS
      );

      if (!existing) {
        script.src = 'market.js?v=20260831v2';
        script.async = true;
        script.dataset.vestraMarketCore = '1';
        document.head.appendChild(script);
      }
    });
  }

  function ensure(options = {}) {
    const loadData = options?.loadData === true;
    if (window.VestraMarket?.ensureLoaded) {
      return loadData
        ? Promise.resolve(window.VestraMarket.ensureLoaded()).then(() => window.VestraMarket)
        : Promise.resolve(window.VestraMarket);
    }
    if (!loadPromise) {
      loadPromise = ensureHelpers()
        .then(loadCore)
        .then(api => {
          // Dossier decoration is not required for the first Market paint.
          // Start it only after the real Market core exists and never block core/data readiness.
          void ensureDossierEnhancements().catch(err => {
            console.warn('Falha a carregar enhancements de dossier', err);
          });
          return api;
        })
        .catch(err => {
          loadPromise = null;
          throw err;
        });
    }
    return loadPromise.then(api => {
      if (!loadData) return api;
      return Promise.resolve(api.ensureLoaded()).then(() => api);
    });
  }

  window.VestraMarketLoader = Object.freeze({
    ensure,
    ensureHelpers,
    ensureDossierEnhancements,
    src: SRC,
    timeoutMs: TIMEOUT_MS,
    version: '1.2',
  });
})();
