/* Vestra Broker Import runtime loader v1.0 — load workbook/parsers only on import. */
(() => {
  'use strict';

  const TIMEOUT_MS = 12000;
  let workbookPromise = null;
  let parsersPromise = null;

  function load(globalName, src, attr) {
    if (window[globalName]) return Promise.resolve(window[globalName]);
    return new Promise((resolve, reject) => {
      if (typeof document === 'undefined') {
        reject(new Error(`Runtime de importação indisponível: ${globalName}`));
        return;
      }
      const selector = `script[data-vestra-broker-import="${attr}"]`;
      const existing = document.querySelector(selector);
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
          if (script.isConnected && !window[globalName]) script.remove();
          reject(error);
          return;
        }
        resolve(window[globalName]);
      };
      const onLoad = () => {
        if (!window[globalName]) {
          finish(new Error(`Runtime carregou sem API: ${globalName}`));
          return;
        }
        finish();
      };
      const onError = () => finish(new Error(`Não foi possível carregar ${globalName}.`));

      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      timeoutId = setTimeout(
        () => finish(new Error(`Tempo esgotado a carregar ${globalName}.`)),
        TIMEOUT_MS
      );

      if (!existing) {
        script.src = src;
        script.async = true;
        script.dataset.vestraBrokerImport = attr;
        document.head.appendChild(script);
      }
    });
  }

  function ensureWorkbook() {
    if (window.VestraBrokerWorkbook) return Promise.resolve(window.VestraBrokerWorkbook);
    if (!workbookPromise) {
      workbookPromise = load('VestraBrokerWorkbook', 'app-broker-workbook.js?v=1.0', 'workbook')
        .catch(err => {
          workbookPromise = null;
          throw err;
        });
    }
    return workbookPromise;
  }

  function ensureParsers() {
    if (window.VestraBrokerParsers) return Promise.resolve(window.VestraBrokerParsers);
    if (!parsersPromise) {
      parsersPromise = ensureWorkbook()
        .then(() => load('VestraBrokerParsers', 'app-broker-parsers.js?v=1.0', 'parsers'))
        .catch(err => {
          parsersPromise = null;
          throw err;
        });
    }
    return parsersPromise;
  }

  window.VestraBrokerImportLoader = Object.freeze({
    ensureWorkbook,
    ensureParsers,
    timeoutMs: TIMEOUT_MS,
    version: '1.0',
  });
})();
