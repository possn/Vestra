/* Vestra Market Scanner Data v1.1 — lazy strategy payload with rollout compatibility. */
(() => {
  'use strict';

  function create({
    resolveStock = () => null,
    fetchImpl = (...args) => fetch(...args),
    text = v => String(v ?? '').trim(),
  } = {}) {
    let loaded = false;
    let loading = null;
    let lastError = '';

    function mergeTickers(tickers) {
      if (!tickers || typeof tickers !== 'object' || Array.isArray(tickers)) return 0;
      let merged = 0;
      for (const [rawTicker, results] of Object.entries(tickers)) {
        if (!results || typeof results !== 'object' || Array.isArray(results)) continue;
        const ticker = text(rawTicker).toUpperCase();
        const stock = resolveStock(ticker);
        if (!stock) continue;
        stock.scanner_results = results;
        merged += 1;
      }
      return merged;
    }

    async function load() {
      if (loaded) return true;
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

    return Object.freeze({ load, mergeTickers, isReady: () => loaded, error: () => lastError });
  }

  let controller = null;
  let replaying = false;

  function runtimeController() {
    if (controller) return controller;
    const api = window.VestraMarket;
    if (!api?.resolvePortfolioStock) return null;
    controller = create({
      resolveStock: ticker => api.resolvePortfolioStock({
        ticker,
        yahooTicker: ticker,
        symbol: ticker,
        class: 'Ações',
      }),
    });
    return controller;
  }

  async function hydrateScanner(toolNode) {
    const api = window.VestraMarket;
    const control = runtimeController();
    if (!api?.ensureLoaded || !control || control.isReady()) return;
    await api.ensureLoaded();
    try {
      await control.load();
    } catch (_) {
      // Rollout compatibility: before the next data rebuild, the published
      // stocks-index.json can still contain inline scanner_results and the new
      // lazy payload may not exist yet. Leave the already-rendered Scanner intact.
      return;
    }
    const sheet = document.getElementById('marketSheet');
    if (!sheet || sheet.dataset.tool !== 'scanner') return;
    replaying = true;
    try { toolNode?.click?.(); } finally { replaying = false; }
  }

  document.addEventListener('click', event => {
    if (replaying) return;
    const tool = event.target.closest?.('[data-market-tool="scanner"]');
    if (!tool) return;
    // market.js handles the original click first in the bubble phase. The lazy
    // payload is then merged and the same tool is replayed once so the private
    // renderScanner() path remains the single renderer.
    queueMicrotask(() => hydrateScanner(tool));
  });

  window.VestraMarketScannerData = Object.freeze({ create, runtimeController, version: '1.1' });
})();
