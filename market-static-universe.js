/* Vestra Market static universe loader v1.0 */
(() => {
  'use strict';

  function ensureScannerCompanion() {
    if (typeof document === 'undefined') return;
    if (window.VestraMarketScannerData || document.querySelector('script[data-vestra-scanner-data]')) return;
    const script = document.createElement('script');
    script.src = 'market-scanner-data.js?v=1.1';
    script.defer = true;
    script.dataset.vestraScannerData = '1';
    document.head.appendChild(script);
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

    async function ensureLoaded() {
      if (state.loaded) return;
      if (state.loading) return state.loading;

      state.loading = (async () => {
        let response = await fetchImpl('data/stocks-index.json', { cache: 'no-store' });
        if (!response.ok) response = await fetchImpl('data/stocks.json', { cache: 'no-store' });
        if (!response.ok) throw new Error(`market data ${response.status}`);

        const data = await response.json();
        const stocks = Array.isArray(data?.stocks) ? data.stocks : [];
        state.data = data;
        state.stocks = stocks;
        state.byTicker = new Map(stocks.map(stock => [txt(stock?.ticker).toUpperCase(), stock]));

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
  window.VestraMarketStaticUniverse = Object.freeze({ create, ensureScannerCompanion, version: '1.0' });
})();
