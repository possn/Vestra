from pathlib import Path

P = Path('vestra-ai-brief-v459.js')
s = P.read_text(encoding='utf-8')
old = "function load(){if(loading)return loading;loading=fetch(`./data/stocks.json?v=${VERSION}`,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{stocks=Array.isArray(d)?d:(d?.stocks||[]);byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s]));return stocks}).catch(()=>[]);return loading}"
new = "function load(){if(loading)return loading;loading=fetch('./data/stocks-index.json',{cache:'no-store'}).then(async r=>{if(r.ok)return r.json();const legacy=await fetch('./data/stocks.json',{cache:'no-store'});if(!legacy.ok)throw 0;return legacy.json()}).then(d=>{stocks=Array.isArray(d)?d:(d?.stocks||[]);byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s]));return stocks}).catch(()=>[]);return loading}"
assert s.count(old) == 1, f'AI brief load marker changed: {s.count(old)}'
s = s.replace(old, new)
assert s.index('stocks-index.json') < s.index('stocks.json')
for token in ('function evidence(s)', 'function payload(s)', 'function install()', 'data-ai459-run'):
    assert token in s, token
P.write_text(s, encoding='utf-8')
print('AI brief now loads lightweight market index natively with legacy fallback.')
