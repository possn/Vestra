const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const source = fs.readFileSync('market-scanner-data.js', 'utf8');

global.window = {};
global.document = {
  addEventListener() {},
  getElementById() { return null; },
};
global.queueMicrotask = global.queueMicrotask || (fn => Promise.resolve().then(fn));

vm.runInThisContext(source, { filename: 'market-scanner-data.js' });

async function main() {
  assert(window.VestraMarketScannerData, 'scanner data API missing');
  assert.strictEqual(window.VestraMarketScannerData.version, '1.1');

  const stock = { ticker: 'MSFT', score: 82 };
  const stocks = new Map([['MSFT', stock]]);
  const calls = [];
  const controller = window.VestraMarketScannerData.create({
    resolveStock: ticker => stocks.get(ticker) || null,
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return {
        ok: true,
        async json() {
          return {
            tickers: {
              MSFT: {
                best_opportunities: { score: 77, label: 'Strong' },
                qarp: { score: 73, reasons: ['Quality', 'Value'] },
              },
              UNKNOWN: { best_opportunities: { score: 99 } },
            },
          };
        },
      };
    },
  });

  assert.strictEqual(stock.scanner_results, undefined, 'scanner data should start lazy');
  assert.strictEqual(controller.isReady(), false);
  assert.strictEqual(await controller.load(), true);
  assert.strictEqual(controller.isReady(), true);
  assert.strictEqual(calls.length, 1, 'scanner payload should fetch once');
  assert.strictEqual(calls[0].url, 'data/stocks-scanner.json');
  assert.deepStrictEqual(calls[0].options, { cache: 'no-store' });
  assert.strictEqual(stock.scanner_results.best_opportunities.score, 77);
  assert.strictEqual(stock.scanner_results.qarp.score, 73);

  await controller.load();
  assert.strictEqual(calls.length, 1, 'loaded scanner payload must be cached in memory');

  const bad = window.VestraMarketScannerData.create({
    resolveStock: () => stock,
    fetchImpl: async () => ({ ok: true, json: async () => ({ tickers: [] }) }),
  });
  await assert.rejects(() => bad.load(), /scanner data inválido/);
  assert.match(bad.error(), /scanner data inválido/);

  console.log('runtime market scanner data contract: ok');
}

main().catch(error => {
  console.error(error);
  process.exit(1);
});
