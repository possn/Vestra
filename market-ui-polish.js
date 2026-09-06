/* Vestra Market UI polish v1.0 — persistent dossier actions + exclusive market mode state. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraMarketUiPolishStyle';

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      /* The visible dossier close control is persistent/fixed. Keep the watch star
         in the same top-right control cluster, immediately to its left. */
      #marketSheetContent .market-watch--detail{
        position:fixed!important;
        top:max(calc(env(safe-area-inset-top) + 10px),14px)!important;
        right:max(calc(env(safe-area-inset-right) + 66px),66px)!important;
        z-index:9998!important;
        width:44px!important;
        height:44px!important;
        border-radius:50%!important;
        background:rgba(239,239,233,.96)!important;
        border:1px solid rgba(115,132,137,.5)!important;
        box-shadow:0 6px 22px rgba(24,43,54,.12)!important;
        backdrop-filter:blur(14px);
        -webkit-backdrop-filter:blur(14px);
      }
      #marketSheetContent .market-detail-actions{min-width:0!important;width:0!important;flex:0 0 0!important;overflow:visible!important}
      #marketSheet[hidden] #marketSheetContent .market-watch--detail{display:none!important}
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
    version: '1.0',
  });
})();
