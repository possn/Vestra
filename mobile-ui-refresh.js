/* Vestra Mobile UI Refresh v1.0 — simpler topbar + useful More hub shortcuts. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraMobileUiRefreshStyle';
  const SHORTCUTS_ID = 'vestraMoreShortcuts';

  function ensureStyles() {
    if (document.getElementById(STYLE_ID)) return;
    const style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = `
      .more-shortcuts{margin:0 0 16px}
      .more-shortcuts__label{font-size:10px;font-weight:850;letter-spacing:.6px;text-transform:uppercase;color:var(--muted,#728694);margin:0 4px 8px}
      .more-shortcuts__grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px}
      .more-shortcut{appearance:none;border:1px solid rgba(31,56,66,.09);background:rgba(251,252,252,.78);border-radius:17px;padding:12px 7px 10px;color:var(--text,#132536);display:flex;flex-direction:column;align-items:center;justify-content:center;gap:6px;min-height:72px;box-shadow:0 2px 10px rgba(28,45,54,.025);font:inherit;cursor:pointer;transition:transform .16s ease,background .16s ease,border-color .16s ease}
      .more-shortcut:active{transform:scale(.97);background:rgba(23,123,120,.06);border-color:rgba(23,123,120,.18)}
      .more-shortcut__icon{width:27px;height:27px;border-radius:9px;display:grid;place-items:center;background:rgba(23,123,120,.09);color:#157571;font-size:15px;font-weight:850;line-height:1}
      .more-shortcut__label{font-size:10px;font-weight:800;white-space:nowrap}
      #viewSettings .more-group{border-color:rgba(31,56,66,.09)!important;box-shadow:none!important}
      #viewSettings .more-group__body>.card{box-shadow:none;border-color:rgba(31,56,66,.075)}
      @media(max-width:720px){
        .topbar{padding:9px 12px;gap:7px;justify-content:flex-start}
        .topbar #btnSidebarToggle,.topbar #btnSettingsNav{display:none!important}
        .topbar .brand{flex:1;min-width:0;gap:9px}
        .topbar .brand__icon{width:38px;height:38px;border-radius:12px}
        .topbar .brand__title{font-size:20px}
        .topbar .brand__sub{display:none}
        .topbar #btnSearchToggle{width:42px;height:42px;padding:0!important;display:grid;place-items:center;font-size:20px!important;border-radius:14px!important}
        .topbar .fab{width:42px;height:42px;border-radius:14px;font-size:24px;box-shadow:0 5px 18px rgba(32,129,126,.22)}
        .more-shortcuts__grid{grid-template-columns:repeat(4,minmax(0,1fr));gap:6px}
        .more-shortcut{min-height:68px;padding:10px 5px 9px;border-radius:15px}
      }
      @media(max-width:360px){.more-shortcuts__grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
    `;
    document.head.appendChild(style);
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

  window.VestraMobileUiRefresh = Object.freeze({ refresh, version:'1.0' });
})();
