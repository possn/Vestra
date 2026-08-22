from pathlib import Path

p=Path('market.js')
s=p.read_text()
anchor="  function portfolioIntelligence(rows,total){\n"
insert="""  const PORTFOLIO_TARGETS_KEY='vestra_portfolio_targets_v1';
  function defaultPortfolioTargets(){ return {maxPosition:10,maxSector:25,overlap:'reduce',tilt:'balanced'}; }
  function loadPortfolioTargets(){
    try{ const raw=JSON.parse(localStorage.getItem(PORTFOLIO_TARGETS_KEY)||'{}'); return {...defaultPortfolioTargets(),...raw}; }
    catch{return defaultPortfolioTargets();}
  }
  function savePortfolioTargets(t){ try{ localStorage.setItem(PORTFOLIO_TARGETS_KEY,JSON.stringify(t)); }catch{} return t; }
  function portfolioTiltBonus(stock,tilt){
    if(tilt==='quality') return ((n(stock?.quality_pct)||50)-50)*.10 + ((n(stock?.cashflow_pct)||50)-50)*.05;
    if(tilt==='growth') return ((n(stock?.growth_pct)||50)-50)*.10 + ((n(stock?.estimate_momentum_score)||50)-50)*.05;
    if(tilt==='dividend'){
      const y=n(stock?.dividend_yield); const q=n(stock?.quality_pct)||50; const cf=n(stock?.cashflow_pct)||50;
      return (y!=null?Math.min(8,Math.max(0,y*100))*0.7:0)+(q-50)*.035+(cf-50)*.035;
    }
    return 0;
  }

"""
if anchor not in s: raise SystemExit('anchor1 missing')
s=s.replace(anchor,insert+anchor,1)
old="    const planHtml=`<div class=\"market-detail-card market-rebalance-plan\" data-rebalance-plan-card><div class=\"market-perspective-head\"><div><small>MULTI-MOVE PLAN</small><h4>Plano de rebalanceamento</h4></div><span class=\"market-data-age\">até 3 movimentos</span></div><p class=\"market-case-note\">Gera um plano pequeno a partir das posições mais frágeis. Evita repetir o mesmo destino e mostra o impacto agregado estimado.</p><button type=\"button\" class=\"market-plan-run\" data-rebalance-plan>Gerar plano</button><div data-rebalance-plan-results><p class=\"market-case-note\">Nenhuma alteração é aplicada à carteira.</p></div></div>`;\n"
new="""    const targets=loadPortfolioTargets();
    const targetHtml=`<div class="market-detail-card market-target-engine" data-target-engine><div class="market-perspective-head"><div><small>PORTFOLIO TARGETS</small><h4>Objetivos da carteira</h4></div><span class="market-data-age">guardado localmente</span></div><p class="market-case-note">Estes objetivos passam a orientar o Rebalancer e o plano multi-movimento. Não alteram a carteira por si só.</p><div class="market-target-grid"><label><span>Máx. por posição</span><div><input data-target-position type="number" min="3" max="30" step="1" value="${targets.maxPosition}"><em>%</em></div></label><label><span>Máx. por setor</span><div><input data-target-sector type="number" min="10" max="60" step="1" value="${targets.maxSector}"><em>%</em></div></label><label><span>Overlap ETF</span><select data-target-overlap><option value="reduce" ${targets.overlap==='reduce'?'selected':''}>Reduzir</option><option value="neutral" ${targets.overlap==='neutral'?'selected':''}>Neutro</option></select></label><label><span>Prioridade</span><select data-target-tilt><option value="balanced" ${targets.tilt==='balanced'?'selected':''}>Equilibrado</option><option value="quality" ${targets.tilt==='quality'?'selected':''}>Quality</option><option value="growth" ${targets.tilt==='growth'?'selected':''}>Growth</option><option value="dividend" ${targets.tilt==='dividend'?'selected':''}>Dividendos</option></select></label></div><button type="button" class="market-plan-run" data-target-save>Guardar objetivos</button><span class="market-target-status" data-target-status></span></div>`;
    const planHtml=`<div class="market-detail-card market-rebalance-plan" data-rebalance-plan-card><div class="market-perspective-head"><div><small>MULTI-MOVE PLAN · TARGET AWARE</small><h4>Plano de rebalanceamento</h4></div><span class="market-data-age">até 3 movimentos</span></div><p class="market-case-note">Gera um plano a partir das posições mais frágeis e respeita os objetivos guardados acima.</p><button type="button" class="market-plan-run" data-rebalance-plan>Gerar plano</button><div data-rebalance-plan-results><p class="market-case-note">Nenhuma alteração é aplicada à carteira.</p></div></div>`;
"""
if old not in s: raise SystemExit('anchor2 missing')
s=s.replace(old,new,1)
oldret="      ${rebalancerHtml}\n      ${planHtml}`;\n"
newret="      ${targetHtml}\n      ${rebalancerHtml}\n      ${planHtml}`;\n"
if oldret not in s: raise SystemExit('anchor3 missing')
s=s.replace(oldret,newret,1)
oldpen="""      let penalty=0;
      if(positionPct>15) penalty+=(positionPct-15)*1.6;
      else if(positionPct>10) penalty+=(positionPct-10)*.7;
      if(sectorPct>35) penalty+=(sectorPct-35)*1.1;
      else if(sectorPct>28) penalty+=(sectorPct-28)*.45;
      if(indirect>2) penalty+=(indirect-2)*2.2;
      const diversityBonus=(destSector!==srcSector && (sectors.get(destSector)||0)/analysed*100<20)?3:0;
      const valuationBonus=txt(stock.valuation_signal)==='undervalued'?3:0;
      const fitScore=conv-penalty+diversityBonus+valuationBonus;
"""
newpen="""      const targets=loadPortfolioTargets();
      const maxPos=Math.max(3,Math.min(30,n(targets.maxPosition)||10));
      const maxSector=Math.max(10,Math.min(60,n(targets.maxSector)||25));
      let penalty=0;
      if(positionPct>maxPos) penalty+=(positionPct-maxPos)*1.7;
      else if(positionPct>maxPos*.85) penalty+=(positionPct-maxPos*.85)*.55;
      if(sectorPct>maxSector) penalty+=(sectorPct-maxSector)*1.2;
      else if(sectorPct>maxSector*.88) penalty+=(sectorPct-maxSector*.88)*.45;
      if(targets.overlap==='reduce'&&indirect>1.5) penalty+=(indirect-1.5)*2.4;
      const diversityBonus=(destSector!==srcSector && (sectors.get(destSector)||0)/analysed*100<Math.min(20,maxSector*.75))?3:0;
      const valuationBonus=txt(stock.valuation_signal)==='undervalued'?3:0;
      const tiltBonus=portfolioTiltBonus(stock,targets.tilt);
      const fitScore=conv-penalty+diversityBonus+valuationBonus+tiltBonus;
"""
if oldpen not in s: raise SystemExit('anchor4 missing')
s=s.replace(oldpen,newpen,1)
oldreturn="      return {stock,conv,convDelta,fitScore,positionPct,sectorPct,indirect,overlapDelta:indirect-srcIndirect,existing:!!existing};\n"
newreturn="      return {stock,conv,convDelta,fitScore,positionPct,sectorPct,indirect,overlapDelta:indirect-srcIndirect,existing:!!existing,targets};\n"
if oldreturn not in s: raise SystemExit('anchor5 missing')
s=s.replace(oldreturn,newreturn,1)
oldrender="    return `<div class=\"market-rebalance-list\">${sim.results.map((r,i)=>`<button type=\"button\" class=\"market-rebalance-row\" data-market-ticker=\"${esc(r.stock.ticker)}\"><span class=\"market-rebalance-rank\">${i+1}</span><span><strong>${esc(r.stock.ticker)} · ${esc(r.stock.name||'')}</strong><small>${r.existing?'Já em carteira':'Nova posição'} · conv. ${Math.round(r.conv)} · peso após ${r.positionPct.toFixed(1)}% · setor ${r.sectorPct.toFixed(0)}%</small><small>Δ convicção carteira ${r.convDelta>=0?'+':''}${r.convDelta.toFixed(2)} · overlap ${r.overlapDelta>=0?'+':''}${r.overlapDelta.toFixed(1)} pp</small></span><em>${r.fitScore.toFixed(0)}</em></button>`).join('')}</div>`;\n"
newrender="""    const t=loadPortfolioTargets();
    return `<div class="market-target-summary">Limites: posição ${t.maxPosition}% · setor ${t.maxSector}% · ${t.overlap==='reduce'?'reduzir overlap':'overlap neutro'} · ${esc(t.tilt)}</div><div class="market-rebalance-list">${sim.results.map((r,i)=>`<button type="button" class="market-rebalance-row" data-market-ticker="${esc(r.stock.ticker)}"><span class="market-rebalance-rank">${i+1}</span><span><strong>${esc(r.stock.ticker)} · ${esc(r.stock.name||'')}</strong><small>${r.existing?'Já em carteira':'Nova posição'} · conv. ${Math.round(r.conv)} · peso após ${r.positionPct.toFixed(1)}% · setor ${r.sectorPct.toFixed(0)}%</small><small>Δ convicção carteira ${r.convDelta>=0?'+':''}${r.convDelta.toFixed(2)} · overlap ${r.overlapDelta>=0?'+':''}${r.overlapDelta.toFixed(1)} pp</small></span><em>${r.fitScore.toFixed(0)}</em></button>`).join('')}</div>`;
"""
if oldrender not in s: raise SystemExit('anchor6 missing')
s=s.replace(oldrender,newrender,1)
clickanchor="    const plan=e.target.closest('[data-rebalance-plan]');\n"
clickinsert="""    const saveTargets=e.target.closest('[data-target-save]');
    if(saveTargets){
      const card=saveTargets.closest('[data-target-engine]');
      const targets={maxPosition:Math.max(3,Math.min(30,n(card?.querySelector('[data-target-position]')?.value)||10)),maxSector:Math.max(10,Math.min(60,n(card?.querySelector('[data-target-sector]')?.value)||25)),overlap:card?.querySelector('[data-target-overlap]')?.value||'reduce',tilt:card?.querySelector('[data-target-tilt]')?.value||'balanced'};
      savePortfolioTargets(targets);
      const status=card?.querySelector('[data-target-status]'); if(status) status.textContent='Guardado';
      return;
    }
"""
if clickanchor not in s: raise SystemExit('anchor7 missing')
s=s.replace(clickanchor,clickinsert+clickanchor,1)
p.write_text(s)

