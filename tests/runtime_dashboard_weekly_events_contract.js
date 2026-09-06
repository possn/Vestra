const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('dashboard-weekly-events.js', 'utf8');
const document = {
  readyState: 'loading',
  addEventListener: () => {},
  getElementById: () => null,
  head: { appendChild: () => {} },
};
const windowObj = {
  addEventListener: () => {},
  VestraMarketStaticUniverse: { getStocks: () => [] },
};
const context = {
  window: windowObj,
  document,
  console,
  Date,
  Intl,
  Set,
  setTimeout: () => 0,
  clearTimeout: () => {},
};
vm.createContext(context);
vm.runInContext(source, context);

const api = context.window.VestraWeeklyEvents;
assert(api && api.version === '1.0');
assert.strictEqual(typeof api.collectEvents, 'function');
assert.strictEqual(typeof api.selectEvents, 'function');
assert.strictEqual(typeof api.parseCalendarDate, 'function');
assert.strictEqual(typeof api.tickerMatchesPortfolio, 'function');

const now = new Date(2026, 8, 6, 9, 0, 0); // Sunday 6 Sep 2026, local calendar semantics.
const stocks = [
  { ticker:'NVDA', name:'NVIDIA', quote_type:'EQUITY', market_cap:4_000_000_000_000, analyst_next_earnings_date:'2026-09-08' },
  { ticker:'AAPL', name:'Apple', quote_type:'EQUITY', market_cap:3_500_000_000_000, analyst_next_earnings_date:'2026-09-09' },
  { ticker:'SMALL', name:'Small Holding', quote_type:'EQUITY', market_cap:10_000_000, analyst_next_earnings_date:'2026-09-12' },
  { ticker:'OLD', name:'Old event', quote_type:'EQUITY', market_cap:9_000_000_000, analyst_next_earnings_date:'2026-09-05' },
  { ticker:'LATE', name:'Too late', quote_type:'EQUITY', market_cap:9_000_000_000, analyst_next_earnings_date:'2026-09-13' },
  { ticker:'ETF1', name:'Fund', quote_type:'ETF', market_cap:8_000_000_000, analyst_next_earnings_date:'2026-09-07' },
];

const portfolio = new Set(['SMALL']);
const collected = api.collectEvents(stocks, portfolio, now);
assert.deepStrictEqual(Array.from(collected, x => x.ticker), ['NVDA','AAPL','SMALL']);
assert.strictEqual(collected.find(x => x.ticker === 'SMALL').inPortfolio, true);
assert.strictEqual(collected.find(x => x.ticker === 'NVDA').inPortfolio, false);

const selected = api.selectEvents(stocks, portfolio, now, 2);
assert.deepStrictEqual(Array.from(selected, x => x.ticker), ['NVDA','SMALL'], 'portfolio event must reserve a slot, then largest market event fills the card');
assert.strictEqual(selected[1].inPortfolio, true);

assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA', new Set(['AIR'])), true);
assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA', new Set(['AIR.PA'])), true);
assert.strictEqual(api.tickerMatchesPortfolio('AIR.PA', new Set(['AAPL'])), false);

const plain = api.parseCalendarDate('2026-09-08');
assert.strictEqual(plain.getFullYear(), 2026);
assert.strictEqual(plain.getMonth(), 8);
assert.strictEqual(plain.getDate(), 8);
assert.strictEqual(api.parseCalendarDate(''), null);
assert.strictEqual(api.parseCalendarDate('not-a-date'), null);

console.log('dashboard weekly events runtime contract: ok');
