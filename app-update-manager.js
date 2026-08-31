/* Vestra App Update Manager v1.0 — safe forced refresh for iOS/PWA. */
(() => {
  'use strict';
  let busy = false;

  const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
  const withTimeout = (promise, ms) => Promise.race([promise, sleep(ms)]);

  async function forceFreshReload() {
    if (busy) return;
    if (!confirm(
      'Forçar actualização?\n\n' +
      'Isto procura a versão mais recente da Vestra sem apagar os teus dados locais.'
    )) return;
    busy = true;

    const overlay = document.getElementById('appLoadingOverlay');
    const msg = document.getElementById('appLoadingMsg');
    if (overlay) { overlay.style.display = 'flex'; overlay.style.opacity = '1'; }
    if (msg) msg.textContent = 'A procurar a versão mais recente…';

    try {
      if ('serviceWorker' in navigator) {
        const reg = await withTimeout(navigator.serviceWorker.getRegistration(), 1200);
        if (reg && typeof reg.update === 'function') {
          await withTimeout(reg.update(), 1800);
        }
      }
    } catch (e) {
      console.warn('[VestraAppUpdate] service worker update', e);
    }

    if (msg) msg.textContent = 'A reabrir a Vestra…';
    const url = new URL(window.location.href);
    url.searchParams.set('_v', String(Date.now()));

    // Do not unregister the controlling SW and do not wipe every CacheStorage
    // entry. On iOS standalone PWAs that can leave the current navigation
    // without a controller and strand the loading overlay. The SW is already
    // network-first for documents/scripts and reg.update() fetches sw.js fresh.
    try {
      window.location.replace(url.toString());
    } catch (_) {
      window.location.href = url.toString();
    }

    // Safety hatch if iOS refuses the navigation for any reason.
    setTimeout(() => {
      busy = false;
      if (overlay) overlay.style.display = 'none';
      if (msg) msg.textContent = 'Não foi possível reabrir automaticamente. Fecha e volta a abrir a app.';
    }, 5000);
  }

  function install() {
    const old = document.getElementById('btnForceUpdate');
    if (!old || old.dataset.vestraSafeUpdate === '1') return false;

    // Clone removes the old app.js listener cleanly without needing to reach
    // into its private lexical scope.
    const btn = old.cloneNode(true);
    btn.dataset.vestraSafeUpdate = '1';
    old.replaceWith(btn);
    btn.addEventListener('click', forceFreshReload);
    return true;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => install(), { once: true });
  } else {
    install();
  }

  window.VestraAppUpdateManager = Object.freeze({ version: '1.0', install, forceFreshReload });
})();
