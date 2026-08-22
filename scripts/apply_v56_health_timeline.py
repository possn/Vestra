from pathlib import Path

p=Path('market.js')
s=p.read_text()

anchor="""  function portfolioTiltBonus(stock,tilt){
    if(tilt==='quality') return ((n(stock?.quality_pct)||50)-50)*.10 + ((n(stock?.cashflow_pct)||50)-50)*.05;
    if(tilt==='growth') return ((n(stock?.growth_pct)||50)-50)*.10 + ((n(stock?.estimate_momentum_score)||50)-50)*.05;
    if(tilt==='dividend'){
      const y=n(stock?.dividend_yield); const q=n(stock?.quality_pct)||50; const cf=n(stock?.cashflow_pct)||50;
      return (y!=null?Math.min(8,Math.max(0,y*100))*0.7:0)+(q-50)*.035+(cf-50)*.035;
    }
    return 0;
  }

"""
insert="""  const PORTFOLIO_HEALTH_KEY='vestra_portfolio_health_v1';
  function portfolioHealthDay(d=new Date()){
    const y=d.getFullYear(), m=String(d.getMonth()+1).padStart(2,'0'), day=String(d.getDate()).padStart(2,'0');
    return `${y}-${m}-${day}`;
  }
  function loadPortfolioHealth(){
    try{ const x=JSON.parse(localStorage.getItem(PORTFOLIO_HEALTH_KEY)||'[]'); return Array.isArray(x)?x:[]; }
    catch{return [];}
  }
  function savePortfolioHealthSnapshot(snapshot){
    try{
      const day=portfolioHealthDay();
      const rows=loadPortfolioHealth().filter(x=>x&&x.day!==day);
      rows.push({...snapshot,day,ts:Date.now()});
      rows.sort((a,b)=>String(a.day).localeCompare(String(b.day)));
      const trimmed=rows.slice(-120);
      localStorage.setItem(PORTFOLIO_HEALTH_KEY,JSON.stringify(trimmed));
      return trimmed;
    }catch{return loadPortfolioHealth();}
  }
  function healthDeltaLabel(value,prev,inverse=false,suffix=''){
    if(value==null||prev==null) return '—';
    const d=value-prev; if(Math.abs(d)<0.05) return '≈ estável';
    const good=inverse?d<0:d>0; return `${good?'↑':'↓'} ${d>0?'+':''}${d.toFixed(1)}${suffix}`;
  }
  function renderPortfolioHealthTimeline(history){
    if(!history?.length) return '';
    const latest=history[history.length-1], prev=history.length>1?history[history.length-2]:null;
    const rows=history.slice(-8);
    const trend=prev?`${healthDeltaLabel(latest.targetFit,prev.targetFit,false,'')} fit · ${healthDeltaLabel(latest.conviction,prev.conviction,false,'')} conv.`:'Primeiro snapshot criado';
    return `<div class="market-detail-card market-health-timeline"><div class="market-perspective-head"><div><small>PORTFOLIO HEALTH · HISTÓRICO</small><h4>A carteira está a melhorar?</h4></div><span class="market-data-age">${history.length} ${history.length===1?'dia':'dias'}</span></div><div class="market-health-kpis"><div><small>Target Fit</small><strong>${Math.round(latest.targetFit)}</strong><em>${prev?healthDeltaLabel(latest.targetFit,prev.targetFit):'baseline'}</em></div><div><small>Convicção</small><strong>${latest.conviction.toFixed(1)}</strong><em>${prev?healthDeltaLabel(latest.conviction,prev.conviction):'baseline'}</em></div><div><small>Maior posição</small><strong>${latest.topPosition.toFixed(1)}%</strong><em>${prev?healthDeltaLabel(latest.topPosition,prev.topPosition,true,' pp'):'baseline'}</em></div><div><small>Rever/Substituir</small><strong>${latest.riskPositions}</strong><em>${prev?healthDeltaLabel(latest.riskPositions,prev.riskPositions,true):'baseline'}</em></div></div><div class="market-health-trend">${esc(trend)}</div><div class="market-health-history">${rows.map(x=>`<div class="market-health-row"><span>${esc(x.day.slice(5))}</span><div><i style="width:${Math.max(3,Math.min(100,x.targetFit))}%"></i></div><strong>${Math.round(x.targetFit)}</strong><small>conv ${x.conviction.toFixed(0)} · pos ${x.topPosition.toFixed(0)}% · setor ${x.topSector.toFixed(0)}% · overlap ${x.overlapCount} · risco ${x.riskPositions}</small></div>`).join('')}</div>${history.length<2?'<p class="market-case-note">A partir do próximo dia a Vestra começa a mostrar a direção das métricas. O snapshot do mesmo dia é atualizado, não duplicado.</p>':''}</div>`;
  }

"""
if anchor not in s: raise SystemExit('helper anchor missing')
s=s.replace(anchor,anchor+insert,1)

