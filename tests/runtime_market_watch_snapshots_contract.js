const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market-watch-snapshots.js', 'utf8');
const store = new Map();
const storage = {
  getItem: key => store.has(key) ? store.get(key) : null,
  setItem: (key, value) => store.set(key, value),
};
const nowValue = Date.parse('2026-09-01T08:00:00Z');

const stocks = [
  {
    ticker: 'WDC', score: 77, thesis_direction: 'up', thesis_type: 'Quality',
    forward_pe_vs_sector_pct: -12, analyst_eps_revisions_up_30d: 4,
    analyst_eps_revisions_down_30d: 1, insider_buy_count_30d: 2,
    insider_sell_count_30d: 0, analyst_next_earnings_date: '2026-09-10', current_price: 91,
  },
  { ticker: 'MSFT', score: 82, current_price: 510 },
];
const byTicker = new Map(stocks.map(stock => [stock.ticker, stock]));
const state = { watchlist: new Set(), previousSnapshot: null, currentSnapshot: null };

const window = { localStorage: storage };
const context = { window, console, Date, Set, Map };
vm.createContext(context);
vm.runInContext(source, context, { filename: 'market-watch-snapshots.js' });

const api = window.VestraMarketWatchSnapshots.create({
  state,
  storage,
  now: () => nowValue,
  getPortfolioTickers: () => new Set(['MSFT']),
  getStocksByTicker: () => byTicker,
  getStocks: () => stocks,
  getGeneratedAt: () => '2026-09-01T07:30:00Z',
  text: value => String(value ?? '').trim(),
  number: value => value === null || value === undefined || value === '' ? null : Number(value),
  escapeHtml: value => String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;'),
  formatShortDate: value => String(value).slice(0, 10),
});

store.set('vestra-market-watchlist-v1', JSON.stringify(['wdc', '', 'msft']));
const loaded = api.loadWatchlist();
assert.deepStrictEqual([...loaded], ['WDC', 'MSFT']);
assert.strictEqual(api.isWatched('wdc'), true);

api.saveWatchlist();
assert.deepStrictEqual(JSON.parse(store.get('vestra-market-watchlist-v1')), ['WDC', 'MSFT']);

const first = api.syncSnapshots();
assert(first && first.stocks.WDC && first.stocks.MSFT, 'watchlist + portfolio tickers must be snapshotted');
assert.strictEqual(first.stocks.WDC.score, 77);
assert.strictEqual(first.savedAt, '2026-09-01T08:00:00.000Z');

state.watchlist.add('NEW');
stocks.push({ ticker: 'NEW', score: 60, current_price: 12 });
byTicker.set('NEW', stocks[2]);
api.syncSnapshots();
const sameGeneration = JSON.parse(store.get('vestra-market-snapshot-last-v1'));
assert(sameGeneration.stocks.NEW, 'same-generation snapshot should enrich newly tracked tickers');

const rotated = window.VestraMarketWatchSnapshots.create({
  state,
  storage,
  now: () => nowValue + 3600000,
  getPortfolioTickers: () => new Set(['MSFT']),
  getStocksByTicker: () => byTicker,
  getStocks: () => stocks,
  getGeneratedAt: () => '2026-09-01T08:30:00Z',
  text: value => String(value ?? '').trim(),
  number: value => value === null || value === undefined || value === '' ? null : Number(value),
  escapeHtml: value => String(value ?? ''),
  formatShortDate: value => String(value).slice(0, 10),
});
rotated.syncSnapshots();
assert(state.previousSnapshot, 'previous snapshot must be exposed after generation rotation');
assert.strictEqual(state.previousSnapshot.generatedAt, '2026-09-01T07:30:00Z');
assert.strictEqual(JSON.parse(store.get('vestra-market-snapshot-prev-v1')).generatedAt, '2026-09-01T07:30:00Z');

state.previousSnapshot = {
  generatedAt: '2026-08-31T08:00:00Z',
  stocks: {
    WDC: {
      score: 72,
      thesis_direction: 'neutral',
      forward_pe_vs_sector_pct: 4,
      analyst_eps_revisions_up_30d: 1,
      analyst_eps_revisions_down_30d: 1,
      insider_buy_count_30d: 0,
      insider_sell_count_30d: 0,
    },
  },
};
const signals = rotated.changeSignals(stocks[0]);
assert(signals.some(signal => signal.label === 'Score +5.0'));
assert(signals.some(signal => signal.label.startsWith('Tese ')));
assert(signals.some(signal => signal.label === 'Revisões EPS melhoraram'));
assert(signals.some(signal => signal.label === 'Valuation mais favorável'));
assert(signals.length <= 4, 'UI contract remains capped at four signals');

const badge = rotated.changeBadge(stocks[0]);
assert(badge.includes('market-change'));
const panel = rotated.changePanel(stocks[0]);
assert(panel.includes('O QUE MUDOU'));

console.log('market watch snapshots contract: ok');
