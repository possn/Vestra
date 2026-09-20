const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const app = fs.readFileSync('app.js', 'utf8');
const start = app.indexOf('function canonicalEquitySectorLabel(raw)');
const end = app.indexOf('\nfunction renderPortfolioSectorBox()', start);
assert.ok(start >= 0 && end > start, 'portfolio sector classifier block must remain reachable');

const context = vm.createContext({
  console,
  window: {},
  currentView: 'dashboard',
  fetch: () => Promise.reject(new Error('not used by classifier contract')),
  normalizePortfolioEquityClass: asset => String(asset?.class || '').toLowerCase(),
  getTickerMeta: () => ({ sector: '' }),
  renderPortfolioSectorBox: () => {},
});
vm.runInContext(app.slice(start, end), context, { filename: 'portfolio-sector-classifier.js' });
vm.runInContext(`portfolioSectorMap = {
  'NFC.DE': {sector:'Communication Services'},
  'NFLX': {sector:'Communication Services'},
  'UBER': {sector:'Technology'},
  'OMV.DE': {sector:'Energy'}
}`, context);

const classify = asset => vm.runInContext(`portfolioEquitySector(${JSON.stringify(asset)})`, context);

assert.strictEqual(classify({ticker:'NFC', name:'Netflix'}), 'Comunicação / Serviços');
assert.strictEqual(classify({ticker:'UT8', name:'Uber Technologies'}), 'Tecnologia');
assert.strictEqual(classify({yahooTicker:'OMV.VI', name:'OMV'}), 'Energia');
assert.strictEqual(classify({ticker:'IPDM.L', name:'Physical Palladium'}), 'Materiais');
assert.strictEqual(classify({ticker:'COPA.L', name:'Copper'}), 'Materiais');
assert.strictEqual(classify({ticker:'ADPT', name:'Adaptive Biotechnologies Corp'}), 'Saúde');
assert.strictEqual(classify({ticker:'NSIS-B.CO', name:'Novonesis'}), 'Materiais');
assert.strictEqual(classify({ticker:'DXYZ', name:'Destiny Tech100'}), 'Tecnologia');
assert.strictEqual(classify({ticker:'MPW', name:'Medical Properties Trust'}), 'Imobiliário', 'REIT identity must win over healthcare vocabulary');
assert.strictEqual(classify({ticker:'AMBA', name:'Ambarella', meta:{sector:'Industrials'}}), 'Industriais', 'live metadata must override static fallback');
assert.strictEqual(classify({ticker:'ZZZZ', name:'Unknown Holdings'}), 'Sector por identificar', 'ambiguous names must not be guessed');

console.log('runtime portfolio sector contract: ok');
