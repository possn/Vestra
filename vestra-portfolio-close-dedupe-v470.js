/* Vestra Portfolio Close Dedupe v4.70 — exactly one close control in portfolio sheet. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();

  function clean(){
    const sh=document.getElementById('marketSheet');
    const c=document.getElementById('marketSheetContent');
    if(!sh||sh.hidden||!c||t(sh.dataset.tool)!=='portfolio') return;

    const head=c.querySelector(':scope > .market-detail-head') || c.querySelector('.market-detail-head');
    if(!head) return;

    const closes=[...head.querySelectorAll('[data-market-close]')];
    if(closes.length<=1) return;

    // Keep the canonical close button that belongs to the current header.
    // Remove any extra control recreated by legacy portfolio observers/hotfixes.
    closes.slice(1).forEach(btn=>btn.remove());
  }

  function start(){
    clean();
    let pending=false;
    const mo=new MutationObserver(()=>{
      if(pending) return;
      pending=true;
      requestAnimationFrame(()=>{pending=false;clean();});
    });
    mo.observe(document.body,{childList:true,subtree:true});
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
