/* Vestra Market Dossier Controls v1.4 — iPhone-safe unified fixed action group. */
(() => {
  'use strict';

  const STYLE_ID = 'vestra-market-dossier-controls-style';

  function installStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'market-dossier-controls.css?v=1.0';
    document.head.appendChild(link);
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
    version: '1.4',
    closeMarketSheet,
    installStyle,
    normalizeButtons,
  });
})();
