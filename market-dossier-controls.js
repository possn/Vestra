/* Vestra Market Dossier Controls v1.2 — iPhone-safe unified fixed action group. */
(() => {
  'use strict';

  const STYLE_ID = 'vestra-market-dossier-controls-style';

  function installStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      /* Dossier actions are one structural unit. The favourite and close button
         share a single fixed flex row, so WebKit cannot place them from two
         independent coordinate systems. Tool sheets keep the persistent X. */
      #marketSheet[data-ticker]:not([data-ticker=""]) > .market-close-persistent{
        display:none !important;
      }
      #marketSheet[data-ticker]:not([data-ticker=""]) #marketSheetContent .market-detail-head{
        padding-right:112px !important;
      }
      #marketSheet[data-ticker]:not([data-ticker=""]) #marketSheetContent .market-detail-actions{
        position:fixed !important;
        z-index:175 !important;
        top:max(calc(env(safe-area-inset-top) + 10px),14px) !important;
        right:max(calc(env(safe-area-inset-right) + 14px),14px) !important;
        display:flex !important;
        flex:0 0 auto !important;
        flex-direction:row !important;
        flex-wrap:nowrap !important;
        align-items:center !important;
        justify-content:flex-end !important;
        gap:8px !important;
        width:auto !important;
        min-width:0 !important;
        max-width:none !important;
        overflow:visible !important;
      }
      #marketSheet[data-ticker]:not([data-ticker=""]) #marketSheetContent .market-detail-actions .market-watch--detail,
      #marketSheet[data-ticker]:not([data-ticker=""]) #marketSheetContent .market-detail-actions .market-close{
        position:static !important;
        box-sizing:border-box !important;
        flex:0 0 46px !important;
        width:46px !important;
        min-width:46px !important;
        max-width:46px !important;
        height:46px !important;
        min-height:46px !important;
        max-height:46px !important;
        aspect-ratio:1 / 1;
        margin:0 !important;
        padding:0 !important;
        display:grid !important;
        place-items:center !important;
        visibility:visible !important;
        pointer-events:auto !important;
        line-height:1 !important;
        touch-action:manipulation;
        -webkit-tap-highlight-color:transparent;
        background:rgba(239,239,233,.96) !important;
        border:1px solid rgba(115,132,137,.5) !important;
        border-radius:50% !important;
        box-shadow:0 6px 22px rgba(24,43,54,.12) !important;
        backdrop-filter:blur(14px);
        -webkit-backdrop-filter:blur(14px);
      }
      #marketSheet[data-ticker]:not([data-ticker=""]) #marketSheetContent .market-detail-actions .market-watch--detail{
        font-size:21px !important;
      }
      #marketSheet[data-ticker]:not([data-ticker=""]) #marketSheetContent .market-detail-actions .market-close{
        font-size:25px !important;
      }
      #marketSheet[hidden] #marketSheetContent .market-detail-actions{
        display:none !important;
      }
    `;
    document.head.appendChild(style);
  }

  function closeMarketSheet(event) {
    const close = event?.target?.closest?.('[data-market-close]');
    if (!close) return false;
    const sheet = document.getElementById('marketSheet');
    if (!sheet || sheet.hidden || !sheet.contains(close)) return false;

    event.preventDefault();
    event.stopPropagation();

    const returnView = String(sheet.dataset.returnView || '').trim();
    sheet.hidden = true;
    sheet.setAttribute('aria-hidden', 'true');
    sheet.dataset.liveReady = '0';
    sheet.dataset.tool = '';
    sheet.dataset.returnView = '';
    document.documentElement.classList.remove('modal-open');
    document.body.classList.remove('modal-open');

    const panel = sheet.querySelector('.market-sheet__panel') || sheet;
    panel.scrollTop = 0;
    panel.scrollLeft = 0;

    if (returnView === 'assets') {
      const assetsNav = document.querySelector('[data-view="assets"]');
      if (assetsNav instanceof HTMLElement) assetsNav.click();
    }
    return true;
  }

  function normalizeButtons() {
    const sheet = document.getElementById('marketSheet');
    if (!sheet) return;
    sheet.querySelectorAll('[data-market-close], [data-market-watch]').forEach(button => {
      if (button instanceof HTMLButtonElement) button.type = 'button';
    });
    sheet.querySelectorAll('[data-market-close]').forEach(button => {
      if (!button.getAttribute('aria-label')) button.setAttribute('aria-label', 'Fechar dossier');
    });
  }

  function start() {
    installStyle();
    normalizeButtons();
    const sheet = document.getElementById('marketSheet');
    if (sheet) {
      const observer = new MutationObserver(normalizeButtons);
      observer.observe(sheet, { childList: true, subtree: true });
    }
    // Capture phase keeps closing independent from the large delegated market handler.
    document.addEventListener('click', closeMarketSheet, true);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();

  window.VestraMarketDossierControls = Object.freeze({
    version: '1.2',
    closeMarketSheet,
    installStyle,
    normalizeButtons,
  });
})();
