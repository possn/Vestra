/* Vestra Market UI polish v1.1 — unified dossier action geometry + exclusive market mode state. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraMarketUiPolishStyle';

  function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      /* Favourite and close must read as one control pair. Previous builds only
         positioned the favourite and inherited the close geometry from another
         module, which could leave a visibly large gap on real iPhones. Own both
         buttons here from the same coordinate system: 46px controls, 8px gap. */
      #marketSheet .market-close-persistent,
      #marketSheetContent .market-watch--detail{
        position:fixed!important;
        top:max(calc(env(safe-area-inset-top) + 10px),14px)!important;
        width:46px!important;
        min-width:46px!important;
        max-width:46px!important;
        height:46px!important;
        min-height:46px!important;
        max-height:46px!important;
        padding:0!important;
        box-sizing:border-box!important;
        border-radius:50%!important;
        display:grid!important;
        place-items:center!important;
        background:rgba(239,239,233,.96)!important;
        border:1px solid rgba(115,132,137,.5)!important;
        box-shadow:0 6px 22px rgba(24,43,54,.12)!important;
        backdrop-filter:blur(14px);
        -webkit-backdrop-filter:blur(14px);
      }
      #marketSheet .market-close-persistent{
        right:max(calc(env(safe-area-inset-right) + 14px),14px)!important;
        z-index:9999!important;
      }
      #marketSheetContent .market-watch--detail{
        right:max(calc(env(safe-area-inset-right) + 68px),68px)!important;
        z-index:9998!important;
      }
      #marketSheetContent .market-detail-actions{
        min-width:0!important;
        width:0!important;
        flex:0 0 0!important;
        overflow:visible!important;
      }
      #marketSheet[hidden] .market-close-persistent,
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
    version: '1.1',
  });
})();
