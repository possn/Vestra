/* Vestra UI Visual Polish v1.1 — lighter hierarchy without changing app semantics. */
(() => {
  'use strict';

  const STYLE_ID = 'vestraUiVisualPolishStyle';

  function ensureStyles() {
    if (typeof document === 'undefined' || document.getElementById(STYLE_ID)) return;
    const link = document.createElement('link');
    link.id = STYLE_ID;
    link.rel = 'stylesheet';
    link.href = 'ui-visual-polish.css?v=1.0';
    document.head.appendChild(link);
  }

  function refresh() {
    ensureStyles();
  }

  function boot() {
    refresh();
    window.addEventListener('vestra:app-ready', refresh);
    window.addEventListener('vestra:market-ready', refresh);
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, { once:true });
  else boot();

  window.VestraUiVisualPolish = Object.freeze({ refresh, version:'1.1' });
})();
