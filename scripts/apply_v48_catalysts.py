from pathlib import Path

# Pipeline integration
p=Path('scripts/run.py')
s=p.read_text(encoding='utf-8')
if 'from catalysts import assess as assess_catalysts' not in s:
    s=s.replace('from earnings_intelligence import assess as assess_earnings_intelligence\n','from earnings_intelligence import assess as assess_earnings_intelligence\nfrom catalysts import assess as assess_catalysts\n')
anchor='''        row.update(evolve_thesis(\n            row, prev_snapshot, prev_date,\n            d7_snapshot, d7_date, d30_snapshot, d30_date,\n        ))\n        row.update(assess_scanner(row))\n'''
replacement='''        row.update(evolve_thesis(\n            row, prev_snapshot, prev_date,\n            d7_snapshot, d7_date, d30_snapshot, d30_date,\n        ))\n        row.update(assess_catalysts(row))\n        row.update(assess_scanner(row))\n'''
if anchor not in s:
    raise SystemExit('run.py catalyst anchor not found')
s=s.replace(anchor,replacement,1)
s=s.replace('"schema_version": 516','"schema_version": 517')
p.write_text(s,encoding='utf-8')

# Dossier UI
p=Path('market.js')
s=p.read_text(encoding='utf-8')
if 'function catalystPanel(s)' not in s:
    marker='\n\n\n\n  function investmentCase(s){'
    block=r'''

  function catalystPanel(s){
    const events=Array.isArray(s.catalyst_events)?s.catalyst_events.slice(0,5):[];
    if(!events.length) return '';
    const icon=e=>e.tone==='risk'?'!':e.tone==='positive'?'↗':e.tone==='event'?'◷':'•';
    const tone=e=>e.tone==='risk'?'down':e.tone==='positive'?'up':e.tone==='event'?'event':'neutral';
    const when=e=>e.date?shortDate(e.date):(e.window?e.window:'Sem data');
    const next=s.catalyst_next_date?`Próximo · ${shortDate(s.catalyst_next_date)}`:`${events.length} sinais`;
    return `<div class="market-detail-card"><div class="market-perspective-head"><div><small>CATALYSTS & RISKS</small><h4>${esc(s.catalyst_summary||'Eventos a acompanhar')}</h4></div><span class="market-data-age">${esc(next)}</span></div><div class="market-change-list">${events.map(e=>`<div class="market-change-item market-change-item--${tone(e)}"><b>${icon(e)}</b><span><strong>${esc(e.label||'Evento')}</strong><small style="display:block;margin-top:2px">${esc(when(e))}${e.evidence?` · ${esc(e.evidence)}`:''}${e.source?` · ${esc(e.source)}`:''}</small></span></div>`).join('')}</div></div>`;
  }
'''
    if marker not in s:
        raise SystemExit('market.js investmentCase marker not found')
    s=s.replace(marker,block+marker,1)
old="if(tab==='overview') body.innerHTML=`${changePanel(s)}${investmentCase(s)}<details"
new="if(tab==='overview') body.innerHTML=`${changePanel(s)}${catalystPanel(s)}${investmentCase(s)}<details"
if old not in s:
    raise SystemExit('market.js overview anchor not found')
s=s.replace(old,new,1)
p.write_text(s,encoding='utf-8')

# README
p=Path('README.md')
s=p.read_text(encoding='utf-8')
head='''## Vestra v4.8 — Catalyst & Risk Engine\n\n- Novo timeline auditável no dossier: “o que pode mexer esta ação e quando”.\n- Usa apenas eventos com evidência já recolhida: earnings, estimate momentum, insiders, trajetória da tese, estrutura de capital e STOCK Act.\n- Datas só são mostradas quando existem na fonte; sinais sem data aparecem como janelas (“30d”, “filings recentes”), nunca como datas inventadas.\n- Eventos de estrutura de capital herdam severidade do Risk Gate e podem dominar o painel quando são materiais.\n- Dataset schema: 517. PWA cache: `vestra-cache-v43`.\n\n'''
if not s.startswith('## Vestra v4.8'):
    p.write_text(head+s,encoding='utf-8')

# Service worker
p=Path('sw.js')
s=p.read_text(encoding='utf-8')
s=s.replace('/* Vestra — Service Worker v4.7.2 */','/* Vestra — Service Worker v4.8 */').replace('vestra-cache-v42','vestra-cache-v43')
p.write_text(s,encoding='utf-8')
