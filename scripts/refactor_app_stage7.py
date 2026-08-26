from pathlib import Path

app = Path('app.js')
index = Path('index.html')
out = Path('app-broker-normalization.js')

src = app.read_text(encoding='utf-8')
html = index.read_text(encoding='utf-8')

start = '// v63: dividend adjustments may legitimately be negative (clawbacks).'
end = '/* v63f: repair assets whose yahooTicker contradicts their ISIN.'

if src.count(start) != 1 or src.count(end) != 1:
    raise SystemExit('Broker normalization markers not unique')

before, rest = src.split(start, 1)
block, after = rest.split(end, 1)
block = start + block

required = [
    'function divFloor(',
    'function getDividendGross(',
    'function getDividendNet(',
    'function normalizeDividendRecord(',
]
for token in required:
    if token not in block:
        raise SystemExit(f'Missing broker normalization token: {token}')

module = '''/* Vestra broker/dividend record normalization v1.0. */\n(() => {\n  "use strict";\n  const { parseNum } = window.VestraUtils || {};\n  if (typeof parseNum !== "function") throw new Error("VestraUtils.parseNum unavailable");\n\n''' + block + '''\n  window.VestraBrokerNormalization = Object.freeze({\n    divFloor, getDividendGross, getDividendNet, normalizeDividendRecord\n  });\n})();\n'''
out.write_text(module, encoding='utf-8')

replacement = '''/* ─── BROKER/DIVIDEND NORMALIZATION — moved to app-broker-normalization.js ─── */\nconst { divFloor, getDividendGross, getDividendNet, normalizeDividendRecord } = window.VestraBrokerNormalization || {};\nif (![divFloor, getDividendGross, getDividendNet, normalizeDividendRecord].every(fn => typeof fn === "function")) {\n  throw new Error("VestraBrokerNormalization não foi carregado antes de app.js");\n}\n\n'''
new_src = before + replacement + end + after
if len(new_src) >= len(src):
    raise SystemExit('Stage 7 did not reduce app.js')

anchor = '<script defer="" src="app-ui-core.js?v=1.0"></script>\n'
tag = '<script defer="" src="app-broker-normalization.js?v=1.0"></script>\n'
if tag not in html:
    if html.count(anchor) != 1:
        raise SystemExit('app-ui-core script anchor not unique')
    html = html.replace(anchor, anchor + tag, 1)

if html.index('app-utils.js') > html.index('app-broker-normalization.js'):
    raise SystemExit('app-utils must load before broker normalization')
if html.index('app-broker-normalization.js') > html.index('app.js'):
    raise SystemExit('broker normalization must load before app.js')

app.write_text(new_src, encoding='utf-8')
index.write_text(html, encoding='utf-8')
print(f'app.js reduced by {len(src)-len(new_src)} bytes; broker normalization module {len(module)} bytes')
