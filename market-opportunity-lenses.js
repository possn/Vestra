/* Vestra Market Opportunity Lenses v1.4 — robust touch/click filtering, index-only. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  let activeLens='all';

  function section(){
    return [...document.querySelectorAll('.market-section')].find(x=>/Oportunidades agora|Melhores oportunidades/.test(t(x.querySelector('h3')?.textContent)))||null;
  }
  function rowStock(row){
    const tk=t(row?.dataset?.marketTicker).toUpperCase();
    if(!tk) return null;
    return row.__vestraStock || null;
  }
  function low52Above(s){
    const direct=n(s?.low52_above_low_pct);
    if(direct!=null) return direct;
    const current=n(s?.current_price), low=n(s?.low52_price_low)??n(s?.fifty_two_week_low);
    return current!=null&&current>0&&low!=null&&low>0?(current/low-1)*100:null;
  }
  function lensMatch(row, lens){
    if(lens==='all') return true;
    const s=rowStock(row);
    const text=t(row.textContent).toLowerCase();
    if(s){
      const est=t(s.estimate_signal), rec=t(s.recovery_status), val=t(s.valuation_signal);
      const opp=n(s.opportunity_timing_score), fv=n(s.fair_value_upside_pct), pt=n(s.analyst_price_target_upside_pct);
      if(lens==='low52'){
        const above=low52Above(s);
        return above!=null&&above>=-0.5&&above<=5;
      }
      if(lens==='emerging') return (opp!=null&&opp>=65)||/timing|momentum|a começar|emerg/.test(text);
      if(lens==='recovery') return ['confirmed','recovering'].includes(rec)||est==='improving'||/recuper|melhorar/.test(text);
      if(lens==='value') return ((fv!=null&&fv>=10)||(pt!=null&&pt>=12)||val==='undervalued')&&(opp==null||opp>=50);
    }
    if(lens==='low52') return false;
    if(lens==='emerging') return /timing|a começar|emerg/.test(text);
    if(lens==='recovery') return /recuper|melhorar/.test(text);
    if(lens==='value') return /underval|value|desconto|upside/.test(text);
    return true;
  }
  function syncButtons(bar){
    bar?.querySelectorAll('[data-vestra-lens]').forEach(button=>{
      const selected=button.dataset.vestraLens===activeLens;
      button.classList.toggle('is-active',selected);
      button.setAttribute('aria-pressed',selected?'true':'false');
    });
  }
  function setRowVisible(row, visible){
    row.hidden=!visible;
    row.classList.toggle('vestra-lens-hidden',!visible);
    if(visible){
      row.removeAttribute('data-vestra-lens-hidden');
      if(row.dataset.vestraLensDisplay==='hidden') row.style.removeProperty('display');
      delete row.dataset.vestraLensDisplay;
    }else{
      row.setAttribute('data-vestra-lens-hidden','1');
      row.dataset.vestraLensDisplay='hidden';
      row.style.setProperty('display','none','important');
    }
  }
  function apply(){
    const s=section(); if(!s) return;
    let bar=s.querySelector('.vestra-opportunity-lenses');
    if(!bar){
      bar=document.createElement('div');bar.className='vestra-opportunity-lenses';bar.setAttribute('role','group');bar.setAttribute('aria-label','Filtrar oportunidades');
      bar.innerHTML='<button type="button" data-vestra-lens="all" aria-pressed="true">Todos</button><button type="button" data-vestra-lens="low52" aria-pressed="false">Mínimos 52s</button><button type="button" data-vestra-lens="emerging" aria-pressed="false">A começar</button><button type="button" data-vestra-lens="recovery" aria-pressed="false">Recuperação</button><button type="button" data-vestra-lens="value" aria-pressed="false">Value + timing</button>';
      const guide=s.querySelector('.ux454-opportunity-guide');(guide||s.querySelector('.market-section__head'))?.insertAdjacentElement('afterend',bar);
    }
    syncButtons(bar);
    const rows=[...s.querySelectorAll('.market-list .market-row')]; let shown=0;
    rows.forEach(r=>{const ok=lensMatch(r,activeLens);setRowVisible(r,ok);if(ok)shown++;});
    let empty=s.querySelector('.vestra-lens-empty');
    if(!shown&&activeLens!=='all'){
      if(!empty){empty=document.createElement('div');empty.className='vestra-lens-empty';s.querySelector('.market-list')?.appendChild(empty);}
      empty.textContent=activeLens==='low52'?'Sem empresas até 5% do mínimo de 52 semanas.':'Sem candidatos fortes nesta lente neste momento.';
    }else empty?.remove();
  }
  function selectLens(button){
    const next=t(button?.dataset?.vestraLens)||'all';
    if(!['all','low52','emerging','recovery','value'].includes(next)) return;
    activeLens=next;
    apply();
  }
  function style(){
    if(document.getElementById('vestra-opportunity-lenses-style'))return;
    const s=document.createElement('style');s.id='vestra-opportunity-lenses-style';s.textContent=`
      .vestra-opportunity-lenses{position:relative;z-index:3;display:flex;gap:6px;overflow-x:auto;margin:0 0 10px;padding:2px 0 3px;scrollbar-width:none;pointer-events:auto;-webkit-overflow-scrolling:touch}
      .vestra-opportunity-lenses::-webkit-scrollbar{display:none}
      .vestra-opportunity-lenses button{position:relative;z-index:4;flex:0 0 auto;appearance:none;-webkit-appearance:none;border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:8px 11px;min-height:34px;font:inherit;font-size:9px;font-weight:850;color:var(--text2);cursor:pointer;pointer-events:auto;touch-action:manipulation;-webkit-tap-highlight-color:transparent}
      .vestra-opportunity-lenses button.is-active{background:var(--accent,#168e89);color:#fff;border-color:transparent}
      .ux454-opportunity-guide{pointer-events:none}
      .market-section .market-list .market-row.vestra-lens-hidden,
      .market-section .market-list .market-row[data-vestra-lens-hidden="1"]{display:none!important}
      .vestra-lens-empty{padding:18px;text-align:center;color:var(--text2);font-size:11px}
    `;document.head.appendChild(s);
  }
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-vestra-lens]');if(!b)return;
    e.preventDefault();e.stopPropagation();selectLens(b);
  });
  function start(){
    style();apply();
    let pending=false;
    new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});}).observe(document.body,{childList:true,subtree:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.VestraMarketOpportunityLenses=Object.freeze({apply,select:lens=>{activeLens=t(lens)||'all';apply();},get active(){return activeLens;},version:'1.4'});
})();
