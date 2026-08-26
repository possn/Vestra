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

  function style(){if(document.getElementById('vestra-portfolio-focus-style'))return;const s=document.createElement('style');s.id='vestra-portfolio-focus-style';s.textContent=`
  .ux453-focusbar{display:flex;align-items:center;gap:7px;margin:8px 0 12px;padding:9px 10px;border-radius:16px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent,#168e89) 8%,var(--card)),var(--card));border:1px solid var(--line)}.ux453-focusbar>span{font-size:10px;text-transform:uppercase;letter-spacing:.1em;font-weight:900;color:var(--text2)}.ux453-focusbar button{border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:7px 11px;font-size:11px;font-weight:800;color:var(--text)}.ux453-focusbar button.is-active{background:var(--accent,#168e89);color:white;border-color:transparent}.ux453-focusbar small{margin-left:auto;color:var(--text2);font-size:9px;max-width:130px;text-align:right}
  #marketSheetContent[data-ux-focus="focus"] [data-ux-kind="map"],#marketSheetContent[data-ux-focus="focus"] [data-ux-kind="scenario"],#marketSheetContent[data-ux-focus="focus"] [data-ux-kind="target"],#marketSheetContent[data-ux-focus="focus"] [data-ux-kind="history"]{display:none!important}
  .ux453-badge{display:inline-flex;font-size:8.5px;font-weight:900;letter-spacing:.1em;border-radius:999px;padding:4px 7px;margin-bottom:6px}.ux453-badge.is-purple{background:#eee8ff;color:#6651a8}.ux453-badge.is-amber{background:#fff0d7;color:#9a6819}.ux453-badge.is-green{background:#e0f6ed;color:#168a69}
  @media(max-width:620px){.ux453-focusbar small{display:none}}
  `;document.head.appendChild(s);}

  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-ux-focus]');if(!b)return;e.preventDefault();e.stopPropagation();setFocus(b.dataset.uxFocus);});
  function start(){style();portfolioFocus();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;portfolioFocus();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  window.VestraPortfolioFocus=Object.freeze({refresh:portfolioFocus,setFocus,focusMode});
})();
