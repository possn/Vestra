from pathlib import Path

app = Path('app.js')
index = Path('index.html')
out = Path('app-xtb-normalization.js')

src = app.read_text(encoding='utf-8')
html = index.read_text(encoding='utf-8')

start = 'function parseXTBNormalizeAction(type, comment) {'
end = '/** XTB Trade History CSV (closed positions) */'

if src.count(start) != 1 or src.count(end) != 1:
    raise SystemExit('XTB normalization markers not unique')

before, rest = src.split(start, 1)
block, after = rest.split(end, 1)
block = start + block

required = [
    'function parseXTBNormalizeAction(',
    'function xtbTickerToYahoo(',
    'function xtbSymbolCurrency(',
]
for token in required:
    if token not in block:
        raise SystemExit(f'Missing XTB normalization token: {token}')

module = '''/* Vestra XTB normalization v1.0. */\n(() => {\n  "use strict";\n  const { normStr } = window.VestraUtils || {};\n  if (typeof normStr !== "function") throw new Error("VestraUtils.normStr unavailable");\n\n''' + block + '''\n  window.VestraXtbNormalization = Object.freeze({\n    parseXTBNormalizeAction, xtbTickerToYahoo, xtbSymbolCurrency\n  });\n})();\n'''
out.write_text(module, encoding='utf-8')

replacement = '''/* ─── XTB NORMALIZATION — moved to app-xtb-normalization.js ─── */\nconst { parseXTBNormalizeAction, xtbTickerToYahoo, xtbSymbolCurrency } = window.VestraXtbNormalization || {};\nif (![parseXTBNormalizeAction, xtbTickerToYahoo, xtbSymbolCurrency].every(fn => typeof fn === "function")) {\n  throw new Error("VestraXtbNormalization não foi carregado antes de app.js");\n}\n\n'''
new_src = before + replacement + end + after
if len(new_src) >= len(src):
    raise SystemExit('Stage 8 did not reduce app.js')

anchor = '<script defer="" src="app-broker-normalization.js?v=1.0"></script>\n'
tag = '<script defer="" src="app-xtb-normalization.js?v=1.0"></script>\n'
if tag not in html:
    if html.count(anchor) != 1:
        raise SystemExit('broker normalization script anchor not unique')
    html = html.replace(anchor, anchor + tag, 1)

if html.index('app-utils.js') > html.index('app-xtb-normalization.js'):
    raise SystemExit('app-utils must load before XTB normalization')
if html.index('app-xtb-normalization.js') > html.index('app.js'):
    raise SystemExit('XTB normalization must load before app.js')

app.write_text(new_src, encoding='utf-8')
index.write_text(html, encoding='utf-8')
print(f'app.js reduced by {len(src)-len(new_src)} bytes; XTB normalization module {len(module)} bytes')
