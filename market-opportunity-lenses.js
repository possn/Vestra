/* Vestra Market Opportunity Lenses v1.0 — lightweight, index-only. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};

  function section(){
    return [...document.querySelectorAll('.market-section')].find(x=>/Oportunidades agora|Melhores oportunidades/.test(t(x.querySelector('h3')?.textContent)))||null;
  }
  function rowStock(row){
    const tk=t(row?.dataset?.marketTicker).toUpperCase();
    if(!tk) return null;
    // market.js already exposes render rows from the lightweight index. We avoid
    // loading a second copy of the market universe here. Scalars needed by the
    // lenses are carried on the rendered row through the public ticker and can
    // be resolved through the current VestraMarket search/open layer when data
    // attributes have been enriched by later patches. If not available, use
    // text-only classification and never trigger stocks.json.
    return row.__vestraStock || null;
  }
  function lensMatch(row, lens){
    if(lens==='all') return true;
    const s=rowStock(row);
    const text=t(row.textContent).toLowerCase();
    if(s){
      const est=t(s.estimate_signal), rec=t(s.recovery_status), val=t(s.valuation_signal);
      const opp=n(s.opportunity_timing_score), fv=n(s.fair_value_upside_pct), pt=n(s.analyst_price_target_upside_pct);
      if(lens==='emerging') return (opp!=null&&opp>=65)||/timing|momentum|a começar|emerg/.test(text);
      if(lens==='recovery') return ['confirmed','recovering'].includes(rec)||est==='improving'||/recuper|melhorar/.test(text);
      if(lens==='value') return ((fv!=null&&fv>=10)||(pt!=null&&pt>=12)||val==='undervalued')&&(opp==null||opp>=50);
    }
    if(lens==='emerging') return /timing|a começar|emerg/.test(text);
    if(lens==='recovery') return /recuper|melhorar/.test(text);
    if(lens==='value') return /underval|value|desconto|upside/.test(text);
    return true;
  }
  function apply(){
    const s=section(); if(!s) return;
    let bar=s.querySelector('.vestra-opportunity-lenses');
    if(!bar){
      bar=document.createElement('div');bar.className='vestra-opportunity-lenses';
      bar.innerHTML='<button class="is-active" data-vestra-lens="all">Todos</button><button data-vestra-lens="emerging">A começar</button><button data-vestra-lens="recovery">Recuperação</button><button data-vestra-lens="value">Value + timing</button>';
      const guide=s.querySelector('.ux454-opportunity-guide');(guide||s.querySelector('.market-section__head'))?.insertAdjacentElement('afterend',bar);
    }
    const lens=t(bar.querySelector('.is-active')?.dataset.vestraLens)||'all';
    const rows=[...s.querySelectorAll('.market-list .market-row')]; let shown=0;
    rows.forEach(r=>{const ok=lensMatch(r,lens);r.hidden=!ok;if(ok)shown++;});
    let empty=s.querySelector('.vestra-lens-empty');
    if(!shown&&lens!=='all'){
      if(!empty){empty=document.createElement('div');empty.className='vestra-lens-empty';s.querySelector('.market-list')?.appendChild(empty);}
      empty.textContent='Sem candidatos fortes nesta lente neste momento.';
    }else empty?.remove();
  }
  function style(){if(document.getElementById('vestra-opportunity-lenses-style'))return;const s=document.createElement('style');s.id='vestra-opportunity-lenses-style';s.textContent='.vestra-opportunity-lenses{display:flex;gap:6px;overflow-x:auto;margin:0 0 10px;padding:1px 0 2px;scrollbar-width:none}.vestra-opportunity-lenses button{flex:0 0 auto;border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:7px 10px;font-size:9px;font-weight:850;color:var(--text2)}.vestra-opportunity-lenses button.is-active{background:var(--accent,#168e89);color:#fff;border-color:transparent}.vestra-lens-empty{padding:18px;text-align:center;color:var(--text2);font-size:11px}';document.head.appendChild(s);}
  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-vestra-lens]');if(!b)return;e.preventDefault();const bar=b.closest('.vestra-opportunity-lenses');bar?.querySelectorAll('button').forEach(x=>x.classList.toggle('is-active',x===b));apply();});
  function start(){style();apply();let pending=false;new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});}).observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
