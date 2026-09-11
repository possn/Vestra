/* Vestra App Update Manager v1.5 — iOS-safe navigation with deterministic exclusive button ownership. */
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
    // that handler again, replaces the node, or runs after our DOM reclaim,
    // the destructive listener never receives the click.
    document.addEventListener('click', event => {
      if (!isUpdateButton(event.target)) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      forceFreshReload();
    }, true);
    return true;
  }

  function install(force = false) {
    const current = document.getElementById('btnForceUpdate');
    if (!current) return false;
    if (!force && current.dataset.vestraSafeUpdateOwner === '1') return false;

    // app.js historically attached a destructive target listener to this button.
    // Replacing the node removes every previously attached listener. The capture
    // guard above remains authoritative even if a later listener is attached.
    const button = current.cloneNode(true);
    button.dataset.vestraSafeUpdateOwner = '1';
    current.replaceWith(button);
    return true;
  }

  function reclaimAfterAppSetup() {
    setTimeout(() => install(true), 0);
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
    version: '1.5',
    install,
    forceFreshReload,
  });
})();
