/* Vestra App Update Manager v1.3 — iOS-safe forced refresh with deterministic exclusive button ownership. */
(() => {
  'use strict';
  let busy = false;

  function forceFreshReload() {
    if (busy) return;
    if (!confirm(
      'Forçar actualização?\n\n' +
      'Isto procura a versão mais recente da Vestra sem apagar os teus dados locais.'
    )) return;
    busy = true;

    // Ask the existing registration to check for a newer worker, but never
    // unregister it and never clear application caches or local data.
    try {
      if ('serviceWorker' in navigator) {
        navigator.serviceWorker.getRegistration()
          .then(reg => reg?.update?.())
          .catch(() => {});
      }
    } catch (_) {}

    const url = new URL(window.location.href);
    url.searchParams.set('_v', String(Date.now()));

    // Do not show the Vestra splash/overlay here. In standalone iOS PWAs the
    // navigation can be delayed or suspended; keeping the current UI visible
    // avoids the apparent permanent freeze seen with the old implementation.
    setTimeout(() => {
      try {
        window.location.replace(url.toString());
      } catch (_) {
        window.location.href = url.toString();
      }
      setTimeout(() => { busy = false; }, 1200);
    }, 40);
  }

  function install(force = false) {
    const current = document.getElementById('btnForceUpdate');
    if (!current) return false;
    if (!force && current.dataset.vestraSafeUpdateOwner === '1') return false;

    // app.js historically attached a destructive target listener to this button.
    // Replacing the node removes every previously attached listener without
    // depending on capture-phase ordering or propagation interception. A forced
    // reinstall is deliberately performed after the main app setup so even a
    // listener attached after an early dynamic load is removed deterministically.
    const button = current.cloneNode(true);
    button.dataset.vestraSafeUpdateOwner = '1';
    current.replaceWith(button);
    button.addEventListener('click', event => {
      event.preventDefault();
      event.stopImmediatePropagation();
      forceFreshReload();
    });
    return true;
  }

  function reclaimAfterAppSetup() {
    setTimeout(() => install(true), 0);
  }

  install();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', reclaimAfterAppSetup, { once: true });
  } else {
    reclaimAfterAppSetup();
  }
  window.addEventListener('vestra:app-ready', reclaimAfterAppSetup, { once: true });

  window.VestraAppUpdateManager = Object.freeze({
    version: '1.3',
    install,
    forceFreshReload,
  });
})();
