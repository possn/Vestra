/* Vestra lazy Market runtime loader v1.0 */
(() => {
  'use strict';

  const SRC = 'market.js?v=20260831v2';
  const TIMEOUT_MS = 12000;
  let loadPromise = null;

  function ensure() {
    if (window.VestraMarket) return Promise.resolve(window.VestraMarket);
    if (loadPromise) return loadPromise;
    if (typeof document === 'undefined') return Promise.reject(new Error('Runtime de Mercado indisponível neste ambiente.'));

    loadPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-vestra-market-runtime]');
      const script = existing || document.createElement('script');
      let settled = false;
      let timeoutId = null;

      const cleanup = () => {
        if (timeoutId !== null && typeof clearTimeout === 'function') clearTimeout(timeoutId);
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
        const api = window.VestraMarket;
        try {
          window.dispatchEvent(new CustomEvent('vestra:market-runtime-ready', { detail: { version: api?.version || null } }));
        } catch (_) {}
        resolve(api);
      };
      const onLoad = () => {
        if (!window.VestraMarket) {
          finish(new Error('Runtime de Mercado carregou sem API VestraMarket.'));
          return;
        }
        finish();
      };
      const onError = () => finish(new Error('Não foi possível carregar o runtime de Mercado.'));

      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      if (typeof setTimeout === 'function') {
        timeoutId = setTimeout(() => finish(new Error('Tempo esgotado a carregar o runtime de Mercado.')), TIMEOUT_MS);
      }

      if (!existing) {
        script.src = SRC;
        script.async = true;
        script.dataset.vestraMarketRuntime = '1';
        document.head.appendChild(script);
      }
    });

    return loadPromise;
  }

  window.VestraMarketRuntimeLoader = Object.freeze({
    ensure,
    src: SRC,
    timeoutMs: TIMEOUT_MS,
    version: '1.0',
  });
})();
