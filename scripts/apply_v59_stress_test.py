from pathlib import Path

p=Path('market.js')
s=p.read_text()

anchor="  const PORTFOLIO_HEALTH_KEY='vestra_portfolio_health_v1';\n"
if anchor not in s:
    raise SystemExit('health anchor missing')
insert=r'''  const PORTFOLIO_STRESS_SCENARIOS={
    rates:{label:'Taxas +100 bps',note:'Choque de taxas. Penaliza sobretudo REITs, utilities e growth de duration longa.'},
    nasdaq:{label:'Nasdaq -20%',note:'Choque risk-off tecnológico. Usa Growth/Technology/beta como proxies de sensibilidade.'},
    oil:{label:'Petróleo -25%',note:'Choque de energia. Penaliza Energy; alguns consumidores intensivos em combustível recebem pequeno amortecedor.'},
    usd:{label:'USD -10%',note:'Choque cambial visto de uma carteira em EUR. Afeta diretamente ativos classificados em USD.'},
    europe:{label:'Recessão europeia',note:'Choque regional/cíclico. Penaliza Europa e setores mais sensíveis ao ciclo económico.'}
  };
  function stressImpactPct(stock,key){
    const tags=stockRiskTags(stock), sec=txt(stock?.sector).toLowerCase(), ind=txt(stock?.industry).toLowerCase();
    const beta=n(stock?.beta); let x=0;
    if(key==='rates'){
      if(tags.includes('Sensível a taxas')) x-=10;
      if(tags.includes('Growth')) x-=4;
      if(/real estate|reit/.test(sec+' '+ind)) x-=4;
      if(/utilities|utility/.test(sec+' '+ind)) x-=3;
      if(/bank|banks/.test(sec+' '+ind)) x+=2;
    }
    if(key==='nasdaq'){
      if(tags.includes('Growth')) x-=14;
      if(/technology|software|semiconductor|internet|cloud|cyber/.test(sec+' '+ind)) x-=7;
      if(beta!=null&&beta>1) x-=Math.min(5,(beta-1)*4);
      if(!x) x=-4;
    }
    if(key==='oil'){
      if(/energy|oil|gas|exploration|petroleum/.test(sec+' '+ind)) x-=18;
      else if(/airline|transport|logistics/.test(sec+' '+ind)) x+=3;
      else x-=1;
    }
    if(key==='usd') x=stockCurrency(stock)==='USD'?-10:0;
    if(key==='europe'){
      if(stockRegion(stock)==='Europa') x-=10;
      if(/financial|industrial|consumer cyclical|materials|automotive|bank/.test(sec+' '+ind)) x-=5;
      if(/utilities|healthcare|consumer defensive/.test(sec+' '+ind)) x+=2;
      if(!x) x=-2;
    }
    return Math.max(-35,Math.min(8,x));
  }
  function portfolioStress(rows,key){
    const total=rows.reduce((a,r)=>a+(n(r.value)||0),0)||1;
    const detail=rows.map(r=>{
      const impact=stressImpactPct(r.stock,key), weight=(n(r.value)||0)/total*100, contribution=impact*weight/100;
      return {...r,impact,weight,contribution};
    });
    const portfolioImpact=detail.reduce((a,r)=>a+r.contribution,0);
    const downside=Math.abs(Math.min(0,portfolioImpact));
    const resilience=Math.max(0,Math.min(100,Math.round(100-downside*4.2)));
    const exposedWeight=detail.filter(r=>r.impact<=-8).reduce((a,r)=>a+r.weight,0);
    const top=detail.filter(r=>r.impact<0).sort((a,b)=>a.contribution-b.contribution).slice(0,6);
    return {key,portfolioImpact,resilience,exposedWeight,top};
  }
  function renderStressScenario(rows,key){
    const sc=PORTFOLIO_STRESS_SCENARIOS[key], r=portfolioStress(rows,key);
    const tone=r.resilience>=75?'is-positive':r.resilience>=55?'is-warn':'is-risk';
    return `<div class="market-stress-result" data-stress-panel="${key}" ${key==='rates'?'':'hidden'}><div class="market-stress-kpis"><div><small>Impacto proxy</small><strong>${r.portfolioImpact>=0?'+':''}${r.portfolioImpact.toFixed(1)}%</strong></div><div><small>Resiliência</small><strong class="${tone}">${r.resilience}/100</strong></div><div><small>Exposição forte</small><strong>${r.exposedWeight.toFixed(0)}%</strong></div></div><p class="market-case-note">${esc(sc.note)}</p>${r.top.length?`<div class="market-stress-list">${r.top.map(x=>`<button type="button" data-market-ticker="${esc(x.stock.ticker)}"><span><strong>${esc(x.stock.ticker)}</strong><small>peso ${x.weight.toFixed(1)}% · choque ${x.impact.toFixed(0)}%</small></span><em>${x.contribution.toFixed(2)} pp</em></button>`).join('')}</div>`:'<p class="market-case-note">Sem exposição negativa material identificada neste cenário.</p>'}<p class="market-case-note">Stress proxy, não previsão: não modela correlações dinâmicas, opções, hedges, impostos nem liquidez.</p></div>`;
  }
  function renderPortfolioStressTest(rows){
    return `<div class="market-detail-card market-stress-test"><div class="market-perspective-head"><div><small>PORTFOLIO STRESS TEST · PROXY</small><h4>Como reage a carteira?</h4></div><span class="market-data-age">cenários</span></div><div class="market-stress-tabs">${Object.entries(PORTFOLIO_STRESS_SCENARIOS).map(([k,v],i)=>`<button type="button" data-stress-scenario="${k}" class="${i===0?'is-active':''}">${esc(v.label)}</button>`).join('')}</div>${Object.keys(PORTFOLIO_STRESS_SCENARIOS).map(k=>renderStressScenario(rows,k)).join('')}</div>`;
  }

'''
s=s.replace(anchor,insert+anchor,1)

