/* Vestra Portfolio Diagnostics v1.0 — diagnosis state, coverage semantics and measurable overlap. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(String(v).replace(',','.').replace(/[^0-9+\-.]/g,''));return Number.isFinite(x)?x:null;};
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let pending=false;

  function root(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }
  function decisionCenter(c){
    return [...(c?.querySelectorAll('.market-detail-card,section,div')||[])].find(x=>/Portfolio Decision Center/i.test(t(x.textContent))&&/O que merece atenção agora/i.test(t(x.textContent)))||null;
  }
  function summaryKpi(c,label){
    const boxes=[...c.querySelectorAll('.market-portfolio-summary .market-portfolio-kpi')];
    return boxes.find(x=>t(x.querySelector('small')?.textContent).toLowerCase()===label.toLowerCase())||null;
  }
  function coverage(c){
    const posBox=summaryKpi(c,'Posições'),researchBox=summaryKpi(c,'Com research'),valueBox=summaryKpi(c,'Cobertura')||summaryKpi(c,'Cobertura por valor');
    const positions=n(posBox?.querySelector('strong')?.textContent),research=n(researchBox?.querySelector('strong')?.textContent),valueCoverage=n(valueBox?.querySelector('strong')?.textContent);
    const positionCoverage=positions>0&&research!=null?Math.round(research/positions*100):null;
    return {positions,research,positionCoverage,valueCoverage,valueBox};
  }
  function syncCoverage(c){
    const m=coverage(c); if(!m.positions)return;
    if(m.valueBox){const l=m.valueBox.querySelector('small');if(l)l.textContent='Cobertura por valor';}
    const hero=[...c.querySelectorAll('.vpu-grid>div')].find(x=>t(x.querySelector('small')?.textContent)==='Cobertura');
    if(hero&&m.positionCoverage!=null){
      const strong=hero.querySelector('strong'),sub=hero.querySelector('span');
      if(strong)strong.textContent=`${m.positionCoverage}%`;
      if(sub)sub.textContent=`${Math.round(m.research||0)}/${Math.round(m.positions)} posições · ${m.valueCoverage==null?'—':Math.round(m.valueCoverage)+'%'} do valor`;
    }
    const health=[...c.querySelectorAll('.vpu-health-row')].find(x=>t(x.querySelector('span')?.textContent).startsWith('Cobertura'));
    if(health&&m.positionCoverage!=null){
      const label=health.querySelector('span'),b=health.querySelector('b'),bar=health.querySelector('.vpu-track i');
      if(label)label.textContent='Cobertura posições'; if(b)b.textContent=`${m.positionCoverage}%`;
      if(bar){bar.style.width=`${Math.max(0,Math.min(100,m.positionCoverage))}%`;bar.className=m.positionCoverage>=70?'is-good':m.positionCoverage>=40?'is-warn':'is-bad';}
    }
  }
  function syncDiagnosis(c){
    const dc=decisionCenter(c),btn=c.querySelector('[data-vpu-detail]'); if(!dc||!btn)return;
    const open=c.dataset.vpdDiagnosis==='1'; dc.hidden=!open; btn.textContent=open?'Ocultar diagnóstico':'Ver diagnóstico';
  }
  function assetValue(a){const x=n(a?.value??a?.marketValueEUR);return x??0;}
  function eligible(a){const cls=t(a?.class).toLowerCase();return !cls.includes('cripto')&&(cls.includes('ações')||cls.includes('acoes')||cls.includes('etf')||cls.includes('fund'));}
  function assetTicker(a){return t(a?.yahooTicker||a?.ticker||a?.symbol).toUpperCase();}
  function baseTicker(v){return t(v).toUpperCase().replace(/\.[A-Z]+$/,'');}
  function isFund(s){const q=t(s?.quote_type||s?.quoteType).toUpperCase(),m=t(s?.score_model).toLowerCase(),name=t(s?.name).toLowerCase();return q==='ETF'||q==='MUTUALFUND'||m==='etf'||/\betf\b|fund/.test(name);}
  function holdingSymbol(h){return baseTicker(h?.symbol||h?.ticker||h?.holding_symbol||h?.holdingSymbol||'');}
  function holdingWeight(h){let x=n(h?.weight??h?.holding_percent??h?.holdingPercent??h?.percent??h?.pct);if(x==null||x<0)return null;if(x<=1)x*=100;return x<=100?x:null;}
  function resolvedRows(){
    let assets=[];try{assets=Array.isArray(window.state?.assets)?window.state.assets:[]}catch(_){return[];}
    const map=new Map();
    for(const a of assets.filter(eligible)){
      const tk=assetTicker(a);if(!tk)continue;
      let stock=null;try{stock=window.VestraMarket?.resolvePortfolioStock?.({ticker:tk,yahooTicker:tk,symbol:tk,class:a.class});}catch(_){}
      if(!stock)continue;const key=t(stock.ticker).toUpperCase();const prev=map.get(key)||{stock,value:0};prev.value+=assetValue(a);map.set(key,prev);
    }
    return [...map.values()].filter(x=>x.value>0);
  }
  function overlapModel(){
    const rows=resolvedRows(),total=rows.reduce((a,r)=>a+r.value,0)||1,held=new Map(rows.map(r=>[baseTicker(r.stock.ticker),r]));
    const allEtfs=rows.filter(r=>isFund(r.stock));
    const etfs=allEtfs.filter(r=>Array.isArray(r.stock?.top_holdings)&&r.stock.top_holdings.some(h=>holdingSymbol(h)&&holdingWeight(h)!=null));
    const items=[];
    for(let i=0;i<etfs.length;i++)for(let j=i+1;j<etfs.length;j++){
      const a=new Map(etfs[i].stock.top_holdings.map(h=>[holdingSymbol(h),holdingWeight(h)]).filter(([k,w])=>k&&w!=null));
      const b=new Map(etfs[j].stock.top_holdings.map(h=>[holdingSymbol(h),holdingWeight(h)]).filter(([k,w])=>k&&w!=null));
      let common=0;const names=[];for(const [k,w] of a){if(b.has(k)){common+=Math.min(w,b.get(k));names.push(k);}}
      if(common<=0)continue;const pa=etfs[i].value/total*100,pb=etfs[j].value/total*100,impact=Math.min(pa,pb)*common/100;
      items.push({impact,type:'ETF × ETF',title:`${etfs[i].stock.ticker} × ${etfs[j].stock.ticker}`,detail:`${common.toFixed(1)}% de top holdings comuns${names.length?' · '+names.slice(0,4).join(', '):''}`});
    }
    for(const e of etfs){
      const ep=e.value/total*100;
      for(const h of e.stock.top_holdings){const sym=holdingSymbol(h),w=holdingWeight(h),direct=held.get(sym);if(!sym||w==null||!direct||sym===baseTicker(e.stock.ticker))continue;const impact=ep*w/100;items.push({impact,type:'AÇÃO + ETF',title:`${sym} também dentro de ${e.stock.ticker}`,detail:`${w.toFixed(1)}% do ETF · exposição indireta ~${impact.toFixed(2)}% da parte analisável`});}
    }
    const uniq=new Map();for(const x of items){const k=`${x.type}|${x.title}`;if(!uniq.has(k)||uniq.get(k).impact<x.impact)uniq.set(k,x);}
    return {rows,total,allEtfs,etfs,items:[...uniq.values()].sort((a,b)=>b.impact-a.impact).slice(0,10)};
  }
  function syncOverlap(c){
    const card=c.querySelector('[data-ux-kind="overlap"]');if(!card)return;const model=overlapModel();
    let host=card.querySelector('.vpd-overlap-results');if(!host){host=document.createElement('div');host.className='vpd-overlap-results';const anchor=card.querySelector('.ux455-overlap-note')||card.querySelector('.ux454-overlap-head');anchor?anchor.insertAdjacentElement('afterend',host):card.prepend(host);}
    [...card.children].forEach(x=>{if(x===host||x.matches?.('.ux454-overlap-head,.ux455-overlap-note,.market-collapse-toggle,.ux454-purpose,.ux-section-hint'))return;if(x.tagName==='H4'||x.matches?.('.market-case-note,.market-case-list'))x.style.display='none';});
    const coverageText=model.allEtfs.length?`${model.etfs.length}/${model.allEtfs.length} ETFs com holdings detalhados`:'Sem ETFs identificados nesta parte da carteira';
    if(model.items.length){
      host.innerHTML=`<div class="vpd-overlap-head"><div><small>TOP OVERLAP DETETADO</small><strong>${model.items.length} sinais mensuráveis</strong></div><span>${esc(coverageText)}</span></div><div class="vpd-overlap-list">${model.items.map(x=>`<div class="vpd-overlap-row"><div><small>${esc(x.type)}</small><strong>${esc(x.title)}</strong><span>${esc(x.detail)}</span></div><b>${x.impact.toFixed(2)}%</b></div>`).join('')}</div><p class="vpd-overlap-foot">Impacto = exposição duplicada estimada sobre a parte analisável da carteira. Mostramos os maiores sinais mesmo abaixo dos antigos cortes de 5%/2%.</p>`;
    }else{
      host.innerHTML=`<div class="vpd-overlap-head"><div><small>OVERLAP</small><strong>Não há overlap mensurável com os dados actuais</strong></div><span>${esc(coverageText)}</span></div><p class="vpd-overlap-foot">Isto não significa necessariamente overlap zero. Quando os holdings dos ETFs não estão disponíveis, a Vestra passa a indicar a limitação em vez de concluir “sem concentração”.</p>`;
    }
  }
  function style(){if(document.getElementById('vestra-portfolio-diagnostics-style'))return;const s=document.createElement('style');s.id='vestra-portfolio-diagnostics-style';s.textContent=`.vpd-overlap-results{margin:0 0 8px}.vpd-overlap-head{display:flex;justify-content:space-between;gap:10px;align-items:end;padding:10px 1px}.vpd-overlap-head>div{display:grid;gap:2px}.vpd-overlap-head small{font-size:8px;font-weight:900;letter-spacing:.12em;color:#9a6819}.vpd-overlap-head strong{font-size:13px}.vpd-overlap-head>span{font-size:8px;color:var(--text2);text-align:right}.vpd-overlap-list{display:grid;gap:6px}.vpd-overlap-row{display:flex;justify-content:space-between;gap:10px;padding:9px 10px;border-radius:13px;background:var(--card);border:1px solid var(--line)}.vpd-overlap-row>div{display:grid;gap:2px;min-width:0}.vpd-overlap-row small{font-size:7.5px;font-weight:900;letter-spacing:.1em;color:#9a6819}.vpd-overlap-row strong{font-size:10px}.vpd-overlap-row span{font-size:8.5px;color:var(--text2)}.vpd-overlap-row>b{font-size:11px;color:#9a6819;flex:0 0 auto}.vpd-overlap-foot{font-size:8.5px!important;color:var(--text2);margin:8px 2px 0!important}`;document.head.appendChild(s);}
  function apply(){const c=root();if(!c)return;syncCoverage(c);syncDiagnosis(c);syncOverlap(c);}
  document.addEventListener('click',e=>{const btn=e.target.closest?.('[data-vpu-detail]');if(!btn)return;const c=root();if(!c)return;const dc=decisionCenter(c);if(!dc)return;const open=!dc.hidden;c.dataset.vpdDiagnosis=open?'1':'0';requestAnimationFrame(()=>{syncDiagnosis(c);if(open)dc.scrollIntoView?.({behavior:'smooth',block:'start'});});},true);
  function start(){style();apply();const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.VestraPortfolioDiagnostics=Object.freeze({refresh:apply,overlapModel,version:'1.0'});
})();
