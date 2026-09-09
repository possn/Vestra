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
  assert.strictEqual(window.VestraMarketScannerData.version, '1.2');

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
                qarp: { score: 73, label: 'Quality at a Reasonable Price' },
                positive_revisions: { score: 68, label: 'Revisões positivas' },
                turnarounds: { score: 71, label: 'Turnarounds' },
                fallen_angels: { score: 65, label: 'Fallen Angels' },
                lows_intact: { score: 79, label: 'Mínimos 52s · fundamentos intactos' },
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

  // The analysis-tools UI still uses these stable tab keys. They must resolve to
  // real evidence-gated scanner strategies instead of silently returning empty.
  assert.strictEqual(stock.scanner_results.quality_at_fair_price, stock.scanner_results.qarp);
  assert.strictEqual(stock.scanner_results.growth_at_reasonable_price, stock.scanner_results.turnarounds,
    'Growth lens should use the strongest existing growth/revision signal');
  assert.strictEqual(stock.scanner_results.deep_value, stock.scanner_results.fallen_angels);
  assert.strictEqual(stock.scanner_results.low_52w, stock.scanner_results.lows_intact,
    '52-week-low lens should prefer the stricter lows_intact signal when available');

  const partial = { ticker: 'ADBE', score: 70 };
  stocks.set('ADBE', partial);
  controller.mergeTickers({
    ADBE: {
      qarp: { score: 83.8, label: 'Quality at a Reasonable Price' },
      positive_revisions: { score: 76.2, label: 'Revisões positivas' },
      fallen_angels: { score: 69.5, label: 'Fallen Angels' },
    },
  });
  assert.strictEqual(partial.scanner_results.quality_at_fair_price.score, 83.8);
  assert.strictEqual(partial.scanner_results.growth_at_reasonable_price.score, 76.2);
  assert.strictEqual(partial.scanner_results.deep_value.score, 69.5);
  assert.strictEqual(partial.scanner_results.low_52w.score, 69.5,
    '52-week-low lens should fall back to the broader fallen-angels signal');

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
