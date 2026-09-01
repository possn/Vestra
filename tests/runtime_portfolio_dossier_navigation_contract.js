const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('portfolio-sheet-navigation.js', 'utf8');

const content = {
  contains: () => true,
  querySelectorAll: () => [],
};
const sheet = {
  hidden: false,
  dataset: { tool: 'portfolio', returnView: 'assets', ticker: '' },
  querySelector: () => null,
  setAttribute: () => {},
  scrollTop: 0,
  scrollLeft: 0,
};

let resolveOpen;
let toolSeenByOpenTicker = null;
let returnViewSeenByOpenTicker = null;
let tickerSeen = null;

const document = {
  readyState: 'loading',
  body: { classList: { remove() {}, add() {} } },
  documentElement: { classList: { remove() {}, add() {} } },
  head: { appendChild() {} },
  getElementById(id) {
    if (id === 'marketSheet') return sheet;
    if (id === 'marketSheetContent') return content;
    return null;
  },
  querySelector: () => null,
  querySelectorAll: () => [],
  createElement: () => ({ id: '', textContent: '' }),
  addEventListener: () => {},
};

const window = {
  VestraMarket: {
    __lazyDossiersInstalled: true,
    openTicker(ticker) {
      tickerSeen = ticker;
      toolSeenByOpenTicker = sheet.dataset.tool;
      returnViewSeenByOpenTicker = sheet.dataset.returnView;
      sheet.dataset.ticker = ticker;
      return new Promise(resolve => { resolveOpen = resolve; });
    },
  },
};

const context = {
  window,
  document,
  console,
  Promise,
  setTimeout: () => 0,
  requestAnimationFrame: fn => fn(),
  MutationObserver: function () { this.observe = () => {}; },
};
vm.createContext(context);
vm.runInContext(source, context, { filename: 'portfolio-sheet-navigation.js' });

(async () => {
  const nav = window.VestraNavigation;
  assert(nav, 'VestraNavigation must be installed');
  assert.strictEqual(nav.version, '1.4');

  const pending = nav.openCompany('wdc', { origin: 'portfolio' });

  assert.strictEqual(tickerSeen, 'WDC', 'ticker must be normalized before opening');
  assert.strictEqual(toolSeenByOpenTicker, 'ticker-from-portfolio', 'sheet must leave portfolio mode before dossier render');
  assert.strictEqual(returnViewSeenByOpenTicker, 'portfolio', 'close path must remember portfolio origin before dossier render');
  assert.strictEqual(sheet.dataset.tool, 'ticker-from-portfolio');
  assert.strictEqual(sheet.dataset.returnView, 'portfolio');
  assert.strictEqual(sheet.dataset.ticker, 'WDC');

  resolveOpen();
  assert.strictEqual(await pending, true);
  assert.strictEqual(sheet.dataset.tool, 'ticker-from-portfolio');
  assert.strictEqual(sheet.dataset.returnView, 'portfolio');

  // Opening from the market must clear portfolio-only navigation state.
  window.VestraMarket.openTicker = ticker => {
    assert.strictEqual(sheet.dataset.tool, '', 'market dossier must clear portfolio mode before render');
    assert.strictEqual(sheet.dataset.returnView, '', 'market dossier must clear portfolio return state before render');
    sheet.dataset.ticker = ticker;
  };
  assert.strictEqual(await nav.openCompany('MSFT', { origin: 'market' }), true);
  assert.strictEqual(sheet.dataset.tool, '');
  assert.strictEqual(sheet.dataset.returnView, '');

  console.log('portfolio dossier navigation contract: ok');
})().catch(error => {
  console.error(error);
  process.exitCode = 1;
});
