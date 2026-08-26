/* Vestra Market Close Controller v1.0 — one close control, one navigation rule. */
(() => {
  'use strict';
  let pending=false;

  const sheet=()=>document.getElementById('marketSheet');
  const content=()=>document.getElementById('marketSheetContent');

  function closePortfolioToMarket(){
    const sh=sheet();
    if(!sh || sh.hidden || sh.dataset.tool!=='portfolio' || sh.dataset.ticker) return false;
    sh.hidden=true;
    sh.setAttribute('aria-hidden','true');
    sh.dataset.liveReady='0';
    sh.dataset.tool='';
    sh.dataset.returnView='';
    document.documentElement.classList.remove('modal-open');
    document.body.classList.remove('modal-open');
    sh.scrollTop=0; sh.scrollLeft=0;
    document.querySelectorAll('[data-view]').forEach(el=>{
      if(el.dataset.view==='market') el.classList.add('is-active');
      else if(el.dataset.view==='assets') el.classList.remove('is-active');
    });
    return true;
  }

  function normalize(){
    const sh=sheet(), c=content(); if(!sh||!c)return;
    const persistent=sh.querySelector(':scope > [data-market-close].market-close-persistent');
    if(persistent){ persistent.hidden=false; persistent.setAttribute('aria-label','Fechar'); }
    // Header close buttons are redundant when the persistent sheet control exists.
    c.querySelectorAll('.market-detail-head [data-market-close]').forEach(btn=>{
      btn.setAttribute('aria-hidden','true');
      btn.tabIndex=-1;
    });
  }

  function style(){
    if(document.getElementById('vestra-market-close-controller-style'))return;
    const s=document.createElement('style'); s.id='vestra-market-close-controller-style';
    s.textContent='#marketSheet:not([hidden]) #marketSheetContent .market-detail-head [data-market-close]{display:none!important}';
    document.head.appendChild(s);
  }

  document.addEventListener('click',e=>{
    const close=e.target.closest?.('[data-market-close]'); if(!close)return;
    const sh=sheet();
    if(!sh || sh.hidden || sh.dataset.tool!=='portfolio' || sh.dataset.ticker) return;
    e.preventDefault(); e.stopPropagation(); e.stopImmediatePropagation();
    closePortfolioToMarket();
  },true);

  function start(){
    style(); normalize();
    const mo=new MutationObserver(()=>{
      if(pending)return; pending=true;
      requestAnimationFrame(()=>{pending=false;normalize();});
    });
    mo.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden','class']});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
})();
