/* Vestra App Update Manager v1.1 — iOS-safe forced refresh without blocking overlay. */
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

    // Ask the registration to check in the background, but never block navigation on it.
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

  function captureForceUpdate(event) {
    const btn = event.target?.closest?.('#btnForceUpdate');
    if (!btn) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    forceFreshReload();
  }

  function install() {
    if (document.documentElement.dataset.vestraSafeUpdateCapture === '1') return false;
    document.documentElement.dataset.vestraSafeUpdateCapture = '1';
    // Capture phase runs before the legacy target listener in app.js, so the old
    // unregister/cache-wipe path cannot execute even if it remains in the bundle.
    document.addEventListener('click', captureForceUpdate, true);
    return true;
  }

  install();

  window.VestraAppUpdateManager = Object.freeze({
    version: '1.1',
    install,
    forceFreshReload,
  });
})();
