/* Vestra Market UI polish v1.3 — exclusive market mode state; dossier geometry owned by dossier-controls. */
(() => {
  'use strict';

  const STOCK_THEMES_LOAD_TIMEOUT_MS = 8000;
  let stockThemesLoadPromise = null;

  function ensureStockThemesTools(attempt = 0) {
    if (window.VestraMarketStockThemesTools) return Promise.resolve(window.VestraMarketStockThemesTools);
    if (stockThemesLoadPromise) return stockThemesLoadPromise;

    const existing = document.querySelector('script[data-vestra-stock-themes-tools]');
    stockThemesLoadPromise = new Promise(resolve => {
      const script = existing || document.createElement('script');
      let settled = false;
      let timeoutId = null;

      const cleanup = () => {
        if (timeoutId !== null && typeof clearTimeout === 'function') clearTimeout(timeoutId);
        script.removeEventListener('load', onLoad);
        script.removeEventListener('error', onError);
      };
      const finish = value => {
        if (settled) return;
        settled = true;
        cleanup();
        stockThemesLoadPromise = null;
        resolve(value || null);
      };
      const retry = () => {
        if (attempt < 1 && typeof setTimeout === 'function') {
          setTimeout(() => ensureStockThemesTools(attempt + 1), 1000);
        }
      };
      const fail = () => {
        if (settled) return;
        if (script.isConnected) script.remove();
        finish(null);
        retry();
      };
      const onLoad = () => {
        const api = window.VestraMarketStockThemesTools || null;
        if (!api) { fail(); return; }
        finish(api);
      };
      const onError = () => fail();

      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      if (typeof setTimeout === 'function') {
        timeoutId = setTimeout(fail, STOCK_THEMES_LOAD_TIMEOUT_MS);
      }
      if (!existing) {
        script.src = 'market-stock-themes-tools.js?v=1.5';
        script.defer = true;
        script.dataset.vestraStockThemesTools = '1';
        document.head.appendChild(script);
      }
    });
    return stockThemesLoadPromise;
  }

  function clearPoliticiansActive() {
    document.querySelector('[data-politicians-mode]')?.classList.remove('is-active');
  }

  function onClickCapture(event) {
    const mode = event.target?.closest?.('[data-market-mode]');
    if (mode) clearPoliticiansActive();
  }

  function boot() {
    ensureStockThemesTools();
    document.addEventListener('click', onClickCapture, true);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();

  window.VestraMarketUiPolish = Object.freeze({
    ensureStockThemesTools,
    clearPoliticiansActive,
    version: '1.3',
  });
})();
