const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const context = {
  console,
  window: { addEventListener() {}, dispatchEvent() {} },
  CustomEvent: function CustomEvent(type, init){ this.type = type; this.detail = init?.detail; },
};
vm.createContext(context);
vm.runInContext(fs.readFileSync('market-etf-intelligence.js', 'utf8'), context);

const api = context.window.VestraEtfIntelligence;
assert(api, 'ETF intelligence API missing');

const equity = { ticker: 'EQ', quote_type: 'EQUITY', score: 81 };
const fund = {
  ticker: 'TEST', quote_type: 'ETF', score: null,
  expense_ratio: 0.0015,
  fund_total_assets: 6_000_000_000,
  top_holdings: [
    { weight: 0.04 }, { weight: 0.04 }, { weight: 0.04 }, { weight: 0.04 }, { weight: 0.04 },
    { weight: 0.04 }, { weight: 0.04 }, { weight: 0.04 }, { weight: 0.04 }, { weight: 0.04 },
  ],
  current_price: 98,
  fifty_two_week_high: 100,
  fifty_two_week_low: 75,
  fund_return_1y_pct: 7,
  fund_ucits: 'confirmed',
  fund_family: 'Test Family',
  fund_category: 'Broad Market',
  fund_region: 'Global',
  fund_style: 'Broad',
  fund_theme: 'World',
};

const result = api.enrichStocks([equity, fund]);
assert.strictEqual(equity.score, 81, 'equity score must remain untouched');
assert.strictEqual(fund.score, null, 'ETF intelligence must not overwrite core score');
assert.strictEqual(fund.etf_score_model, 'etf_v1');
assert(Number.isFinite(fund.etf_score) && fund.etf_score >= 70, 'expected a publishable ETF score');
assert.strictEqual(fund.etf_score_status, 'published');
assert.strictEqual(result.funds, 1);
assert.strictEqual(result.scored, 1);

const pending = api.assess({ ticker:'PENDING', quote_type:'ETF', fund_region:'Europe' });
assert.strictEqual(pending.etf_score, null);
assert.strictEqual(pending.etf_score_status, 'pending');
assert(pending.etf_score_coverage_pct > 0 && pending.etf_score_coverage_pct < 50);

console.log('ETF intelligence runtime contract OK');
