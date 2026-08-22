from pathlib import Path

p=Path('market.js')
s=p.read_text()

old="""<div class=\"market-action-summary\"><span class=\"is-positive\">Reforçar ${actionCounts.reinforce||0}</span><span>Manter ${actionCounts.hold||0}</span><span class=\"is-warn\">Rever ${actionCounts.review||0}</span><span class=\"is-risk\">Substituir ${actionCounts.replace||0}</span></div>"""
new="""<div class=\"market-action-summary\"><button type=\"button\" class=\"is-positive\" data-action-filter=\"reinforce\">Reforçar ${actionCounts.reinforce||0}</button><button type=\"button\" data-action-filter=\"hold\">Manter ${actionCounts.hold||0}</button><button type=\"button\" class=\"is-warn\" data-action-filter=\"review\">Rever ${actionCounts.review||0}</button><button type=\"button\" class=\"is-risk\" data-action-filter=\"replace\">Substituir ${actionCounts.replace||0}</button></div><div class=\"market-action-filter-status\" data-action-filter-status>Mostrar todas as posições</div>"""
if old not in s:
    raise SystemExit('action summary anchor missing')
s=s.replace(old,new,1)

old='class=\"market-action-row\" data-market-ticker=\"${esc(r.stock.ticker)}\"'
new='class=\"market-action-row\" data-action-key=\"${esc(r.action.key)}\" data-market-ticker=\"${esc(r.stock.ticker)}\"'
count=s.count(old)
if count < 2:
    raise SystemExit(f'action row anchors missing: {count}')
s=s.replace(old,new)

insert="""

  // v6.0.1 — Action Map summary acts as an immediate filter.
  document.addEventListener('click', e=>{
    const btn=e.target.closest?.('[data-action-filter]');
    if(!btn) return;
    const map=btn.closest('.market-action-map');
    if(!map) return;
    e.preventDefault();
    const requested=btn.dataset.actionFilter||'';
    const active=map.dataset.actionFilter||'';
    const next=active===requested?'':requested;
    map.dataset.actionFilter=next;
    map.querySelectorAll('[data-action-filter]').forEach(x=>x.classList.toggle('is-active',next && x.dataset.actionFilter===next));
    let shown=0;
    map.querySelectorAll('.market-action-row[data-action-key]').forEach(row=>{
      const visible=!next || row.dataset.actionKey===next;
      row.hidden=!visible;
      if(visible) shown++;
    });
    map.querySelectorAll('.market-detail-disclosure').forEach(d=>{
      const any=[...d.querySelectorAll('.market-action-row[data-action-key]')].some(r=>!r.hidden);
      d.hidden=!!next && !any;
      d.open=!!next && any;
    });
    const status=map.querySelector('[data-action-filter-status]');
    if(status){
      const labels={reinforce:'a reforçar',hold:'a manter',review:'a rever',replace:'a substituir'};
      status.textContent=next?`${shown} ${shown===1?'posição':'posições'} ${labels[next]||''}`:'Mostrar todas as posições';
    }
    map.querySelector('.market-action-list')?.scrollIntoView?.({behavior:'smooth',block:'nearest'});
  });
"""
end='\n})();\n'
if end not in s:
    raise SystemExit('market.js end anchor missing')
s=s.replace(end,insert+end,1)
p.write_text(s)

p=Path('market.css')
s=p.read_text()
s += """

/* v6.0.1 — Action Map interactive filters */
.market-action-summary button{appearance:none;border:1px solid var(--line);background:var(--card2);color:var(--text2);border-radius:13px;padding:10px 8px;font:inherit;font-size:11px;font-weight:850;cursor:pointer;min-width:0}.market-action-summary button.is-positive{color:#34764a}.market-action-summary button.is-warn{color:#8a6b2f}.market-action-summary button.is-risk{color:#9b4b44}.market-action-summary button.is-active{outline:2px solid rgba(32,129,126,.22);border-color:rgba(32,129,126,.5);background:rgba(32,129,126,.1);color:var(--text)}.market-action-filter-status{font-size:10px;color:var(--muted);font-weight:750;margin:7px 2px 0}.market-action-row[hidden]{display:none!important}
"""
p.write_text(s)

p=Path('README.md')
s=p.read_text()
s="""## Vestra v6.0.1 — Action Map Filters\n\n- Reforçar / Manter / Rever / Substituir passam a ser filtros interativos no Action Map.\n- Tocar num estado mostra imediatamente apenas as posições dessa categoria; tocar novamente repõe a lista completa.\n- O filtro selecionado fica visualmente ativo e mostra quantas posições estão visíveis.\n- Os detalhes expandem automaticamente quando o filtro tem resultados fora das primeiras 12 posições.\n- PWA cache: `vestra-cache-v57`.\n\n"""+s
p.write_text(s)

p=Path('sw.js')
s=p.read_text().replace('vestra-cache-v56','vestra-cache-v57')
p.write_text(s)
