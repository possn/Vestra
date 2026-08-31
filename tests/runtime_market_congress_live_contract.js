const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market-congress-live.js', 'utf8');
const store = new Map();
const storage = {
  getItem: key => store.has(key) ? store.get(key) : null,
  setItem: (key, value) => store.set(key, value),
};
const now = Date.parse('2026-08-31T20:00:00Z');
const calls = [];
let resolver;
const pending = new Promise(resolve => { resolver = resolve; });
const context = {
  window: { localStorage: storage },
  fetch: async () => { throw new Error('unexpected global fetch'); },
  console,
  Date,
  Map,
  Set,
  JSON,
  Number,
  String,
  Object,
  Array,
  Promise,
  encodeURIComponent,
};
vm.createContext(context);
vm.runInContext(source, context, { filename: 'market-congress-live.js' });
assert.ok(context.window.VestraMarketCongressLive, 'module should publish its factory');

const state = { trades: [], loaded: false, loading: null, error: '' };
const stock = { ticker: 'MSFT', congress_trades: [{ transaction_date: '2026-08-20', representative: 'A', type: 'Purchase', amount: '$1', asset: 'Microsoft' }] };
const api = context.window.VestraMarketCongressLive.create({
  state,
  getStocksByTicker: () => new Map([['MSFT', stock]]),
  getStocks: () => [stock],
  text: v => String(v ?? '').trim(),
  storage,
  now: () => now,
  fetchImpl: async (url, init) => {
    calls.push({ url, init });
    await pending;
    return {
      ok: true,
      json: async () => ({
        schema_version: 2,
        newest_disclosure: '2026-08-30',
        trades: [
          { ticker: 'MSFT', representative: 'A', type: 'Purchase', amount: '$1', transaction_date: '2026-08-20', asset: 'Microsoft' },
          { ticker: 'MSFT', member: 'B', transaction: 'Sale', amount_range: '$2-$3', date: '2026-08-29', asset: 'Microsoft' },
          { ticker: 'AAPL', representative: 'C', type: 'Purchase', amount: '$4', transaction_date: '2026-08-29', asset: 'Apple' },
        ],
      }),
    };
  },
});

(async () => {
  const first = api.load('MSFT');
  const second = api.load('MSFT');
  assert.strictEqual(calls.length, 1, 'concurrent loads should share one request');
  assert.strictEqual(calls[0].init.cache, 'no-store');
  resolver();
  const [a, b] = await Promise.all([first, second]);
  assert.strictEqual(a.length, 2);
  assert.strictEqual(b.length, 2);
  assert.strictEqual(state.loaded, true);
  assert.strictEqual(state.error, '');
  assert.strictEqual(stock.congress_trades.length, 2, 'existing trade must not be duplicated');
  assert.strictEqual(stock.congress_trades[1].representative, 'B');

  const cachedState = { trades: [], loaded: false, loading: null, error: '' };
  let cachedFetches = 0;
  const cachedApi = context.window.VestraMarketCongressLive.create({
    state: cachedState,
    getStocksByTicker: () => new Map(),
    getStocks: () => [],
    text: v => String(v ?? '').trim(),
    storage,
    now: () => now + 1000,
    fetchImpl: async () => { cachedFetches += 1; throw new Error('cache should win'); },
  });
  const cached = await cachedApi.load('AAPL');
  assert.strictEqual(cachedFetches, 0, 'fresh local cache should avoid network');
  assert.strictEqual(cached.length, 1);
  assert.strictEqual(cached[0].ticker, 'AAPL');

  const staleState = { trades: [], loaded: false, loading: null, error: '' };
  const staleApi = context.window.VestraMarketCongressLive.create({
    state: staleState,
    getStocksByTicker: () => new Map(),
    getStocks: () => [],
    text: v => String(v ?? '').trim(),
    storage: { getItem: () => null, setItem: () => {} },
    now: () => now,
    fetchImpl: async () => ({ ok: true, json: async () => ({ schema_version: 2, newest_disclosure: '2026-01-01', trades: [] }) }),
  });
  const stale = await staleApi.load();
  assert.deepStrictEqual(Array.from(stale), []);
  assert.strictEqual(staleState.loaded, true);
  assert.strictEqual(staleState.error, 'Congress snapshot desactualizado');

  console.log('market congress live contract: ok');
})().catch(error => {
  console.error(error);
  process.exit(1);
});
