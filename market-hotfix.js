/* Vestra Market Hotfix v4.50 — direct deploy, independent of Actions. */
(() => {
  'use strict';
  const VERSION='4.50';
  const COLLAPSE_KEY='vestra-market-collapse-v1';
  let stocks=[];
  let byTicker=new Map();
  let loading=null;
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  const t=v=>String(v??'').trim();
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const clamp=v=>Math.max(0,Math.min(100,v));

  function load(){
    if(loading)return loading;
    loading=fetch(`./data/stocks.json?v=${VERSION}`,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject(new Error(`stocks ${r.status}`))).then(d=>{
      stocks=Array.isArray(d)?d:(Array.isArray(d?.stocks)?d.stocks:[]);
      byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s]));
      return stocks;
    }).catch(()=>[]);
    return loading;
  }

  function returns(s){
    const h=Array.isArray(s?.price_history_1y)?s.price_history_1y:[];
    const c=h.map(x=>n(x?.close)).filter(x=>x!=null&&x>0);
    const ret=d=>c.length>d&&c[c.length-d-1]>0?(c[c.length-1]/c[c.length-d-1]-1)*100:null;
    const hi=c.length?Math.max(...c):null,cur=c.length?c[c.length-1]:null;
    return {r5:ret(5),r20:ret(20),r60:ret(60),room:hi&&cur?(1-cur/hi)*100:null};
  }
  function timing(s){
    const official=n(s?.opportunity_timing_score); if(official!=null)return official;
    const {r5,r20,r60,room}=returns(s); let x=50;
    if(r20!=null)x+=r20>=1&&r20<=10?20:r20>-5&&r20<1?8:r20>18?-13:r20<=-12?-14:0;
    if(r60!=null)x+=r60>=3&&r60<=25?13:r60>40?-11:r60<=-20?-10:0;
    if(r5!=null&&r20!=null){ if(r5>0&&r20>-2&&r20<12)x+=5; if(r5<-6)x-=6; }
    if(room!=null)x+=room>=5&&room<=28?9:room<2?-7:room>45?-4:0;
    if(t(s?.estimate_signal)==='improving')x+=7; if(t(s?.estimate_signal)==='deteriorating')x-=9;
    if(['confirmed','recovering'].includes(t(s?.recovery_status)))x+=6;
    if(['failed','bounce_only'].includes(t(s?.recovery_status)))x-=8;
    return clamp(x);
  }
  function overextended(s){
    if(typeof s?.opportunity_overextended==='boolean')return s.opportunity_overextended;
    const {r20,r60,room}=returns(s);
    return (r20!=null&&r20>22)||(r60!=null&&r60>45)||((room!=null&&room<2)&&(r60!=null&&r60>20));
  }
  function eligible(s){
    const q=t(s?.quote_type||s?.quoteType).toUpperCase();
    if(['ETF','CRYPTOCURRENCY','MUTUALFUND'].includes(q))return false;
    const score=n(s?.score),cov=n(s?.data_coverage_pct),conf=n(s?.confidence_score),crit=n(s?.critical_metric_coverage_pct);
    const rel=t(s?.score_reliability).toLowerCase(),risk=t(s?.risk_gate).toLowerCase();
    if(score==null||score<58||cov==null||cov<55||conf==null||conf<50)return false;
    if(crit!=null&&crit<35)return false;
    if(['insufficient','suppressed'].includes(rel)||['high','severe'].includes(risk)||t(s?.zombie).toLowerCase()==='yes')return false;
    if(overextended(s))return false;
    return timing(s)>=44;
  }
  function opportunity(s){
    const score=n(s?.score),tm=timing(s),conf=n(s?.confidence_score),qarp=n(s?.qarp_score),moat=n(s?.moat_score),cap=n(s?.capital_allocation_intelligence_score),rec=n(s?.recovery_score),val=n(s?.value_pct),growth=n(s?.growth_pct),upside=n(s?.fair_value_upside_pct),target=n(s?.analyst_price_target_upside_pct);
    const parts=[]; const add=(v,w)=>{if(v!=null)parts.push([clamp(v),w]);};
    add(score,.29); add(tm,.25); add(q arpFix(qarp),.11); add(moat,.08); add(cap,.06); add(conf,.08); add(rec,.06); add(val,.04); add(growth,.03);
    if(!parts.length)return null;
    let x=parts.reduce((a,[v,w])=>a+v*w,0)/parts.reduce((a,[,w])=>a+w,0);
    if(upside!=null)x+=Math.max(-6,Math.min(7,upside/5));
    else if(target!=null)x+=Math.max(-4,Math.min(5,target/8));
    if(t(s?.estimate_signal)==='improving')x+=3;
    if(t(s?.thesis_direction)==='up')x+=2;
    if(['confirmed','recovering'].includes(t(s?.recovery_status)))x+=3;
    if(t(s?.valuation_signal)==='overvalued')x-=6;
    if(t(s?.estimate_signal)==='deteriorating')x-=6;
    if(['failed','bounce_only'].includes(t(s?.recovery_status)))x-=5;
    if(overextended(s))x=Math.min(x,59);
    return clamp(x);
  }
  function qarpFix(v){ return n(v); }
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
    const active=section.querySelector('[data-market-sector].is-active'); if(active)return t(active.dataset.marketSector)||'all';
    const select=section.querySelector('[data-market-sector-select]'); return t(select?.value)||'all';
  }
  function scoreClass(v){return v>=75?'is-good':v>=60?'is-mid':'is-low';}
  function timingLabel(v){return v>=76?'Momento emergente':v>=62?'Momento favorável':v>=50?'Timing neutro':'Timing fraco';}
  function rowHTML(s){
    const os=opportunity(s),tm=timing(s),desc=brief(s),rr=returns(s);
    const meta=[os!=null?`Opportunity ${Math.round(os)}/100`:'',timingLabel(tm),`Momento ${Math.round(tm)}/100`,rr.r20!=null?`20d ${rr.r20>=0?'+':''}${rr.r20.toFixed(1)}%`:''].filter(Boolean).join(' · ');
    return `<div class="market-row market-row--hotfix" data-market-ticker="${esc(s.ticker)}"><div><div class="market-row__title"><span class="market-row__ticker">${esc(s.ticker)}</span><span class="market-row__name">${esc(s.name||'')}</span></div><div class="market-row__description">${esc(desc)}</div><div class="market-row__meta">${esc(meta)}</div></div><div class="market-row__end"><div class="market-score ${scoreClass(os||0)}">${os==null?'—':Math.round(os)}</div></div></div>`;
  }

  function repairOpportunitySection(){
    const section=[...document.querySelectorAll('.market-section')].find(x=>t(x.querySelector('h3')?.textContent)==='Melhores oportunidades');
    if(!section)return;
    const list=section.querySelector('.market-list'); if(!list)return;
    const sector=sectorFilter(section); let rows=stocks.filter(eligible);
    if(sector!=='all')rows=rows.filter(s=>t(s?.sector)===sector);
    rows.sort((a,b)=>(opportunity(b)||0)-(opportunity(a)||0)||(timing(b)||0)-(timing(a)||0)); rows=rows.slice(0,20);
    if(!rows.length)return;
    const signature=rows.map(s=>`${t(s.ticker)}:${Math.round(opportunity(s)||0)}`).join('|')+`|${sector}`;
    if(list.dataset.vestraHotfix===VERSION&&list.dataset.vestraSignature===signature)return;
    list.innerHTML=rows.map(rowHTML).join(''); list.dataset.vestraHotfix=VERSION; list.dataset.vestraSignature=signature;
    const subtitle=section.querySelector('.market-section__head p'); if(subtitle)subtitle.textContent='Oportunidades emergentes · qualidade + momentum + recuperação + valuation, penalizando preço já esticado';
  }

  function repairDossierDescription(){
    const sheet=document.getElementById('marketSheet'); if(!sheet||sheet.hidden)return;
    const ticker=t(sheet.dataset.ticker).toUpperCase(); if(!ticker)return;
    const s=byTicker.get(ticker)||stocks.find(x=>t(x?.ticker).toUpperCase().split('.')[0]===ticker.split('.')[0]); if(!s)return;
    const head=sheet.querySelector('.market-detail-head'); const info=head?.querySelector('.market-detail-head > div:first-child'); if(!info)return;
    const desc=brief(s); let node=info.querySelector('.market-company-brief');
    if(!node){node=document.createElement('div');node.className='market-company-brief';const name=info.querySelector('.market-title-line + p')||info.querySelector('p');if(name)name.insertAdjacentElement('afterend',node);else info.appendChild(node);}
    if(node.dataset.ticker===ticker&&node.textContent===desc)return; node.textContent=desc; node.dataset.ticker=ticker;
  }

  function ptNumber(text){const raw=t(text);if(!/[0-9]/.test(raw))return null;const z=raw.replace(/\s/g,'').replace(/\./g,'').replace(',','.').replace(/[^0-9+\-.]/g,'');if(!z)return null;const x=Number(z);return Number.isFinite(x)?x:null;}
  function repairValuationMultiples(root=document){
    const labels=new Set(['P/E','Forward P/E','EV/EBITDA','PEG']);
    root.querySelectorAll('.market-metric,.market-kv,.market-detail-card,.market-stat').forEach(card=>{const label=t(card.querySelector('small,label,.market-kv__label')?.textContent);if(!labels.has(label))return;const value=card.querySelector('strong,.market-kv__value');if(!value)return;const x=ptNumber(value.textContent);if(x!=null&&x<=0&&t(value.textContent)!=='—')value.textContent='—';});
  }
  function repairLow52(root=document){
    root.querySelectorAll('[data-market-ticker]').forEach(row=>{const s=byTicker.get(t(row.dataset.marketTicker).toUpperCase());if(!s||t(s.low52_status)!=='insufficient')return;const meta=row.querySelector('.market-row__meta');if(!meta)return;const before=meta.textContent,after=before.replace(/Opportunity\s+50\/100\s*·?\s*/i,'Dados insuficientes para Opportunity Rank · ');if(after!==before)meta.textContent=after;});
  }

  function collapseState(){try{return JSON.parse(localStorage.getItem(COLLAPSE_KEY)||'{}')||{};}catch{return {};}}
  function saveCollapseState(x){try{localStorage.setItem(COLLAPSE_KEY,JSON.stringify(x||{}));}catch{}}
  function collapseKey(card,i){
    const title=t(card.querySelector('.market-perspective-head h4')?.textContent||card.querySelector(':scope > h4')?.textContent||card.querySelector('h4')?.textContent||`section-${i}`);
    return title.toLowerCase().replace(/[^a-z0-9À-ÿ]+/gi,'-').replace(/^-|-$/g,'').slice(0,80)||`section-${i}`;
  }
  function setCollapsed(card,collapsed){
    card.classList.toggle('is-collapsed',collapsed); const b=card.querySelector(':scope > .market-collapse-toggle'); if(b){b.textContent=collapsed?'＋':'−';b.setAttribute('aria-label',collapsed?'Abrir secção':'Fechar secção');b.title=collapsed?'Abrir secção':'Fechar secção';}
  }
  function installPortfolioCollapsibles(){
    const sheet=document.getElementById('marketSheet'); if(!sheet||sheet.hidden||t(sheet.dataset.tool)!=='portfolio')return;
    const content=document.getElementById('marketSheetContent'); if(!content)return;
    const state=collapseState();
    const cards=[...content.querySelectorAll('.market-detail-card')];
    cards.forEach((card,i)=>{
      if(card.classList.contains('market-decision-center'))return;
      if(card.dataset.collapsible==='1')return;
      card.dataset.collapsible='1'; const key=collapseKey(card,i); card.dataset.collapseKey=key;
      const btn=document.createElement('button'); btn.type='button'; btn.className='market-collapse-toggle'; btn.dataset.collapseToggle=key;
      card.appendChild(btn);
      const defaultClosed=i>1 || card.classList.contains('market-research-queue');
      setCollapsed(card,state[key]===undefined?defaultClosed:!!state[key]);
    });
    if(!content.querySelector('.market-collapse-toolbar')){
      const center=content.querySelector('.market-decision-center');
      const bar=document.createElement('div'); bar.className='market-collapse-toolbar'; bar.innerHTML='<span>Secções</span><button type="button" data-collapse-all="open">Abrir tudo</button><button type="button" data-collapse-all="close">Fechar tudo</button>';
      if(center)center.insertAdjacentElement('afterend',bar); else content.prepend(bar);
    }
  }

  function addStyle(){
    if(document.getElementById('vestra-market-hotfix-v450'))return;
    const st=document.createElement('style'); st.id='vestra-market-hotfix-v450';
    st.textContent='.market-row__description{font-size:11px;line-height:1.4;color:var(--text2,#62757c);margin-top:5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;max-width:560px}.market-row--hotfix .market-row__meta{margin-top:4px}.market-company-brief{font-size:12px;line-height:1.45;color:var(--text2,#62757c);margin-top:5px;max-width:520px;display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}.market-detail-card[data-collapsible="1"]{position:relative;padding-top:18px}.market-collapse-toggle{position:absolute;right:12px;top:11px;width:32px;height:32px;border-radius:11px;border:1px solid var(--line);background:var(--soft);color:var(--text);font-size:20px;line-height:1;z-index:2}.market-detail-card.is-collapsed>:not(.market-perspective-head):not(h4):not(.market-collapse-toggle){display:none!important}.market-detail-card.is-collapsed{padding-bottom:16px}.market-detail-card.is-collapsed>.market-perspective-head{margin-bottom:0;padding-right:38px}.market-detail-card.is-collapsed>h4{margin:0;padding-right:42px}.market-collapse-toolbar{display:flex;align-items:center;gap:8px;margin:10px 0 14px;padding:10px 12px;border:1px solid var(--line);border-radius:16px;background:var(--card)}.market-collapse-toolbar span{font-size:11px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:var(--text2);margin-right:auto}.market-collapse-toolbar button{border:1px solid var(--line);background:var(--soft);color:var(--text);border-radius:10px;padding:7px 10px;font-size:11px;font-weight:700}';
    document.head.appendChild(st);
  }
  function apply(){repairOpportunitySection();repairDossierDescription();repairValuationMultiples();repairLow52();installPortfolioCollapsibles();}

  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-collapse-toggle]'); if(b){e.preventDefault();e.stopPropagation();const card=b.closest('.market-detail-card');if(!card)return;const next=!card.classList.contains('is-collapsed');setCollapsed(card,next);const st=collapseState();st[card.dataset.collapseKey]=next;saveCollapseState(st);return;}
    const all=e.target.closest?.('[data-collapse-all]'); if(all){e.preventDefault();e.stopPropagation();const close=all.dataset.collapseAll==='close';const st=collapseState();document.querySelectorAll('#marketSheetContent .market-detail-card[data-collapsible="1"]').forEach(card=>{setCollapsed(card,close);st[card.dataset.collapseKey]=close;});saveCollapseState(st);return;}
  });

  function start(){
    addStyle(); load().then(()=>{apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
