const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market-opportunities.js', 'utf8');
const documentStub = {
  readyState: 'loading',
  addEventListener() {},
  getElementById() { return null; },
  querySelectorAll() { return []; },
  head: { appendChild() {} },
  createElement() { return { className:'', dataset:{}, appendChild(){}, setAttribute(){}, style:{} }; },
};
const context = {
  window: {
    VestraMarketStaticUniverse: { getStocks: () => [] },
  },
  document: documentStub,
  console,
  CSS: { escape: x => String(x) },
  requestAnimationFrame: fn => fn(),
  MutationObserver: function(){ this.observe = () => {}; },
};
vm.createContext(context);
vm.runInContext(source, context);

const api = context.window.VestraMarketOpportunities;
assert(api, 'Opportunity API should be exposed');

function candidate(ticker, score, sector, industry) {
  return {
    ticker,
    name: ticker,
    opportunity_eligible: true,
    opportunity_score: score,
    sector,
    industry,
    score: 80,
    confidence_score: 80,
    data_coverage_pct: 80,
    critical_metric_coverage_pct: 80,
    score_reliability: 'reliable',
    risk_gate: 'clear',
    zombie: 'no',
  };
}

{
  const universe = [
    candidate('TOP1', 99, 'Technology', 'Software'),
    candidate('TOP2', 98, 'Technology', 'Semiconductors'),
    candidate('TOP3', 97, 'Industrials', 'Aerospace'),
    candidate('A', 90, 'Healthcare', 'Biotechnology'),
    candidate('B', 89, 'Financial Services', 'Banks'),
    candidate('C', 88, 'Energy', 'Oil & Gas'),
  ];
  const rows = api.rankLens(universe, 'all', {limit: 6, sector: 'all'});
  assert.deepStrictEqual(Array.from(rows.slice(0, 3), x => x.ticker), ['TOP1','TOP2','TOP3'],
    'compatible top-3 Discovery anchors must survive the final shortlist');
}

{
  const universe = [
    candidate('TOP1', 99, 'Technology', 'Software'),
    candidate('TOP2', 98, 'Technology', 'Software'),
    candidate('TOP3', 97, 'Technology', 'Software'),
    candidate('ALT1', 96, 'Technology', 'Semiconductors'),
    candidate('ALT2', 95, 'Healthcare', 'Biotechnology'),
    candidate('ALT3', 94, 'Financial Services', 'Banks'),
    candidate('ALT4', 93, 'Energy', 'Oil & Gas'),
  ];
  const rows = api.rankLens(universe, 'all', {limit: 6, sector: 'all'});
  const tickers = Array.from(rows, x => x.ticker);
  assert(tickers.includes('TOP1') && tickers.includes('TOP2'));
  assert(!tickers.includes('TOP3'),
    'third same-industry anchor must yield to the industry concentration cap');

  const sectorCounts = new Map();
  const industryCounts = new Map();
  for (const row of rows) {
    sectorCounts.set(row.sector, (sectorCounts.get(row.sector) || 0) + 1);
    industryCounts.set(row.industry, (industryCounts.get(row.industry) || 0) + 1);
  }
  assert([...sectorCounts.values()].every(x => x <= 3), 'sector cap must remain <=3');
  assert([...industryCounts.values()].every(x => x <= 2), 'industry cap must remain <=2');
}

console.log('opportunity shortlist runtime contract: ok');
