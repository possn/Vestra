/* Vestra Market UI polish v1.3 — exclusive market mode state; dossier geometry owned by dossier-controls. */
(() => {
  'use strict';

  function ensureStockThemesTools() {
    if (window.VestraMarketStockThemesTools || document.querySelector('script[data-vestra-stock-themes-tools]')) return;
    const script = document.createElement('script');
    script.src = 'market-stock-themes-tools.js?v=1.4';
    script.defer = true;
    script.dataset.vestraStockThemesTools = '1';
    document.head.appendChild(script);
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