anchor2="""    const targetFitHtml=`<div class=\"market-detail-card market-target-fit\"><div class=\"market-perspective-head\"><div><small>TARGET FIT</small><h4>Aderência aos objetivos</h4></div><span class=\"market-target-fit-score ${targetTone}\">${targetFit}/100</span></div><div class=\"market-action-context\"><span>${targetPositionBreaches.length} posições acima</span><span>${targetSectorBreaches.length} setores acima</span><span>${targetOverlapBreaches.length} overlap</span></div>${targetIssues.length?`<ul class=\"market-case-list\">${targetIssues.map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class=\"market-case-note\">A parte analisável da carteira está dentro dos objetivos definidos.</p>'}</div>`;
"""
insert2="""    const healthSnapshot={targetFit,conviction:portfolioConvictionNow,topPosition:topPosPct,topSector:sectorRows[0]?.pct||0,overlapCount:ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2).length,riskPositions:(actionCounts.review||0)+(actionCounts.replace||0)};
    const healthHistory=savePortfolioHealthSnapshot(healthSnapshot);
    const healthTimelineHtml=renderPortfolioHealthTimeline(healthHistory);
"""
if anchor2 not in s: raise SystemExit('fit anchor missing')
s=s.replace(anchor2,anchor2+insert2,1)

anchor3="""      ${targetFitHtml}
      ${targetHtml}
"""
repl3="""      ${targetFitHtml}
      ${healthTimelineHtml}
      ${targetHtml}
"""
if anchor3 not in s: raise SystemExit('render anchor missing')
s=s.replace(anchor3,repl3,1)

anchor4="""      savePortfolioTargets(targets);
      const status=card?.querySelector('[data-target-status]'); if(status) status.textContent='Guardado';
      return;
"""
repl4="""      savePortfolioTargets(targets);
      const status=card?.querySelector('[data-target-status]'); if(status) status.textContent='Guardado · a recalcular';
      setTimeout(()=>openTool('portfolio'),120);
      return;
"""
if anchor4 not in s: raise SystemExit('save anchor missing')
s=s.replace(anchor4,repl4,1)
p.write_text(s)

p=Path('market.css'); c=p.read_text(); c += """

/* v5.6 — Portfolio Health Timeline */
.market-health-kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:7px;margin:10px 0}.market-health-kpis>div{background:var(--item-bg);border:1px solid var(--line2);border-radius:13px;padding:9px;min-width:0}.market-health-kpis small,.market-health-kpis em{display:block;font-size:8px;line-height:1.3;color:var(--text2);font-style:normal}.market-health-kpis strong{display:block;font-size:15px;margin:2px 0;color:var(--text)}.market-health-trend{font-size:10px;font-weight:800;color:var(--text2);margin:5px 0 9px}.market-health-history{display:grid;gap:6px}.market-health-row{display:grid;grid-template-columns:34px minmax(60px,1fr) 28px minmax(0,1.6fr);gap:7px;align-items:center;font-size:9px;color:var(--text2)}.market-health-row>div{height:6px;background:var(--card2);border-radius:999px;overflow:hidden}.market-health-row i{display:block;height:100%;background:currentColor;border-radius:999px;opacity:.65}.market-health-row strong{font-size:10px;color:var(--text);text-align:right}.market-health-row small{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;font-size:8px;color:var(--text2)}@media(max-width:520px){.market-health-kpis{grid-template-columns:1fr 1fr}.market-health-row{grid-template-columns:30px minmax(50px,1fr) 25px}.market-health-row small{grid-column:1/-1;padding-left:37px;margin-top:-3px}}
"""; p.write_text(c)

p=Path('README.md'); r=p.read_text(); r="""## Vestra v5.6 — Portfolio Health Timeline

- Guarda localmente um snapshot diário da saúde da carteira; reabrir no mesmo dia atualiza o snapshot em vez de o duplicar.
- Histórico inclui Target Fit, convicção ponderada, maior posição, maior setor, overlap indireto e número de posições em Rever/Substituir.
- Mostra tendência vs snapshot anterior e os últimos 8 registos diretamente em As minhas posições.
- Ao guardar novos Portfolio Targets, Target Fit e snapshot são recalculados imediatamente.
- Histórico fica apenas no dispositivo e mantém até 120 snapshots.
- PWA cache: `vestra-cache-v51`.

"""+r; p.write_text(r)

p=Path('sw.js'); w=p.read_text().replace('Service Worker v5.5','Service Worker v5.6').replace('vestra-cache-v50','vestra-cache-v51'); p.write_text(w)
