/* Vestra Market Close Cleanup v4.71 — one canonical close button per market sheet. */
(() => {
  'use strict';

  function installStyle(){
    if(document.getElementById('vestra-v471-close-style')) return;
    const s=document.createElement('style');
    s.id='vestra-v471-close-style';
    s.textContent=`
      /* The sheet already owns a persistent close button. Header-level close buttons
         duplicate it visually, especially on iPhone. Keep the persistent control only. */
      #marketSheet:not([hidden]) #marketSheetContent .market-detail-head [data-market-close]{display:none!important}
    `;
    document.head.appendChild(s);
  }

  function normalize(){
    const sh=document.getElementById('marketSheet');
    if(!sh) return;
    const persistent=sh.querySelector(':scope > [data-market-close].market-close-persistent');
    if(persistent){
      persistent.hidden=false;
      persistent.setAttribute('aria-label','Fechar');
    }
  }

  function start(){
    installStyle(); normalize();
    let pending=false;
    const mo=new MutationObserver(()=>{
      if(pending) return;
      pending=true;
      requestAnimationFrame(()=>{pending=false;normalize();});
    });
    mo.observe(document.body,{childList:true,subtree:true,attributes:true,attributeFilter:['hidden','class']});
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
