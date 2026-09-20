/* Vestra Chart runtime loader v1.0 — Chart.js after hydration or on first use. */
(() => {
  'use strict';

  const SRC = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js';
  const TIMEOUT_MS = 12000;
  let loadingPromise = null;
  let readyAnnounced = false;
  let idleScheduled = false;

  function announceReady() {
    if (readyAnnounced || typeof window.Chart === 'undefined') return;
    readyAnnounced = true;
    try {
      window.dispatchEvent(new CustomEvent('vestra:charts-ready', {
        detail: { version: '4.4.3' }
      }));
    } catch (_) {}
  }

  function ensure() {
    if (typeof window.Chart !== 'undefined') {
      announceReady();
      return Promise.resolve(window.Chart);
    }
    if (loadingPromise) return loadingPromise;

    loadingPromise = new Promise((resolve, reject) => {
      const previous = document.querySelector('script[data-vestra-chart-runtime]');
      if (previous) previous.remove();

      const script = document.createElement('script');
      let settled = false;
      const timer = setTimeout(() => finish(new Error('O carregamento dos gráficos excedeu o tempo limite.')), TIMEOUT_MS);

      function finish(error) {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        script.onload = null;
        script.onerror = null;
        if (error || typeof window.Chart === 'undefined') {
          script.remove();
          loadingPromise = null;
          reject(error || new Error('Chart.js carregou sem disponibilizar o runtime.'));
          return;
        }
        announceReady();
        resolve(window.Chart);
      }

      script.async = true;
      script.dataset.vestraChartRuntime = '1';
      script.src = SRC;
      script.onload = () => finish();
      script.onerror = () => finish(new Error('Não foi possível carregar os gráficos.'));
      (document.head || document.documentElement).appendChild(script);
    });

    return loadingPromise;
  }

  function scheduleAfterHydration() {
    if (idleScheduled || typeof window.Chart !== 'undefined') return;
    idleScheduled = true;
    const load = () => ensure().catch(() => {});
    if (typeof window.requestIdleCallback === 'function') {
      window.requestIdleCallback(load, { timeout: 1800 });
    } else {
      setTimeout(load, 700);
    }
  }

  window.VestraChartLoader = Object.freeze({
    ensure,
    scheduleAfterHydration,
    src: SRC,
    timeoutMs: TIMEOUT_MS,
    version: '1.0'
  });

  if (window.__vestraAppHydrated === true) scheduleAfterHydration();
  else window.addEventListener('vestra:app-ready', scheduleAfterHydration, { once: true });
})();
