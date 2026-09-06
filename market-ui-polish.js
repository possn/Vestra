/* Vestra Market UI polish v1.2 — exclusive market mode state; dossier geometry owned by dossier-controls. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraMarketUiPolishStyle';

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      /* Dossier button geometry intentionally lives only in
         market-dossier-controls.js. Keeping this module out of positioning
         avoids competing fixed coordinates on real iPhone/WebKit builds. */
      #marketSheet[hidden] #marketSheetContent .market-detail-actions{display:none!important}
    `;
    document.head.appendChild(style);
  }

  function clearPoliticiansActive() {
    document.querySelector('[data-politicians-mode]')?.classList.remove('is-active');
  }

  function onClickCapture(event) {
    const mode = event.target?.closest?.('[data-market-mode]');
    if (mode) clearPoliticiansActive();
  }

  function boot() {
    ensureStyle();
    document.addEventListener('click', onClickCapture, true);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once: true });
  else boot();

  window.VestraMarketUiPolish = Object.freeze({
    ensureStyle,
    clearPoliticiansActive,
    version: '1.2',
  });
})();
