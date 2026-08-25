/* Vestra Portfolio Overview v4.62 — keep legacy Decision Pulse out of the detailed flow. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  function root(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }
  function apply(){
    const c=root(); if(!c) return;
    c.classList.add('ux462-portfolio');
    // v4.58 can recreate Decision Pulse after later DOM moves. It is now redundant
    // with the v4.60/v4.61 global overview, so keep every instance suppressed.
    c.querySelectorAll('.ux458-pulse').forEach(x=>{x.hidden=true;x.setAttribute('aria-hidden','true');});
  }
  function style(){
    if(document.getElementById('vestra-v462-style')) return;
    const s=document.createElement('style');s.id='vestra-v462-style';
    s.textContent=`#marketSheetContent.ux462-portfolio .ux458-pulse{display:none!important}`;
    document.head.appendChild(s);
  }
  function start(){style();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
