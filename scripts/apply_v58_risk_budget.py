from pathlib import Path

p=Path('market.js')
s=p.read_text()

anchor="""  const PORTFOLIO_HEALTH_KEY='vestra_portfolio_health_v1';
"""
insert=r"""
  function stockCurrency(stock){
    const explicit=txt(stock?.currency||stock?.financial_currency||stock?.financialCurrency).toUpperCase();
    if(explicit) return explicit;
    const t=txt(stock?.ticker).toUpperCase();
    if(t.endsWith('.L')) return 'GBP'; if(/\.(DE|PA|AS|MI|MC|LS)$/.test(t)) return 'EUR';
    if(t.endsWith('.SW')) return 'CHF'; if(/\.(TO|V)$/.test(t)) return 'CAD'; if(t.endsWith('.T')) return 'JPY';
    if(t.endsWith('.HK')) return 'HKD'; if(t.endsWith('.AX')) return 'AUD'; if(t.endsWith('.ST')) return 'SEK';
    if(t.endsWith('.CO')) return 'DKK'; if(t.endsWith('.OL')) return 'NOK';
    return t.includes('.')?'Outra':'USD';
  }
  function stockRegion(stock){
    const c=txt(stock?.country||stock?.country_name||stock?.region).toLowerCase();
    if(/united states|usa|canada|mexico/.test(c)) return 'Am. Norte';
    if(/portugal|spain|france|germany|italy|netherlands|belgium|switzerland|austria|ireland|united kingdom|uk|sweden|norway|denmark|finland|poland/.test(c)) return 'Europa';
    if(/china|hong kong|japan|korea|taiwan|india|singapore|indonesia|thailand|malaysia/.test(c)) return 'Ásia';
    if(/australia|new zealand/.test(c)) return 'Pacífico';
    const t=txt(stock?.ticker).toUpperCase();
    if(/\.(L|DE|PA|AS|MI|MC|LS|SW|ST|CO|OL)$/.test(t)) return 'Europa';
    if(/\.(T|HK)$/.test(t)) return 'Ásia'; if(t.endsWith('.AX')) return 'Pacífico'; if(/\.(TO|V)$/.test(t)||!t.includes('.')) return 'Am. Norte';
    return 'Outra';
  }
  function stockRiskTags(stock){
    const tags=[]; const growth=n(stock?.growth_pct), value=n(stock?.value_pct), y=n(stock?.dividend_yield), cap=n(stock?.market_cap??stock?.marketCap);
    const model=txt(stock?.score_model).toLowerCase(), sec=txt(stock?.sector).toLowerCase(), ind=txt(stock?.industry).toLowerCase();
    if(model==='growth'||growth>=65||((n(stock?.revenue_growth)||0)>.20)) tags.push('Growth');
    if(value>=65) tags.push('Value');
    if(y!=null&&y>=.025) tags.push('Dividendos');
    if(cap!=null&&cap>0&&cap<2e9) tags.push('Small caps');
    if(model==='reit'||/real estate|reit|utilities|utility/.test(sec+' '+ind)||model==='growth') tags.push('Sensível a taxas');
    return [...new Set(tags)];
  }
  function riskMapAdd(map,key,value){ if(!key||!Number.isFinite(value)) return; map.set(key,(map.get(key)||0)+value); }
  function portfolioRiskProfile(rows,totalOverride){
    const total=totalOverride||rows.reduce((a,r)=>a+(n(r.value)||0),0)||1;
    const factors=new Map(), currencies=new Map(), regions=new Map();
    for(const r of rows){
      const v=n(r.value)||0; if(v<=0) continue;
      stockRiskTags(r.stock).forEach(tag=>riskMapAdd(factors,tag,v));
      riskMapAdd(currencies,stockCurrency(r.stock),v); riskMapAdd(regions,stockRegion(r.stock),v);
    }
    const pctRows=m=>[...m.entries()].map(([name,value])=>({name,value,pct:value/total*100})).sort((a,b)=>b.pct-a.pct);
    return {total,factors:pctRows(factors),currencies:pctRows(currencies),regions:pctRows(regions)};
  }
  function riskBudgetPenalty(stock,rows,amount,totalAfter,sourceStock=null){
    const targets=loadPortfolioTargets(); const maxFactor=n(targets.maxFactor)||45, maxCurrency=n(targets.maxCurrency)||70, maxRegion=n(targets.maxRegion)||70;
    const prof=portfolioRiskProfile(rows,totalAfter); const a=Math.max(0,n(amount)||0), delta=a/(totalAfter||1)*100;
    let penalty=0; const factors=stockRiskTags(stock), srcFactors=sourceStock?stockRiskTags(sourceStock):[];
    for(const tag of factors){ const now=prof.factors.find(x=>x.name===tag)?.pct||0; const after=now+delta-(srcFactors.includes(tag)?delta:0); if(after>maxFactor) penalty+=(after-maxFactor)*.65; }
    const cur=stockCurrency(stock), srcCur=sourceStock?stockCurrency(sourceStock):null, curNow=prof.currencies.find(x=>x.name===cur)?.pct||0;
    const curAfter=curNow+delta-(srcCur===cur?delta:0); if(curAfter>maxCurrency) penalty+=(curAfter-maxCurrency)*.55;
    const reg=stockRegion(stock), srcReg=sourceStock?stockRegion(sourceStock):null, regNow=prof.regions.find(x=>x.name===reg)?.pct||0;
    const regAfter=regNow+delta-(srcReg===reg?delta:0); if(regAfter>maxRegion) penalty+=(regAfter-maxRegion)*.45;
    return penalty;
  }
  function renderRiskBudget(rows){
    const profile=portfolioRiskProfile(rows), t=loadPortfolioTargets();
    const maxFactor=n(t.maxFactor)||45, maxCurrency=n(t.maxCurrency)||70, maxRegion=n(t.maxRegion)||70;
    const breaches=[...profile.factors.filter(x=>x.pct>maxFactor).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxFactor}%`),...profile.currencies.filter(x=>x.pct>maxCurrency).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxCurrency}%`),...profile.regions.filter(x=>x.pct>maxRegion).map(x=>`${x.name} ${x.pct.toFixed(0)}% > ${maxRegion}%`)];
    const excess=profile.factors.reduce((a,x)=>a+Math.max(0,x.pct-maxFactor),0)+profile.currencies.reduce((a,x)=>a+Math.max(0,x.pct-maxCurrency),0)+profile.regions.reduce((a,x)=>a+Math.max(0,x.pct-maxRegion),0);
    const fit=Math.max(0,Math.min(100,Math.round(100-excess*1.4))), tone=fit>=85?'is-positive':fit>=65?'is-warn':'is-risk';
    const chips=(items,limit)=>items.slice(0,limit).map(x=>`<span><strong>${esc(x.name)}</strong>${x.pct.toFixed(0)}%</span>`).join('');
    const html=`<div class=\"market-detail-card market-risk-budget\"><div class=\"market-perspective-head\"><div><small>PORTFOLIO RISK BUDGET · PROXY</small><h4>Diversificação real</h4></div><span class=\"market-target-fit-score ${tone}\">${fit}/100</span></div><p class=\"market-case-note\">Exposição ponderada por fatores, moeda e região. É um proxy baseado nos dados disponíveis; não é um modelo quantitativo de risco/volatilidade.</p><div class=\"market-risk-group\"><small>Fatores</small><div>${chips(profile.factors,5)||'<span>Sem classificação suficiente</span>'}</div></div><div class=\"market-risk-group\"><small>Moedas</small><div>${chips(profile.currencies,4)}</div></div><div class=\"market-risk-group\"><small>Regiões</small><div>${chips(profile.regions,4)}</div></div>${breaches.length?`<ul class=\"market-case-list\">${breaches.slice(0,5).map(x=>`<li>${esc(x)}</li>`).join('')}</ul>`:'<p class=\"market-case-note\">Sem excesso material face aos orçamentos definidos.</p>'}</div>`;
    return {fit,html,profile};
  }

"""
if anchor not in s: raise SystemExit('risk functions anchor missing')
s=s.replace(anchor,insert+anchor,1)

