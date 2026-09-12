/* Vestra Market static universe loader v1.9 */
(() => {
  'use strict';

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
      if (!existing) {
        script.src = 'market-etf-intelligence.js?v=1.2';
        script.defer = true;
        script.dataset.vestraEtfIntelligence = '1';
        document.head.appendChild(script);
      }
      if (window.VestraEtfIntelligence) { resolve(window.VestraEtfIntelligence); return; }
      script.addEventListener('load', () => resolve(window.VestraEtfIntelligence || null), { once: true });
      script.addEventListener('error', () => resolve(null), { once: true });
    });
    return etfIntelligencePromise;
  }

  function loadCompanion(globalName, selector, src, datasetKey) {
    if (typeof document === 'undefined') return;
    if (window[globalName] || document.querySelector(selector)) return;
    const script = document.createElement('script');
    script.src = src;
    script.defer = true;
    script.dataset[datasetKey] = '1';
    document.head.appendChild(script);
  }

  function ensureScannerCompanion() { loadCompanion('VestraMarketScannerData','script[data-vestra-scanner-data]','market-scanner-data.js?v=1.3','vestraScannerData'); }
  function ensureAnalysisToolsRuntime() { loadCompanion('VestraMarketAnalysisToolsRuntime','script[data-vestra-analysis-tools-runtime]','market-analysis-tools-runtime.js?v=1.0','vestraAnalysisToolsRuntime'); }
  function ensureWeeklyEventsCompanion() { loadCompanion('VestraWeeklyEvents','script[data-vestra-weekly-events]','dashboard-weekly-events.js?v=1.7','vestraWeeklyEvents'); }
  function ensureWeeklyEventsNavigation() { loadCompanion('VestraWeeklyEventsNavigation','script[data-vestra-weekly-events-navigation]','dashboard-weekly-events-navigation.js?v=1.0','vestraWeeklyEventsNavigation'); }
  function ensureDashboardUiRefresh() { loadCompanion('VestraDashboardUiRefresh','script[data-vestra-dashboard-ui-refresh]','dashboard-ui-refresh.js?v=1.4','vestraDashboardUiRefresh'); }
  function ensureMobileUiRefresh() { loadCompanion('VestraMobileUiRefresh','script[data-vestra-mobile-ui-refresh]','mobile-ui-refresh.js?v=1.4','vestraMobileUiRefresh'); }
  function ensureMarketUiPolish() { loadCompanion('VestraMarketUiPolish','script[data-vestra-market-ui-polish]','market-ui-polish.js?v=1.2&stockthemes=2','vestraMarketUiPolish'); }
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

  function create({ state, text, fetchImpl = (...args) => fetch(...args), beforeReady = () => {}, onReady = () => {}, onError = () => {} } = {}) {
    if (!state) throw new Error('VestraMarketStaticUniverse: state is required');
    const txt = typeof text === 'function' ? text : (v => String(v ?? '').trim());
    async function loadFirstAvailable() {
      const candidates = [['data/stocks-startup.json', true], ['data/stocks-index.json', false]];
      let lastStatus = 0;
      for (const [url, packed] of candidates) {
        const response = await fetchImpl(url, { cache: 'no-store' });
        lastStatus = response.status;
        if (!response.ok) continue;
        const raw = await response.json();
        const data = packed ? unpackStartupPayload(raw) : raw;
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
  ensureWeeklyEventsCompanion(); ensureWeeklyEventsNavigation(); ensureDashboardUiRefresh();
  ensureMobileUiRefresh(); ensureMarketUiPolish(); ensureUiVisualPolish();
  window.VestraMarketStaticUniverse = Object.freeze({
    create, getStocks, ensureEtfIntelligence, ensureScannerCompanion, ensureAnalysisToolsRuntime,
    ensureWeeklyEventsCompanion, ensureWeeklyEventsNavigation, ensureDashboardUiRefresh,
    ensureMobileUiRefresh, ensureMarketUiPolish, ensureUiVisualPolish, unpackStartupPayload, version: '1.9',
  });
})();