/* Vestra Portfolio close navigation v4.69 — close portfolio analysis back to Market, never Assets. */
(() => {
  'use strict';

  const sheet=()=>document.getElementById('marketSheet');

  function closePortfolioToMarket(){
    const sh=sheet();
    if(!sh) return false;
    if(sh.hidden || sh.dataset.tool!=='portfolio' || sh.dataset.ticker) return false;

    sh.hidden=true;
    sh.setAttribute('aria-hidden','true');
    sh.dataset.liveReady='0';
    sh.dataset.tool='';
    sh.dataset.returnView='';
    document.documentElement.classList.remove('modal-open');
    document.body.classList.remove('modal-open');
    sh.scrollTop=0;
    sh.scrollLeft=0;

    // The Market page is already underneath this sheet. Do not call setView('assets').
    // Keep the bottom navigation visually on Mercado if another legacy handler changed it.
    document.querySelectorAll('[data-view]').forEach(el=>{
      if(el.dataset.view==='market') el.classList.add('is-active');
      else if(el.classList.contains('is-active') && el.dataset.view==='assets') el.classList.remove('is-active');
    });
    return true;
  }

  document.addEventListener('click',e=>{
    const close=e.target.closest?.('[data-market-close]');
    if(!close) return;
    const sh=sheet();
    if(!sh || sh.hidden || sh.dataset.tool!=='portfolio' || sh.dataset.ticker) return;
    e.preventDefault();
    e.stopPropagation();
    e.stopImmediatePropagation();
    closePortfolioToMarket();
  },true);
})();
