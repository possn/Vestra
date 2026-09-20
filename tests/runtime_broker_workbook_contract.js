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
  ['Data as of report generated', '2026-09-20'],
  ['Product', 'Metric', 'Amount', 'Currency'],
  ['My Trades', 'Value', '24', 'EUR'],
  [],
  ['Note', 'Summary values and open positions'],
  ['Product', 'Instrument/Position', 'Ticker', 'Category', 'Type', 'Volume', 'Value', 'Current price', 'Open price', 'Open time (UTC)'],
  ['My Trades', 'Example plc', 'EXM.UK', 'STOCK', '', '2', '24', '', '10', ''],
  ['My Trades', '1001', 'EXM.UK', '', 'BUY', '2', '24', '12', '10', '2025-01-02'],
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
      ['Data as of report generated', '2026-09-20'],
      ['Product', 'Metric', 'Amount', 'Currency'],
      ['My Trades', 'Value', '24', 'EUR'],
      [],
      ['Note', 'Summary values and open positions'],
      ['Product', 'Instrument/Position', 'Ticker', 'Category', 'Type', 'Volume', 'Value', 'Current price', 'Open price', 'Open time (UTC)'],
      ['My Trades', 'Example plc', 'EXM.UK', 'STOCK', '', '2', '24', '', '10', ''],
      ['My Trades', '1001', 'EXM.UK', '', 'BUY', '2', '24', '12', '10', '2025-01-02'],
    ] },
  },
});
assert.deepStrictEqual(Array.from(blocks, block => block.format), [
  'xtb_trades', 'xtb_cash', 'xtb_positions',
]);

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
  { hash: 'fixture', name: 'fixture.xlsx', broker: 'XTB', asOfDate: '2026-09-20' },
);
assert.strictEqual(parsedPositions.length, 1);
assert.strictEqual(parsedPositions[0].ticker, 'EXM.L');
assert.strictEqual(parsedPositions[0].qty, 2, 'summary and lot quantities must not be added together');

console.log('runtime broker workbook contract: ok');
