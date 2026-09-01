const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market-portfolio-context.js', 'utf8');
const window = {};
const context = { window, console, Intl, Set };
vm.createContext(context);
vm.runInContext(source, context, { filename: 'market-portfolio-context.js' });

assert(window.VestraMarketPortfolioContext, 'module must expose VestraMarketPortfolioContext');
assert.strictEqual(window.VestraMarketPortfolioContext.version, '1.0');

const assets = [
  { class: 'Ações', yahooTicker: 'SIE.DE', ticker: 'SIE', value: 1200 },
  { class: 'ETF', ticker: 'VWCE.DE', marketValueEUR: 2500 },
  { class: 'Fund', symbol: 'FUND.L', value: 300 },
  { class: 'Cripto', ticker: 'ATOM', value: 900 },
  { class: 'Cash', ticker: 'EUR', value: 400 },
];

const api = window.VestraMarketPortfolioContext.create({
  getAssets: () => assets,
  text: value => String(value ?? '').trim(),
  number: value => {
    if (value === null || value === undefined || value === '') return null;
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  },
});

assert.strictEqual(api.portfolioAssets(), assets);
assert.strictEqual(api.researchEligibleAsset(assets[0]), true);
assert.strictEqual(api.researchEligibleAsset(assets[1]), true);
assert.strictEqual(api.researchEligibleAsset(assets[2]), true);
assert.strictEqual(api.researchEligibleAsset(assets[3]), false, 'crypto must never be inferred as listed-company research');
assert.strictEqual(api.researchEligibleAsset(assets[4]), false);

assert.strictEqual(api.assetTicker(assets[0]), 'SIE.DE', 'authoritative yahooTicker must win');
assert.strictEqual(api.assetTicker(assets[2]), 'FUND.L', 'symbol remains fallback');
assert.deepStrictEqual([...api.portfolioTickers()], ['SIE.DE', 'VWCE.DE', 'FUND.L']);
assert.strictEqual(api.inPortfolio('SIE.DE'), true);
assert.strictEqual(api.inPortfolio('SIE'), true, 'base ticker must match exchange-qualified holding');
assert.strictEqual(api.inPortfolio('ATOM'), false, 'crypto collision must stay excluded');
assert.strictEqual(api.inPortfolio('MSFT'), false);

assert.strictEqual(api.portfolioValue({ value: 0, marketValueEUR: 99 }), 0, 'explicit zero value must be preserved');
assert.strictEqual(api.portfolioValue({ marketValueEUR: 99 }), 99);
assert.strictEqual(api.portfolioValue({}), 0);
assert.strictEqual(api.euro(null), '—');
assert(api.euro(1234).includes('€'), 'EUR formatter must remain euro-denominated');

console.log('market portfolio context contract: ok');
