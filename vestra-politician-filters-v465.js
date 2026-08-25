/* Vestra Politician Filters v4.65 — explicit, persistent buy/sell filtering. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  let currentView='all';

  function section(){return document.querySelector('.politicians-section');}
  function controls(sec=section()){return sec?.querySelector('.ux-politician-controls')||null;}
  function tradeKind(el){
    const em=el?.querySelector('em');
    if(em?.classList.contains('is-buy'))return 'buy';
    if(em?.classList.contains('is-sell'))return 'sell';
    const s=t(em?.textContent).toLowerCase();
    if(/compra|purchase|buy/.test(s))return 'buy';
    if(/venda|sale|sell/.test(s))return 'sell';
    return 'other';
  }
  function sideKind(el){
    const h=t(el?.querySelector('.politician-side-head')?.textContent).toLowerCase();
    if(/compra|purchase|buy/.test(h))return 'buy';
    if(/venda|sale|sell/.test(h))return 'sell';
    return 'other';
  }
  function visibleCount(sec,view){
    if(view==='all')return sec.querySelectorAll('.politician-trade').length;
    return [...sec.querySelectorAll('.politician-trade')].filter(x=>tradeKind(x)===view).length;
  }
  function label(view){return view==='buy'?'Compras':view==='sell'?'Vendas':'Todas as operações';}

  function ensureStatus(sec){
    const ctl=controls(sec);if(!ctl)return null;
    let st=sec.querySelector('.ux465-filter-status');
    if(!st){
      st=document.createElement('div');st.className='ux465-filter-status';
      ctl.insertAdjacentElement('afterend',st);
    }
    return st;
  }
  function normalizeButtons(sec){
    const ctl=controls(sec);if(!ctl)return;
    const all=ctl.querySelector('[data-ux-politician-view="all"]');
    const buy=ctl.querySelector('[data-ux-politician-view="buy"]');
    const sell=ctl.querySelector('[data-ux-politician-view="sell"]');
    if(all)all.textContent='Ver tudo';
    if(buy)buy.textContent='↗ Só compras';
    if(sell)sell.textContent='↘ Só vendas';
    const fav=ctl.querySelector('[data-ux-politician-fav]');if(fav&&/Favorito/.test(fav.textContent))fav.textContent=fav.classList.contains('is-fav')?'★ A seguir':'☆ Seguir';
  }
  function apply(sec=section(),view=currentView){
    if(!sec)return;
    currentView=['all','buy','sell'].includes(view)?view:'all';
    sec.dataset.uxPoliticianView=currentView;
    normalizeButtons(sec);
    const ctl=controls(sec);
    ctl?.querySelectorAll('[data-ux-politician-view]').forEach(b=>b.classList.toggle('is-active',b.dataset.uxPoliticianView===currentView));

    sec.querySelectorAll('.politician-sides > section').forEach(x=>{
      const k=sideKind(x);x.hidden=currentView!=='all'&&k!==currentView;
      x.style.display=x.hidden?'none':'';
    });
    sec.querySelectorAll('.politician-trade').forEach(x=>{
      const k=tradeKind(x);x.hidden=currentView!=='all'&&k!==currentView;
      x.style.display=x.hidden?'none':'';
    });

    const allCard=sec.querySelector('.politician-all');
    if(allCard)allCard.dataset.filter=currentView;
    const count=visibleCount(sec,currentView);
    const st=ensureStatus(sec);
    if(st){
      st.className=`ux465-filter-status is-${currentView}`;
      st.innerHTML=`<span>${currentView==='buy'?'↗':currentView==='sell'?'↘':'◎'}</span><div><small>A MOSTRAR</small><strong>${label(currentView)}</strong><em>${count?`${count} operações visíveis`:'sem operações identificadas neste resumo'}</em></div>`;
    }
  }

  function style(){
    if(document.getElementById('vestra-politician-filters-v465-style'))return;
    const s=document.createElement('style');s.id='vestra-politician-filters-v465-style';s.textContent=`
      .ux-politician-controls{margin-top:-5px!important}.ux-politician-controls button{transition:background .15s ease,color .15s ease,border-color .15s ease,transform .15s ease}.ux-politician-controls button:active{transform:scale(.97)}
      .ux465-filter-status{display:flex;align-items:center;gap:9px;margin:-4px 0 12px;padding:9px 11px;border-radius:13px;background:var(--soft);border:1px solid var(--line)}.ux465-filter-status>span{font-size:18px}.ux465-filter-status>div{display:grid;gap:0}.ux465-filter-status small{font-size:7.5px;letter-spacing:.11em;font-weight:900;color:var(--text2)}.ux465-filter-status strong{font-size:11px}.ux465-filter-status em{font-size:8.5px;font-style:normal;color:var(--text2)}.ux465-filter-status.is-buy{background:rgba(33,178,143,.08)}.ux465-filter-status.is-sell{background:rgba(217,93,114,.08)}
      .politician-sides>section[hidden],.politician-trade[hidden]{display:none!important}
    `;document.head.appendChild(s);
  }

  document.addEventListener('click',e=>{
    const b=e.target.closest?.('.politicians-section [data-ux-politician-view]');if(!b)return;
    e.preventDefault();e.stopPropagation();
    apply(b.closest('.politicians-section'),b.dataset.uxPoliticianView);
  },true);

  document.addEventListener('change',e=>{
    if(!e.target.matches?.('[data-politician-select]'))return;
    currentView='all';
    setTimeout(()=>apply(section(),'all'),80);
  },true);

  function start(){style();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;const sec=section();if(sec)apply(sec,currentView);});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
