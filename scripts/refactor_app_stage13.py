from pathlib import Path
import re

APP = Path('app.js')
INDEX = Path('index.html')
PARSERS = Path('app-broker-parsers.js')
MODULE = Path('app-broker-workbook.js')

src = APP.read_text()
html = INDEX.read_text()
parsers = PARSERS.read_text()
original_len = len(src)

names = [
    'fileToText',
    'fileToObjectRows',
    'xtbWorkbookSheetToRows',
    'xtbExtractSheetMeta',
    'workbookToBrokerBlocks',
]

pat = re.compile(r'(?m)^(?:async\s+)?function\s+([A-Za-z0-9_$]+)\s*\(')
all_matches = list(pat.finditer(src))
by_name = {m.group(1): m for m in all_matches}
missing = [n for n in names if n not in by_name]
if missing:
    raise SystemExit(f'missing workbook functions: {missing}')


def function_end(text, start):
    brace = text.find('{', start)
    if brace < 0:
        raise SystemExit('opening brace not found')
    i = brace
    depth = 0
    quote = None
    escape = False
    line_comment = False
    block_comment = False
    regex = False
    regex_class = False
    prev_sig = ''
    while i < len(text):
        c = text[i]
        n = text[i+1] if i + 1 < len(text) else ''
        if line_comment:
            if c == '\n': line_comment = False
            i += 1; continue
        if block_comment:
            if c == '*' and n == '/': block_comment = False; i += 2; continue
            i += 1; continue
        if quote:
            if escape: escape = False
            elif c == '\\': escape = True
            elif c == quote: quote = None
            i += 1; continue
        if regex:
            if escape: escape = False
            elif c == '\\': escape = True
            elif c == '[': regex_class = True
            elif c == ']' and regex_class: regex_class = False
            elif c == '/' and not regex_class: regex = False
            i += 1; continue
        if c == '/' and n == '/': line_comment = True; i += 2; continue
        if c == '/' and n == '*': block_comment = True; i += 2; continue
        if c in ('\"', "'", '`'): quote = c; i += 1; continue
        if c == '/' and prev_sig in ('', '(', '[', '{', '=', ':', ',', '!', '?', ';'):
            regex = True; regex_class = False; i += 1; continue
        if c == '{': depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0: return i + 1
        if not c.isspace(): prev_sig = c
        i += 1
    raise SystemExit('function closing brace not found')

blocks = {}
ranges = []
for name in names:
    m = by_name[name]
    start = m.start()
    end = function_end(src, start)
    blocks[name] = src[start:end].rstrip() + '\n\n'
    ranges.append((start, end, name))

for forbidden in ['state.assets', 'state.liabilities', 'state.transactions', 'saveState(', 'rebuildBrokerGeneratedData(']:
    if any(forbidden in b for b in blocks.values()):
        raise SystemExit(f'unsafe workbook boundary captured: {forbidden}')

for start, end, name in sorted(ranges, reverse=True):
    src = src[:start] + src[end:]

module = """/* Vestra broker workbook/file readers v1.0 — file IO + workbook structure only. */
(() => {
  'use strict';

  const { csvToObjects, normalizeRow } = window.VestraFileParsing || {};
  const { detectBrokerRowsFormat } = window.VestraBrokerParsingCore || {};
  if (![csvToObjects, normalizeRow, detectBrokerRowsFormat].every(fn => typeof fn === 'function')) {
    throw new Error('Broker workbook dependencies were not loaded before app-broker-workbook.js');
  }

""" + ''.join(blocks[n] for n in names) + """  window.VestraBrokerWorkbook = Object.freeze({
    fileToText,
    fileToObjectRows,
    xtbWorkbookSheetToRows,
    xtbExtractSheetMeta,
    workbookToBrokerBlocks,
  });
})();
"""

# app.js still uses fileToText in generic/bank imports, so import it explicitly.
anchor = '/* ─── BROKER PARSERS — moved to app-broker-parsers.js ───── */'
if anchor not in src:
    raise SystemExit('broker parser import anchor missing')
import_block = """/* ─── BROKER WORKBOOK READERS — moved to app-broker-workbook.js ─ */
const { fileToText } = window.VestraBrokerWorkbook || {};
if (typeof fileToText !== 'function') {
  throw new Error('VestraBrokerWorkbook não foi carregado antes de app.js');
}

"""
src = src.replace(anchor, import_block + anchor, 1)

# Parser module now consumes the workbook helpers explicitly rather than via globals.
parser_anchor = "  const { parseXTBNormalizeAction, xtbTickerToYahoo, xtbSymbolCurrency } = window.VestraXtbNormalization || {};\n"
if parser_anchor not in parsers:
    raise SystemExit('parser dependency anchor missing')
parser_insert = parser_anchor + "  const { fileToObjectRows, workbookToBrokerBlocks } = window.VestraBrokerWorkbook || {};\n"
parsers = parsers.replace(parser_anchor, parser_insert, 1)
old_check = "        xtbTickerToYahoo, xtbSymbolCurrency].every(fn => typeof fn === 'function')) {"
new_check = "        xtbTickerToYahoo, xtbSymbolCurrency, fileToObjectRows, workbookToBrokerBlocks].every(fn => typeof fn === 'function')) {"
if old_check not in parsers:
    raise SystemExit('parser dependency check anchor missing')
parsers = parsers.replace(old_check, new_check, 1)

script_tag = '<script defer="" src="app-broker-workbook.js?v=1.0"></script>\n'
if 'app-broker-workbook.js' not in html:
    m = re.search(r'(?m)^\s*<script\s+defer=""[^>]*src="app-broker-parsers\.js[^>]*></script>$', html)
    if not m:
        raise SystemExit('broker parser script tag not found')
    html = html[:m.start()] + script_tag + html[m.start():]

for name in names:
    if re.search(rf'(?m)^(?:async\s+)?function\s+{re.escape(name)}\s*\(', src):
        raise SystemExit(f'{name} still implemented in app.js')
if 'function rebuildBrokerGeneratedData(' not in src:
    raise SystemExit('stateful broker rebuild unexpectedly removed')
if 'fileToObjectRows' not in parsers or 'workbookToBrokerBlocks' not in parsers:
    raise SystemExit('broker parser module lost workbook dependencies')

APP.write_text(src)
INDEX.write_text(html)
PARSERS.write_text(parsers)
MODULE.write_text(module)
print(f'app.js reduced by {original_len - len(src)} bytes')
print(f'broker workbook module {len(module)} bytes')