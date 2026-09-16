/* Vestra Market Opportunity Lenses v2.7 — strategy controls over independent full-universe rankings. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const LENSES=new Set(['all','low52','emerging','recovery','value']);
  let activeLens='all';

  function section(){
    return [...document.querySelectorAll('.market-section')].find(x=>/Oportunidades agora|Melhores oportunidades|Mínimos 52 semanas|A começar|Recuperação|Value \+ timing/.test(t(x.querySelector('h3')?.textContent)))||null;
  }
  function ensureBar(s){
    let bar=s?.querySelector('.vestra-opportunity-lenses');
    if(bar)return bar;
    if(!s)return null;
    bar=document.createElement('div');bar.className='vestra-opportunity-lenses';bar.setAttribute('role','group');bar.setAttribute('aria-label','Filtrar oportunidades');
    bar.innerHTML='<button type="button" data-vestra-lens="all" aria-pressed="true">Todos</button><button type="button" data-vestra-lens="low52" aria-pressed="false">Mínimos 52s</button><button type="button" data-vestra-lens="emerging" aria-pressed="false">A começar</button><button type="button" data-vestra-lens="recovery" aria-pressed="false">Recuperação</button><button type="button" data-vestra-lens="value" aria-pressed="false">Value + timing</button>';
    const guide=s.querySelector('.ux454-opportunity-guide');(guide||s.querySelector('.market-section__head'))?.insertAdjacentElement('afterend',bar);
    return bar;
  }
  function syncButtons(bar){
    bar?.querySelectorAll('[data-vestra-lens]').forEach(button=>{
      const selected=button.dataset.vestraLens===activeLens;
      button.classList.toggle('is-active',selected);
      button.setAttribute('aria-pressed',selected?'true':'false');
    });
  }
  function emptyCopy(lens){
    if(lens==='low52')return 'Sem empresas robustas até 5% do mínimo de 52 semanas com os dados atuais.';
    if(lens==='emerging')return 'Sem setups iniciais com qualidade e timing suficientes neste momento.';
    if(lens==='recovery')return 'Sem recuperações suficientemente confirmadas neste momento.';
    if(lens==='value')return 'Sem candidatos com desconto/upside e timing mínimo neste momento.';
    return '';
  }
  function syncEmpty(s){
    const list=s?.querySelector('.market-list');if(!list)return;
    const rows=list.querySelectorAll('.market-row').length;
    let empty=list.querySelector('.vestra-lens-empty');
    if(!rows&&activeLens!=='all'){
      if(!empty){empty=document.createElement('div');empty.className='vestra-lens-empty';list.appendChild(empty);}
      empty.textContent=emptyCopy(activeLens);
    }else empty?.remove();
  }
  function syncMoreSectorVisual(){
    const s=section();if(!s)return;
    const select=s.querySelector('[data-market-sector-select]');
    const label=select?.closest?.('.market-sector-more');
    if(!label)return;
    const selected=t(select?.value);
    label.classList.toggle('is-active',Boolean(selected));
    const text=label.querySelector('span');if(text)text.textContent=selected||'Mais';
    delete label.dataset.marketSector;
    delete label.dataset.marketSectorRecall;
    if(select)select.style.pointerEvents='auto';
  }
  function withMoreSectorBridge(callback){
    const s=section();
    const select=s?.querySelector('[data-market-sector-select]');
    const label=select?.closest?.('.market-sector-more');
    const selected=t(select?.value);
    if(!label||!selected)return callback();
    label.dataset.marketSector=selected;
    try{return callback();}
    finally{delete label.dataset.marketSector;}
  }
  function refreshUi(){
    const s=section();if(!s)return;
    syncButtons(ensureBar(s));
    syncMoreSectorVisual();
    syncEmpty(s);
  }
  function selectLens(value){
    const next=t(value)||'all';if(!LENSES.has(next))return;
    activeLens=next;
    withMoreSectorBridge(()=>window.VestraMarketOpportunities?.selectLens?.(activeLens));
    requestAnimationFrame(refreshUi);
  }
  function refreshAfterSectorSelection(){
    requestAnimationFrame(()=>{
      syncMoreSectorVisual();
      withMoreSectorBridge(()=>window.VestraMarketOpportunities?.refresh?.(activeLens));
      refreshUi();
    });
  }
  function style(){
    if(document.getElementById('vestra-opportunity-lenses-style'))return;
    const link=document.createElement('link');
    link.id='vestra-opportunity-lenses-style';
    link.rel='stylesheet';
    link.href='market-opportunity-lenses.css?v=1.0';
    document.head.appendChild(link);
  }
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-vestra-lens]');
    if(b){e.preventDefault();e.stopPropagation();selectLens(b.dataset.vestraLens);return;}
    const sector=e.target.closest?.('[data-market-sector]');
    if(sector)refreshAfterSectorSelection();
  });
  document.addEventListener('change',e=>{
    if(e.target.matches?.('[data-market-sector-select]'))refreshAfterSectorSelection();
  });
  function start(){
    style();
    const canonical=window.VestraMarketOpportunities?.activeLens;if(LENSES.has(canonical))activeLens=canonical;
    refreshUi();
    let pending=false;
    new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;refreshUi();});}).observe(document.body,{childList:true,subtree:true});
    window.addEventListener('vestra:market-ready',refreshUi);
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.VestraMarketOpportunityLenses=Object.freeze({refresh:refreshUi,select:selectLens,get active(){return activeLens;},version:'2.7'});
})();