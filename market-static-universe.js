/* Vestra Market static universe loader v1.12 */
(() => {
  'use strict';

  const DATA_FETCH_TIMEOUT_MS = 8000;
  const ETF_INTELLIGENCE_LOAD_TIMEOUT_MS = 8000;
  const COMPANION_LOAD_TIMEOUT_MS = 8000;
  let sharedStocks = [];
  let etfIntelligencePromise = null;

  function getStocks() { return sharedStocks; }

  function ensureEtfIntelligence() {
    if (typeof document === 'undefined') return Promise.resolve(window.VestraEtfIntelligence || null);
    if (window.VestraEtfIntelligence) return Promise.resolve(window.VestraEtfIntelligence);
    if (etfIntelligencePromise) return etfIntelligencePromise;
    const existing = document.querySelector('script[data-vestra-etf-intelligence]');
    etfIntelligencePromise = new Promise(resolve => {
      const script = existing || document.createElement('script');
      let settled = false;
      let timeoutId = null;
      const cleanup = () => {
        if (timeoutId !== null && typeof clearTimeout === 'function') clearTimeout(timeoutId);
        script.removeEventListener('load', onLoad);
        script.removeEventListener('error', onError);
      };
      const finish = value => {
        if (settled) return;
        settled = true;
        cleanup();
        etfIntelligencePromise = null;
        resolve(value || null);
      };
      const discardAndFinish = () => {
        if (script.isConnected) script.remove();
        finish(null);
      };
      const onLoad = () => {
        const api = window.VestraEtfIntelligence || null;
        if (!api) { discardAndFinish(); return; }
        finish(api);
      };
      const onError = () => discardAndFinish();

      script.addEventListener('load', onLoad, { once: true });
      script.addEventListener('error', onError, { once: true });
      if (typeof setTimeout === 'function') {
        timeoutId = setTimeout(discardAndFinish, ETF_INTELLIGENCE_LOAD_TIMEOUT_MS);
      }
      if (!existing) {
        script.src = 'market-etf-intelligence.js?v=1.2';
        script.defer = true;
        script.dataset.vestraEtfIntelligence = '1';
        document.head.appendChild(script);
      }
    });
    return etfIntelligencePromise;
  }

  function loadCompanion(globalName, selector, src, datasetKey, attempt = 0) {
    if (typeof document === 'undefined') return;
    if (window[globalName] || document.querySelector(selector)) return;
    const script = document.createElement('script');
    let settled = false;
    let timeoutId = null;
    const cleanup = () => {
      if (timeoutId !== null && typeof clearTimeout === 'function') clearTimeout(timeoutId);
      script.removeEventListener('load', onLoad);
      script.removeEventListener('error', onError);
    };
    const retry = () => {
      if (attempt < 1 && typeof setTimeout === 'function') {
        setTimeout(() => loadCompanion(globalName, selector, src, datasetKey, attempt + 1), 1000);
      }
    };
    const fail = () => {
      if (settled) return;
      settled = true;
      cleanup();
      if (script.isConnected) script.remove();
      retry();
    };
    const onLoad = () => {
      if (settled) return;
      if (!window[globalName]) { fail(); return; }
      settled = true;
      cleanup();
    };
    const onError = () => fail();

    script.src = src;
    script.defer = true;
    script.dataset[datasetKey] = '1';
    script.addEventListener('load', onLoad, { once: true });
    script.addEventListener('error', onError, { once: true });
    if (typeof setTimeout === 'function') {
      timeoutId = setTimeout(fail, COMPANION_LOAD_TIMEOUT_MS);
    }
    document.head.appendChild(script);
  }

  function ensureScannerCompanion() { loadCompanion('VestraMarketScannerData','script[data-vestra-scanner-data]','market-scanner-data.js?v=1.3','vestraScannerData'); }
  function ensureAnalysisToolsRuntime() { loadCompanion('VestraMarketAnalysisToolsRuntime','script[data-vestra-analysis-tools-runtime]','market-analysis-tools-runtime.js?v=1.3','vestraAnalysisToolsRuntime'); }
  function ensureWeeklyEventsCompanion() { loadCompanion('VestraWeeklyEvents','script[data-vestra-weekly-events]','dashboard-weekly-events.js?v=2.0','vestraWeeklyEvents'); }
  function ensureWeeklyEventsNavigation() { loadCompanion('VestraWeeklyEventsNavigation','script[data-vestra-weekly-events-navigation]','dashboard-weekly-events-navigation.js?v=1.1','vestraWeeklyEventsNavigation'); }
  function ensureDashboardUiRefresh() { loadCompanion('VestraDashboardUiRefresh','script[data-vestra-dashboard-ui-refresh]','dashboard-ui-refresh.js?v=1.4','vestraDashboardUiRefresh'); }
  function ensureDashboardDailyNews() { loadCompanion('VestraDashboardDailyNews','script[data-vestra-dashboard-daily-news]','dashboard-daily-news.js?v=1.1','vestraDashboardDailyNews'); }
  function ensureMobileUiRefresh() { loadCompanion('VestraMobileUiRefresh','script[data-vestra-mobile-ui-refresh]','mobile-ui-refresh.js?v=1.4','vestraMobileUiRefresh'); }
  function ensureMarketUiPolish() { loadCompanion('VestraMarketUiPolish','script[data-vestra-market-ui-polish]','market-ui-polish.js?v=1.3&stockthemes=2','vestraMarketUiPolish'); }
  function ensureUiVisualPolish() { loadCompanion('VestraUiVisualPolish','script[data-vestra-ui-visual-polish]','ui-visual-polish.js?v=1.1','vestraUiVisualPolish'); }

  function announceReady(stocks) {
    try {
      if (typeof window.dispatchEvent === 'function' && typeof CustomEvent === 'function') window.dispatchEvent(new CustomEvent('vestra:market-ready', { detail: { count: stocks.length } }));
    } catch (_) {}
  }

  function unpackStartupPayload(payload) {
    if (!payload || payload.layout !== 'field_rows_v1') return null;
    const fields = Array.isArray(payload.fields) ? payload.fields : [];
    const rows = Array.isArray(payload.rows) ? payload.rows : [];
    if (!fields.length || !rows.length) return null;
    const stocks = rows.map(values => {
      if (!Array.isArray(values)) return null;
      const stock = {};
      const limit = Math.min(values.length, fields.length);
      for (let i = 0; i < limit; i += 1) stock[fields[i]] = values[i];
      return stock;
    }).filter(Boolean);
    if (!stocks.length) return null;
    const data = { ...payload, stocks };
    delete data.layout; delete data.fields; delete data.rows;
    return data;
  }

  function create({ state, text, fetchImpl = (...args) => fetch(...args), fetchTimeoutMs = DATA_FETCH_TIMEOUT_MS, beforeReady = () => {}, onReady = () => {}, onError = () => {} } = {}) {
    if (!state) throw new Error('VestraMarketStaticUniverse: state is required');
    const txt = typeof text === 'function' ? text : (v => String(v ?? '').trim());
    async function fetchCandidate(url, packed) {
      const controller = typeof AbortController === 'function' ? new AbortController() : null;
      const request = (async () => {
        try {
          const init = { cache: 'no-store' };
          if (controller) init.signal = controller.signal;
          const response = await fetchImpl(url, init);
          const status = Number(response?.status) || 0;
          if (!response?.ok) return { status, data: null };
          const raw = await response.json();
          const data = packed ? unpackStartupPayload(raw) : raw;
          return { status, data };
        } catch (_) {
          return { status: 0, data: null };
        }
      })();
      if (typeof setTimeout !== 'function') return request;
      let timeoutId = null;
      const timeout = new Promise(resolve => {
        timeoutId = setTimeout(() => {
          try { controller?.abort(); } catch (_) {}
          resolve({ status: 0, data: null });
        }, Math.max(1, Number(fetchTimeoutMs) || DATA_FETCH_TIMEOUT_MS));
      });
      try {
        return await Promise.race([request, timeout]);
      } finally {
        if (timeoutId !== null && typeof clearTimeout === 'function') clearTimeout(timeoutId);
      }
    }
    async function loadFirstAvailable() {
      const candidates = [['data/stocks-startup.json', true], ['data/stocks-index.json', false]];
      let lastStatus = 0;
      for (const [url, packed] of candidates) {
        const result = await fetchCandidate(url, packed);
        if (result.status) lastStatus = result.status;
        const data = result.data;
        if (data && Array.isArray(data.stocks) && data.stocks.length) return data;
      }
      throw new Error(`market data ${lastStatus || 'unavailable'}`);
    }
    async function ensureLoaded() {
      if (state.loaded) return;
      if (state.loading) return state.loading;
      state.loading = (async () => {
        const data = await loadFirstAvailable();
        const stocks = data.stocks;
        state.data = data; state.stocks = stocks;
        state.byTicker = new Map(stocks.map(stock => [txt(stock?.ticker).toUpperCase(), stock]));
        sharedStocks = stocks;
        await ensureEtfIntelligence();
        try { window.VestraEtfIntelligence?.enrichStocks(stocks); } catch (_) {}
        beforeReady(); state.loaded = true; onReady(); announceReady(stocks);
      })().catch(error => { onError(error); }).finally(() => { state.loading = null; });
      return state.loading;
    }
    return Object.freeze({ ensureLoaded });
  }

  ensureEtfIntelligence(); ensureScannerCompanion(); ensureAnalysisToolsRuntime();
  ensureWeeklyEventsCompanion(); ensureWeeklyEventsNavigation(); ensureDashboardUiRefresh(); ensureDashboardDailyNews();
  ensureMobileUiRefresh(); ensureMarketUiPolish(); ensureUiVisualPolish();
  window.VestraMarketStaticUniverse = Object.freeze({
    create, getStocks, ensureEtfIntelligence, ensureScannerCompanion, ensureAnalysisToolsRuntime,
    ensureWeeklyEventsCompanion, ensureWeeklyEventsNavigation, ensureDashboardUiRefresh, ensureDashboardDailyNews,
    ensureMobileUiRefresh, ensureMarketUiPolish, ensureUiVisualPolish, unpackStartupPayload,
    dataFetchTimeoutMs: DATA_FETCH_TIMEOUT_MS, etfIntelligenceLoadTimeoutMs: ETF_INTELLIGENCE_LOAD_TIMEOUT_MS,
    companionLoadTimeoutMs: COMPANION_LOAD_TIMEOUT_MS, version: '1.12',
  });
})();