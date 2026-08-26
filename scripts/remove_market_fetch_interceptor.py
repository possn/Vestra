from pathlib import Path

LOADER = Path('market-data-loader.js')
HOTFIX = Path('market-hotfix.js')

s = LOADER.read_text(encoding='utf-8')
h = HOTFIX.read_text(encoding='utf-8')

assert 'Market Data Loader v1.2' in s
assert 'window.fetch = async function vestraMarketFetch' in s
assert 'async function loadManifest()' in s
assert "data/stocks.json?full=1" in s

s = s.replace('Market Data Loader v1.2 — shared lightweight index + lazy dossier hydration.',
              'Market Data Loader v2.0 — lazy dossier hydration only; no global fetch interception.')
s = s.replace('  let indexPayloadPromise = null;\n', '')

start = s.index('  function requestUrl(input){')
end = s.index('  async function loadManifest(){', start)
s = s[:start] + s[end:]

s = s.replace("window.VestraMarketData={hydrateTicker,hydratePortfolio,loadManifest,version:'1.2'};",
              "window.VestraMarketData={hydrateTicker,hydratePortfolio,loadManifest,version:'2.0'};")

for token in ('window.fetch =', 'sharedIndexPayload', 'requestUrl(', 'indexPayloadPromise'):
    assert token not in s, token
for token in ('dossiers-manifest.json', 'data/dossiers/', 'hydrateTicker', 'hydratePortfolio', 'data/stocks.json?full=1'):
    assert token in s, token

assert "market-data-loader.js?v=1.2" in h
h = h.replace("market-data-loader.js?v=1.2", "market-data-loader.js?v=2.0")
h = h.replace('compatibility loader v4.93', 'compatibility loader v4.94')
assert "market-data-loader.js?v=2.0" in h

LOADER.write_text(s, encoding='utf-8')
HOTFIX.write_text(h, encoding='utf-8')
print('Removed global market fetch interception; lazy dossier hydration remains active.')
