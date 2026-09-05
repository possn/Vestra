/* Vestra Market static universe loader v1.0 */
(() => {
  'use strict';

  let sharedStocks = [];

  function getStocks() {
    return sharedStocks;
  }

  function ensureScannerCompanion() {
    if (typeof document === 'undefined') return;
    if (window.VestraMarketScannerData || document.querySelector('script[data-vestra-scanner-data]')) return;
    const script = document.createElement('script');
    script.src = 'market-scanner-data.js?v=1.1';
    script.defer = true;
    script.dataset.vestraScannerData = '1';
    document.head.appendChild(script);
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
    delete data.layout;
    delete data.fields;
    delete data.rows;
    return data;
  }

  function create({
    state,
    text,
    fetchImpl = (...args) => fetch(...args),
    beforeReady = () => {},
    onReady = () => {},
    onError = () => {},
  } = {}) {
    if (!state) throw new Error('VestraMarketStaticUniverse: state is required');
    const txt = typeof text === 'function' ? text : (v => String(v ?? '').trim());

    async function loadFirstAvailable() {
      const candidates = [
        ['data/stocks-startup.json', true],
        ['data/stocks-index.json', false],
        ['data/stocks.json', false],
      ];
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
        state.data = data;
        state.stocks = stocks;
        state.byTicker = new Map(stocks.map(stock => [txt(stock?.ticker).toUpperCase(), stock]));
        sharedStocks = stocks;

        beforeReady();
        state.loaded = true;
        onReady();
      })().catch(error => {
        onError(error);
      }).finally(() => {
        state.loading = null;
      });

      return state.loading;
    }

    return Object.freeze({ ensureLoaded });
  }

  ensureScannerCompanion();
  window.VestraMarketStaticUniverse = Object.freeze({ create, getStocks, ensureScannerCompanion, unpackStartupPayload, version: '1.0' });
})();
