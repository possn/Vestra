/* Vestra Runtime Bridge v1.0 — read-only bridge from the app lexical state to isolated runtime modules. */
(() => {
  'use strict';
  try {
    const desc = Object.getOwnPropertyDescriptor(window, 'state');
    if (!desc) {
      Object.defineProperty(window, 'state', {
        configurable: true,
        enumerable: false,
        get() {
          try { return state; } catch (_) { return undefined; }
        }
      });
    }
  } catch (_) {}
  window.VestraRuntimeBridge = Object.freeze({ version: '1.0' });
})();
