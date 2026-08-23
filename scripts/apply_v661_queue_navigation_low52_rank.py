from pathlib import Path

root=Path(__file__).resolve().parents[1]
p=root/'market.js'
s=p.read_text()

# 1) Low52 Opportunity Rank: ranking-only overlay, not Score Vestra.
if 'function low52OpportunityRank(s,stats)' not in s:
    marker='  function renderLows(){\n'
    assert marker in s
    fn=r'''  function low52OpportunityRank(s,stats){
    const low=n(s.low52_score), recovery=n(s.recovery_score), quality=n(s.quality_pct), confidence=n(s.confidence_score);
    const rel=n(s.sector_relative_return_1y_pct), upside=n(s.fair_value_upside_pct);
    const risk=txt(s.risk_gate).toLowerCase(), lowStatus=txt(s.low52_status), rec=txt(s.recovery_status);
    let parts=[], weight=0;
    const add=(v,w)=>{ if(v!=null){ parts.push(Math.max(0,Math.min(100,v))*w); weight+=w; } };
    add(low,0.35); add(recovery,0.25); add(quality,0.15); add(confidence,0.05);
    if(upside!=null) add(Math.max(0,Math.min(100,50+upside)),0.10);
    if(rel!=null) add(Math.max(0,Math.min(100,50+rel)),0.10);
    let score=weight?parts.reduce((a,b)=>a+b,0)/weight:50;
    if(lowStatus==='opportunity') score+=7;
    if(lowStatus==='watch') score+=2;
    if(lowStatus==='value_trap_risk') score-=18;
    if(lowStatus==='structural_risk') score-=30;
    if(rec==='confirmed') score+=8;
    else if(rec==='recovering') score+=5;
    else if(rec==='stabilizing') score+=2;
    else if(rec==='bounce_only') score-=7;
    else if(rec==='failed') score-=16;
    if(risk==='high') score-=25; else if(risk==='severe') score-=40;
    const dist=stats?.above; if(dist!=null && dist<=2) score+=2;
    return Math.round(Math.max(0,Math.min(100,score)));
  }

'''
    s=s.replace(marker,fn+marker,1)

old="""    let rows=M.stocks.filter(s=>!isFund(s)).map(s=>({s,stats:low52Stats(s)}))
      .filter(x=>x.stats && x.stats.above>=-0.5 && x.stats.above<=5)
      .sort((a,b)=>{const rank={opportunity:0,watch:1,uncertain:2,value_trap_risk:3,structural_risk:4,insufficient:5}; return (rank[txt(a.s.low52_status)]??9)-(rank[txt(b.s.low52_status)]??9)||(n(b.s.low52_score)||0)-(n(a.s.low52_score)||0)||a.stats.above-b.stats.above;});"""
new="""    let rows=M.stocks.filter(s=>!isFund(s)).map(s=>({s,stats:low52Stats(s)}))
      .filter(x=>x.stats && x.stats.above>=-0.5 && x.stats.above<=5)
      .map(x=>({...x,opportunityRank:low52OpportunityRank(x.s,x.stats)}))
      .sort((a,b)=>b.opportunityRank-a.opportunityRank||a.stats.above-b.stats.above);"""
assert old in s
s=s.replace(old,new,1)

old="""    const body=rows.length?rows.map(({s,stats})=>{
      const currency=txt(s.currency)||'USD';"""
new="""    const body=rows.length?rows.map(({s,stats,opportunityRank})=>{
      const currency=txt(s.currency)||'USD';"""
assert old in s
s=s.replace(old,new,1)

old="""      const meta=[`${dist.toFixed(1)}% acima do mínimo`,label,lowScore!=null?`Low52 ${Math.round(lowScore)}/100`:'',cause,trendText,recoveryLabel,recoveryScore!=null?`Recovery ${Math.round(recoveryScore)}/100`:'' ].filter(Boolean).join(' · ');"""
assert old in s
new="""      const meta=[`Opportunity ${opportunityRank}/100`,`${dist.toFixed(1)}% acima do mínimo`,label,lowScore!=null?`Low52 ${Math.round(lowScore)}/100`:'',cause,trendText,recoveryLabel,recoveryScore!=null?`Recovery ${Math.round(recoveryScore)}/100`:'' ].filter(Boolean).join(' · ');"""
s=s.replace(old,new,1)
s=s.replace('<h3>Mínimos de 52 semanas</h3><p>Até 5% do mínimo, agora classificados por oportunidade potencial, queda saudável, value trap ou deterioração estrutural.</p>', '<h3>Mínimos de 52 semanas</h3><p>Até 5% do mínimo, ordenados pelo Opportunity Rank: qualidade + valuation + causa da queda + setor + confirmação de recuperação.</p>',1)

