/* Vestra UX v4.57 — dedupe portfolio section hierarchy. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();

  function root(){
    const sh=document.getElementById('marketSheet');
    const c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }

  function cleanup(){
    const c=root();
    if(!c)return;

    // v4.54 and v4.55 can both create semantic group headings. v4.55 is the
    // canonical hierarchy now, so remove the older labels whenever they reappear.
    c.querySelectorAll('.ux454-group-label').forEach(x=>x.remove());

    // Defensive dedupe in case a rerender produced the same v4.55 label twice.
    const seen=new Set();
    c.querySelectorAll('.ux455-group-label').forEach(x=>{
      const key=t(x.dataset.ux455Group)||t(x.textContent).toLowerCase();
      if(seen.has(key)) x.remove(); else seen.add(key);
    });

    // Keep only one navigation heading/surface.
    const navs=[...c.querySelectorAll('.ux454-nav-title')];
    navs.slice(1).forEach(x=>x.remove());
    const toolbars=[...c.querySelectorAll('.market-collapse-toolbar')];
    toolbars.slice(1).forEach(x=>x.remove());
    const focus=[...c.querySelectorAll('.ux453-focusbar')];
    focus.slice(1).forEach(x=>x.remove());
    const shortcuts=[...c.querySelectorAll('.ux-portfolio-shortcuts')];
    shortcuts.slice(1).forEach(x=>x.remove());
  }

  function style(){
    if(document.getElementById('vestra-ux-v457-style'))return;
    const s=document.createElement('style');
    s.id='vestra-ux-v457-style';
    // Hide legacy labels even in the brief interval before cleanup runs.
    s.textContent=`#marketSheetContent.ux454-portfolio .ux454-group-label{display:none!important}.ux455-group-label+.ux455-group-label{margin-top:0}`;
    document.head.appendChild(s);
  }

  function start(){
    style();cleanup();
    let pending=false;
    const mo=new MutationObserver(()=>{
      if(pending)return;
      pending=true;
      requestAnimationFrame(()=>{pending=false;cleanup();});
    });
    mo.observe(document.body,{childList:true,subtree:true});
  }

  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
