/* Vestra Portfolio Navigation Fix v4.64 — keep view controls with navigation, never stranded in content. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  function root(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }
  function clean(){
    const c=root(); if(!c)return;
    const reveal=c.querySelector('.ux461-reveal');
    const toolbar=[...c.querySelectorAll('.market-collapse-toolbar')];
    const shortcuts=[...c.querySelectorAll('.ux-portfolio-shortcuts')];
    const focusbars=[...c.querySelectorAll('.ux453-focusbar')];

    // Keep only one canonical instance of each navigation control.
    toolbar.slice(1).forEach(x=>x.remove());
    shortcuts.slice(1).forEach(x=>x.remove());
    focusbars.slice(1).forEach(x=>x.remove());

    const tb=toolbar[0], sc=shortcuts[0], fb=focusbars[0];
    if(!reveal)return;

    // Detailed navigation must live immediately below "Explorar a carteira".
    // Order: sections toolbar -> shortcuts -> view selector.
    let anchor=reveal;
    [tb,sc,fb].filter(Boolean).forEach(el=>{
      if(anchor.nextElementSibling!==el) anchor.insertAdjacentElement('afterend',el);
      anchor=el;
    });

    // Respect v4.61 collapsed/expanded state even if older observers recreate controls.
    const expanded=c.dataset.ux461Expanded==='1';
    [tb,sc,fb].filter(Boolean).forEach(el=>{el.hidden=!expanded;el.classList.add('ux461-secondary-nav');});
  }
  function style(){
    if(document.getElementById('vestra-v464-style'))return;
    const s=document.createElement('style');s.id='vestra-v464-style';s.textContent=`
      .ux461-reveal + .market-collapse-toolbar{margin-top:8px!important}
      .ux461-reveal ~ .ux-portfolio-shortcuts{margin-top:7px!important}
      .ux461-reveal ~ .ux453-focusbar{margin-top:7px!important;margin-bottom:12px!important}
      .ux461-secondary-nav[hidden]{display:none!important}
    `;document.head.appendChild(s);
  }
  function loadPortfolioTabs(){
    if(document.querySelector('script[data-vestra-portfolio-tabs-v479]'))return;
    const s=document.createElement('script');
    s.src='./vestra-portfolio-tabs-v479.js?v=4.79';
    s.defer=true;
    s.dataset.vestraPortfolioTabsV479='1';
    document.head.appendChild(s);
  }
  function start(){style();clean();loadPortfolioTabs();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;clean();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
