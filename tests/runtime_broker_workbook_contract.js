const assert = require('assert');
const fs = require('fs');
const vm = require('vm');

const context = vm.createContext({
  console,
  window: {},
});
context.window.window = context.window;

for (const file of [
  'app-utils.js',
  'app-asset-identity.js',
  'app-file-parsing.js',
  'app-broker-parsing-core.js',
]) {
  vm.runInContext(fs.readFileSync(file, 'utf8'), context, { filename: file });
}

context.window.XLSX = {
  utils: {
    sheet_to_json(ws) { return ws.rows; },
  },
};
context.XLSX = context.window.XLSX;

vm.runInContext(fs.readFileSync('app-broker-workbook.js', 'utf8'), context, {
  filename: 'app-broker-workbook.js',
});

const workbook = context.window.VestraBrokerWorkbook;
assert.ok(workbook, 'broker workbook API missing');

assert.strictEqual(workbook.categoriseBankTransaction('Vencimento Setembro', 'in'), 'Salário');
assert.strictEqual(workbook.categoriseBankTransaction('Pingo Doce Lisboa', 'out'), 'Supermercado');
assert.strictEqual(workbook.categoriseBankTransaction('FARMÁCIA CENTRAL', 'out'), 'Saúde');
assert.strictEqual(workbook.categoriseBankTransaction('MB WAY PARA JOÃO', 'out'), 'MB Way enviado');
assert.strictEqual(workbook.categoriseBankTransaction('movimento desconhecido', 'in'), 'Outros recebimentos');
assert.strictEqual(workbook.categoriseBankTransaction('movimento desconhecido', 'out'), 'Outras despesas');

const closed = workbook.xtbWorkbookSheetToRows({ rows: [
  ['Account number', 'redacted'],
  ['Closed Positions'],
  ['Date from (UTC)', '2023-01-01'],
  ['Date to (UTC)', '2026-09-20'],
  ['Instrument', 'Ticker', 'Category', 'Type', 'Volume', 'Open Price', 'Open Time (UTC)', 'Close Price', 'Close Time (UTC)', 'Purchase Value', 'Sale Value'],
  ['Example plc', 'EXM.UK', 'STOCK', 'BUY', '2', '10', '2025-01-02', '12', '2025-02-03', '20', '24'],
] });
assert.strictEqual(closed.length, 1);
assert.strictEqual(closed[0].Instrument, 'Example plc');

const cash = workbook.xtbWorkbookSheetToRows({ rows: [
  ['Account number', 'redacted'],
  ['Cash Operations'],
  ['Date from (UTC)', '2023-01-01'],
  ['Date to (UTC)', '2026-09-20'],
  ['Type', 'Instrument', 'Ticker', 'Category', 'Time', 'Amount', 'ID', 'Comment'],
  ['Dividend', 'Example plc', 'EXM.UK', 'STOCK', '2026-09-01', '1.25', '1', 'EXM.UK dividend'],
] });
assert.strictEqual(cash.length, 1);
assert.strictEqual(cash[0].Type, 'Dividend');

const open = workbook.xtbWorkbookSheetToRows({ rows: [
  ['Account number', 'redacted'],
  ['Open Positions'],
  ['Data as of report generated', '2026-08-23 13:31:17'],
  ['Product', 'Metric', 'Amount', 'Currency'],
  ['My Trades', 'Value', '24', 'EUR'],
  [],
  ['Note', 'Summary values and open positions'],
  ['Product', 'Instrument/Position', 'Ticker', 'Category', 'Type', 'Volume', 'Value', 'Current price', 'Open price', 'Open time (UTC)', 'Net Profit'],
  ['My Trades', 'Example plc', 'EXM.UK', 'STOCK', '', '2', '24', '', '10', '', '4'],
  ['My Trades', '1001', 'EXM.UK', '', 'BUY', '2', '24', '12', '10', '2025-01-02', '4'],
] });
assert.strictEqual(open.length, 2);
assert.strictEqual(open[1].Ticker, 'EXM.UK');

