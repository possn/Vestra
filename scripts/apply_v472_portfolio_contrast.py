from pathlib import Path

p=Path('market.css')
s=p.read_text(encoding='utf-8')
block='''\n/* v4.7.2 — Portfolio Intelligence contrast on light cards */\n.market-detail-card .market-case-list li{color:var(--text2)!important}\n.market-detail-card .market-case-note{color:var(--muted)!important}\n.market-detail-card .market-case-list{color:var(--text2)}\n.market-detail-card>p{color:var(--text2)}\n'''
if 'v4.7.2 — Portfolio Intelligence contrast' not in s:
    s += block
p.write_text(s,encoding='utf-8')

sw=Path('sw.js')
x=sw.read_text(encoding='utf-8')
x=x.replace('/* Vestra — Service Worker v4.7.1 */','/* Vestra — Service Worker v4.7.2 */').replace('vestra-cache-v41','vestra-cache-v42')
sw.write_text(x,encoding='utf-8')

r=Path('README.md')
t=r.read_text(encoding='utf-8')
head='''## Vestra v4.7.2 — Portfolio Intelligence Contrast\n\n- Corrige texto secundário ilegível nos cards claros de Portfolio Intelligence.\n- O override é scoped a `.market-detail-card`, preservando o texto claro do Investment Case escuro.\n- PWA cache: `vestra-cache-v42`.\n\n'''
if not t.startswith('## Vestra v4.7.2'):
    r.write_text(head+t,encoding='utf-8')
