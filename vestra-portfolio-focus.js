/* Vestra Portfolio Focus v1.0 — essential/all portfolio view only. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const FOCUS_KEY='vestra-portfolio-focus-v1';

  function focusMode(){try{return localStorage.getItem(FOCUS_KEY)||'focus'}catch{return'focus'}}
  function setFocus(mode){try{localStorage.setItem(FOCUS_KEY,mode)}catch{};const c=document.getElementById('marketSheetContent');if(c)c.dataset.uxFocus=mode;document.querySelectorAll('[data-ux-focus]').forEach(b=>b.classList.toggle('is-active',b.dataset.uxFocus===mode));}
  function portfolioFocus(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)return;
    c.dataset.uxFocus=focusMode();
    const toolbar=c.querySelector('.market-collapse-toolbar');if(toolbar&&!c.querySelector('.ux453-focusbar')){
      const b=document.createElement('div');b.className='ux453-focusbar';b.innerHTML='<span>Vista</span><button data-ux-focus="focus">Essencial</button><button data-ux-focus="all">Tudo</button><small>Mostra primeiro o que pede decisão.</small>';toolbar.insertAdjacentElement('afterend',b);
    }
    document.querySelectorAll('[data-ux-focus]').forEach(b=>b.classList.toggle('is-active',b.dataset.uxFocus===focusMode()));
    const swap=c.querySelector('[data-ux-kind="swap"]');if(swap&&!swap.querySelector('.ux453-badge'))swap.insertAdjacentHTML('afterbegin','<span class="ux453-badge is-purple">⇄ TROCAS INTELIGENTES</span>');
    const overlap=c.querySelector('[data-ux-kind="overlap"]');if(overlap&&!overlap.querySelector('.ux453-badge'))overlap.insertAdjacentHTML('afterbegin','<span class="ux453-badge is-amber">◉ DUPLICAÇÃO DE EXPOSIÇÃO</span>');
    const reinforce=c.querySelector('[data-ux-kind="reinforce"]');if(reinforce&&!reinforce.querySelector('.ux453-badge'))reinforce.insertAdjacentHTML('afterbegin','<span class="ux453-badge is-green">↗ CAPITAL NOVO</span>');
  }

  function style(){
    if(document.getElementById('vestra-portfolio-focus-style'))return;
    const link=document.createElement('link');
    link.id='vestra-portfolio-focus-style';
    link.rel='stylesheet';
    link.href='vestra-portfolio-focus.css?v=1.0';
    document.head.appendChild(link);
  }

  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-ux-focus]');if(!b)return;e.preventDefault();e.stopPropagation();setFocus(b.dataset.uxFocus);});
  function start(){style();portfolioFocus();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;portfolioFocus();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  window.VestraPortfolioFocus=Object.freeze({refresh:portfolioFocus,setFocus,focusMode});
})();
