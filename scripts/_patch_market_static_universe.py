from pathlib import Path

p=Path('market.js')
s=p.read_text(encoding='utf-8')
start='  async function ensureLoaded(){\n'
end='\n  function bestStocks(){\n'
if s.count(start)!=1 or s.count(end)!=1:
    raise SystemExit('ensureLoaded markers are not unique')
a=s.index(start)
b=s.index(end,a)
new='''  const staticUniverseState = {};
  Object.defineProperties(staticUniverseState, {
    loaded: { get: () => M.loaded, set: value => { M.loaded = Boolean(value); } },
    loading: { get: () => M.loading, set: value => { M.loading = value || null; } },
    data: { get: () => M.data, set: value => { M.data = value || null; } },
    stocks: { get: () => M.stocks, set: value => { M.stocks = Array.isArray(value) ? value : []; } },
    byTicker: { get: () => M.byTicker, set: value => { M.byTicker = value instanceof Map ? value : new Map(); } },
  });
  const staticUniverse = window.VestraMarketStaticUniverse?.create({
    state: staticUniverseState,
    text: txt,
    beforeReady: syncSnapshots,
    onReady: renderPrimary,
    onError: err => {
      const el=$m('marketPrimary'); if(el) el.innerHTML=`<div class="market-empty market-empty--error"><strong>Mercado indisponível</strong><br><span>Não foi possível carregar os dados agora.</span><br><button class="btn btn--outline btn--sm" data-market-retry style="margin-top:12px">Tentar novamente</button><small class="market-error-detail">${esc(err.message)}</small></div>`;
    },
  }) || null;
  async function ensureLoaded(){ return staticUniverse?.ensureLoaded(); }
'''
p.write_text(s[:a]+new+s[b:],encoding='utf-8')

def once(path, old, new):
    q=Path(path); t=q.read_text(encoding='utf-8')
    if t.count(old)!=1: raise SystemExit(f'{path}: marker count={t.count(old)}')
    q.write_text(t.replace(old,new,1),encoding='utf-8')

once('index.html', '<script defer="" src="market-watch-snapshots.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v2"></script>', '<script defer="" src="market-watch-snapshots.js?v=1.0"></script>\n<script defer="" src="market-static-universe.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v2"></script>')
once('sw.js', '  "./market-watch-snapshots.js",\n', '  "./market-watch-snapshots.js",\n  "./market-static-universe.js",\n')
print('static universe extraction applied')
