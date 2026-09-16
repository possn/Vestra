/* Vestra Market Opportunity Lenses v2.6 — strategy controls over independent full-universe rankings. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const LENSES=new Set(['all','low52','emerging','recovery','value']);
  let activeLens='all';
  let lastMoreSector='';

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
  function bridgeMoreSectorSelection(){
    const s=section();if(!s)return;
    const select=s.querySelector('[data-market-sector-select]');
    const label=select?.closest?.('.market-sector-more');
    if(!label)return;
    const selected=t(select?.value);
    if(selected){
      lastMoreSector=selected;
      select.style.pointerEvents='auto';
      delete label.dataset.marketSectorRecall;
      s.querySelectorAll('[data-market-sector].is-active').forEach(node=>{if(node!==label)node.classList.remove('is-active');});
      label.dataset.marketSector=selected;
      label.classList.add('is-active');
    }else{
      delete label.dataset.marketSector;
      label.classList.remove('is-active');
      if(lastMoreSector){
        label.dataset.marketSectorRecall=lastMoreSector;
        const text=label.querySelector('span');if(text)text.textContent=lastMoreSector;
        select.style.pointerEvents='none';
      }else{
        delete label.dataset.marketSectorRecall;
        select.style.pointerEvents='auto';
      }
    }
  }
  function clearMoreSectorSelectionForCanonicalClick(target){
    const s=section();if(!s)return;
    const sector=target?.closest?.('[data-market-sector]');
    if(!sector||sector.closest?.('.market-sector-more'))return;
    const select=s.querySelector('[data-market-sector-select]');
    const label=select?.closest?.('.market-sector-more');
    if(select&&t(select.value)){lastMoreSector=t(select.value);select.value='';}
    if(label){
      delete label.dataset.marketSector;
      label.classList.remove('is-active');
      if(lastMoreSector){label.dataset.marketSectorRecall=lastMoreSector;if(select)select.style.pointerEvents='none';}
    }
  }
  function recallMoreSectorSelection(target){
    const label=target?.closest?.('.market-sector-more');
    const select=label?.querySelector?.('[data-market-sector-select]');
    if(!select||t(select.value))return false;
    const recalled=t(label?.dataset.marketSectorRecall||lastMoreSector);
    if(!recalled||![...select.options].some(option=>t(option.value)===recalled))return false;
    select.value=recalled;
    select.dispatchEvent(new Event('change',{bubbles:true}));
    return true;
  }
  function refreshUi(){
    const s=section();if(!s)return;
    syncButtons(ensureBar(s));
    syncEmpty(s);
  }
  function selectLens(value){
    const next=t(value)||'all';if(!LENSES.has(next))return;
    activeLens=next;
    bridgeMoreSectorSelection();
    window.VestraMarketOpportunities?.selectLens?.(activeLens);
    requestAnimationFrame(refreshUi);
  }
  function refreshAfterSectorSelection(){
    requestAnimationFrame(()=>{
      bridgeMoreSectorSelection();
      window.VestraMarketOpportunities?.refresh?.(activeLens);
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
    const recall=e.target.closest?.('.market-sector-more[data-market-sector-recall]');
    if(recall&&!recall.classList.contains('is-active')){
      e.preventDefault();e.stopPropagation();
      if(recallMoreSectorSelection(recall))return;
    }
    const sector=e.target.closest?.('[data-market-sector]');
    if(sector){clearMoreSectorSelectionForCanonicalClick(sector);refreshAfterSectorSelection();}
  });
  document.addEventListener('change',e=>{
    if(e.target.matches?.('[data-market-sector-select]'))refreshAfterSectorSelection();
  });
  function start(){
    style();
    const canonical=window.VestraMarketOpportunities?.activeLens;if(LENSES.has(canonical))activeLens=canonical;
    bridgeMoreSectorSelection();
    refreshUi();
    let pending=false;
    new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;bridgeMoreSectorSelection();refreshUi();});}).observe(document.body,{childList:true,subtree:true});
    window.addEventListener('vestra:market-ready',()=>{bridgeMoreSectorSelection();refreshUi();});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
  window.VestraMarketOpportunityLenses=Object.freeze({refresh:refreshUi,select:selectLens,get active(){return activeLens;},version:'2.6'});
})();
