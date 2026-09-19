/* Vestra lazy SheetJS loader v1.0 */
(() => {
  'use strict';

  const SRC = 'https://cdn.jsdelivr.net/npm/xlsx@0.18.5/dist/xlsx.full.min.js';
  const TIMEOUT_MS = 12000;
  let loadPromise = null;

  function ensure() {
    if (window.XLSX) return Promise.resolve(window.XLSX);
    if (loadPromise) return loadPromise;
    if (typeof document === 'undefined') return Promise.reject(new Error('Excel indisponível neste ambiente.'));

    loadPromise = new Promise((resolve, reject) => {
      const existing = document.querySelector('script[data-vestra-xlsx]');
      const script = existing || document.createElement('script');
      let settled = false;
      let timeoutId = null;

      const cleanup = () => {
        if (timeoutId !== null) clearTimeout(timeoutId);
        script.removeEventListener('load', onLoad);
        script.removeEventListener('error', onError);
      };
      const finish = (error = null) => {
        if (settled) return;
        settled = true;
        cleanup();
        if (error) {
          if (script.isConnected && !window.XLSX) script.remove();
          loadPromise = null;
          reject(error);
          return;
        }
        resolve(window.XLSX);
      };
      const onLoad = () => {
        if (!window.XLSX) {
          finish(new Error('Biblioteca Excel carregou sem API XLSX.'));
          return;
        }
        finish();
      };
      const onError = () => finish(new Error('Não foi possível carregar a biblioteca Excel.'));

      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      timeoutId = setTimeout(() => finish(new Error('Tempo esgotado a carregar a biblioteca Excel.')), TIMEOUT_MS);

      if (!existing) {
        script.src = SRC;
        script.async = true;
        script.dataset.vestraXlsx = '1';
        document.head.appendChild(script);
      }
    });
    return loadPromise;
  }

  window.VestraXlsxLoader = Object.freeze({
    ensure,
    src: SRC,
    timeoutMs: TIMEOUT_MS,
    version: '1.0',
  });
})();
