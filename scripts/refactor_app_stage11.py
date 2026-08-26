from pathlib import Path

app_path=Path('app.js')
idx_path=Path('index.html')
module_path=Path('app-file-parsing.js')

app=app_path.read_text(encoding='utf-8')
idx=idx_path.read_text(encoding='utf-8')

start=app.find('function splitCSVLine(line, delim) {')
end=app.find('function importRows(rows) {', start)
if start < 0 or end < 0:
    raise RuntimeError('Stage11 file parsing markers not found')
block=app[start:end].rstrip()
required=[
    'function splitCSVLine(',
    'function csvToObjects(',
    'function normKey(',
    'function normalizeRow(',
    'function parseNumberSmart(',
    'function classifyRow('
]
for token in required:
    if token not in block:
        raise RuntimeError(f'Missing expected parser token: {token}')

module="""/* Vestra generic file parsing v1.0 — CSV/row normalization only. */
(() => {
  'use strict';

"""+block+"""

  window.VestraFileParsing = Object.freeze({
    splitCSVLine,
    csvToObjects,
    normKey,
    normalizeRow,
    parseNumberSmart,
    classifyRow,
  });
})();
"""
module_path.write_text(module,encoding='utf-8')

bridge="""/* ─── GENERIC FILE PARSING — moved to app-file-parsing.js ─── */
const {
  splitCSVLine,
  csvToObjects,
  normKey,
  normalizeRow,
  parseNumberSmart,
  classifyRow,
} = window.VestraFileParsing || {};
if ([splitCSVLine, csvToObjects, normKey, normalizeRow, parseNumberSmart, classifyRow].some(fn => typeof fn !== 'function')) {
  throw new Error('VestraFileParsing não foi carregado antes de app.js');
}

"""
app2=app[:start]+bridge+app[end:]
for token in required:
    if token in app2:
        raise RuntimeError(f'Generic parsing implementation remained in app.js: {token}')
if 'function importRows(rows) {' not in app2:
    raise RuntimeError('Stateful importRows was accidentally removed')

script='<script defer="" src="app-file-parsing.js?v=1.0"></script>'
if script not in idx:
    anchor='<script defer="" src="app-broker-parsing-core.js?v=1.0"></script>'
    if anchor not in idx:
        raise RuntimeError('Broker parsing core script anchor missing')
    idx=idx.replace(anchor,anchor+'\n  '+script,1)
if idx.index('app-file-parsing.js') > idx.index('app.js'):
    raise RuntimeError('app-file-parsing.js must load before app.js')

app_path.write_text(app2,encoding='utf-8')
idx_path.write_text(idx,encoding='utf-8')
print(f'app.js reduced by {len(app)-len(app2)} bytes; generic file parsing module {len(module)} bytes')
