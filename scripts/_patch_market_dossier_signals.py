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
start='  function catalystPanel(s){\n'
end='\n  function investmentCase(s){\n'
if s.count(start)!=1 or s.count(end)!=1:
    raise SystemExit(f'market.js panel markers: start={s.count(start)} end={s.count(end)}')
a=s.index(start)
b=s.index(end,a)
old=s[a:b]
for required in ('CATALYSTS & RISKS','RECOVERY CONFIRMATION','PORQUE CAIU? · DIAGNÓSTICO'):
    if required not in old:
        raise SystemExit(f'market.js panel block missing {required!r}')
new='''  const dossierSignals = window.VestraMarketDossierSignals?.create({
    text: txt,
    number: n,
    escapeHtml: esc,
    formatShortDate: shortDate,
  }) || null;
  function catalystPanel(s){ return dossierSignals?.catalystPanel(s) || ''; }
  function recoveryPanel(s){ return dossierSignals?.recoveryPanel(s) || ''; }
  function drawdownPanel(s){ return dossierSignals?.drawdownPanel(s) || ''; }
'''
p.write_text(s[:a]+new+s[b:],encoding='utf-8')

replace_once(
    'index.html',
    '<script defer="" src="market-static-universe.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v2"></script>',
    '<script defer="" src="market-static-universe.js?v=1.0"></script>\n<script defer="" src="market-dossier-signals.js?v=1.0"></script>\n<script defer="" src="market.js?v=20260831v2"></script>',
)
replace_once(
    'sw.js',
    '  "./market-static-universe.js",\n',
    '  "./market-static-universe.js",\n  "./market-dossier-signals.js",\n',
)

print('dossier signals extraction applied')
