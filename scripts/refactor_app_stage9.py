from pathlib import Path

app = Path('app.js')
index = Path('index.html')
out = Path('app-broker-identity-data.js')

src = app.read_text(encoding='utf-8')
html = index.read_text(encoding='utf-8')

token = 'const BROKER_SECURITY_IDENTITY_BY_NAME = {'
if src.count(token) != 1:
    raise SystemExit('Broker identity map token not unique')

start = src.index(token)
end = src.find('};', start)
if end < 0:
    raise SystemExit('Broker identity map terminator not found')
end += 2
block = src[start:end]

for probe in ['"APPLE"', '"MICROSOFT"', '"REALTY INCOME"', '"C3 AI"']:
    if probe not in block:
        raise SystemExit(f'Missing broker identity probe {probe}')

module = '''/* Vestra broker security identity data v1.0. Security identities only; no account values. */\n(() => {\n  "use strict";\n''' + block + '''\n  window.VestraBrokerIdentityData = Object.freeze({ BROKER_SECURITY_IDENTITY_BY_NAME });\n})();\n'''
out.write_text(module, encoding='utf-8')

replacement = '''const { BROKER_SECURITY_IDENTITY_BY_NAME } = window.VestraBrokerIdentityData || {};\nif (!BROKER_SECURITY_IDENTITY_BY_NAME || typeof BROKER_SECURITY_IDENTITY_BY_NAME !== "object") {\n  throw new Error("VestraBrokerIdentityData não foi carregado antes de app.js");\n}\n'''
new_src = src[:start] + replacement + src[end:]
if len(new_src) >= len(src):
    raise SystemExit('Stage 9 did not reduce app.js')

anchor = '<script defer="" src="app-xtb-normalization.js?v=1.0"></script>\n'
tag = '<script defer="" src="app-broker-identity-data.js?v=1.0"></script>\n'
if tag not in html:
    if html.count(anchor) != 1:
        raise SystemExit('XTB normalization script anchor not unique')
    html = html.replace(anchor, anchor + tag, 1)

if html.index('app-broker-identity-data.js') > html.index('app.js'):
    raise SystemExit('broker identity data must load before app.js')

app.write_text(new_src, encoding='utf-8')
index.write_text(html, encoding='utf-8')
print(f'app.js reduced by {len(src)-len(new_src)} bytes; broker identity module {len(module)} bytes')
