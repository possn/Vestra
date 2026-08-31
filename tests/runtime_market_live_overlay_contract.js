const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const source = fs.readFileSync('market-live-overlay.js', 'utf8');

function loadModule() {
  const sandbox = {
    window: {},
    Intl,
    Date,
    encodeURIComponent,
    setTimeout,
    clearTimeout,
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
    sentinel: 'do-not-rerender',
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
  const moduleApi = loadModule();
  assert(moduleApi, 'module must expose VestraMarketLiveOverlay');
  assert.strictEqual(moduleApi.version, '1.0');

  const { sheet, fields } = makeSheet('MSFT');
  const loadingSet = new Set();
  const requests = [];
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
    fetchImpl: async (url, init) => {
      requests.push({ url, init });
      return {
        ok: true,
        async json() {
          return {
            ticker: 'MSFT',
            current_price: 111,
            forward_pe: 25,
            roe: 0.3,
            revenue_growth: 0.2,
            fcf_yield: 0.05,
            updated: '2026-08-31T20:00:00Z'
          };
        }
      };
    }
  });

  const live = await overlay.enrichTickerLive(stock);
  assert(live, 'successful live response should be returned');
  assert.strictEqual(requests.length, 1);
  assert.strictEqual(requests[0].url, 'https://worker.example/market?ticker=MSFT');
  assert.strictEqual(requests[0].init.cache, 'no-store');
  assert.strictEqual(stock.current_price, 111);
  assert.strictEqual(stock._liveUpdated, '2026-08-31T20:00:00Z');
  assert.strictEqual(sheet.sentinel, 'do-not-rerender');
  assert.strictEqual(sheet.dataset.liveReady, '1');
  assert.strictEqual(fields.get('current_price').textContent, 'USD:111');
  assert.strictEqual(fields.get('forward_pe').textContent, 'N:25');
  assert.strictEqual(fields.get('roe').textContent, 'P:0.3');
  assert.strictEqual(fields.get('revenue_growth').textContent, 'P:0.2');
  assert.strictEqual(fields.get('fcf_yield').textContent, 'P:0.05');
  assert.strictEqual(loadingSet.size, 0, 'loading gate must be released');

  let release;
  let pendingFetches = 0;
  const pendingOverlay = moduleApi.create({
    getWorkerBase: () => 'https://worker.example',
    getSheet: () => makeSheet('RRX').sheet,
    loadingSet: new Set(),
    text: value => String(value ?? '').trim(),
    fetchImpl: async () => {
      pendingFetches += 1;
      await new Promise(resolve => { release = resolve; });
      return { ok: true, json: async () => ({ current_price: 10, updated: '2026-08-31T20:00:00Z' }) };
    }
  });
  const pendingStock = { ticker: 'RRX' };
  const first = pendingOverlay.enrichTickerLive(pendingStock);
  const duplicate = await pendingOverlay.enrichTickerLive(pendingStock);
  assert.strictEqual(duplicate, null, 'duplicate in-flight enrichment must be ignored');
  assert.strictEqual(pendingFetches, 1);
  release();
  await first;

  const fallbackStock = { ticker: 'FAIL', current_price: 7 };
  const fallbackOverlay = moduleApi.create({
    getWorkerBase: () => 'https://worker.example',
    getSheet: () => makeSheet('FAIL').sheet,
    loadingSet: new Set(),
    text: value => String(value ?? '').trim(),
    fetchImpl: async () => ({ ok: false, status: 503 })
  });
  assert.strictEqual(await fallbackOverlay.enrichTickerLive(fallbackStock), null);
  assert.strictEqual(fallbackStock.current_price, 7, 'local snapshot must survive live failure');

  console.log('market live overlay contract: ok');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
