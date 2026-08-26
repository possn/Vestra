from pathlib import Path

ENH = Path('market-enhancements.js')
SWAP = Path('vestra-ux-v456.js')

e = ENH.read_text(encoding='utf-8')
v = SWAP.read_text(encoding='utf-8')

old_load = "function load(){if(loading)return loading;loading=fetch(`./data/stocks.json?v=${VERSION}`,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{stocks=Array.isArray(d)?d:(d?.stocks||[]);byTicker=new Map(stocks.map(s=>[t(s.ticker).toUpperCase(),s]));return stocks}).catch(()=>[]);return loading}"
new_load = "function load(){if(loading)return loading;loading=fetch('./data/stocks-index.json',{cache:'no-store'}).then(async r=>{if(r.ok)return r.json();const legacy=await fetch('./data/stocks.json',{cache:'no-store'});if(!legacy.ok)throw 0;return legacy.json()}).then(d=>{stocks=Array.isArray(d)?d:(d?.stocks||[]);byTicker=new Map(stocks.map(s=>[t(s.ticker).toUpperCase(),s]));return stocks}).catch(()=>[]);return loading}"
assert e.count(old_load) == 1, 'market-enhancements load marker changed'
e = e.replace(old_load, new_load)

# The canonical market-opportunities.js now owns opportunity eligibility/ranking/rendering.
start = e.index('function priceStats(s)')
end = e.index('function brief(s)', start)
e = e[:start] + e[end:]
start = e.index('function sectorFilter(section)')
end = e.index('function repairDescription()', start)
e = e[:start] + e[end:]
e = e.replace('function apply(){repairOpportunities();repairDescription();repairMultiples();installCollapsibles()}',
              'function apply(){repairDescription();repairMultiples();installCollapsibles()}')
for token in ('repairOpportunities', 'function opportunity(', 'function timing(', 'function eligible(', 'rowHTML'):
    assert token not in e, token
for token in ('repairDescription()', 'repairMultiples()', 'installCollapsibles()', "stocks-index.json"):
    assert token in e, token

old_swap_load = """  function load(){\n    if(loading)return loading;\n    loading=fetch(`./data/stocks.json?v=${VERSION}`,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{\n      stocks=Array.isArray(d)?d:(Array.isArray(d?.stocks)?d.stocks:[]);\n      byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s]));\n      return stocks;\n    }).catch(()=>[]);\n    return loading;\n  }\n"""
new_swap_load = """  function load(){\n    if(loading)return loading;\n    loading=fetch('./data/stocks-index.json',{cache:'no-store'}).then(async r=>{\n      if(r.ok)return r.json();\n      const legacy=await fetch('./data/stocks.json',{cache:'no-store'});\n      if(!legacy.ok)throw 0;\n      return legacy.json();\n    }).then(d=>{\n      stocks=Array.isArray(d)?d:(Array.isArray(d?.stocks)?d.stocks:[]);\n      byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s]));\n      return stocks;\n    }).catch(()=>[]);\n    return loading;\n  }\n"""
assert v.count(old_swap_load) == 1, 'v456 load marker changed'
v = v.replace(old_swap_load, new_swap_load)
assert v.index('stocks-index.json') < v.index('stocks.json')

ENH.write_text(e, encoding='utf-8')
SWAP.write_text(v, encoding='utf-8')
print('Removed superseded v4.50 opportunity renderer and made enhancements/swap index-native.')
