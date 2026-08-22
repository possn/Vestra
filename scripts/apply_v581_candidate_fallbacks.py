from pathlib import Path

p=Path('market.js')
s=p.read_text()

def rep(old,new,label,count=1):
    global s
    if old not in s:
        raise SystemExit(f'{label} anchor missing')
    s=s.replace(old,new,count)

rep("Não encontrei um plano multi-movimento suficientemente robusto com os dados atuais.",
    "Não encontrei um plano automático robusto. Experimenta o Rebalancer manual: a Vestra agora mostra candidatos aceitáveis com alertas em vez de esconder tudo.",
    'multimove message')

rep("const universe=M.stocks.filter(x=>!isFund(x)&&txt(x.ticker).toUpperCase()!==source&&n(x.score)!=null&&n(x.confidence_score)>=60&&!['high','severe'].includes(txt(x.risk_gate))&&txt(x.valuation_signal)!=='overvalued'&&txt(x.estimate_signal)!=='deteriorating');",
    "const universe=M.stocks.filter(x=>!isFund(x)&&txt(x.ticker).toUpperCase()!==source&&n(x.score)!=null&&!['high','severe'].includes(txt(x.risk_gate)));",
    'rebalance universe')

old="""      const riskPenalty=riskBudgetPenalty(stock,rows,move,analysed,src.stock);
      const fitScore=conv-penalty-riskPenalty+diversityBonus+valuationBonus+tiltBonus;
      return {stock,conv,convDelta,fitScore,positionPct,sectorPct,indirect,overlapDelta:indirect-srcIndirect,existing:!!existing,targets};
    }).filter(Boolean).sort((a,b)=>b.fitScore-a.fitScore).slice(0,5);"""
new="""      const riskPenalty=riskBudgetPenalty(stock,rows,move,analysed,src.stock);
      const conf=n(stock.confidence_score), valuation=txt(stock.valuation_signal), estimates=txt(stock.estimate_signal);
      const strict=conf!=null&&conf>=60&&valuation!=='overvalued'&&estimates!=='deteriorating';
      const acceptable=(conf==null||conf>=45)&&!(valuation==='overvalued'&&estimates==='deteriorating');
      let evidencePenalty=0; const warnings=[];
      if(conf==null){ evidencePenalty+=7; warnings.push('confiança sem score'); }
      else if(conf<60){ evidencePenalty+=(60-conf)*.35+3; warnings.push(`confiança ${Math.round(conf)}`); }
      if(valuation==='overvalued'){ evidencePenalty+=9; warnings.push('valuation exigente'); }
      else if(valuation==='uncertain'){ evidencePenalty+=3; warnings.push('valuation incerto'); }
      if(estimates==='deteriorating'){ evidencePenalty+=8; warnings.push('expectativas a piorar'); }
      const tier=strict?'preferred':acceptable?'acceptable':'research';
      if(tier==='research') evidencePenalty+=12;
      const fitScore=conv-penalty-riskPenalty+diversityBonus+valuationBonus+tiltBonus-evidencePenalty;
      return {stock,conv,convDelta,fitScore,positionPct,sectorPct,indirect,overlapDelta:indirect-srcIndirect,existing:!!existing,targets,tier,warnings};
    }).filter(Boolean).sort((a,b)=>{ const rank={preferred:0,acceptable:1,research:2}; return (rank[a.tier]-rank[b.tier])||b.fitScore-a.fitScore; }).slice(0,5);"""
rep(old,new,'rebalance ranking')

rep("if(!sim?.results?.length) return '<p class=\"market-case-note\">Sem destinos elegíveis com os filtros atuais.</p>';",
    "if(!sim?.results?.length) return '<p class=\"market-case-note\">Sem candidatos sequer para research. Revê o universo de dados ou os Portfolio Targets.</p>';",
    'rebalance empty')

