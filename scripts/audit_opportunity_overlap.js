const fs = require('fs');
const vm = require('vm');

const payload = JSON.parse(fs.readFileSync('data/stocks-index.json', 'utf8'));
const stocks = Array.isArray(payload?.stocks) ? payload.stocks : [];

global.window = {
  VestraMarketStaticUniverse: { getStocks: () => stocks },
};
global.document = {
  readyState: 'loading',
  addEventListener() {},
  getElementById() { return null; },
  querySelectorAll() { return []; },
  head: { appendChild() {} },
  createElement() { return { addEventListener() {}, removeEventListener() {}, dataset: {}, classList: { add() {}, remove() {}, toggle() {} } }; },
};
global.MutationObserver = class { observe() {} };
global.requestAnimationFrame = fn => fn();
global.CustomEvent = class {};

const source = fs.readFileSync('market-opportunities.js', 'utf8');
vm.runInThisContext(source, { filename: 'market-opportunities.js' });
const api = global.window.VestraMarketOpportunities;
if (!api) throw new Error('VestraMarketOpportunities API unavailable');
if (typeof api.rankLens !== 'function') throw new Error('canonical rankLens API unavailable');

const lenses = ['all', 'low52', 'emerging', 'recovery', 'value'];
const topN = Number(process.argv[2] || 12);
const ranked = {};
for (const lens of lenses) {
  ranked[lens] = api.rankLens(stocks, lens, { limit: topN })
    .map(stock => String(stock?.ticker || '').trim())
    .filter(Boolean);
}

function overlap(a, b) {
  const A = new Set(ranked[a]);
  const B = new Set(ranked[b]);
  const shared = [...A].filter(x => B.has(x));
  const union = new Set([...A, ...B]);
  return {
    shared_count: shared.length,
    overlap_of_top_n_pct: topN ? Number((shared.length / topN * 100).toFixed(1)) : 0,
    jaccard_pct: union.size ? Number((shared.length / union.size * 100).toFixed(1)) : 0,
    shared,
  };
}

const pairs = {};
for (let i = 0; i < lenses.length; i += 1) {
  for (let j = i + 1; j < lenses.length; j += 1) {
    pairs[`${lenses[i]}__${lenses[j]}`] = overlap(lenses[i], lenses[j]);
  }
}

const appearances = {};
for (const lens of lenses) {
  for (const ticker of ranked[lens]) appearances[ticker] = (appearances[ticker] || 0) + 1;
}
const repeated = Object.entries(appearances)
  .filter(([, count]) => count >= 3)
  .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  .map(([ticker, lens_count]) => ({ ticker, lens_count }));

const eligibleCounts = Object.fromEntries(lenses.map(lens => [lens, stocks.filter(stock => api.lensEligible(stock, lens)).length]));
const report = {
  generated_at: payload?.generated_at || null,
  universe_count: stocks.length,
  top_n: topN,
  eligible_counts: eligibleCounts,
  ranked,
  pairs,
  repeated_in_3plus_lenses: repeated,
};
console.log(JSON.stringify(report, null, 2));
