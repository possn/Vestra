/* Vestra Market runtime loader v1.0 — defer heavy market core until first use. */
(() => {
  'use strict';

  const SRC = 'market.js?v=20260831v2';
  const TIMEOUT_MS = 12000;
  let loadPromise = null;

  function ensure(options = {}) {
    const loadData = options?.loadData === true;
    if (window.VestraMarket?.ensureLoaded) {
      return loadData
        ? Promise.resolve(window.VestraMarket.ensureLoaded()).then(() => window.VestraMarket)
        : Promise.resolve(window.VestraMarket);
    }
    if (!loadPromise) {
      loadPromise = new Promise((resolve, reject) => {
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
            loadPromise = null;
            reject(error);
            return;
          }
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
          script.src = SRC;
          script.async = true;
          script.dataset.vestraMarketCore = '1';
          document.head.appendChild(script);
        }
      });
    }

    return loadPromise.then(api => {
      if (!loadData) return api;
      return Promise.resolve(api.ensureLoaded()).then(() => api);
    });
  }

  window.VestraMarketLoader = Object.freeze({
    ensure,
    src: SRC,
    timeoutMs: TIMEOUT_MS,
    version: '1.0',
  });
})();
