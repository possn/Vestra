from pathlib import Path

p=Path('market.js')
s=p.read_text()

anchor="""    const concentratedCount=ranked.filter(r=>r.portfolioFit?.fit==='concentrated').length;
"""
insert="""    const rebalSourceRows=actionRows.filter(r=>r.value>0&&r.conviction!=null).slice().sort((a,b)=>(a.conviction??999)-(b.conviction??999));
    const defaultSource=rebalSourceRows[0]||null;
    const rebalancerHtml=defaultSource?`<div class=\"market-detail-card market-rebalancer\" data-rebalancer-card><div class=\"market-perspective-head\"><div><small>ASSISTED REBALANCER</small><h4>Onde melhora mais este capital?</h4></div><span class=\"market-data-age\">simulação</span></div><p class=\"market-case-note\">Escolhe a posição de origem e o montante. A Vestra mantém o valor total da carteira e compara destinos elegíveis por convicção, concentração, overlap e valuation.</p><div class=\"market-rebalancer-controls\"><label><span>Libertar de</span><select data-rebalance-source>${rebalSourceRows.map(r=>`<option value=\"${esc(r.stock.ticker)}\">${esc(r.stock.ticker)} · ${euro(r.value)} · conv. ${Math.round(r.conviction)}</option>`).join('')}</select></label><label><span>Montante</span><input data-rebalance-amount type=\"number\" min=\"50\" step=\"50\" value=\"${Math.max(50,Math.min(1000,Math.round(defaultSource.value/50)*50||50))}\"></label><button type=\"button\" data-rebalance-run>Simular</button></div><div class=\"market-rebalancer-results\" data-rebalance-results><p class=\"market-case-note\">Toca em Simular para comparar os melhores destinos.</p></div><p class=\"market-case-note\">Research assistido; não considera fiscalidade, custos de transação, liquidez pessoal ou ordens reais.</p></div>`:'';
"""
if anchor not in s: raise SystemExit('anchor1 missing')
s=s.replace(anchor,insert+anchor,1)

anchor2="""      ${scenarioHtml}`;
  }

  function openTool(tool){
"""
repl2="""      ${scenarioHtml}
      ${rebalancerHtml}`;
  }

  function rebalanceSimulation(sourceTicker, amount){
    const source=txt(sourceTicker).toUpperCase();
    const assets=portfolioAssets().slice();
    const eligible=assets.filter(researchEligibleAsset);
    const rowMap=new Map();
    for(const a of eligible){
      const t=assetTicker(a); if(!t) continue; const base=t.replace(/\\.[A-Z]+$/,'');
      const stock=M.byTicker.get(t)||M.stocks.find(x=>txt(x.ticker).toUpperCase().replace(/\\.[A-Z]+$/,'')===base);
      if(!stock) continue;
      const key=txt(stock.ticker).toUpperCase();
      const prev=rowMap.get(key)||{stock,value:0}; prev.value+=portfolioValue(a); rowMap.set(key,prev);
    }
    const rows=[...rowMap.values()];
    const analysed=rows.reduce((sum,r)=>sum+r.value,0)||1;
    const src=rows.find(r=>txt(r.stock.ticker).toUpperCase()===source); if(!src) return {error:'Posição de origem não encontrada.'};
    const move=Math.max(0,Math.min(n(amount)||0,src.value)); if(move<=0) return {error:'Indica um montante válido.'};
    const srcConv=portfolioConviction(src.stock); if(srcConv==null) return {error:'A posição de origem não tem convicção calculável.'};
    const sectors=new Map(); for(const r of rows){ const k=txt(r.stock.sector)||'Sem setor'; sectors.set(k,(sectors.get(k)||0)+r.value); }
    const etfs=rows.filter(r=>isFund(r.stock)&&Array.isArray(r.stock.top_holdings)&&r.stock.top_holdings.length).map(r=>({...r,portfolioPct:r.value/analysed*100}));
    const held=new Map(rows.map(r=>[txt(r.stock.ticker).toUpperCase().replace(/\\.[A-Z]+$/,''),r]));
    const srcSector=txt(src.stock.sector)||'Sem setor';
    const srcIndirect=isFund(src.stock)?0:indirectExposurePct(src.stock,etfs);
    const universe=M.stocks.filter(x=>!isFund(x)&&txt(x.ticker).toUpperCase()!==source&&n(x.score)!=null&&n(x.confidence_score)>=60&&!['high','severe'].includes(txt(x.risk_gate))&&txt(x.valuation_signal)!=='overvalued'&&txt(x.estimate_signal)!=='deteriorating');
    const ranked=universe.map(stock=>{
      const conv=portfolioConviction(stock); if(conv==null) return null;
      const base=txt(stock.ticker).toUpperCase().replace(/\\.[A-Z]+$/,'');
      const existing=held.get(base); const existingValue=existing?.value||0;
      const destSector=txt(stock.sector)||'Sem setor';
      let sectorValue=sectors.get(destSector)||0;
      if(destSector===srcSector) sectorValue-=move;
      sectorValue+=move;
      const sectorPct=sectorValue/analysed*100;
      const positionPct=(existingValue+move)/analysed*100;
      const indirect=isFund(stock)?0:indirectExposurePct(stock,etfs);
      const convDelta=(conv-srcConv)*(move/analysed);
      let penalty=0;
      if(positionPct>15) penalty+=(positionPct-15)*1.6;
      else if(positionPct>10) penalty+=(positionPct-10)*.7;
      if(sectorPct>35) penalty+=(sectorPct-35)*1.1;
      else if(sectorPct>28) penalty+=(sectorPct-28)*.45;
      if(indirect>2) penalty+=(indirect-2)*2.2;
      const diversityBonus=(destSector!==srcSector && (sectors.get(destSector)||0)/analysed*100<20)?3:0;
      const valuationBonus=txt(stock.valuation_signal)==='undervalued'?3:0;
      const fitScore=conv-penalty+diversityBonus+valuationBonus;
      return {stock,conv,convDelta,fitScore,positionPct,sectorPct,indirect,overlapDelta:indirect-srcIndirect,existing:!!existing};
    }).filter(Boolean).sort((a,b)=>b.fitScore-a.fitScore).slice(0,5);
    return {source:src.stock,amount:move,sourceConv:srcConv,results:ranked};
  }

  function renderRebalanceResults(sim){
    if(sim?.error) return `<p class=\"market-case-note\">${esc(sim.error)}</p>`;
    if(!sim?.results?.length) return '<p class=\"market-case-note\">Sem destinos elegíveis com os filtros atuais.</p>';
    return `<div class=\"market-rebalance-list\">${sim.results.map((r,i)=>`<button type=\"button\" class=\"market-rebalance-row\" data-market-ticker=\"${esc(r.stock.ticker)}\"><span class=\"market-rebalance-rank\">${i+1}</span><span><strong>${esc(r.stock.ticker)} · ${esc(r.stock.name||'')}</strong><small>${r.existing?'Já em carteira':'Nova posição'} · conv. ${Math.round(r.conv)} · peso após ${r.positionPct.toFixed(1)}% · setor ${r.sectorPct.toFixed(0)}%</small><small>Δ convicção carteira ${r.convDelta>=0?'+':''}${r.convDelta.toFixed(2)} · overlap ${r.overlapDelta>=0?'+':''}${r.overlapDelta.toFixed(1)} pp</small></span><em>${r.fitScore.toFixed(0)}</em></button>`).join('')}</div>`;
  }

  function openTool(tool){
"""
if anchor2 not in s: raise SystemExit('anchor2 missing')
s=s.replace(anchor2,repl2,1)

