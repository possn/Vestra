from pathlib import Path

app = Path('app.js')
index = Path('index.html')
out = Path('app-ui-core.js')

src = app.read_text(encoding='utf-8')
html = index.read_text(encoding='utf-8')

start = '/* ─── DOM HELPER ──────────────────────────────────────────── */'
end = '/* ─── SAVE / LOAD ─────────────────────────────────────────── */'

if src.count(start) != 1 or src.count(end) != 1:
    raise SystemExit('UI core markers not unique')

before, rest = src.split(start, 1)
block, after = rest.split(end, 1)
block = start + block

required = [
    'const NOOP_EL = {',
    'function $(id)',
    'function resolveChartHeight(',
    'function prepareChartCanvas(',
    'function buildNiceAxis(',
    'function ensureChartCtx(',
    'function ensureAllChartCanvasesReady(',
    'function renderChartUnavailable(',
    'function clearChartUnavailable(',
]
for token in required:
    if token not in block:
        raise SystemExit(f'Missing UI core token: {token}')

exports = [
    'NOOP_EL', '$', 'resolveChartHeight', 'prepareChartCanvas', 'buildNiceAxis',
    'ensureChartCtx', 'ensureAllChartCanvasesReady', 'renderChartUnavailable',
    'clearChartUnavailable'
]
module = (
    "/* Vestra UI core v1.0 — DOM and Chart infrastructure extracted from app.js. */\n"
    "(() => {\n  'use strict';\n"
    + block
    + "\n  window.VestraUiCore = Object.freeze({ " + ', '.join(exports) + " });\n})();\n"
)
out.write_text(module, encoding='utf-8')

replacement = '''/* ─── DOM + CHART UI CORE — moved to app-ui-core.js ───────── */\nconst {\n  NOOP_EL, $, resolveChartHeight, prepareChartCanvas, buildNiceAxis,\n  ensureChartCtx, ensureAllChartCanvasesReady, renderChartUnavailable,\n  clearChartUnavailable,\n} = window.VestraUiCore || {};\n\nif (![ $, resolveChartHeight, prepareChartCanvas, buildNiceAxis, ensureChartCtx,\n       ensureAllChartCanvasesReady, renderChartUnavailable, clearChartUnavailable\n     ].every(fn => typeof fn === "function")) {\n  throw new Error("VestraUiCore não foi carregado antes de app.js");\n}\n\n'''
new_src = before + replacement + end + after
if len(new_src) >= len(src):
    raise SystemExit('Stage 5 did not reduce app.js')

anchor = '<script defer="" src="app-asset-identity.js?v=1.0"></script>\n'
tag = '<script defer="" src="app-ui-core.js?v=1.0"></script>\n'
if tag not in html:
    if html.count(anchor) != 1:
        raise SystemExit('app-asset-identity script anchor not unique')
    html = html.replace(anchor, anchor + tag, 1)

if html.index('app-ui-core.js') > html.index('app.js'):
    raise SystemExit('UI core module must load before app.js')

app.write_text(new_src, encoding='utf-8')
index.write_text(html, encoding='utf-8')
print(f'app.js reduced by {len(src)-len(new_src)} bytes; UI core module {len(module)} bytes')
