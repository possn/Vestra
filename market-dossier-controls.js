/* Vestra Market Dossier Controls v1.0 — iPhone-safe close and action geometry. */
(() => {
  'use strict';

  const STYLE_ID = 'vestra-market-dossier-controls-style';

  function installStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .market-detail-actions{
        flex:0 0 auto;
        position:relative;
        z-index:5;
      }
      .market-detail-actions .market-watch--detail,
      .market-detail-actions .market-close{
        box-sizing:border-box;
        flex:0 0 40px !important;
        width:40px !important;
        min-width:40px !important;
        height:40px !important;
        min-height:40px !important;
        aspect-ratio:1 / 1;
        padding:0 !important;
        display:grid;
        place-items:center;
        line-height:1;
        touch-action:manipulation;
        -webkit-tap-highlight-color:transparent;
      }
      .market-detail-actions .market-watch--detail{border-radius:50% !important}
      .market-detail-actions .market-close{border-radius:50% !important}
    `;
    document.head.appendChild(style);
  }

  function closeMarketSheet(event) {
    const close = event?.target?.closest?.('[data-market-close]');
    if (!close) return false;
    const sheet = document.getElementById('marketSheet');
    if (!sheet || sheet.hidden) return false;

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

  function start() {
    installStyle();
    // Capture phase makes the close control independent of the large delegated
    // market handler. A failure in another branch can no longer swallow the X.
    document.addEventListener('click', closeMarketSheet, true);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();

  window.VestraMarketDossierControls = Object.freeze({
    version: '1.0',
    closeMarketSheet,
    installStyle,
  });
})();
