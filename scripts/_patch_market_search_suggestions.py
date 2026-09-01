from pathlib import Path


def replace_once(path: str, old: str, new: str):
    p=Path(path)
    s=p.read_text(encoding='utf-8')
    count=s.count(old)
    if count != 1:
        raise SystemExit(f'{path}: expected exactly one marker, got {count}')
    p.write_text(s.replace(old,new,1),encoding='utf-8')

p=Path('market.js')
s=p.read_text(encoding='utf-8')
start='  function marketSearchMatches(query, limit=7){\n'
end='\n  function resolvePortfolioStock(asset){\n'
if s.count(start)!=1 or s.count(end)!=1:
    raise SystemExit(f'market.js search markers: start={s.count(start)} end={s.count(end)}')
a=s.index(start)
b=s.index(end,a)
old=s[a:b]
for required in ('Sem correspondências imediatas','market-suggestion__ticker','scoreMatch'):
    if required not in old:
        raise SystemExit(f'market.js search block missing {required!r}')
new='''  const marketSearchSuggestions = window.VestraMarketSearchSuggestions?.create({
    getStocks: () => M.stocks,
    getQuery: () => M.query,
    isLoaded: () => M.loaded,
    getBox: () => $m('marketSuggestions'),
    text: txt,
    number: n,
    escapeHtml: esc,
    isFund,
  }) || null;
  function marketSearchMatches(query, limit=7){ return marketSearchSuggestions?.matches(query,limit) || []; }
  function hideSearchSuggestions(){ return marketSearchSuggestions?.hide(); }
  function renderSearchSuggestions(){ return marketSearchSuggestions?.render(); }
'''
p.write_text(s[:a]+new+s[b:],encoding='utf-8')

replace_once(
    'index.html',
    '<script defer="" src="market-dossier-signals.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v2"></script>',
    '<script defer="" src="market-dossier-signals.js?v=1.0"></script>\n<script defer="" src="market-search-suggestions.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v2"></script>',
)
replace_once(
    'sw.js',
    '  "./market-dossier-signals.js",\n',
    '  "./market-dossier-signals.js",\n  "./market-search-suggestions.js",\n',
)
print('market search suggestions extraction applied')
