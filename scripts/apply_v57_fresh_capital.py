from pathlib import Path

p=Path('market.js'); s=p.read_text()

anchor="""    const planHtml=`<div class=\"market-detail-card market-rebalance-plan\" data-rebalance-plan-card>"""
insert="""    const freshCapitalHtml=`<div class=\"market-detail-card market-fresh-capital\" data-fresh-capital-card><div class=\"market-perspective-head\"><div><small>FRESH CAPITAL PLANNER</small><h4>Entrou capital novo. Onde reforçar?</h4></div><span class=\"market-data-age\">sem vendas</span></div><p class=\"market-case-note\">Distribui novo capital por até 3 destinos elegíveis, respeitando os Portfolio Targets e sem vender posições existentes.</p><div class=\"market-fresh-controls\"><label><span>Novo capital</span><div><input data-fresh-amount type=\"number\" min=\"50\" step=\"50\" value=\"1000\"><em>€</em></div></label><button type=\"button\" data-fresh-run>Distribuir</button></div><div data-fresh-results><p class=\"market-case-note\">A simulação privilegia convicção, margem de segurança, espaço dentro dos limites e a prioridade da carteira.</p></div></div>`;
"""
if anchor not in s: raise SystemExit('plan anchor missing')
s=s.replace(anchor,insert+anchor,1)

anchor2="""      ${targetHtml}
      ${rebalancerHtml}
"""
repl2="""      ${targetHtml}
      ${freshCapitalHtml}
      ${rebalancerHtml}
"""
if anchor2 not in s: raise SystemExit('render anchor missing')
s=s.replace(anchor2,repl2,1)