old="""    return `<div class=\"market-target-summary\">Limites: posição ${t.maxPosition}% · setor ${t.maxSector}% · ${t.overlap==='reduce'?'reduzir overlap':'overlap neutro'} · ${esc(t.tilt)}</div><div class=\"market-rebalance-list\">${sim.results.map((r,i)=>`<button type=\"button\" class=\"market-rebalance-row\" data-market-ticker=\"${esc(r.stock.ticker)}\"><span class=\"market-rebalance-rank\">${i+1}</span><span><strong>${esc(r.stock.ticker)} · ${esc(r.stock.name||'')}</strong><small>${r.existing?'Já em carteira':'Nova posição'} · conv. ${Math.round(r.conv)} · peso após ${r.positionPct.toFixed(1)}% · setor ${r.sectorPct.toFixed(0)}%</small><small>Δ convicção carteira ${r.convDelta>=0?'+':''}${r.convDelta.toFixed(2)} · overlap ${r.overlapDelta>=0?'+':''}${r.overlapDelta.toFixed(1)} pp</small></span><em>${r.fitScore.toFixed(0)}</em></button>`).join('')}</div>`;"""
new="""    const tierLabel=r=>r.tier==='preferred'?'Preferido':r.tier==='acceptable'?'Aceitável':'Research';
    return `<div class=\"market-target-summary\">Limites: posição ${t.maxPosition}% · setor ${t.maxSector}% · ${t.overlap==='reduce'?'reduzir overlap':'overlap neutro'} · ${esc(t.tilt)}</div><div class=\"market-rebalance-list\">${sim.results.map((r,i)=>`<button type=\"button\" class=\"market-rebalance-row\" data-market-ticker=\"${esc(r.stock.ticker)}\"><span class=\"market-rebalance-rank\">${i+1}</span><span><strong>${esc(r.stock.ticker)} · ${esc(r.stock.name||'')}</strong><small>${tierLabel(r)} · ${r.existing?'já em carteira':'nova posição'} · conv. ${Math.round(r.conv)} · peso após ${r.positionPct.toFixed(1)}% · setor ${r.sectorPct.toFixed(0)}%</small><small>Δ convicção ${r.convDelta>=0?'+':''}${r.convDelta.toFixed(2)} · overlap ${r.overlapDelta>=0?'+':''}${r.overlapDelta.toFixed(1)} pp${r.warnings?.length?' · ⚠ '+esc(r.warnings.slice(0,2).join(' · ')):''}</small></span><em>${r.fitScore.toFixed(0)}</em></button>`).join('')}</div>`;"""
rep(old,new,'rebalance render')

rep("const universe=M.stocks.filter(x=>!isFund(x)&&n(x.score)!=null&&n(x.confidence_score)>=60&&!['high','severe'].includes(txt(x.risk_gate))&&txt(x.valuation_signal)!=='overvalued'&&txt(x.estimate_signal)!=='deteriorating');",
    "const universe=M.stocks.filter(x=>!isFund(x)&&n(x.score)!=null&&!['high','severe'].includes(txt(x.risk_gate)));",
    'fresh universe')

old="""      const posCapacity=Math.max(0,afterTotal*maxPos/100-existingValue), sectorCapacity=Math.max(0,afterTotal*maxSector/100-sectorValue), capacity=Math.min(posCapacity,sectorCapacity,fresh);
      if(capacity<50) return null;
      let score=conv+portfolioTiltBonus(stock,targets.tilt);
      if(txt(stock.valuation_signal)==='undervalued') score+=4; else if(txt(stock.valuation_signal)==='fair') score+=1;"""
new="""      const strictPosCapacity=Math.max(0,afterTotal*maxPos/100-existingValue), strictSectorCapacity=Math.max(0,afterTotal*maxSector/100-sectorValue);
      const softPosCapacity=Math.max(0,afterTotal*(maxPos+3)/100-existingValue), softSectorCapacity=Math.max(0,afterTotal*(maxSector+5)/100-sectorValue);
      let capacity=Math.min(strictPosCapacity,strictSectorCapacity,fresh), budgetMode='within targets';
      if(capacity<50){ capacity=Math.min(softPosCapacity,softSectorCapacity,fresh); budgetMode='soft budget'; }
      if(capacity<50) return null;
      const conf=n(stock.confidence_score), valuation=txt(stock.valuation_signal), estimates=txt(stock.estimate_signal);
      const strict=conf!=null&&conf>=60&&valuation!=='overvalued'&&estimates!=='deteriorating'&&budgetMode==='within targets';
      const acceptable=(conf==null||conf>=45)&&!(valuation==='overvalued'&&estimates==='deteriorating');
      const tier=strict?'preferred':acceptable?'acceptable':'research';
      const warnings=[]; let score=conv+portfolioTiltBonus(stock,targets.tilt);
      if(conf==null){ score-=7; warnings.push('confiança sem score'); } else if(conf<60){ score-=(60-conf)*.35+3; warnings.push(`confiança ${Math.round(conf)}`); }
      if(valuation==='overvalued'){ score-=9; warnings.push('valuation exigente'); }
      if(estimates==='deteriorating'){ score-=8; warnings.push('expectativas a piorar'); }
      if(budgetMode==='soft budget'){ score-=6; warnings.push('excede objetivo ligeiramente'); }
      if(tier==='research') score-=12;
      if(valuation==='undervalued') score+=4; else if(valuation==='fair') score+=1;"""
rep(old,new,'fresh capacity')

old="""      score-=riskBudgetPenalty(stock,rows,Math.min(capacity,fresh),afterTotal);
      return {stock,conv,score,capacity,existingValue,sector,sectorValue,indirect};
    }).filter(Boolean).sort((a,b)=>b.score-a.score);"""
new="""      score-=riskBudgetPenalty(stock,rows,Math.min(capacity,fresh),afterTotal);
      return {stock,conv,score,capacity,existingValue,sector,sectorValue,indirect,tier,warnings,budgetMode};
    }).filter(Boolean).sort((a,b)=>{ const rank={preferred:0,acceptable:1,research:2}; return (rank[a.tier]-rank[b.tier])||b.score-a.score; });"""