anchor2="    const riskBudget=renderRiskBudget(ranked);\n    const riskBudgetHtml=riskBudget.html;\n"
if anchor2 not in s:
    raise SystemExit('risk budget anchor missing')
s=s.replace(anchor2,anchor2+"    const stressTestHtml=renderPortfolioStressTest(ranked);\n",1)

anchor3="      ${riskBudgetHtml}\n      ${targetHtml}\n"
if anchor3 not in s:
    raise SystemExit('return anchor missing')
s=s.replace(anchor3,"      ${riskBudgetHtml}\n      ${stressTestHtml}\n      ${targetHtml}\n",1)

click_anchor="    const freshRun=e.target.closest('[data-fresh-run]');\n"
if click_anchor not in s:
    raise SystemExit('click anchor missing')
click_code=r'''    const stressBtn=e.target.closest('[data-stress-scenario]');
    if(stressBtn){
      const card=stressBtn.closest('.market-stress-test'), key=stressBtn.dataset.stressScenario;
      card?.querySelectorAll('[data-stress-scenario]').forEach(b=>b.classList.toggle('is-active',b===stressBtn));
      card?.querySelectorAll('[data-stress-panel]').forEach(p=>p.hidden=p.dataset.stressPanel!==key);
      return;
    }
'''
s=s.replace(click_anchor,click_code+click_anchor,1)
p.write_text(s)

p=Path('market.css'); css=p.read_text(); css += r'''
/* Vestra v5.9 — Portfolio Stress Test */
.market-stress-tabs{display:flex;gap:7px;overflow-x:auto;padding:2px 0 10px;scrollbar-width:none}.market-stress-tabs::-webkit-scrollbar{display:none}.market-stress-tabs button{flex:0 0 auto;border:1px solid var(--market-border,rgba(15,47,58,.16));background:transparent;color:inherit;border-radius:999px;padding:8px 11px;font:inherit;font-size:12px;font-weight:700}.market-stress-tabs button.is-active{background:var(--market-ink,#0d3040);color:#fff;border-color:transparent}.market-stress-kpis{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:4px 0 8px}.market-stress-kpis>div{padding:10px;border-radius:14px;background:rgba(15,47,58,.055)}.market-stress-kpis small{display:block;font-size:10px;opacity:.7}.market-stress-kpis strong{display:block;margin-top:3px;font-size:17px}.market-stress-list{display:grid;gap:7px}.market-stress-list button{display:flex;width:100%;justify-content:space-between;align-items:center;gap:10px;text-align:left;border:1px solid rgba(15,47,58,.12);border-radius:14px;background:transparent;color:inherit;padding:10px 12px}.market-stress-list button span{min-width:0}.market-stress-list button strong,.market-stress-list button small{display:block}.market-stress-list button small{margin-top:2px;opacity:.68}.market-stress-list button em{font-style:normal;font-weight:750;white-space:nowrap}@media(max-width:520px){.market-stress-kpis{grid-template-columns:1fr 1fr}.market-stress-kpis>div:last-child{grid-column:1/-1}}
'''; p.write_text(css)

p=Path('README.md'); s=p.read_text(); s="""## Vestra v5.9 — Portfolio Stress Test\n\n- Novo Stress Test proxy dentro de As minhas posições, sem alterar a navegação principal.\n- Cenários iniciais: Taxas +100 bps, Nasdaq -20%, Petróleo -25%, USD -10% e Recessão europeia.\n- Mostra impacto ponderado estimado, Stress Resilience 0–100, peso com exposição forte e posições que mais contribuem para o choque.\n- Usa fatores, setor/indústria, beta, moeda e região já disponíveis; é explicitamente uma heurística de stress, não previsão, VaR ou modelo de correlação.\n- Nenhum cenário altera Score Vestra, Investment Case ou Portfolio Targets.\n- PWA cache: `vestra-cache-v55`.\n\n"""+s; p.write_text(s)

p=Path('sw.js'); s=p.read_text().replace('vestra-cache-v54','vestra-cache-v55'); p.write_text(s)