func_anchor="""  function openTool(tool){
"""
funcs="""  function freshCapitalPlan(amount){
    const fresh=Math.max(0,n(amount)||0); if(fresh<50) return {error:'Indica pelo menos 50 € de novo capital.'};
    const assets=portfolioAssets().slice().filter(researchEligibleAsset);
    const rowMap=new Map();
    for(const a of assets){
      const t=assetTicker(a); if(!t) continue; const base=t.replace(/\\.[A-Z]+$/,'');
      const stock=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\\.[A-Z]+$/,'')===base); if(!stock) continue;
      const key=txt(stock.ticker).toUpperCase(); const prev=rowMap.get(key)||{stock,value:0}; prev.value+=portfolioValue(a); rowMap.set(key,prev);
    }
    const rows=[...rowMap.values()]; const analysed=rows.reduce((sum,r)=>sum+r.value,0)||1; const afterTotal=analysed+fresh;
    const sectors=new Map(); for(const r of rows){ const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value); }
    const held=new Map(rows.map(r=>[txt(r.stock.ticker).toUpperCase().replace(/\\.[A-Z]+$/,''),r]));
    const etfs=rows.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/analysed*100}));
    const targets=loadPortfolioTargets(), maxPos=Math.max(3,Math.min(30,n(targets.maxPosition)||10)), maxSector=Math.max(10,Math.min(60,n(targets.maxSector)||25));
    const universe=M.stocks.filter(x=>!isFund(x)&&n(x.score)!=null&&n(x.confidence_score)>=60&&!['high','severe'].includes(txt(x.risk_gate))&&txt(x.valuation_signal)!=='overvalued'&&txt(x.estimate_signal)!=='deteriorating');
    const candidates=universe.map(stock=>{
      const conv=portfolioConviction(stock); if(conv==null) return null;
      const base=txt(stock.ticker).toUpperCase().replace(/\\.[A-Z]+$/,''); const existing=held.get(base); const existingValue=existing?.value||0;
      const sector=txt(stock.sector)||'Sem setor', sectorValue=sectors.get(sector)||0, indirect=isFund(stock)?0:indirectExposurePct(stock,etfs);
      const posCapacity=Math.max(0,afterTotal*maxPos/100-existingValue), sectorCapacity=Math.max(0,afterTotal*maxSector/100-sectorValue), capacity=Math.min(posCapacity,sectorCapacity,fresh);
      if(capacity<50) return null;
      let score=conv+portfolioTiltBonus(stock,targets.tilt);
      if(txt(stock.valuation_signal)==='undervalued') score+=4; else if(txt(stock.valuation_signal)==='fair') score+=1;
      const sectorNow=sectorValue/analysed*100; if(sectorNow<maxSector*.55) score+=3; else if(sectorNow>maxSector*.85) score-=3;
      if(existing&&existingValue/analysed*100<maxPos*.65) score+=2;
      if(targets.overlap==='reduce'&&indirect>1.5) score-=(indirect-1.5)*2.5;
      return {stock,conv,score,capacity,existingValue,sector,sectorValue,indirect};
    }).filter(Boolean).sort((a,b)=>b.score-a.score);
    const allocations=[], used=new Set(); let remaining=fresh; const shares=[.5,.3,.2];
    for(let i=0;i<shares.length&&remaining>=50;i++){
      const cand=candidates.find(c=>!used.has(txt(c.stock.ticker).toUpperCase())&&c.capacity>=50); if(!cand) break;
      let desired=i===shares.length-1?remaining:Math.max(50,Math.round((fresh*shares[i])/50)*50);
      let alloc=Math.min(remaining,cand.capacity,desired); alloc=Math.floor(alloc/50)*50; if(alloc<50){used.add(txt(cand.stock.ticker).toUpperCase()); i--; continue;}
      used.add(txt(cand.stock.ticker).toUpperCase()); remaining-=alloc;
      const positionPct=(cand.existingValue+alloc)/afterTotal*100, sectorPct=(cand.sectorValue+alloc)/afterTotal*100;
      allocations.push({...cand,amount:alloc,positionPct,sectorPct});
    }
    if(remaining>=50){
      for(const cand of candidates){
        if(remaining<50) break; if(used.has(txt(cand.stock.ticker).toUpperCase())) continue;
        let alloc=Math.min(remaining,cand.capacity); alloc=Math.floor(alloc/50)*50; if(alloc<50) continue;
        used.add(txt(cand.stock.ticker).toUpperCase()); remaining-=alloc;
        allocations.push({...cand,amount:alloc,positionPct:(cand.existingValue+alloc)/afterTotal*100,sectorPct:(cand.sectorValue+alloc)/afterTotal*100});
        if(allocations.length>=5) break;
      }
    }
    const currentConvRows=rows.map(r=>({...r,conv:portfolioConviction(r.stock)})).filter(r=>r.conv!=null&&r.value>0), convBase=currentConvRows.reduce((a,r)=>a+r.value,0)||1;
    const currentConv=currentConvRows.reduce((a,r)=>a+r.value*r.conv,0)/convBase;
    const added=allocations.reduce((a,x)=>a+x.amount,0), afterConv=(currentConv*convBase+allocations.reduce((a,x)=>a+x.amount*x.conv,0))/(convBase+added||1);
    return {fresh,allocated:added,remaining:fresh-added,currentConv,afterConv,allocations,targets};
  }

  function renderFreshCapitalPlan(plan){
    if(plan?.error) return `<p class=\"market-case-note\">${esc(plan.error)}</p>`;
    if(!plan?.allocations?.length) return '<p class=\"market-case-note\">Não encontrei destinos robustos dentro dos objetivos atuais.</p>';
    return `<div class=\"market-fresh-summary\"><strong>${euro(plan.allocated)} distribuídos</strong><span>Convicção ponderada ${plan.currentConv.toFixed(1)} → ${plan.afterConv.toFixed(1)}${plan.remaining>=50?` · ${euro(plan.remaining)} ficam por alocar`:''}</span></div><div class=\"market-fresh-list\">${plan.allocations.map((x,i)=>`<button type=\"button\" class=\"market-fresh-row\" data-market-ticker=\"${esc(x.stock.ticker)}\"><span class=\"market-rebalance-rank\">${i+1}</span><span><strong>${esc(x.stock.ticker)} · ${euro(x.amount)}</strong><small>${x.existingValue>0?'Reforço existente':'Nova posição'} · conv. ${Math.round(x.conv)} · ${esc(x.sector)}</small><small>Peso após ${x.positionPct.toFixed(1)}% · setor após ${x.sectorPct.toFixed(1)}% · fit ${x.score.toFixed(0)}</small></span></button>`).join('')}</div><p class=\"market-case-note\">Simulação de research. Não considera impostos, comissões, spreads nem necessidades pessoais de liquidez.</p>`;
  }

"""
if func_anchor not in s: raise SystemExit('openTool anchor missing')
s=s.replace(func_anchor,funcs+func_anchor,1)

