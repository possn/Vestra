const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('market-live-overlay.js', 'utf8');

function loadModule(refreshCalls) {
  const windowObj = {
    VestraMarketData: {
      refreshOpenDossier(ticker, stock) { refreshCalls.push([ticker, stock]); }
    }
  };
  const sandbox = {
    window: windowObj,
    Intl,
    Date,
    encodeURIComponent,
    setTimeout,
    clearTimeout,
    requestAnimationFrame(fn) { fn(); return 1; },
    document: {
      createElement() {
        return {
          firstElementChild: null,
          set innerHTML(value) {
            this.firstElementChild = value ? { markup: value } : null;
          }
        };
      }
    }
  };
  vm.createContext(sandbox);
  vm.runInContext(source, sandbox, { filename: 'market-live-overlay.js' });
  return sandbox.window.VestraMarketLiveOverlay;
}

function makeSheet(ticker = 'MSFT') {
  const fields = new Map([
    ['current_price', { textContent: 'old-price' }],
    ['forward_pe', { textContent: 'old-pe' }],
    ['roe', { textContent: 'old-roe' }],
    ['revenue_growth', { textContent: 'old-growth' }],
    ['fcf_yield', { textContent: 'old-fcf' }],
  ]);
  const sheet = {
    hidden: false,
    dataset: { ticker },
    querySelector(selector) {
      const match = selector.match(/^\[data-live-field="(.+)"\]$/);
      if (match) return fields.get(match[1]) || null;
      if (selector === '.market-detail-head') return null;
      return null;
    }
  };
  return { sheet, fields };
}

(async () => {
  const refreshCalls = [];
  const moduleApi = loadModule(refreshCalls);
  assert(moduleApi, 'module must expose VestraMarketLiveOverlay');
  assert.strictEqual(moduleApi.version, '1.2');
  assert.strictEqual(moduleApi.timeoutMs, 4500);

  const { sheet, fields } = makeSheet('MSFT');
  const loadingSet = new Set();
  const stock = { ticker: 'MSFT', currency: 'USD', current_price: 100 };
  const overlay = moduleApi.create({
    getWorkerBase: () => 'https://worker.example/',
    getSheet: () => sheet,
    loadingSet,
    text: value => String(value ?? '').trim(),
    escapeHtml: value => String(value),
    formatMoney: (value, currency) => `${currency}:${value}`,
    formatNum: value => `N:${value}`,
    formatPct: value => `P:${value}`,
    fetchImpl: async () => ({
      ok: true,
      async json() {
        return {
          ticker: 'MSFT',
          provider_symbol: 'MSFT',
          retrieval_ticker: 'MSFT',
          current_price: 111,
          forward_pe: 25,
          roe: 0.3,
          revenue_growth: 0.2,
          fcf_yield: 0.05,
          updated: '2026-08-31T20:00:00Z'
        };
      }
    })
  });

  const live = await overlay.enrichTickerLive(stock);
  assert(live, 'exact live response should be returned');
  assert.strictEqual(stock.current_price, 111);
  assert.strictEqual(stock.provider_symbol, 'MSFT');
  assert.strictEqual(stock.identity_verified, true);
  assert.strictEqual(fields.get('current_price').textContent, 'USD:111');
  assert.strictEqual(refreshCalls.length, 1);
  assert.strictEqual(refreshCalls[0][0], 'MSFT');
  assert.strictEqual(loadingSet.size, 0);

  const mismatchStock = { ticker: 'SPIE', current_price: 44 };
  const mismatchOverlay = moduleApi.create({
    getWorkerBase: () => 'https://worker.example',
    getSheet: () => makeSheet('SPIE').sheet,
    loadingSet: new Set(),
    text: value => String(value ?? '').trim(),
    fetchImpl: async () => ({
      ok: true,
      json: async () => ({
        ticker: 'SPIE',
        provider_symbol: 'GOOG',
        retrieval_ticker: 'SPIE',
        current_price: 343.68,
        name: 'Alphabet Inc.'
      })
    })
  });
  assert.strictEqual(await mismatchOverlay.enrichTickerLive(mismatchStock), null);
  assert.strictEqual(mismatchStock.current_price, 44, 'mismatched live identity must not mutate the stock');

  const timeoutLoading = new Set();
  const timeoutOverlay = moduleApi.create({
    getWorkerBase: () => 'https://worker.example',
    getSheet: () => makeSheet('SLOW').sheet,
    loadingSet: timeoutLoading,
    text: value => String(value ?? '').trim(),
    timeoutMs: 5,
    fetchImpl: async () => new Promise(() => {})
  });
  assert.strictEqual(await timeoutOverlay.enrichTickerLive({ ticker: 'SLOW', current_price: 8 }), null);
  assert.strictEqual(timeoutLoading.size, 0);

  console.log('market live overlay contract: ok');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
