/* Vestra Market Dossier Controls v1.8 — frozen fixed star + close action pair. */
(() => {
  'use strict';

  const STYLE_ID = 'vestra-market-dossier-controls-style';

  function installStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'market-dossier-controls.css?v=1.2';
    document.head.appendChild(link);
  }

  function closeMarketSheet(event) {
    const close = event?.target?.closest?.('[data-market-close]');
    if (!close) return false;
    const sheet = document.getElementById('marketSheet');
    if (!sheet || sheet.hidden || !sheet.contains(close)) return false;

    const returnView = String(sheet.dataset.returnView || '').trim();
    // Dossiers opened from Portfolio have a dedicated close owner in
    // portfolio-sheet-navigation.js. This generic capture handler may be
    // registered first because dossier controls are loaded dynamically; do not
    // hide the sheet or erase returnView before the portfolio handler runs.
    if (returnView === 'portfolio' || sheet.dataset.tool === 'ticker-from-portfolio') return false;

    event.preventDefault();
    event.stopPropagation();

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
      if (button instanceof HTMLButtonElement && button.type !== 'button') button.type = 'button';
    });
    sheet.querySelectorAll('[data-market-close]').forEach(button => {
      if (!button.getAttribute('aria-label')) button.setAttribute('aria-label', 'Fechar dossier');
    });

    // Keep the watch star in the same fixed-coordinate owner as the persistent X.
    // WebKit can establish a fixed-position containing block for descendants of
    // the sticky/backdrop-filter dossier header, so leaving the star nested there
    // makes identical top/right rules render at different coordinates.
    const nestedWatch = sheet.querySelector('#marketSheetContent .market-detail-actions .market-watch--detail');
    const directWatch = sheet.querySelector(':scope > .market-watch--detail');
    if (nestedWatch && nestedWatch !== directWatch) {
      directWatch?.remove();
      sheet.appendChild(nestedWatch);
    }
  }

  function start() {
    installStyle();
    normalizeButtons();
    // Capture phase keeps closing independent from the large delegated market handler.
    document.addEventListener('click', closeMarketSheet, true);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();

  window.VestraMarketDossierControls = Object.freeze({
    version: '1.8',
    closeMarketSheet,
    installStyle,
    normalizeButtons,
  });
})();
