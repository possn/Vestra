/* Vestra Portfolio Focus v1.2 — compact portfolio badges only. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();

  // Compatibility surface for older callers. The canonical Portfolio UI owns
  // visibility now, so legacy focus mode is permanently neutral.
  function focusMode(){ return 'all'; }
  function setFocus(){ const c=document.getElementById('marketSheetContent'); if(c)c.dataset.uxFocus='all'; }

  function portfolioFocus(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)return;
    c.dataset.uxFocus='all';
    c.querySelector('.ux453-focusbar')?.remove();
    const swap=c.querySelector('[data-ux-kind="swap"]');if(swap&&!swap.querySelector('.ux453-badge'))swap.insertAdjacentHTML('afterbegin','<span class="ux453-badge is-purple">⇄ TROCAS INTELIGENTES</span>');
    const overlap=c.querySelector('[data-ux-kind="overlap"]');if(overlap&&!overlap.querySelector('.ux453-badge'))overlap.insertAdjacentHTML('afterbegin','<span class="ux453-badge is-amber">◉ DUPLICAÇÃO DE EXPOSIÇÃO</span>');
    const reinforce=c.querySelector('[data-ux-kind="reinforce"]');if(reinforce&&!reinforce.querySelector('.ux453-badge'))reinforce.insertAdjacentHTML('afterbegin','<span class="ux453-badge is-green">↗ CAPITAL NOVO</span>');
  }

  function style(){
    if(document.getElementById('vestra-portfolio-focus-style'))return;
    const link=document.createElement('link');
    link.id='vestra-portfolio-focus-style';
    link.rel='stylesheet';
    link.href='vestra-portfolio-focus.css?v=1.1';
    document.head.appendChild(link);
  }

  function start(){style();portfolioFocus();}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  window.VestraPortfolioFocus=Object.freeze({refresh:portfolioFocus,setFocus,focusMode,version:'1.2'});
})();
