from pathlib import Path

P = Path('market.js')
s = P.read_text(encoding='utf-8')

old = """      const r = await fetch('data/stocks.json', {cache:'no-store'});\n      if(!r.ok) throw new Error(`stocks.json ${r.status}`);\n      M.data = await r.json();\n"""
new = """      let r = await fetch('data/stocks-index.json', {cache:'no-store'});\n      if(!r.ok) r = await fetch('data/stocks.json', {cache:'no-store'});\n      if(!r.ok) throw new Error(`market data ${r.status}`);\n      M.data = await r.json();\n"""

assert s.count(old) == 1, f'native market load marker changed: {s.count(old)} matches'
s = s.replace(old, new)

ensure_start = s.index('  async function ensureLoaded(){')
ensure_end = s.index('\n  function ', ensure_start + 10)
ensure = s[ensure_start:ensure_end]
assert "fetch('data/stocks-index.json'" in ensure
assert "fetch('data/stocks.json'" in ensure
assert ensure.index("stocks-index.json") < ensure.index("stocks.json")
assert "M.stocks = Array.isArray(M.data.stocks) ? M.data.stocks : [];" in ensure

P.write_text(s, encoding='utf-8')
print('market.js now loads the lightweight index natively with legacy fallback.')