anchor3="""    const close=e.target.closest('[data-market-close]'); if(close){ closeSheet(); return; }
"""
insert3="""    const reb=e.target.closest('[data-rebalance-run]');
    if(reb){
      const card=reb.closest('[data-rebalancer-card]');
      const source=card?.querySelector('[data-rebalance-source]')?.value;
      const amount=card?.querySelector('[data-rebalance-amount]')?.value;
      const out=card?.querySelector('[data-rebalance-results]');
      if(out) out.innerHTML=renderRebalanceResults(rebalanceSimulation(source,amount));
      return;
    }
"""
if anchor3 not in s: raise SystemExit('anchor3 missing')
s=s.replace(anchor3,insert3+anchor3,1)
p.write_text(s)

p=Path('market.css'); c=p.read_text(); c += """

/* v5.2 — Assisted Rebalancer */
.market-rebalancer-controls{display:grid;grid-template-columns:1.4fr .8fr auto;gap:8px;align-items:end;margin:10px 0}.market-rebalancer-controls label span{display:block;font-size:9px;font-weight:850;color:var(--text2);margin:0 0 4px 2px}.market-rebalancer-controls select,.market-rebalancer-controls input{width:100%;border:1px solid var(--line);background:var(--card2);color:var(--text);border-radius:12px;padding:9px;font:inherit;font-size:11px}.market-rebalancer-controls button{border:0;background:var(--text);color:var(--card);border-radius:12px;padding:10px 12px;font-size:11px;font-weight:850}.market-rebalance-list{display:grid;gap:7px;margin-top:8px}.market-rebalance-row{width:100%;display:grid;grid-template-columns:24px minmax(0,1fr) 34px;gap:8px;align-items:center;text-align:left;border:1px solid var(--line2);background:var(--item-bg);border-radius:14px;padding:10px;color:var(--text)}.market-rebalance-row>span:nth-child(2){min-width:0}.market-rebalance-row strong{display:block;font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.market-rebalance-row small{display:block;font-size:9px;line-height:1.35;color:var(--text2);margin-top:2px}.market-rebalance-row em{font-style:normal;font-size:11px;font-weight:900;text-align:right;color:var(--vio)}.market-rebalance-rank{width:24px;height:24px;border-radius:8px;display:grid;place-items:center;background:var(--card2);font-size:10px;font-weight:900;color:var(--text2)}@media(max-width:520px){.market-rebalancer-controls{grid-template-columns:1fr 1fr}.market-rebalancer-controls label:first-child{grid-column:1/-1}.market-rebalancer-controls button{min-height:38px}}
"""
p.write_text(c)

p=Path('README.md'); r=p.read_text(); r="""## Vestra v5.2 — Assisted Rebalancer

- Novo simulador interativo em As minhas posições: escolhe a posição de origem e o montante a libertar.
- Mantém o valor total da carteira e ordena até 5 destinos elegíveis por convicção, concentração, overlap indireto e valuation.
- Destinos com Risk Gate alto/severo, confiança <60, valuation excessivo ou expectativas em deterioração são excluídos.
- Mostra peso e setor após a realocação, impacto estimado na convicção ponderada e alteração de overlap via ETFs.
- Não executa ordens nem inclui fiscalidade/custos; é uma ferramenta de research e cenário.
- PWA cache: `vestra-cache-v47`.

"""+r; p.write_text(r)

p=Path('sw.js'); w=p.read_text().replace('Service Worker v5.1','Service Worker v5.2').replace('vestra-cache-v46','vestra-cache-v47'); p.write_text(w)
