/* Vestra Portfolio UX v4.79 — canonical analysis tabs: Prioridades / Monitorizar / Otimizar. */
(() => {
  'use strict';

  const GROUPS = [
    {id:'decide', label:'Prioridades', title:'Prioridades', sub:'Research, reforços e posições que merecem atenção.', kinds:['research','priority','reinforce','review']},
    {id:'monitor', label:'Monitorizar', title:'Monitorizar', sub:'Saúde, objetivos, concentração e resistência da carteira.', kinds:['target','history','risk','stress']},
    {id:'optimize', label:'Otimizar', title:'Otimizar', sub:'Trocas, alternativas, overlap e impacto antes de mexer.', kinds:['swap','scenario','overlap','map']}
  ];

  const t = v => String(v ?? '').trim();
  let active = 'decide';

  function root(){
    const sh=document.getElementById('marketSheet');
    const c=document.getElementById('marketSheetContent');
    return (!sh || sh.hidden || t(sh.dataset.tool)!=='portfolio' || !c) ? null : c;
  }

  function groupForCard(card){
    if(!card) return null;
    const tagged=t(card.dataset.ux455Group || card.dataset.ux454GroupCard);
    if(tagged) return tagged;
    const kind=t(card.dataset.uxKind);
    return GROUPS.find(g=>g.kinds.includes(kind))?.id || null;
  }

  function collapseCard(card){
    if(!card || card.classList.contains('is-collapsed')) return;
    const btn=card.querySelector(':scope > [data-collapse-toggle], :scope > .market-collapse-toggle');
    if(btn) btn.click();
  }

  function ensureTabs(c){
    let shell=c.querySelector('.v479-portfolio-tabs');
    if(shell) return shell;

    shell=document.createElement('section');
    shell.className='v479-portfolio-tabs';
    shell.innerHTML=`
      <div class="v479-tabs" role="tablist" aria-label="Análise da carteira">
        ${GROUPS.map(g=>`<button type="button" role="tab" data-v479-tab="${g.id}" aria-selected="false">${g.label}</button>`).join('')}
      </div>
      <div class="v479-tab-intro"><strong></strong><span></span></div>`;

    const explore=[...c.querySelectorAll('*')].find(x=>x.children.length<8 && /Explorar a carteira/i.test(t(x.textContent)));
    const anchor=explore?.closest('.market-detail-card,.portfolio-explore,.market-card') || c.querySelector('.ux454-nav-title') || c.querySelector('.market-collapse-toolbar');
    if(anchor) anchor.insertAdjacentElement('afterend',shell);
    else c.prepend(shell);
    return shell;
  }

  function hideLegacyNav(c){
    c.querySelectorAll('.ux455-group-label,.ux454-group-label').forEach(x=>x.style.display='none');
    c.querySelectorAll('.ux-portfolio-shortcuts,.ux453-focusbar,.market-collapse-toolbar,.ux454-nav-title').forEach(x=>{
      if(!x.closest('.v479-portfolio-tabs')) x.classList.add('v479-legacy-nav-hidden');
    });
  }

  function applyGroup(c, id, collapse=true){
    if(!GROUPS.some(g=>g.id===id)) id='decide';
    active=id;
    try{localStorage.setItem('vestra.portfolio.analysisTab',id);}catch{}

    const shell=ensureTabs(c);
    const meta=GROUPS.find(g=>g.id===id);
    shell.querySelectorAll('[data-v479-tab]').forEach(b=>{
      const on=b.dataset.v479Tab===id;
      b.classList.toggle('is-active',on);
      b.setAttribute('aria-selected',on?'true':'false');
    });
    shell.querySelector('.v479-tab-intro strong').textContent=meta.title;
    shell.querySelector('.v479-tab-intro span').textContent=meta.sub;

    c.querySelectorAll('[data-ux-kind]').forEach(card=>{
      const group=groupForCard(card);
      if(!group) return;
      const visible=group===id;
      card.classList.toggle('v479-group-hidden',!visible);
      if(visible){
        card.dataset.v479Group=id;
        if(collapse) collapseCard(card);
      }
    });
  }

  function style(){
    if(document.getElementById('vestra-portfolio-v479-style')) return;
    const s=document.createElement('style');
    s.id='vestra-portfolio-v479-style';
    s.textContent=`
      #marketSheetContent .v479-legacy-nav-hidden{display:none!important}
      #marketSheetContent .v479-group-hidden{display:none!important}
      .v479-portfolio-tabs{margin:12px 0 14px;padding:10px;border:1px solid var(--line);border-radius:20px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent,#168e89) 5%,var(--card)),var(--card));box-shadow:0 6px 20px rgba(17,50,56,.04)}
      .v479-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:7px}
      .v479-tabs button{appearance:none;border:1px solid var(--line);background:var(--card);color:var(--text);min-height:46px;border-radius:14px;font-weight:850;font-size:12px;padding:9px 7px}
      .v479-tabs button.is-active{background:var(--accent,#168e89);color:#fff;border-color:transparent;box-shadow:0 7px 16px color-mix(in srgb,var(--accent,#168e89) 20%,transparent)}
      .v479-tab-intro{display:grid;gap:2px;padding:11px 5px 2px}.v479-tab-intro strong{font-size:17px;letter-spacing:-.02em}.v479-tab-intro span{font-size:10px;line-height:1.4;color:var(--text2)}
      #marketSheetContent [data-v479-group]{margin-top:10px!important}
      #marketSheetContent [data-v479-group].is-collapsed{min-height:80px!important}
      @media(max-width:620px){.v479-portfolio-tabs{padding:8px}.v479-tabs{gap:5px}.v479-tabs button{font-size:10.5px;min-height:44px;padding:7px 4px}.v479-tab-intro strong{font-size:16px}}
    `;
    document.head.appendChild(s);
  }

  function apply(){
    const c=root(); if(!c) return;
    style();
    const shell=ensureTabs(c);
    hideLegacyNav(c);
    let saved=''; try{saved=localStorage.getItem('vestra.portfolio.analysisTab')||'';}catch{}
    const target=GROUPS.some(g=>g.id===saved)?saved:active;
    applyGroup(c,target,false);
  }

  function start(){
    apply();
    let pending=false;
    const mo=new MutationObserver(()=>{
      if(pending) return;
      pending=true;
      requestAnimationFrame(()=>{pending=false;apply();});
    });
    mo.observe(document.body,{childList:true,subtree:true});
  }

  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-v479-tab]');
    if(!b) return;
    const c=root(); if(!c) return;
    e.preventDefault();
    applyGroup(c,b.dataset.v479Tab,true);
    setTimeout(()=>c.querySelector('.v479-portfolio-tabs')?.scrollIntoView({behavior:'smooth',block:'start'}),20);
  });

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true});
  else start();
})();
