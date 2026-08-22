from pathlib import Path

p=Path('index.html')
s=p.read_text(encoding='utf-8')
old='''<div aria-label="Áreas de mercado" class="market-mode-grid">\n<button class="market-mode is-active" data-market-mode="discover"><span class="market-mode__icon">◫</span><strong>Ideias</strong></button>\n<button class="market-mode" data-market-mode="funds"><span class="market-mode__icon">◎</span><strong>ETFs</strong></button>\n<button class="market-mode" data-market-mode="smart"><span class="market-mode__icon">↗</span><strong>Smart money</strong></button>\n<button class="market-mode" data-market-mode="watch"><span class="market-mode__icon">☆</span><strong>A acompanhar</strong></button>\n<button class="market-mode" data-market-mode="lows"><span class="market-mode__icon">↘</span><strong>Mínimos 52s</strong></button>\n</div>'''
new='''<div aria-label="Áreas de mercado" class="market-mode-grid">\n<button class="market-mode is-active" data-market-mode="discover"><span class="market-mode__icon">◫</span><strong>Ideias</strong></button>\n<button class="market-mode" data-market-mode="funds"><span class="market-mode__icon">◎</span><strong>ETFs</strong></button>\n<button class="market-mode" data-market-mode="smart"><span class="market-mode__icon">↗</span><strong>Smart money</strong></button>\n<button class="market-mode" data-market-mode="watch"><span class="market-mode__icon">☆</span><strong>A acompanhar</strong></button>\n<button class="market-mode" data-market-mode="lows"><span class="market-mode__icon">↘</span><strong>Mínimos 52s</strong></button>\n</div>\n<button class="market-portfolio-access" data-market-tool="portfolio" type="button" aria-label="Abrir inteligência das minhas posições">\n  <span class="market-portfolio-access__icon">▦</span>\n  <span><strong>As minhas posições</strong><small>Convicção · reforços · posições a rever · overlap · alternativas</small></span>\n  <span class="market-portfolio-access__arrow">›</span>\n</button>'''
if old not in s: raise SystemExit('market mode anchor not found')
p.write_text(s.replace(old,new,1),encoding='utf-8')

p=Path('market.css')
s=p.read_text(encoding='utf-8')
s += '''\n/* v4.7.1 — visible portfolio intelligence access */\n.market-portfolio-access{width:100%;display:grid;grid-template-columns:38px minmax(0,1fr) 22px;align-items:center;gap:10px;margin:10px 0 14px;padding:13px 14px;border:1px solid var(--line);border-radius:16px;background:var(--card);color:var(--ink);text-align:left;box-shadow:var(--shadow-sm);cursor:pointer}\n.market-portfolio-access__icon{width:34px;height:34px;border-radius:11px;display:grid;place-items:center;background:var(--soft);font-size:19px}\n.market-portfolio-access strong{display:block;font-size:14px;line-height:1.2}\n.market-portfolio-access small{display:block;margin-top:3px;color:var(--muted);font-size:11px;line-height:1.25}\n.market-portfolio-access__arrow{font-size:26px;color:var(--muted);text-align:right}\n.market-portfolio-access:active{transform:scale(.995)}\n'''
p.write_text(s,encoding='utf-8')

p=Path('sw.js')
s=p.read_text(encoding='utf-8').replace('/* Vestra — Service Worker v4.7 */','/* Vestra — Service Worker v4.7.1 */',1).replace('vestra-cache-v40','vestra-cache-v41',1)
p.write_text(s,encoding='utf-8')

p=Path('README.md')
s=p.read_text(encoding='utf-8')
s='''## Vestra v4.7.1 — Portfolio Intelligence Access\n\n- “As minhas posições” deixa de ficar escondido em Mais ferramentas e passa a ter acesso direto visível na área Mercado.\n- O acesso abre a mesma inteligência v4.7: convicção, candidatos a reforço, posições a rever, concentração/overlap e alternativas.\n- Mantém-se o layout global; apenas se torna visível uma funcionalidade já existente.\n- PWA cache: `vestra-cache-v41`.\n\n'''+s
p.write_text(s,encoding='utf-8')
