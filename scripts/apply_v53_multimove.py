from pathlib import Path

p=Path('market.js'); s=p.read_text()
anchor="""    const concentratedCount=ranked.filter(r=>r.portfolioFit?.fit==='concentrated').length;
"""
insert="""    const planHtml=`<div class=\"market-detail-card market-rebalance-plan\" data-rebalance-plan-card><div class=\"market-perspective-head\"><div><small>MULTI-MOVE PLAN</small><h4>Plano de rebalanceamento</h4></div><span class=\"market-data-age\">até 3 movimentos</span></div><p class=\"market-case-note\">Gera um plano pequeno a partir das posições mais frágeis. Evita repetir o mesmo destino e mostra o impacto agregado estimado.</p><button type=\"button\" class=\"market-plan-run\" data-rebalance-plan>Gerar plano</button><div data-rebalance-plan-results><p class=\"market-case-note\">Nenhuma alteração é aplicada à carteira.</p></div></div>`;
"""
if anchor not in s: raise SystemExit('anchor1 missing')
s=s.replace(anchor,insert+anchor,1)

anchor2="""      ${rebalancerHtml}`;
  }

  function rebalanceSimulation(sourceTicker, amount){
"""
repl2="""      ${rebalancerHtml}
      ${planHtml}`;
  }

  function buildMultiMovePlan(){
    const assets=portfolioAssets().slice();
    const eligible=assets.filter(researchEligibleAsset);
    const rowMap=new Map();
    for(const a of eligible){
      const t=assetTicker(a); if(!t) continue; const base=t.replace(/\\.[A-Z]+$/,'');
      const stock=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\\.[A-Z]+$/,'')===base);
      if(!stock) continue;
      const key=txt(stock.ticker).toUpperCase(); const prev=rowMap.get(key)||{stock,value:0}; prev.value+=portfolioValue(a); rowMap.set(key,prev);
    }
    const rows=[...rowMap.values()].map(r=>({...r,conviction:portfolioConviction(r.stock)})).filter(r=>r.conviction!=null&&r.value>0);
    const sources=rows.filter(r=>['high','severe'].includes(txt(r.stock.risk_gate))||txt(r.stock.thesis_direction)==='down'||txt(r.stock.estimate_signal)==='deteriorating'||r.conviction<55).sort((a,b)=>a.conviction-b.conviction||b.value-a.value);
    const fallback=rows.slice().sort((a,b)=>a.conviction-b.conviction||b.value-a.value);
    const queue=(sources.length?sources:fallback).slice(0,5);
    const usedDest=new Set(), moves=[]; let totalConvDelta=0, totalOverlapDelta=0, totalMoved=0;
    for(const src of queue){
      if(moves.length>=3) break;
      const amount=Math.max(100,Math.min(1000,Math.round((src.value*.25)/50)*50||100));
      const sim=rebalanceSimulation(src.stock.ticker,amount); if(sim.error||!sim.results?.length) continue;
      const dest=sim.results.find(r=>!usedDest.has(txt(r.stock.ticker).toUpperCase())&&r.convDelta>0&&r.overlapDelta<3) || sim.results.find(r=>!usedDest.has(txt(r.stock.ticker).toUpperCase()));
      if(!dest) continue;
      usedDest.add(txt(dest.stock.ticker).toUpperCase());
      totalConvDelta+=dest.convDelta; totalOverlapDelta+=dest.overlapDelta; totalMoved+=sim.amount;
      moves.push({from:sim.source,to:dest.stock,amount:sim.amount,convDelta:dest.convDelta,overlapDelta:dest.overlapDelta,fitScore:dest.fitScore});
    }
    return {moves,totalConvDelta,totalOverlapDelta,totalMoved};
  }

  function renderMultiMovePlan(plan){
    if(!plan?.moves?.length) return '<p class=\"market-case-note\">Não encontrei um plano multi-movimento suficientemente robusto com os dados atuais.</p>';
    const impact=plan.totalConvDelta>0&&plan.totalOverlapDelta<=1?'Melhora':plan.totalConvDelta<0||plan.totalOverlapDelta>=4?'Piora':'Neutro';
    return `<div class=\"market-plan-summary\"><strong>${impact}</strong><span>${euro(plan.totalMoved)} realocados · Δ convicção ${plan.totalConvDelta>=0?'+':''}${plan.totalConvDelta.toFixed(2)} · Δ overlap ${plan.totalOverlapDelta>=0?'+':''}${plan.totalOverlapDelta.toFixed(1)} pp</span></div><div class=\"market-plan-list\">${plan.moves.map((m,i)=>`<div class=\"market-plan-row\"><span class=\"market-rebalance-rank\">${i+1}</span><div><strong>${esc(m.from.ticker)} → ${esc(m.to.ticker)} · ${euro(m.amount)}</strong><small>Δ convicção ${m.convDelta>=0?'+':''}${m.convDelta.toFixed(2)} · overlap ${m.overlapDelta>=0?'+':''}${m.overlapDelta.toFixed(1)} pp · fit ${m.fitScore.toFixed(0)}</small></div></div>`).join('')}</div><p class=\"market-case-note\">Plano indicativo: não considera impostos, spreads, comissões, liquidez nem preferências pessoais.</p>`;
  }

  function rebalanceSimulation(sourceTicker, amount){
"""
if anchor2 not in s: raise SystemExit('anchor2 missing')
s=s.replace(anchor2,repl2,1)

