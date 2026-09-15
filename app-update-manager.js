/* Vestra App Update Manager v1.6 — iOS-safe navigation with deterministic exclusive button ownership. */
(() => {
  'use strict';
  let busy = false;
  let captureInstalled = false;

  function forceFreshReload() {
    if (busy) return;
    if (!confirm(
      'Forçar actualização?\n\n' +
      'Isto recarrega a Vestra sem apagar os teus dados locais.'
    )) return;
    busy = true;

    // Service-worker lifecycle ownership stays in the canonical bootstrap in
    // index.html. This manager owns only the user action and must not trigger a
    // second registration.update()/controllerchange path that can race reloads.
    const url = new URL(window.location.href);
    url.searchParams.set('_v', String(Date.now()));

    // Navigate while still inside the user gesture. Standalone iOS/WebKit can
    // suspend or drop a navigation that is deferred to a later timer tick.
    // Keeping this synchronous also leaves the current UI visible until the
    // browser commits the replacement navigation.
    try {
      window.location.replace(url.toString());
    } catch (_) {
      window.location.href = url.toString();
    }
    setTimeout(() => { busy = false; }, 1200);
  }

  function isUpdateButton(target) {
    if (!target) return false;
    if (target.id === 'btnForceUpdate') return true;
    return Boolean(target.closest?.('#btnForceUpdate'));
  }

  function installCaptureGuard() {
    if (captureInstalled) return false;
    captureInstalled = true;

    // This listener runs before target listeners. It is the final containment
    // layer for the historical app.js update handler: even if app.js attaches
    // that handler after ownership has been claimed, the destructive listener
    // never receives the click.
    document.addEventListener('click', event => {
      if (!isUpdateButton(event.target)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      forceFreshReload();
    }, true);
    return true;
  }

  function install() {
    const current = document.getElementById('btnForceUpdate');
    if (!current) return false;
    if (current.dataset.vestraSafeUpdateOwner === '1') return false;

    // app.js historically attached a destructive target listener to this button.
    // Replacing the node once removes any listener that predates this manager.
    // After ownership is established, the capture guard is sufficient for any
    // later listener, so repeated DOM replacement would only discard legitimate
    // button state/listeners added by other modules.
    const button = current.cloneNode(true);
    button.dataset.vestraSafeUpdateOwner = '1';
    current.replaceWith(button);
    return true;
  }

  function reclaimAfterAppSetup() {
    setTimeout(() => install(), 0);
  }

  installCaptureGuard();
  install();
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', reclaimAfterAppSetup, { once: true });
  } else {
    reclaimAfterAppSetup();
  }
  window.addEventListener('vestra:app-ready', reclaimAfterAppSetup, { once: true });

  window.VestraAppUpdateManager = Object.freeze({
    version: '1.6',
    install,
    forceFreshReload,
  });
})();
