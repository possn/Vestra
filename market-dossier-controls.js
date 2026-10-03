/* Vestra Market Dossier Controls v2.0 — compact body-level iPhone action portal. */
(() => {
  'use strict';

  const STYLE_ID = 'vestra-market-dossier-controls-style';

  function installStyle() {
    if (document.getElementById(STYLE_ID)) return;
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'market-dossier-controls.css?v=1.4';
    document.head.appendChild(link);
  }

  const PORTAL_ID = 'marketDossierActionPortal';

  function ensurePortal() {
    let portal = document.getElementById(PORTAL_ID);
    if (portal) return portal;
    portal = document.createElement('div');
    portal.id = PORTAL_ID;
    portal.className = 'market-dossier-action-portal';
    portal.hidden = true;
    portal.innerHTML = '<button type="button" class="market-watch market-watch--portal" data-portal-watch aria-label="Guardar para acompanhar">☆</button><button type="button" class="market-close market-close--portal" data-portal-close aria-label="Fechar dossier">×</button>';
    portal.addEventListener('click', event => {
      const sheet = document.getElementById('marketSheet');
      if (!sheet || sheet.hidden) return;
      if (event.target.closest('[data-portal-watch]')) {
        event.preventDefault();
        event.stopPropagation();
        sheet.querySelector(':scope > .market-watch--detail')?.click();
        return;
      }
      if (event.target.closest('[data-portal-close]')) {
        event.preventDefault();
        event.stopPropagation();
        sheet.querySelector(':scope > .market-close-persistent')?.click();
      }
    });
    document.body.appendChild(portal);
    return portal;
  }

  function syncPortal(sheet) {
    const portal = ensurePortal();
    const ticker = String(sheet?.dataset?.ticker || '').trim().toUpperCase();
    const visible = Boolean(sheet && !sheet.hidden);
    portal.hidden = !visible;
    portal.classList.toggle('market-dossier-action-portal--tool', visible && !ticker);
    if (!visible) return;

    const original = sheet.querySelector(':scope > .market-watch--detail');
    const watch = portal.querySelector('[data-portal-watch]');
    const hasWatchTarget = Boolean(ticker && original);
    watch.classList.toggle('is-unavailable', !hasWatchTarget);
    watch.setAttribute('aria-hidden', hasWatchTarget ? 'false' : 'true');
    watch.tabIndex = hasWatchTarget ? 0 : -1;
    if (!hasWatchTarget) return;

    const active = original.classList.contains('is-active');
    watch.textContent = active ? '★' : '☆';
    watch.classList.toggle('is-active', Boolean(active));
    watch.setAttribute('aria-label', original.getAttribute('aria-label') || (active ? 'Remover da lista' : 'Guardar para acompanhar'));
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

    syncPortal(sheet);

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
    syncPortal(sheet);
  }

  function start() {
    installStyle();
    ensurePortal();
    normalizeButtons();
    // Dossier mutation ownership stays in market-company-brief.js. That single
    // sheet-scoped observer calls normalizeButtons() after every dossier render.
    // Capture phase keeps closing independent from the large delegated market handler.
    document.addEventListener('click', closeMarketSheet, true);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();

  window.VestraMarketDossierControls = Object.freeze({
    version: '2.1',
    closeMarketSheet,
    installStyle,
    normalizeButtons,
    syncPortal,
  });
})();