# 2) Mark tool origin so closing portfolio intelligence returns to the real Portfolio view.
old="""      const sh=$m('marketSheet'), c=$m('marketSheetContent'); if(!sh||!c)return;
      sh.hidden=false; sh.setAttribute('aria-hidden','false'); document.body.classList.add('modal-open'); sh.dataset.ticker='';"""
new="""      const sh=$m('marketSheet'), c=$m('marketSheetContent'); if(!sh||!c)return;
      sh.hidden=false; sh.setAttribute('aria-hidden','false'); document.body.classList.add('modal-open'); sh.dataset.ticker='';
      sh.dataset.tool=tool||''; sh.dataset.returnView=tool==='portfolio'?'assets':'';"""
assert old in s
s=s.replace(old,new,1)

old="""  function closeSheet(){
    const sh=$m('marketSheet'); if(!sh)return;
    sh.hidden=true; sh.setAttribute('aria-hidden','true'); sh.dataset.liveReady='0';
    document.documentElement.classList.remove('modal-open'); document.body.classList.remove('modal-open');
    const panel=sheetPanel(); if(panel){panel.scrollTop=0;panel.scrollLeft=0;}
  }"""
new="""  function closeSheet(){
    const sh=$m('marketSheet'); if(!sh)return;
    const returnView=txt(sh.dataset.returnView);
    sh.hidden=true; sh.setAttribute('aria-hidden','true'); sh.dataset.liveReady='0'; sh.dataset.tool=''; sh.dataset.returnView='';
    document.documentElement.classList.remove('modal-open'); document.body.classList.remove('modal-open');
    const panel=sheetPanel(); if(panel){panel.scrollTop=0;panel.scrollLeft=0;}
    if(returnView==='assets' && typeof setView==='function') setView('assets');
  }"""
assert old in s
s=s.replace(old,new,1)

# 3) Queue actions must refresh the visible portfolio sheet, not Market behind it.
old="""    setResearchQueueState(row.dataset.queueTicker||'',btn.dataset.queueStatus||'new');
    renderPrimary();
    requestAnimationFrame(()=>document.querySelector('.market-research-queue')?.scrollIntoView?.({behavior:'smooth',block:'start'}));"""
new="""    setResearchQueueState(row.dataset.queueTicker||'',btn.dataset.queueStatus||'new');
    if(txt($m('marketSheet')?.dataset.tool)==='portfolio'){
      openTool('portfolio');
      setTimeout(()=>document.querySelector('.market-research-queue')?.scrollIntoView?.({behavior:'smooth',block:'start'}),0);
    } else renderPrimary();"""
assert old in s
s=s.replace(old,new,1)

p.write_text(s)

# README + cache
p=root/'README.md'; r=p.read_text()
if not r.startswith('## Vestra v6.6.1'):
    r='''## Vestra v6.6.1 — Research Queue Repair & Low52 Opportunity Rank\n\n- Research Queue agora atualiza a própria janela de Portfolio Intelligence imediatamente ao marcar Em revisão / Revisto / Adiar 7d.\n- Fechar “As minhas posições” regressa ao separador Carteira, em vez de deixar o utilizador no Mercado por trás do modal.\n- Novo Low52 Opportunity Rank 0–100 ordena os mínimos combinando Low52 intelligence, Recovery Confirmation, qualidade, confiança, valuation e comportamento relativo ao setor.\n- O Opportunity Rank é apenas ranking de research e não altera o Score Vestra.\n- PWA cache: `vestra-cache-v64`.\n\n'''+r
p.write_text(r)

p=root/'sw.js'; sw=p.read_text().replace('vestra-cache-v63','vestra-cache-v64'); p.write_text(sw)
p=root/'app.js'; a=p.read_text().replace('sw.js?v=20260509v63','sw.js?v=20260509v64').replace('sw.js?v=20260509v62','sw.js?v=20260509v64'); p.write_text(a)