# Extend defaults while preserving old saved settings.
s=s.replace("function defaultPortfolioTargets(){ return {maxPosition:10,maxSector:25,overlap:'reduce',tilt:'balanced'}; }","function defaultPortfolioTargets(){ return {maxPosition:10,maxSector:25,maxFactor:45,maxCurrency:70,maxRegion:70,overlap:'reduce',tilt:'balanced'}; }",1)

# Add risk budget into portfolio intelligence before health snapshot.
anchor2="""    const healthSnapshot={targetFit,conviction:portfolioConvictionNow,topPosition:topPosPct,topSector:sectorRows[0]?.pct||0,overlapCount:ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2).length,riskPositions:(actionCounts.review||0)+(actionCounts.replace||0)};
"""
repl2="""    const riskBudget=renderRiskBudget(ranked);
    const riskBudgetHtml=riskBudget.html;
    const healthSnapshot={targetFit,conviction:portfolioConvictionNow,topPosition:topPosPct,topSector:sectorRows[0]?.pct||0,overlapCount:ranked.filter(r=>(r.portfolioFit?.indirectPct||0)>=2).length,riskPositions:(actionCounts.review||0)+(actionCounts.replace||0),riskFit:riskBudget.fit};
"""
if anchor2 not in s: raise SystemExit('health anchor missing')
s=s.replace(anchor2,repl2,1)

# Extend target controls with risk budgets.
old="""<label><span>Overlap ETF</span><select data-target-overlap>"""
new="""<label><span>Máx. fator</span><div><input data-target-factor type=\"number\" min=\"20\" max=\"80\" step=\"5\" value=\"${targets.maxFactor}\"><em>%</em></div></label><label><span>Máx. moeda</span><div><input data-target-currency type=\"number\" min=\"30\" max=\"100\" step=\"5\" value=\"${targets.maxCurrency}\"><em>%</em></div></label><label><span>Máx. região</span><div><input data-target-region type=\"number\" min=\"30\" max=\"100\" step=\"5\" value=\"${targets.maxRegion}\"><em>%</em></div></label><label><span>Overlap ETF</span><select data-target-overlap>"""
if old not in s: raise SystemExit('target control anchor missing')
s=s.replace(old,new,1)

