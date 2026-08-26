from pathlib import Path

app = Path('app.js')
index = Path('index.html')
out = Path('app-asset-identity.js')

src = app.read_text(encoding='utf-8')
html = index.read_text(encoding='utf-8')

start = '/* ─── ISIN → Yahoo Finance ticker map (built from real T212 data) ─────────'
end = 'let state = safeClone(DEFAULT_STATE);'

if src.count(start) != 1 or src.count(end) != 1:
    raise SystemExit('Asset identity markers not unique')

before, rest = src.split(start, 1)
block, after = rest.split(end, 1)
block = start + block

for token in ['const ISIN_YAHOO_MAP = {', 'const CRYPTO_YAHOO_MAP = {', 'function cryptoToYahoo(raw)']:
    if token not in block:
        raise SystemExit(f'Missing asset identity token: {token}')

module = "/* Vestra asset identity maps v1.0 — generated from the canonical app data. */\n(() => {\n  'use strict';\n" + block + "\n  window.VestraAssetIdentity = Object.freeze({ ISIN_YAHOO_MAP, CRYPTO_YAHOO_MAP, cryptoToYahoo });\n})();\n"
out.write_text(module, encoding='utf-8')

replacement = '''/* ─── ASSET IDENTITY — moved to app-asset-identity.js ────── */\nconst { ISIN_YAHOO_MAP, CRYPTO_YAHOO_MAP, cryptoToYahoo } = window.VestraAssetIdentity || {};\nif (!ISIN_YAHOO_MAP || !CRYPTO_YAHOO_MAP || typeof cryptoToYahoo !== "function") {\n  throw new Error("VestraAssetIdentity não foi carregado antes de app.js");\n}\n\n'''
new_src = before + replacement + end + after
if len(new_src) >= len(src):
    raise SystemExit('Stage 4 did not reduce app.js')

anchor = '<script defer="" src="app-storage.js?v=1.0"></script>\n'
tag = '<script defer="" src="app-asset-identity.js?v=1.0"></script>\n'
if tag not in html:
    if html.count(anchor) != 1:
        raise SystemExit('app-storage script anchor not unique')
    html = html.replace(anchor, anchor + tag, 1)

if html.index('app-asset-identity.js') > html.index('app.js'):
    raise SystemExit('asset identity module must load before app.js')

app.write_text(new_src, encoding='utf-8')
index.write_text(html, encoding='utf-8')
print(f'app.js reduced by {len(src)-len(new_src)} bytes; identity module {len(module)} bytes')