p=Path('market.css'); c=p.read_text()+"""

/* v5.4 — Portfolio Target Engine */
.market-target-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:10px 0}.market-target-grid label>span{display:block;font-size:9px;font-weight:850;color:var(--text2);margin:0 0 4px 2px}.market-target-grid label>div{display:flex;align-items:center;border:1px solid var(--line);background:var(--card2);border-radius:12px;overflow:hidden}.market-target-grid input,.market-target-grid select{width:100%;border:1px solid var(--line);background:var(--card2);color:var(--text);border-radius:12px;padding:9px;font:inherit;font-size:11px}.market-target-grid label>div input{border:0;border-radius:0;background:transparent}.market-target-grid label>div em{font-style:normal;padding-right:9px;font-size:10px;color:var(--text2);font-weight:800}.market-target-status{font-size:9px;color:var(--teal);font-weight:850;margin-left:8px}.market-target-summary{font-size:9px;color:var(--text2);font-weight:750;margin:8px 0;padding:7px 9px;border:1px solid var(--line2);border-radius:10px;background:var(--card2)}
"""; p.write_text(c)

p=Path('README.md'); r=p.read_text(); r="""## Vestra v5.4 — Portfolio Target Engine

- Objetivos persistentes e locais para orientar o rebalanceamento: máximo por posição, máximo por setor, política de overlap e prioridade de carteira.
- Perfis de prioridade: Equilibrado, Quality, Growth e Dividendos.
- Assisted Rebalancer e Multi-Move Plan passam a usar estes objetivos em vez de thresholds fixos.
- Destinos que excedem os limites recebem penalização progressiva; reduzir overlap pode ser imposto como objetivo explícito.
- Nenhuma alteração é executada automaticamente; os objetivos são guardados apenas no dispositivo.
- PWA cache: `vestra-cache-v49`.

"""+r; p.write_text(r)

p=Path('sw.js'); w=p.read_text().replace('Service Worker v5.3','Service Worker v5.4').replace('vestra-cache-v48','vestra-cache-v49'); p.write_text(w)
