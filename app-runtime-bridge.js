/* Vestra Runtime Bridge v1.1 — read-only bridge from the app lexical state to isolated runtime modules. */
(() => {
  'use strict';
  const CANONICAL_WORKER_URL = 'https://delicate-bar-cc80.pedrossnunes.workers.dev';

  function bridgedState() {
    try {
      const s = state;
      if (!s) return s;
      const configured = String(s?.settings?.workerUrl || '').trim();
      if (configured) return s;
      return {
        ...s,
        settings: {
          ...(s.settings || {}),
          workerUrl: CANONICAL_WORKER_URL,
        },
      };
    } catch (_) {
      return { settings: { workerUrl: CANONICAL_WORKER_URL } };
    }
  }

  try {
    const desc = Object.getOwnPropertyDescriptor(window, 'state');
    if (!desc || desc.configurable) {
      Object.defineProperty(window, 'state', {
        configurable: true,
        enumerable: false,
        get: bridgedState,
      });
    }
  } catch (_) {}

  window.VestraRuntimeBridge = Object.freeze({
    version: '1.1',
    canonicalWorkerUrl: CANONICAL_WORKER_URL,
    getState: bridgedState,
  });
})();
