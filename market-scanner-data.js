/* Vestra Market Scanner Data v1.0 — lazy strategy payload with rollout compatibility. */
(() => {
  'use strict';

  function create({
    getStocks = () => [],
    getStocksByTicker = () => new Map(),
    fetchImpl = (...args) => fetch(...args),
    text = v => String(v ?? '').trim(),
  } = {}) {
    let loaded = false;
    let loading = null;
    let lastError = '';

    function inlineAvailable() {
      return getStocks().some(stock => stock?.scanner_results && typeof stock.scanner_results === 'object');
    }

    function result(stock, key) {
      const results = stock?.scanner_results;
      return results && typeof results === 'object' ? results[key] || null : null;
    }

    function mergeTickers(tickers) {
      if (!tickers || typeof tickers !== 'object' || Array.isArray(tickers)) return 0;
      const byTicker = getStocksByTicker();
      let merged = 0;
      for (const [rawTicker, results] of Object.entries(tickers)) {
        if (!results || typeof results !== 'object' || Array.isArray(results)) continue;
        const ticker = text(rawTicker).toUpperCase();
        const stock = byTicker.get(ticker);
        if (!stock) continue;
        stock.scanner_results = results;
        merged += 1;
      }
      return merged;
    }

    async function load() {
      // During the rollout, the currently published stocks-index.json may still
      // contain scanner_results. Use those immediately and avoid an unnecessary
      // request until the next market-data rebuild publishes stocks-scanner.json.
      if (loaded || inlineAvailable()) {
        loaded = true;
        lastError = '';
        return true;
      }
      if (loading) return loading;

      loading = (async () => {
        const response = await fetchImpl('data/stocks-scanner.json', { cache: 'no-store' });
        if (!response.ok) throw new Error(`scanner data ${response.status}`);
        const payload = await response.json();
        const tickers = payload?.tickers;
        if (!tickers || typeof tickers !== 'object' || Array.isArray(tickers)) {
          throw new Error('scanner data inválido');
        }
        mergeTickers(tickers);
        loaded = true;
        lastError = '';
        return true;
      })().catch(error => {
        lastError = text(error?.message) || 'scanner indisponível';
        throw error;
      }).finally(() => {
        loading = null;
      });

      return loading;
    }

    function isReady() {
      return loaded || inlineAvailable();
    }

    function error() {
      return lastError;
    }

    return Object.freeze({ load, result, mergeTickers, isReady, error });
  }

  window.VestraMarketScannerData = Object.freeze({ create, version: '1.0' });
})();
