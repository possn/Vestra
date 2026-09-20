/* Vestra Market runtime loader v1.4 — defer market core + dossier data until first use. */
(() => {
  'use strict';

  const SRC = 'market.js?v=20260920v1';
  const TIMEOUT_MS = 12000;
  let portfolioHelpersPromise = null;
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

  function ensurePortfolioHelpers() {
    if (
      window.VestraNavigation &&
      window.VestraPortfolioCollapsibles &&
      window.VestraPortfolioCardClassifier
    ) return Promise.resolve();

    if (!portfolioHelpersPromise) {
      // Navigation must exist before portfolio rows can open dossiers. The
      // classifier consumes the attributes installed by collapsibles.
      portfolioHelpersPromise = loadHelper('VestraNavigation', 'portfolio-sheet-navigation.js?v=1.5')
        .then(() => loadHelper('VestraPortfolioCollapsibles', 'portfolio-collapsibles.js?v=1.2'))
        .then(() => loadHelper('VestraPortfolioCardClassifier', 'portfolio-card-classifier.js?v=1.2'))
        .catch(err => {
          portfolioHelpersPromise = null;
          throw err;
        });
    }
    return portfolioHelpersPromise;
  }

  function ensureHelpers() {
    if (
      window.VestraMarketLiveOverlay &&
      window.VestraMarketCongressLive &&
      window.VestraMarketPortfolioContext &&
      window.VestraMarketWatchSnapshots &&
      window.VestraMarketDossierSignals &&
      window.VestraMarketSearchSuggestions &&
      window.VestraMarketRowUI &&
      window.VestraNavigation &&
      window.VestraMarketData &&
      window.VestraPortfolioCollapsibles &&
      window.VestraPortfolioCardClassifier
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
        // Dossier data has no load-time dependency on navigation. Fetch it in
        // parallel so it does not add another round trip before the core.
        loadHelper('VestraMarketData', 'market-data-loader.js?v=2.6'),
        ensurePortfolioHelpers(),
      ]).catch(err => {
        helpersPromise = null;
        throw err;
      });
    }
    return helpersPromise;
  }

  function ensureEnhancements() {
    if (window.VestraMarketMetricCleanup && window.VestraMarketCompanyBrief) {
      return Promise.resolve();
    }
    if (!enhancementsPromise) {
      enhancementsPromise = loadHelper('VestraMarketMetricCleanup', 'market-metric-cleanup.js?v=1.2')
        .then(() => loadHelper('VestraMarketCompanyBrief', 'market-company-brief.js?v=2.1'))
        .catch(err => {
          enhancementsPromise = null;
          throw err;
        });
    }
    return enhancementsPromise;
  }

  function replayPendingSearch() {
    // Market becomes visible immediately while its heavy core loads. A fast
    // user can type before market.js installs the delegated input listener;
    // replay that value once the listener exists instead of losing the query.
    const search = document.getElementById?.('marketSearch');
    if (!search?.value) return;
    try { search.dispatchEvent(new Event('input', { bubbles: true })); } catch (_) {}
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
          window.dispatchEvent(new CustomEvent('vestra:market-core-ready', { detail: { version: '1.4' } }));
        } catch (_) {}
        replayPendingSearch();
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
        script.src = 'market.js?v=20260920v1';
        script.async = true;
        script.dataset.vestraMarketCore = '1';
        document.head.appendChild(script);
      }
    });
  }

  function ensure(options = {}) {
    const loadData = options?.loadData === true;
    if (window.VestraMarket?.ensureLoaded) {
      // Enhancements improve an open dossier, but must never delay Market itself.
      ensureEnhancements().catch(err => console.warn('Falha ao carregar enhancements de Mercado', err));
      const ready = Promise.resolve(window.VestraMarket);
      return loadData
        ? ready.then(api => Promise.resolve(api.ensureLoaded()).then(() => api))
        : ready;
    }
    if (!loadPromise) {
      loadPromise = ensureHelpers()
        .then(loadCore)
        .then(api => {
          ensureEnhancements().catch(err => console.warn('Falha ao carregar enhancements de Mercado', err));
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
    ensurePortfolioHelpers,
    ensureEnhancements,
    src: SRC,
    timeoutMs: TIMEOUT_MS,
    version: '1.4',
  });
})();