anchor3="""    const reb=e.target.closest('[data-rebalance-run]');
"""
insert3="""    const plan=e.target.closest('[data-rebalance-plan]');
    if(plan){
      const card=plan.closest('[data-rebalance-plan-card]'); const out=card?.querySelector('[data-rebalance-plan-results]');
      if(out) out.innerHTML=renderMultiMovePlan(buildMultiMovePlan());
      return;
    }
"""
if anchor3 not in s: raise SystemExit('anchor3 missing')
s=s.replace(anchor3,insert3+anchor3,1)
p.write_text(s)

p=Path('market.css'); c=p.read_text()+"""

/* v5.3 — Multi-Move Rebalance Plan */
.market-plan-run{border:0;background:var(--text);color:var(--card);border-radius:12px;padding:10px 13px;font-size:11px;font-weight:850;margin:9px 0}.market-plan-summary{display:flex;justify-content:space-between;gap:10px;align-items:center;border:1px solid var(--line);background:var(--card2);border-radius:13px;padding:10px;margin:6px 0 8px}.market-plan-summary strong{font-size:12px}.market-plan-summary span{font-size:9px;color:var(--text2);text-align:right}.market-plan-list{display:grid;gap:7px}.market-plan-row{display:grid;grid-template-columns:24px minmax(0,1fr);gap:8px;align-items:center;border:1px solid var(--line2);background:var(--item-bg);border-radius:13px;padding:9px}.market-plan-row strong{display:block;font-size:10px}.market-plan-row small{display:block;font-size:9px;color:var(--text2);margin-top:2px;line-height:1.35}@media(max-width:520px){.market-plan-summary{align-items:flex-start;flex-direction:column}.market-plan-summary span{text-align:left}}
"""; p.write_text(c)

p=Path('README.md'); r=p.read_text(); r="""## Vestra v5.3 — Multi-Move Rebalance Plan

- Novo plano de rebalanceamento com até 3 movimentos coerentes a partir das posições mais frágeis.
- Cada movimento usa o Assisted Rebalancer v5.2 e evita repetir o mesmo destino.
- O plano mostra capital total realocado e impacto agregado estimado na convicção ponderada e overlap indireto.
- Prefere movimentos com melhoria de convicção e rejeita cenários com agravamento excessivo de overlap quando há alternativa.
- Não altera a carteira nem considera impostos/spreads/comissões; continua a ser simulação de research.
- PWA cache: `vestra-cache-v48`.

"""+r; p.write_text(r)

p=Path('sw.js'); w=p.read_text().replace('Service Worker v5.2','Service Worker v5.3').replace('vestra-cache-v47','vestra-cache-v48'); p.write_text(w)
