/* Vestra Portfolio Hierarchy v1.0 — canonical final hierarchy from UX 4.54/4.55/4.57. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};

  const ORDER=[
    {id:'decide',title:'Decidir agora',sub:'As ações que podem exigir atenção.',kinds:['research','priority','reinforce','review']},
    {id:'optimize',title:'Otimizar a carteira',sub:'Trocas, overlap e eficiência da alocação.',kinds:['swap','scenario','overlap','map']},
    {id:'monitor',title:'Monitorizar',sub:'Saúde, objetivos e resistência da carteira.',kinds:['target','history','risk','stress']}
  ];
  const PURPOSES={
    research:'Pendências de research',priority:'O que merece atenção',map:'Como está distribuída',reinforce:'Onde colocar capital novo',review:'O que reavaliar',
    overlap:'Exposição duplicada',swap:'Melhores substitutos',scenario:'Simular antes de trocar',target:'Fit com os teus objetivos',history:'Evolução da qualidade',risk:'Concentração e diversificação',stress:'Comportamento em quedas'
  };

  function root(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }
  function card(kind,c){return c.querySelector(`[data-ux-kind="${kind}"]`);}
  function makeLabel(g){
    const d=document.createElement('div');d.className='ux455-group-label';d.dataset.ux455Group=g.id;
    d.innerHTML=`<span>${g.title}</span><small>${g.sub}</small>`;return d;
  }

  function decorateBase(c){
    c.classList.add('ux454-portfolio');
    const toolbar=c.querySelector('.market-collapse-toolbar');
    const focus=c.querySelector('.ux453-focusbar');
    const shortcuts=c.querySelector('.ux-portfolio-shortcuts');
    if(toolbar)toolbar.classList.add('ux454-toolbar');
    if(focus)focus.classList.add('ux454-focus');
    if(shortcuts)shortcuts.classList.add('ux454-shortcuts');

    if(toolbar&&!c.querySelector('.ux454-nav-title')){
      const title=document.createElement('div');title.className='ux454-nav-title';
      title.innerHTML='<div><small>PORTFOLIO INTELLIGENCE</small><strong>Navegação rápida</strong></div><span>Escolhe o que queres analisar</span>';
      toolbar.insertAdjacentElement('beforebegin',title);
    }

    c.querySelectorAll('[data-ux-kind]').forEach(x=>{
      const kind=x.dataset.uxKind;
      if(!kind||x.querySelector(':scope > .ux454-purpose'))return;
      const p=document.createElement('div');p.className='ux454-purpose';p.textContent=PURPOSES[kind]||'';x.appendChild(p);
    });

    const swap=card('swap',c);
    if(swap&&!swap.querySelector('.ux454-swap-head')){
      const h=document.createElement('div');h.className='ux454-swap-head';
      h.innerHTML='<div><small>SWAP LAB</small><strong>Trocar só quando melhora a carteira</strong><span>Compara qualidade, valuation, momentum e impacto na concentração.</span></div><button type="button" data-ux454-open-swap>Comparar →</button>';
      swap.prepend(h);
    }
    const overlap=card('overlap',c);
    if(overlap&&!overlap.querySelector('.ux454-overlap-head')){
      const h=document.createElement('div');h.className='ux454-overlap-head';h.innerHTML='<small>EXPOSURE MAP</small><strong>Onde estás a comprar a mesma coisa duas vezes?</strong>';overlap.prepend(h);
    }
  }

  function hierarchyIsCurrent(c){
    const labels=[...c.querySelectorAll(':scope > .ux455-group-label')];
    if(labels.length!==ORDER.length)return false;
    return ORDER.every((g,i)=>t(labels[i]?.dataset.ux455Group)===g.id);
  }
  function repairHierarchy(c){
    const anchor=c.querySelector('.ux-portfolio-shortcuts')||c.querySelector('.ux453-focusbar')||c.querySelector('.market-collapse-toolbar');
    if(!anchor)return;
    if(hierarchyIsCurrent(c))return;
    c.querySelectorAll('.ux454-group-label,.ux455-group-label').forEach(x=>x.remove());
    let cursor=anchor;
    ORDER.forEach(g=>{
      const cards=g.kinds.map(k=>card(k,c)).filter(Boolean);
      if(!cards.length)return;
      const label=makeLabel(g);cursor.insertAdjacentElement('afterend',label);cursor=label;
      cards.forEach(x=>{cursor.insertAdjacentElement('afterend',x);cursor=x;x.dataset.ux455Group=g.id;});
    });
  }

  function fixHeaderCollisions(c){
    c.querySelectorAll('.market-detail-card[data-collapsible="1"]').forEach(x=>{
      const toggle=x.querySelector(':scope > .market-collapse-toggle');if(!toggle)return;
      x.classList.add('ux455-safe-head');
      const head=x.querySelector(':scope > .market-perspective-head');if(head)head.classList.add('ux455-safe-perspective-head');
    });
    const swapHead=card('swap',c)?.querySelector('.ux454-swap-head');if(swapHead)swapHead.classList.add('ux455-swap-head');
  }

  function parseAlternative(row){
    const ticker=t(row.querySelector('.market-row__ticker,strong')?.textContent);
    const name=t(row.querySelector('.market-row__name')?.textContent);
    const score=n(row.querySelector('.market-score')?.textContent);
    const meta=t(row.querySelector('.market-row__meta,small,p')?.textContent);
    const source=(meta.match(/Alternativa a\s+([^·\s]+)/i)||[])[1]||'';
    const deltaMatch=meta.match(/Score\s*\+?(-?\d+)/i);const delta=deltaMatch?Number(deltaMatch[1]):null;
    return {ticker,name,score,source,delta,meta};
  }
  function swapLab(c){
    const swap=card('swap',c),scenario=card('scenario',c);if(!swap)return;
    const rows=[...swap.querySelectorAll('.market-row')];if(!rows.length)return;
    const alts=rows.map(parseAlternative).filter(x=>x.ticker);if(!alts.length)return;
    let panel=swap.querySelector('.ux455-swap-summary');
    if(!panel){panel=document.createElement('div');panel.className='ux455-swap-summary';const head=swap.querySelector('.ux454-swap-head');head?head.insertAdjacentElement('afterend',panel):swap.prepend(panel);}
    const best=[...alts].sort((a,b)=>(b.delta??-999)-(a.delta??-999))[0];
    panel.innerHTML=`<div><small>MELHOR MELHORIA DETETADA</small><strong>${best.source?best.source+' → ':''}${best.ticker}</strong><span>${best.delta!=null?`+${best.delta} pontos de Score Vestra`:''}${best.name?` · ${best.name}`:''}</span></div><button type="button" data-ux455-simulate>Ver impacto</button>`;
    rows.forEach((row,i)=>{
      if(row.querySelector('.ux455-swap-tag'))return;
      const a=alts[i]||parseAlternative(row),tag=document.createElement('div');tag.className='ux455-swap-tag';
      const strength=a.delta==null?'Comparar':a.delta>=25?'Melhoria forte':a.delta>=12?'Melhoria relevante':'Melhoria moderada';
      tag.innerHTML=`<span>${strength}</span>${a.delta!=null?`<b>+${a.delta}</b>`:''}`;row.appendChild(tag);
    });
    const button=swap.querySelector('[data-ux454-open-swap]');if(button){button.textContent='Ver comparação';button.dataset.ux455Simulate='1';}
    if(scenario)scenario.classList.add('ux455-scenario');
  }
  function overlapCard(c){
    const overlap=card('overlap',c);if(!overlap||overlap.querySelector('.ux455-overlap-note'))return;
    const note=document.createElement('div');note.className='ux455-overlap-note';
    note.innerHTML='<b>Exposure Map</b><span>Prioriza duplicações que aumentem concentração real; pequenas sobreposições podem ser intencionais.</span>';
    const head=overlap.querySelector('.ux454-overlap-head');head?head.insertAdjacentElement('afterend',note):overlap.prepend(note);
  }
  function dedupeSurfaces(c){
    c.querySelectorAll('.ux454-group-label').forEach(x=>x.remove());
    const seen=new Set();
    c.querySelectorAll('.ux455-group-label').forEach(x=>{const key=t(x.dataset.ux455Group)||t(x.textContent).toLowerCase();if(seen.has(key))x.remove();else seen.add(key);});
    for(const sel of ('.ux454-nav-title','.market-collapse-toolbar','.ux453-focusbar','.ux-portfolio-shortcuts')){
      [...c.querySelectorAll(sel)].slice(1).forEach(x=>x.remove());
    }
  }

  function openScenario(){
    const c=root();if(!c)return;const scenario=card('scenario',c);if(!scenario)return;
    if(scenario.classList.contains('is-collapsed'))scenario.querySelector('[data-collapse-toggle]')?.click();
    setTimeout(()=>scenario.scrollIntoView({behavior:'smooth',block:'start'}),30);
  }

  function style(){
    if(document.getElementById('vestra-portfolio-hierarchy-style'))return;
    const s=document.createElement('style');s.id='vestra-portfolio-hierarchy-style';s.textContent=`
      .ux454-portfolio{--uxPad:14px}.ux454-nav-title{margin:10px 0 0;padding:14px 15px 4px;display:flex;align-items:end;justify-content:space-between}.ux454-nav-title div{display:grid}.ux454-nav-title small{font-size:8.5px;letter-spacing:.14em;font-weight:900;color:var(--accent,#168e89)}.ux454-nav-title strong{font-size:17px;margin-top:2px}.ux454-nav-title>span{font-size:9px;color:var(--text2);max-width:120px;text-align:right}.ux454-toolbar{margin-top:4px!important;border-radius:18px!important;background:linear-gradient(135deg,color-mix(in srgb,var(--accent,#168e89) 8%,var(--card)),var(--card))!important}.ux454-focus{margin-top:7px!important}.ux454-shortcuts{margin-top:7px!important;padding:3px!important;background:transparent!important;border:0!important;box-shadow:none!important}.ux454-shortcuts button{min-height:44px!important;border-radius:14px!important;background:var(--card)!important;border:1px solid var(--line)!important;box-shadow:0 4px 14px rgba(20,50,55,.045)!important}
      .ux454-purpose{display:none}.market-detail-card.is-collapsed>.ux454-purpose{display:block!important;position:absolute;left:52px;right:62px;bottom:12px;font-size:9px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ux454-portfolio .market-detail-card.is-collapsed{min-height:78px!important;padding-bottom:27px!important}.ux454-portfolio .market-detail-card:not(.is-collapsed){box-shadow:0 8px 26px rgba(18,52,58,.055)}
      .ux454-swap-head,.ux454-overlap-head{margin:-2px -2px 12px;padding:13px;border-radius:15px;background:linear-gradient(135deg,#f3efff,#faf8ff);display:flex;align-items:center;justify-content:space-between;gap:10px}.ux454-swap-head div{display:grid;gap:2px}.ux454-swap-head small,.ux454-overlap-head small{font-size:8px;font-weight:900;letter-spacing:.12em;color:#6a55aa}.ux454-swap-head strong,.ux454-overlap-head strong{font-size:14px}.ux454-swap-head span{font-size:9px;color:var(--text2)}.ux454-swap-head button{border:0;border-radius:999px;padding:8px 11px;background:#7664b7;color:white;font-size:10px;font-weight:800}.ux454-overlap-head{display:grid;background:linear-gradient(135deg,#fff3df,#fffaf1)}.ux454-overlap-head small{color:#9a6819}
      .ux455-group-label{display:grid;gap:2px;margin:19px 5px 9px;padding:0 2px}.ux455-group-label span{font-size:21px;line-height:1.08;font-weight:900;letter-spacing:-.025em}.ux455-group-label small{font-size:12px;color:var(--text2)}.ux455-safe-head{position:relative}.ux455-safe-head>.market-perspective-head,.ux455-safe-head>h4{padding-right:72px!important}.ux455-safe-perspective-head>span:last-child{max-width:86px;text-align:right;white-space:normal;line-height:1.15}.ux455-safe-head>.market-collapse-toggle{right:13px!important;top:13px!important;z-index:5!important}.ux455-swap-head{padding-right:54px!important;position:relative}.ux455-swap-head>button{margin-right:0;max-width:118px}.ux455-swap-summary{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 11px;padding:11px 12px;border-radius:15px;background:linear-gradient(135deg,#eee8ff,#f8f5ff);border:1px solid rgba(118,100,183,.15)}.ux455-swap-summary>div{display:grid;gap:2px;min-width:0}.ux455-swap-summary small{font-size:8px;letter-spacing:.1em;font-weight:900;color:#6a55aa}.ux455-swap-summary strong{font-size:14px}.ux455-swap-summary span{font-size:9px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ux455-swap-summary button{border:0;border-radius:999px;background:#7664b7;color:#fff;padding:8px 10px;font-size:9px;font-weight:850;flex:0 0 auto}.ux455-swap-tag{display:flex;gap:5px;align-items:center;margin-top:6px}.ux455-swap-tag span{font-size:8px;font-weight:850;color:#6651a8;background:#f1ecff;padding:4px 7px;border-radius:999px}.ux455-swap-tag b{font-size:9px;color:#15836c}.ux455-overlap-note{display:flex;gap:8px;align-items:flex-start;margin:0 0 10px;padding:10px 11px;border-radius:14px;background:#fff7e8}.ux455-overlap-note b{font-size:10px;color:#97651a;flex:0 0 auto}.ux455-overlap-note span{font-size:9px;line-height:1.35;color:var(--text2)}.ux455-scenario:not(.is-collapsed){border-color:rgba(118,100,183,.24)!important}
      @media(max-width:620px){.ux454-nav-title>span{display:none}.ux455-group-label span{font-size:19px}.ux455-swap-head{display:grid!important;padding-right:54px!important}.ux455-swap-head>button{justify-self:start}.ux455-swap-summary{align-items:flex-start}.ux455-safe-perspective-head>span:last-child{max-width:72px;font-size:9px}}
    `;document.head.appendChild(s);
  }

  function apply(){
    const c=root();if(!c)return;
    decorateBase(c);repairHierarchy(c);fixHeaderCollisions(c);swapLab(c);overlapCard(c);dedupeSurfaces(c);
  }
  function start(){
    style();apply();let pending=false;
    const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});
    mo.observe(document.body,{childList:true,subtree:true});
  }
  document.addEventListener('click',e=>{
    const open=e.target.closest?.('[data-ux454-open-swap]');
    if(open){e.preventDefault();e.stopPropagation();const x=open.closest('[data-ux-kind="swap"]');if(x?.classList.contains('is-collapsed'))x.querySelector('[data-collapse-toggle]')?.click();setTimeout(()=>x?.scrollIntoView({behavior:'smooth',block:'start'}),20);return;}
    if(e.target.closest?.('[data-ux455-simulate],[data-ux455-simulate="1"]')){e.preventDefault();e.stopPropagation();openScenario();}
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  window.VestraPortfolioHierarchy=Object.freeze({refresh:apply});
})();
