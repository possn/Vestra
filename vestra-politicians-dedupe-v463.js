/* Vestra Politicians v4.63 — remove duplicate recent-flow summaries. */
(() => {
  'use strict';
  function apply(){
    document.querySelectorAll('.politicians-section').forEach(section=>{
      const canonical=section.querySelector('.ux454-flow');
      const duplicate=section.querySelector('.ux458-politician-leaders');
      if(canonical&&duplicate) duplicate.remove();
      // v4.58 may recreate the leaders card via its observer; mark the section so CSS
      // suppresses any later recreation while the richer Political Flow is present.
      section.classList.toggle('ux463-has-canonical-flow',!!canonical);
    });
  }
  function style(){
    if(document.getElementById('vestra-v463-style')) return;
    const s=document.createElement('style');s.id='vestra-v463-style';
    s.textContent='.politicians-section.ux463-has-canonical-flow .ux458-politician-leaders{display:none!important}';
    document.head.appendChild(s);
  }
  function start(){
    style();apply();let pending=false;
    const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});
    mo.observe(document.body,{childList:true,subtree:true});
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
