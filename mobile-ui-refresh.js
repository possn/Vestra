/* Vestra Mobile UI Refresh v1.4 — compact topbar + presentation-only mobile polish + useful More shortcuts. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraMobileUiRefreshStyle';
  const SHORTCUTS_ID = 'vestraMoreShortcuts';

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'mobile-ui-refresh.css?v=1.0';
    document.head.appendChild(link);
  }

  function callView(view) {
    try { if (typeof setView === 'function') setView(view); } catch (_) {}
  }

  function handleAction(action) {
    if (action === 'dividends') return callView('dividends');
    if (action === 'analysis') return callView('analysis');
    if (action === 'import') {
      const button = document.getElementById('btnGoImport');
      if (button) button.click();
      return;
    }
    if (action === 'backup') {
      const button = document.getElementById('btnExportJSON');
      if (button) button.click();
    }
  }

  function ensureShortcuts() {
    const settings = document.getElementById('viewSettings');
    const hero = settings?.querySelector('.more-hero');
    if (!settings || !hero) return null;
    let hub = document.getElementById(SHORTCUTS_ID);
    if (hub) return hub;
    hub = document.createElement('div');
    hub.id = SHORTCUTS_ID;
    hub.className = 'more-shortcuts';
    hub.innerHTML = `
      <div class="more-shortcuts__label">Atalhos</div>
      <div class="more-shortcuts__grid">
        <button type="button" class="more-shortcut" data-ui-shortcut="dividends"><span class="more-shortcut__icon">€</span><span class="more-shortcut__label">Dividendos</span></button>
        <button type="button" class="more-shortcut" data-ui-shortcut="analysis"><span class="more-shortcut__icon">↗</span><span class="more-shortcut__label">Análise</span></button>
        <button type="button" class="more-shortcut" data-ui-shortcut="import"><span class="more-shortcut__icon">⇅</span><span class="more-shortcut__label">Importar</span></button>
        <button type="button" class="more-shortcut" data-ui-shortcut="backup"><span class="more-shortcut__icon">↑</span><span class="more-shortcut__label">Backup</span></button>
      </div>`;
    hero.insertAdjacentElement('afterend', hub);
    hub.addEventListener('click', event => {
      const button = event.target?.closest?.('[data-ui-shortcut]');
      if (!button) return;
      handleAction(button.dataset.uiShortcut);
    });
    return hub;
  }

  function normalizeTopbarIcons() {
    const search = document.getElementById('btnSearchToggle');
    if (search) search.textContent = '⌕';
  }

  function refresh() {
    ensureStyles();
    normalizeTopbarIcons();
    ensureShortcuts();
  }

  function boot() {
    refresh();
    window.addEventListener('vestra:app-ready', refresh);
    document.addEventListener('click', event => {
      if (event.target?.closest?.('[data-view="settings"]')) setTimeout(refresh, 40);
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once:true });
  else boot();

  // Sidebar state and event wiring are intentionally owned by app.js (wireSidebar).
  // This module is presentation-only so iPhone/WebKit never receives duplicate drawer listeners.
  window.VestraMobileUiRefresh = Object.freeze({ refresh, version:'1.4' });
})();
