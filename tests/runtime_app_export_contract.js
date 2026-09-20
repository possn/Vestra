const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const context = vm.createContext({
  console,
  window: {},
  Blob,
  URL: { createObjectURL() { return 'blob:test'; }, revokeObjectURL() {} },
  document: {
    createElement() { return { style: {}, click() {}, parentNode: null }; },
    body: { appendChild(node) { node.parentNode = this; }, removeChild(node) { node.parentNode = null; } },
  },
  setTimeout(fn) { fn(); },
});
context.window.window = context.window;

vm.runInContext(fs.readFileSync('app-export-runtime.js', 'utf8'), context, {
  filename: 'app-export-runtime.js',
});

const exportsApi = context.window.VestraAppExports;
assert.ok(exportsApi, 'application export API missing');
assert.strictEqual(exportsApi.version, '1.0');
assert.strictEqual(
  exportsApi.csvFromRows([['Data', 'Valor'], ['2026-09-20', 12.5]]),
  '"Data";"Valor"\n"2026-09-20";"12.5"',
);

const backup = vm.runInContext(`window.VestraAppExports.serializeBackup({
  keep: 1,
  _scratch: 'drop',
  set: new Set(['A', 'B']),
  map: new Map([['x', 2]])
})`, context);
const parsed = JSON.parse(backup);
assert.strictEqual(parsed.keep, 1);
assert.strictEqual(parsed._scratch, undefined);
assert.deepStrictEqual(parsed.set, ['A', 'B']);
assert.deepStrictEqual(parsed.map, [['x', 2]]);

const report = exportsApi.buildAnnualReportText({
  totals: { assetsTotal: 100, liabsTotal: 10, net: 90, displayedPassiveAnnual: 12 },
  portfolioYield: { weightedYield: 2, totalReturnBlended: 5 },
  twr: { annualised: 4, years: 2 },
  diversification: { score: 75, label: 'Excelente', breakdown: [{ cls: 'Ações', pct: 100, val: 100 }] },
  pnl: {
    totalCost: 80, totalCurrent: 100, totalGain: 20, totalGainPct: 25,
    totalRealized: 3, totalDivAll: 2, grandTotalReturn: 25, grandTotalReturnPct: 31.25,
    positions: [{ asset: { name: 'Teste' }, pos: { gain: 20, gainPct: 25, realizedPnL: 3, divAll: 2, trueYieldPct: 2, totalReturn: 25 } }],
  },
  year: 2026,
  generatedDate: '20/09/2026',
  fmtEUR: value => `${value} EUR`,
  fmtPct: value => `${value}%`,
});
assert.ok(report.includes('RELATÓRIO PATRIMONIAL 2026'));
assert.ok(report.includes('Teste'));
assert.ok(report.includes('Score diversificação: 75/100 (Excelente)'));

console.log('runtime application export contract: ok');
