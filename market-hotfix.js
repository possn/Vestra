/* Vestra Market Hotfix v4.45 — direct deploy, independent of Actions. */
(() => {
  'use strict';
  const VERSION='4.45';
  let stocks=[];
  let byTicker=new Map();
  let loading=null;
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function load(){
    if(loading)return loading;
    loading=fetch(`./data/stocks.json?v=${VERSION}`,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject(new Error(`stocks ${r.status}`))).then(d=>{
      stocks=Array.isArray(d)?d:(Array.isArray(d?.stocks)?d.stocks:[]);
      byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s]));
      return stocks;
    }).catch(()=>[]);
    return loading;
  }

  function timing(s){
    const official=n(s?.opportunity_timing_score); if(official!=null)return official;
    const h=Array.isArray(s?.price_history_1y)?s.price_history_1y:[];
    const c=h.map(x=>n(x?.close)).filter(x=>x!=null&&x>0); if(c.length<22)return 50;
    const ret=d=>c.length>d&&c[c.length-d-1]>0?(c[c.length-1]/c[c.length-d-1]-1)*100:null;
    const r20=ret(20),r60=ret(60),hi=Math.max(...c),cur=c[c.length-1]; let x=50;
    if(r20!=null)x+=r20>=0&&r20<=12?18:r20>-6&&r20<0?5:r20>20?-15:r20<=-12?-12:0;
    if(r60!=null)x+=r60>=0&&r60<=25?12:r60>40?-12:r60<=-20?-10:0;
    const room=hi>0?(1-cur/hi)*100:null; if(room!=null)x+=room>=5&&room<=30?8:room<2?-8:0;
    if(t(s?.estimate_signal)==='improving')x+=6; if(t(s?.estimate_signal)==='deteriorating')x-=8;
    return Math.max(0,Math.min(100,x));
  }
  function overextended(s){
    if(typeof s?.opportunity_overextended==='boolean')return s.opportunity_overextended;
    const h=Array.isArray(s?.price_history_1y)?s.price_history_1y:[];
    const c=h.map(x=>n(x?.close)).filter(x=>x!=null&&x>0); if(c.length<22)return false;
    const ret=d=>c.length>d&&c[c.length-d-1]>0?(c[c.length-1]/c[c.length-d-1]-1)*100:null;
    const r20=ret(20),r60=ret(60); return (r20!=null&&r20>25)||(r60!=null&&r60>50);
  }
  function eligible(s){
    const q=t(s?.quote_type||s?.quoteType).toUpperCase();
    if(['ETF','CRYPTOCURRENCY','MUTUALFUND'].includes(q))return false;
    const score=n(s?.score),cov=n(s?.data_coverage_pct),conf=n(s?.confidence_score),crit=n(s?.critical_metric_coverage_pct);
    const rel=t(s?.score_reliability).toLowerCase(),risk=t(s?.risk_gate).toLowerCase();
    if(score==null||score<60||cov==null||cov<55||conf==null||conf<50)return false;
    if(crit!=null&&crit<35)return false;
    if(['insufficient','suppressed'].includes(rel)||['high','severe'].includes(risk)||t(s?.zombie).toLowerCase()==='yes')return false;
    return !overextended(s);
  }
  function opportunity(s){
    const official=n(s?.opportunity_score); if(official!=null&&s?.opportunity_eligible===true)return official;
    const parts=[[n(s?.score),.55],[timing(s),.25],[n(s?.confidence_score),.10],[n(s?.value_pct),.05],[n(s?.growth_pct),.05]].filter(([v])=>v!=null);
    if(!parts.length)return null;
    return Math.max(0,Math.min(100,parts.reduce((a,[v,w])=>a+v*w,0)/parts.reduce((a,[,w])=>a+w,0)));
  }
  function brief(s){
    const direct=t(s?.business_summary||s?.longBusinessSummary||s?.long_business_summary||s?.description||s?.company_description);
    if(direct)return direct;
    const industry=t(s?.industry), sector=t(s?.sector), country=t(s?.country);
    if(industry&&sector&&industry.toLowerCase()!==sector.toLowerCase())return `Empresa do setor ${sector}, com atividade principal em ${industry}.`;
    if(industry)return `Empresa com atividade principal em ${industry}.`;
    if(sector)return `Empresa integrada no setor ${sector}.`;
    if(country)return `Empresa cotada com sede/atividade principal em ${country}.`;
    return 'Empresa cotada acompanhada pelo universo Vestra.';
  }
  function sectorFilter(section){
    const active=section.querySelector('[data-market-sector].is-active');
    if(active)return t(active.dataset.marketSector)||'all';
    const select=section.querySelector('[data-market-sector-select]');
    return t(select?.value)||'all';
  }
  function scoreClass(v){return v>=75?'is-good':v>=60?'is-mid':'is-low';}
  function rowHTML(s){
    const os=opportunity(s), tm=timing(s), desc=brief(s);
    const meta=[os!=null?`Opportunity ${Math.round(os)}/100`:'',`Momento ${Math.round(tm)}/100`,t(s?.opportunity_label)].filter(Boolean).join(' · ');
    return `<div class="market-row market-row--hotfix" data-market-ticker="${esc(s.ticker)}"><div><div class="market-row__title"><span class="market-row__ticker">${esc(s.ticker)}</span><span class="market-row__name">${esc(s.name||'')}</span></div><div class="market-row__description">${esc(desc)}</div><div class="market-row__meta">${esc(meta)}</div></div><div class="market-row__end"><div class="market-score ${scoreClass(os||0)}">${os==null?'—':Math.round(os)}</div></div></div>`;
  }

  function repairOpportunitySection(){
    const section=[...document.querySelectorAll('.market-section')].find(x=>t(x.querySelector('h3')?.textContent)==='Melhores oportunidades');
    if(!section)return;
    const list=section.querySelector('.market-list'); if(!list)return;
    const sector=sectorFilter(section);
    let rows=stocks.filter(eligible);
    if(sector!=='all')rows=rows.filter(s=>t(s?.sector)===sector);
    rows.sort((a,b)=>(opportunity(b)||0)-(opportunity(a)||0)||(timing(b)||0)-(timing(a)||0));
    rows=rows.slice(0,20);
    if(!rows.length)return;
    const signature=rows.map(s=>`${t(s.ticker)}:${Math.round(opportunity(s)||0)}`).join('|')+`|${sector}`;
    if(list.dataset.vestraHotfix===VERSION && list.dataset.vestraSignature===signature)return;
    list.innerHTML=rows.map(rowHTML).join('');
    list.dataset.vestraHotfix=VERSION;
    list.dataset.vestraSignature=signature;
  }

  function ptNumber(text){
    const z=t(text).replace(/\s/g,'').replace(/\./g,'').replace(',','.').replace(/[^0-9+\-.]/g,'');
    const x=Number(z); return Number.isFinite(x)?x:null;
  }
  function repairValuationMultiples(root=document){
    const labels=new Set(['P/E','Forward P/E','EV/EBITDA','PEG']);
    root.querySelectorAll('.market-metric,.market-kv,.market-detail-card,.market-stat').forEach(card=>{
      const label=t(card.querySelector('small,label,.market-kv__label')?.textContent);
      if(!labels.has(label))return;
      const value=card.querySelector('strong,.market-kv__value'); if(!value)return;
      const x=ptNumber(value.textContent); if(x!=null&&x<=0)value.textContent='—';
    });
  }
  function repairLow52(root=document){
    root.querySelectorAll('[data-market-ticker]').forEach(row=>{
      const s=byTicker.get(t(row.dataset.marketTicker).toUpperCase());
      if(!s||t(s.low52_status)!=='insufficient')return;
      const meta=row.querySelector('.market-row__meta'); if(!meta)return;
      meta.textContent=meta.textContent.replace(/Opportunity\s+50\/100\s*·?\s*/i,'Dados insuficientes para Opportunity Rank · ');
    });
  }
  function addStyle(){
    if(document.getElementById('vestra-market-hotfix-v445'))return;
    const st=document.createElement('style'); st.id='vestra-market-hotfix-v445';
    st.textContent='.market-row__description{font-size:11px;line-height:1.4;color:var(--text2,#62757c);margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;max-width:560px}.market-row--hotfix .market-row__meta{margin-top:4px}';
    document.head.appendChild(st);
  }
  function apply(){repairOpportunitySection();repairValuationMultiples();repairLow52();}
  function start(){
    addStyle(); load().then(()=>{apply(); const mo=new MutationObserver(()=>apply()); mo.observe(document.body,{childList:true,subtree:true});});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();