const blocks = workbook.workbookToBrokerBlocks({
  SheetNames: ['Closed Positions', 'Cash Operations', 'Open Positions'],
  Sheets: {
    'Closed Positions': { rows: [
      ['Account number', 'redacted'],
      ['Closed Positions'],
      ['Date from (UTC)', '2023-01-01'],
      ['Date to (UTC)', '2026-09-20'],
      ['Instrument', 'Ticker', 'Category', 'Type', 'Volume', 'Open Price', 'Open Time (UTC)', 'Close Price', 'Close Time (UTC)', 'Purchase Value', 'Sale Value'],
      ['Example plc', 'EXM.UK', 'STOCK', 'BUY', '2', '10', '2025-01-02', '12', '2025-02-03', '20', '24'],
    ] },
    'Cash Operations': { rows: [
      ['Account number', 'redacted'],
      ['Cash Operations'],
      ['Date from (UTC)', '2023-01-01'],
      ['Date to (UTC)', '2026-09-20'],
      ['Type', 'Instrument', 'Ticker', 'Category', 'Time', 'Amount', 'ID', 'Comment'],
      ['Dividend', 'Example plc', 'EXM.UK', 'STOCK', '2026-09-01', '1.25', '1', 'EXM.UK dividend'],
    ] },
    'Open Positions': { rows: [
      ['Account number', 'redacted'],
      ['Open Positions'],
      ['Data as of report generated', '2026-08-23 13:31:17'],
      ['Product', 'Metric', 'Amount', 'Currency'],
      ['My Trades', 'Value', '24', 'EUR'],
      [],
      ['Note', 'Summary values and open positions'],
      ['Product', 'Instrument/Position', 'Ticker', 'Category', 'Type', 'Volume', 'Value', 'Current price', 'Open price', 'Open time (UTC)', 'Net Profit'],
      ['My Trades', 'Example plc', 'EXM.UK', 'STOCK', '', '2', '24', '', '10', '', '4'],
      ['My Trades', '1001', 'EXM.UK', '', 'BUY', '2', '24', '12', '10', '2025-01-02', '4'],
    ] },
  },
});
assert.deepStrictEqual(Array.from(blocks, block => block.format), [
  'xtb_trades', 'xtb_cash', 'xtb_positions',
]);
assert.strictEqual(blocks[0].meta.asOfDate, '2026-09-20');
assert.strictEqual(blocks[1].meta.asOfDate, '2026-09-20');
assert.strictEqual(blocks[2].meta.asOfDate, '2026-08-23');

context.normalizeBrokerAction = context.window.VestraBrokerParsingCore.normalizeBrokerAction;
context.brokerApproxFxToEUR = () => 1;
vm.runInContext(fs.readFileSync('app-xtb-normalization.js', 'utf8'), context, {
  filename: 'app-xtb-normalization.js',
});
vm.runInContext(fs.readFileSync('app-broker-parsers.js', 'utf8'), context, {
  filename: 'app-broker-parsers.js',
});
const parsedPositions = context.window.VestraBrokerParsers.parseXTBPositionsRows(
  blocks[2].rows,
  { hash: 'fixture', name: 'fixture.xlsx', broker: 'XTB', asOfDate: blocks[2].meta.asOfDate },
);
assert.strictEqual(parsedPositions.length, 1);
assert.strictEqual(parsedPositions[0].ticker, 'EXM.L');
assert.strictEqual(parsedPositions[0].qty, 2, 'summary and lot quantities must not be added together');
assert.strictEqual(parsedPositions[0].marketValueEUR, 24, 'exact broker-reported EUR Value must win');
assert.strictEqual(parsedPositions[0].costBasisEUR, 20, 'exact Value minus Net Profit must determine cost basis');
assert.strictEqual(parsedPositions[0].snapshotDate, '2026-08-23');

assert.strictEqual(context.normalizeBrokerAction('Stock acquisition'), 'STOCK_DISTRIBUTION');
assert.strictEqual(context.normalizeBrokerAction('Result adjustment'), 'CASH_ADJUSTMENT');

const corporateActions = context.window.VestraBrokerParsers.parseBrokerLedgerRows([
  { Action: 'Stock acquisition', Time: '2026-07-21 13:56:29', ISIN: 'CA38141A6025', Ticker: 'GORO', Name: 'Example acquisition', 'No. of shares': '25.333', Total: '0.00', 'Currency (Total)': 'EUR' },
  { Action: 'Result adjustment', Time: '2026-07-21 14:14:18', Notes: 'Rights proceeds', Total: '0.42', 'Currency (Total)': 'EUR' },
], { hash: 'fixture', name: 'fixture.csv', broker: 'Trading 212' });
assert.strictEqual(corporateActions.length, 2);
assert.strictEqual(corporateActions[0].type, 'STOCK_DISTRIBUTION');
assert.strictEqual(corporateActions[0].qty, 25.333);
assert.strictEqual(corporateActions[1].type, 'CASH_ADJUSTMENT');
assert.strictEqual(corporateActions[1].totalEUR, 0.42);

console.log('runtime broker workbook contract: ok');