event_anchor="""    const plan=e.target.closest('[data-rebalance-plan]');
"""
event="""    const freshRun=e.target.closest('[data-fresh-run]');
    if(freshRun){
      const card=freshRun.closest('[data-fresh-capital-card]'), out=card?.querySelector('[data-fresh-results]'), amount=card?.querySelector('[data-fresh-amount]')?.value;
      if(out) out.innerHTML=renderFreshCapitalPlan(freshCapitalPlan(amount));
      return;
    }
"""
if event_anchor not in s: raise SystemExit('event anchor missing')
s=s.replace(event_anchor,event+event_anchor,1)
p.write_text(s)

p=Path('market.css'); c=p.read_text(); c += """

/* v5.7 — Fresh Capital Planner */
.market-fresh-controls{display:grid;grid-template-columns:1fr auto;gap:8px;align-items:end;margin:10px 0}.market-fresh-controls label span{display:block;font-size:9px;font-weight:850;color:var(--text2);margin:0 0 4px 2px}.market-fresh-controls label>div{display:flex;align-items:center;border:1px solid var(--line);background:var(--card2);border-radius:12px;padding:0 9px}.market-fresh-controls input{width:100%;border:0;background:transparent;color:var(--text);padding:9px 0;font:inherit;font-size:11px;outline:0}.market-fresh-controls em{font-style:normal;font-size:10px;color:var(--text2)}.market-fresh-controls button{border:0;background:var(--text);color:var(--card);border-radius:12px;padding:10px 13px;font-size:11px;font-weight:850}.market-fresh-summary{display:flex;justify-content:space-between;gap:8px;align-items:center;padding:9px 10px;background:var(--item-bg);border:1px solid var(--line2);border-radius:13px;margin:8px 0}.market-fresh-summary strong{font-size:11px}.market-fresh-summary span{font-size:9px;color:var(--text2);text-align:right}.market-fresh-list{display:grid;gap:7px}.market-fresh-row{width:100%;display:grid;grid-template-columns:24px minmax(0,1fr);gap:8px;align-items:center;text-align:left;border:1px solid var(--line2);background:var(--item-bg);border-radius:14px;padding:10px;color:var(--text)}.market-fresh-row strong{display:block;font-size:11px}.market-fresh-row small{display:block;font-size:9px;color:var(--text2);margin-top:2px}@media(max-width:520px){.market-fresh-summary{display:block}.market-fresh-summary span{display:block;text-align:left;margin-top:3px}}
"""; p.write_text(c)

p=Path('README.md'); r=p.read_text(); r="""## Vestra v5.7 — Fresh Capital Planner

- Novo simulador para alocar capital novo sem vender posições existentes.
- Distribui o montante por até 3 destinos principais, podendo usar destinos adicionais quando os limites impedem a alocação completa.
- Respeita máximo por posição, máximo por setor, política de overlap e prioridade Equilibrado/Quality/Growth/Dividendos.
- Exclui Risk Gate alto/severo, confiança <60, valuation excessivo e expectativas em deterioração.
- Mostra impacto estimado na convicção ponderada e peso/setor após cada reforço.
- PWA cache: `vestra-cache-v52`.

"""+r; p.write_text(r)

p=Path('sw.js'); w=p.read_text().replace('Service Worker v5.6','Service Worker v5.7').replace('vestra-cache-v51','vestra-cache-v52'); p.write_text(w)