rep(old,new,'fresh ranking')

rep("if(!plan?.allocations?.length) return '<p class=\"market-case-note\">Não encontrei destinos robustos dentro dos objetivos atuais.</p>';",
    "if(!plan?.allocations?.length) return '<p class=\"market-case-note\">Não encontrei candidatos mesmo após relaxar os filtros. Revê os objetivos ou a cobertura do universo.</p>';",
    'fresh empty')

old="""    return `<div class=\"market-fresh-summary\"><strong>${euro(plan.allocated)} distribuídos</strong><span>Convicção ponderada ${plan.currentConv.toFixed(1)} → ${plan.afterConv.toFixed(1)}${plan.remaining>=50?` · ${euro(plan.remaining)} ficam por alocar`:''}</span></div><div class=\"market-fresh-list\">${plan.allocations.map((x,i)=>`<button type=\"button\" class=\"market-fresh-row\" data-market-ticker=\"${esc(x.stock.ticker)}\"><span class=\"market-rebalance-rank\">${i+1}</span><span><strong>${esc(x.stock.ticker)} · ${euro(x.amount)}</strong><small>${x.existingValue>0?'Reforço existente':'Nova posição'} · conv. ${Math.round(x.conv)} · ${esc(x.sector)}</small><small>Peso após ${x.positionPct.toFixed(1)}% · setor após ${x.sectorPct.toFixed(1)}% · fit ${x.score.toFixed(0)}</small></span></button>`).join('')}</div><p class=\"market-case-note\">Simulação de research. Não considera impostos, comissões, spreads nem necessidades pessoais de liquidez.</p>`;"""
new="""    const tierLabel=x=>x.tier==='preferred'?'Preferido':x.tier==='acceptable'?'Aceitável':'Research';
    return `<div class=\"market-fresh-summary\"><strong>${euro(plan.allocated)} distribuídos</strong><span>Convicção ponderada ${plan.currentConv.toFixed(1)} → ${plan.afterConv.toFixed(1)}${plan.remaining>=50?` · ${euro(plan.remaining)} ficam por alocar`:''}</span></div><div class=\"market-fresh-list\">${plan.allocations.map((x,i)=>`<button type=\"button\" class=\"market-fresh-row\" data-market-ticker=\"${esc(x.stock.ticker)}\"><span class=\"market-rebalance-rank\">${i+1}</span><span><strong>${esc(x.stock.ticker)} · ${euro(x.amount)}</strong><small>${tierLabel(x)} · ${x.existingValue>0?'reforço existente':'nova posição'} · conv. ${Math.round(x.conv)} · ${esc(x.sector)}</small><small>Peso ${x.positionPct.toFixed(1)}% · setor ${x.sectorPct.toFixed(1)}% · fit ${x.score.toFixed(0)}${x.warnings?.length?' · ⚠ '+esc(x.warnings.slice(0,2).join(' · ')):''}</small></span></button>`).join('')}</div><p class=\"market-case-note\">Preferido = cumpre filtros ideais; Aceitável/Research aparecem com alertas em vez de serem escondidos. Risk Gate high/severe continua excluído.</p>`;"""
rep(old,new,'fresh render')

old='<label><span>Montante</span><input data-rebalance-amount type="number" min="50" step="50" value="${Math.max(50,Math.min(1000,Math.round(defaultSource.value/50)*50||50))}"></label>'
new='<label><span>Montante</span><input data-rebalance-amount type="number" min="1" max="${Math.max(1,Math.floor(defaultSource.value))}" step="1" value="${Math.max(1,Math.min(1000,Math.round(defaultSource.value)||1))}"></label>'
rep(old,new,'rebalancer amount')

p.write_text(s)

p=Path('README.md'); s=p.read_text();
if not s.startswith('## Vestra v5.8.1'):
    s="""## Vestra v5.8.1 — Candidate Fallbacks

- Fresh Capital Planner e Assisted Rebalancer deixam de falhar silenciosamente quando nenhum ativo cumpre simultaneamente todos os filtros ideais.
- Candidatos são classificados em Preferido, Aceitável com alertas e Apenas research; Risk Gate high/severe continua a ser exclusão dura.
- Portfolio Targets continuam prioritários, mas existe um soft budget limitado quando pequenas ultrapassagens bloqueiam todos os candidatos.
- A interface mostra confiança baixa/ausente, valuation exigente, expectativas em deterioração e soft budget em vez de esconder o candidato.
- Rebalancer deixa de sugerir um montante superior ao valor da posição de origem.
- PWA cache: `vestra-cache-v54`.

"""+s
p.write_text(s)

p=Path('sw.js'); s=p.read_text().replace('vestra-cache-v53','vestra-cache-v54'); p.write_text(s)
