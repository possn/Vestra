from pathlib import Path
import re

APP = Path('app.js')
INDEX = Path('index.html')
MODULE = Path('app-broker-parsers.js')

src = APP.read_text()
html = INDEX.read_text()
original_len = len(src)

names = [
    'estimateEURFactorFromRow',
    'parseBrokerLedgerRows',
    'parseBrokerPositionRows',
    'parseXTBTradesRows',
    'parseXTBPositionsRows',
    'parseXTBCashRows',
    'parseBrokerImportFile',
    'parseTrading212HoldingsPdf',
]

pat = re.compile(r'(?m)^(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(')
all_matches = list(pat.finditer(src))
by_name = {m.group(1): m for m in all_matches}
missing = [n for n in names if n not in by_name]
if missing:
    raise SystemExit(f'missing parser functions: {missing}')

# Extract exactly one function declaration. We scan from its opening brace until
# brace depth returns to zero. Braces that appear inside regex quantifiers or
# template substitutions are balanced locally, and node --check remains the final guard.
def function_range(name):
    m = by_name[name]
    start = m.start()
    brace = src.find('{', m.end())
    if brace < 0:
        raise SystemExit(f'opening brace not found for {name}')
    depth = 0
    for i in range(brace, len(src)):
        ch = src[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return start, i + 1
    raise SystemExit(f'closing brace not found for {name}')

ranges = []
blocks = {}
for name in names:
    start, end = function_range(name)
    block = src[start:end].rstrip() + '\n\n'
    blocks[name] = block
    ranges.append((start, end, name))

for forbidden in ['function rebuildBrokerGeneratedData(', 'state.assets.push(', 'state.liabilities.push(']:
    if any(forbidden in b for b in blocks.values()):
        raise SystemExit(f'unsafe parser boundary captured: {forbidden}')

for start, end, name in sorted(ranges, reverse=True):
    src = src[:start] + src[end:]

module = """/* Vestra broker parsers v1.0 — file/row transformation only. */
(() => {
  'use strict';

  const { uid, isoToday, normalizeDate, normStr } = window.VestraUtils || {};
  const { normalizeRow, parseNumberSmart } = window.VestraFileParsing || {};
  const {
    normalizeISIN, brokerPositionClassFromTicker, brokerEventKey, brokerPositionKey,
    detectBrokerRowsFormat, detectBrokerTextFormat,
  } = window.VestraBrokerParsingCore || {};
  const { parseXTBNormalizeAction, xtbTickerToYahoo, xtbSymbolCurrency } = window.VestraXtbNormalization || {};

  if (![uid, isoToday, normalizeDate, normStr, normalizeRow, parseNumberSmart,
        normalizeISIN, brokerPositionClassFromTicker, brokerEventKey, brokerPositionKey,
        detectBrokerRowsFormat, detectBrokerTextFormat, parseXTBNormalizeAction,
        xtbTickerToYahoo, xtbSymbolCurrency].every(fn => typeof fn === 'function')) {
    throw new Error('Broker parser dependencies were not loaded before app-broker-parsers.js');
  }

""" + ''.join(blocks[n] for n in names) + """  window.VestraBrokerParsers = Object.freeze({
    estimateEURFactorFromRow,
    parseBrokerLedgerRows,
    parseBrokerPositionRows,
    parseXTBTradesRows,
    parseXTBPositionsRows,
    parseXTBCashRows,
    parseBrokerImportFile,
    parseTrading212HoldingsPdf,
  });
})();
"""

anchor = '/* ─── SAVE / LOAD ─────────────────────────────────────────── */'
if anchor not in src:
    raise SystemExit('app import anchor not found')
import_block = """/* ─── BROKER PARSERS — moved to app-broker-parsers.js ───── */
const {
  estimateEURFactorFromRow,
  parseBrokerLedgerRows,
  parseBrokerPositionRows,
  parseXTBTradesRows,
  parseXTBPositionsRows,
  parseXTBCashRows,
  parseBrokerImportFile,
  parseTrading212HoldingsPdf,
} = window.VestraBrokerParsers || {};
if (![estimateEURFactorFromRow, parseBrokerLedgerRows, parseBrokerPositionRows,
      parseXTBTradesRows, parseXTBPositionsRows, parseXTBCashRows,
      parseBrokerImportFile, parseTrading212HoldingsPdf].every(fn => typeof fn === 'function')) {
  throw new Error('VestraBrokerParsers não foi carregado antes de app.js');
}

"""
src = src.replace(anchor, import_block + anchor, 1)

script_tag = '<script defer="" src="app-broker-parsers.js?v=1.0"></script>\n'
if 'app-broker-parsers.js' not in html:
    m = re.search(r'(?m)^<script\s+defer=""[^>]*src="app\.js[^>]*></script>$', html)
    if not m:
        raise SystemExit('app.js script tag not found')
    html = html[:m.start()] + script_tag + html[m.start():]

for name in names:
    if re.search(rf'(?m)^(?:async\s+)?function\s+{re.escape(name)}\s*\(', src):
        raise SystemExit(f'{name} still implemented in app.js')
if 'function rebuildBrokerGeneratedData(' not in src:
    raise SystemExit('stateful broker rebuild unexpectedly removed')

APP.write_text(src)
INDEX.write_text(html)
MODULE.write_text(module)
print(f'app.js reduced by {original_len - len(src)} bytes')
print(f'broker parser module {len(module)} bytes')
