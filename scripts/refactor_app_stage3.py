from pathlib import Path

app = Path('app.js')
index = Path('index.html')

src = app.read_text(encoding='utf-8')
html = index.read_text(encoding='utf-8')

start = '/* ─── PERSISTENCE (IndexedDB + localStorage fallback) ─────── */'
end = '/* ─── STATE ───────────────────────────────────────────────── */'

if src.count(start) != 1 or src.count(end) != 1:
    raise SystemExit('Persistence markers not unique')

before, rest = src.split(start, 1)
block, after = rest.split(end, 1)

required = [
    'const STORAGE_KEY = "PF_STATE_V6";',
    'const DB_NAME = "pf_v6", DB_STORE = "kv", DB_KEY = "state";',
    'function idbOpen()',
    'async function storageGet()',
    'async function storageSet(raw)',
    'async function storageClear()',
]
for token in required:
    if token not in block:
        raise SystemExit(f'Missing expected persistence token: {token}')

replacement = '''/* ─── PERSISTENCE — moved to app-storage.js ──────────────── */\nconst {\n  requestPersistentStorage,\n  storageGet,\n  storageSet,\n  storageClear,\n} = window.VestraStorage || {};\n\nif (![requestPersistentStorage, storageGet, storageSet, storageClear].every(fn => typeof fn === "function")) {\n  throw new Error("VestraStorage não foi carregado antes de app.js");\n}\n\n'''

new_src = before + replacement + end + after
if len(new_src) >= len(src):
    raise SystemExit('Stage 3 did not reduce app.js')

anchor = '<script defer="" src="app-feedback.js?v=1.0"></script>\n'
storage_tag = '<script defer="" src="app-storage.js?v=1.0"></script>\n'
if storage_tag not in html:
    if html.count(anchor) != 1:
        raise SystemExit('app-feedback script anchor not unique')
    html = html.replace(anchor, anchor + storage_tag, 1)

if html.index('app-storage.js') > html.index('app.js'):
    raise SystemExit('app-storage.js must load before app.js')

app.write_text(new_src, encoding='utf-8')
index.write_text(html, encoding='utf-8')
print(f'app.js reduced by {len(src)-len(new_src)} bytes')