# Insert risk budget in rendered sequence.
seq="""      ${healthTimelineHtml}
      ${targetHtml}
"""
repseq="""      ${healthTimelineHtml}
      ${riskBudgetHtml}
      ${targetHtml}
"""
if seq not in s: raise SystemExit('render sequence anchor missing')
s=s.replace(seq,repseq,1)

# Candidate penalty in rebalancer.
old3="""      const tiltBonus=portfolioTiltBonus(stock,targets.tilt);
      const fitScore=conv-penalty+diversityBonus+valuationBonus+tiltBonus;
"""
new3="""      const tiltBonus=portfolioTiltBonus(stock,targets.tilt);
      const riskPenalty=riskBudgetPenalty(stock,rows,move,analysed,src.stock);
      const fitScore=conv-penalty-riskPenalty+diversityBonus+valuationBonus+tiltBonus;
"""
if old3 not in s: raise SystemExit('rebalancer fit anchor missing')
s=s.replace(old3,new3,1)

# Candidate penalty in fresh capital planner.
old4="""      if(targets.overlap==='reduce'&&indirect>1.5) score-=(indirect-1.5)*2.5;
      return {stock,conv,score,capacity,existingValue,sector,sectorValue,indirect};
"""
new4="""      if(targets.overlap==='reduce'&&indirect>1.5) score-=(indirect-1.5)*2.5;
      score-=riskBudgetPenalty(stock,rows,Math.min(capacity,fresh),afterTotal);
      return {stock,conv,score,capacity,existingValue,sector,sectorValue,indirect};
"""
if old4 not in s: raise SystemExit('fresh fit anchor missing')
s=s.replace(old4,new4,1)

# Save new target fields.
old5="""const targets={maxPosition:Math.max(3,Math.min(30,n(card?.querySelector('[data-target-position]')?.value)||10)),maxSector:Math.max(10,Math.min(60,n(card?.querySelector('[data-target-sector]')?.value)||25)),overlap:card?.querySelector('[data-target-overlap]')?.value||'reduce',tilt:card?.querySelector('[data-target-tilt]')?.value||'balanced'};"""
new5="""const targets={maxPosition:Math.max(3,Math.min(30,n(card?.querySelector('[data-target-position]')?.value)||10)),maxSector:Math.max(10,Math.min(60,n(card?.querySelector('[data-target-sector]')?.value)||25)),maxFactor:Math.max(20,Math.min(80,n(card?.querySelector('[data-target-factor]')?.value)||45)),maxCurrency:Math.max(30,Math.min(100,n(card?.querySelector('[data-target-currency]')?.value)||70)),maxRegion:Math.max(30,Math.min(100,n(card?.querySelector('[data-target-region]')?.value)||70)),overlap:card?.querySelector('[data-target-overlap]')?.value||'reduce',tilt:card?.querySelector('[data-target-tilt]')?.value||'balanced'};"""
if old5 not in s: raise SystemExit('save targets anchor missing')
s=s.replace(old5,new5,1)
p.write_text(s)

p=Path('market.css'); c=p.read_text(); c += r"""

/* v5.8 — Portfolio Risk Budget */
.market-risk-budget .market-perspective-head{margin-bottom:8px}.market-risk-group{margin-top:9px}.market-risk-group>small{display:block;font-size:9px;font-weight:850;color:var(--text2);margin-bottom:5px}.market-risk-group>div{display:flex;flex-wrap:wrap;gap:6px}.market-risk-group span{display:inline-flex;gap:5px;align-items:center;border:1px solid var(--line2);background:var(--item-bg);border-radius:999px;padding:6px 8px;font-size:9px;color:var(--text2)}.market-risk-group span strong{color:var(--text);font-size:9px}.market-risk-budget .market-case-list{margin-top:10px}
"""
p.write_text(c)

p=Path('README.md'); r=p.read_text(); r="""## Vestra v5.8 — Portfolio Risk Budget

- Novo Risk Budget proxy na Portfolio Intelligence: fatores, moeda, região e sensibilidade provável a taxas.
- Fatores suportados com os dados atuais: Growth, Value, Dividendos, Small caps e Sensível a taxas.
- Portfolio Targets passam a incluir máximos configuráveis por fator, moeda e região.
- Assisted Rebalancer e Fresh Capital Planner penalizam destinos que agravem concentrações acima desses orçamentos.
- País/moeda usam dados explícitos quando disponíveis e fallback pelo ticker/mercado quando necessário; a interface identifica a leitura como proxy.
- O Risk Budget mede construção/diversificação e não substitui VaR, volatilidade ou análise macro profissional.
- PWA cache: `vestra-cache-v53`.

"""+r; p.write_text(r)

p=Path('sw.js'); w=p.read_text().replace('Service Worker v5.7','Service Worker v5.8').replace('vestra-cache-v52','vestra-cache-v53'); p.write_text(w)
