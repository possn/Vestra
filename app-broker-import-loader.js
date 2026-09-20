/* Vestra Broker Import runtime loader v1.5 — load broker-only helpers on demand. */
(() => {
  'use strict';

  const TIMEOUT_MS = 12000;
  let identityDataPromise = null;
  let xtbNormalizationPromise = null;
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
      workbookPromise = load('VestraBrokerWorkbook', 'app-broker-workbook.js?v=1.3', 'workbook')
        .catch(err => {
          workbookPromise = null;
          throw err;
        });
    }
    return workbookPromise;
  }

  function ensureIdentityData() {
    if (window.VestraBrokerIdentityData) return Promise.resolve(window.VestraBrokerIdentityData);
    if (!identityDataPromise) {
      identityDataPromise = load('VestraBrokerIdentityData', 'app-broker-identity-data.js?v=1.0', 'identity-data').catch(err => {
        identityDataPromise = null;
        throw err;
      });
    }
    return identityDataPromise;
  }

  function ensureXtbNormalization() {
    if (window.VestraXtbNormalization) return Promise.resolve(window.VestraXtbNormalization);
    if (!xtbNormalizationPromise) {
      xtbNormalizationPromise = load('VestraXtbNormalization', 'app-xtb-normalization.js?v=1.0', 'xtb-normalization').catch(err => {
        xtbNormalizationPromise = null;
        throw err;
      });
    }
    return xtbNormalizationPromise;
  }

  function ensureParsers() {
    if (window.VestraBrokerParsers) return Promise.resolve(window.VestraBrokerParsers);
    if (!parsersPromise) {
      parsersPromise = Promise.all([ensureWorkbook(), ensureXtbNormalization()])
        .then(() => load('VestraBrokerParsers', 'app-broker-parsers.js?v=1.2', 'parsers'))
        .catch(err => {
          parsersPromise = null;
          throw err;
        });
    }
    return parsersPromise;
  }

  window.VestraBrokerImportLoader = Object.freeze({
    ensureIdentityData,
    ensureXtbNormalization,
    ensureWorkbook,
    ensureParsers,
    timeoutMs: TIMEOUT_MS,
    version: '1.5',
  });
})();
