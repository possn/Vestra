/* Vestra Portfolio Hierarchy v1.9 — canonical card ordering with single-pass observed refreshes. */
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
  function decorateBase(c){
    c.classList.add('ux454-portfolio');
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

  function orderedCards(c){
    const rows=[];
    ORDER.forEach(g=>g.kinds.map(k=>card(k,c)).filter(Boolean).forEach(x=>{x.dataset.ux455Group=g.id;rows.push(x);}));
    return rows;
  }
  function hierarchyIsCurrent(anchor,cards){
    let cursor=anchor;
    return cards.every(x=>{const ok=cursor.nextElementSibling===x;cursor=x;return ok;});
  }
  function repairHierarchy(c){
    const anchor=c.querySelector('.market-decision-center');
    if(!anchor)return;
    c.querySelectorAll(':scope > .ux454-group-label,:scope > .ux455-group-label,:scope > .ux454-nav-title').forEach(x=>x.remove());
    const cards=orderedCards(c);
    if(!cards.length||hierarchyIsCurrent(anchor,cards))return;
    let cursor=anchor;
    cards.forEach(x=>{cursor.insertAdjacentElement('afterend',x);cursor=x;});
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
    const signature=JSON.stringify([best.source,best.ticker,best.delta,best.name]);
    if(panel.dataset.signature!==signature){
      panel.dataset.signature=signature;
      panel.innerHTML=`<div><small>MELHOR MELHORIA DETETADA</small><strong>${best.source?best.source+' → ':''}${best.ticker}</strong><span>${best.delta!=null?`+${best.delta} pontos de Score Vestra`:''}${best.name?` · ${best.name}`:''}</span></div><button type="button" data-ux455-simulate>Ver impacto</button>`;
    }
    rows.forEach((row,i)=>{
      if(row.querySelector('.ux455-swap-tag'))return;
      const a=alts[i]||parseAlternative(row),tag=document.createElement('div');tag.className='ux455-swap-tag';
      const strength=a.delta==null?'Comparar':a.delta>=25?'Melhoria forte':a.delta>=12?'Melhoria relevante':'Melhoria moderada';
      tag.innerHTML=`<span>${strength}</span>${a.delta!=null?`<b>+${a.delta}</b>`:''}`;row.appendChild(tag);
    });
    const button=swap.querySelector('[data-ux454-open-swap]');if(button){if(button.textContent!=='Ver comparação')button.textContent='Ver comparação';button.dataset.ux455Simulate='1';}
    if(scenario)scenario.classList.add('ux455-scenario');
  }
  function overlapCard(c){
    const overlap=card('overlap',c);if(!overlap||overlap.querySelector('.ux455-overlap-note'))return;
    const note=document.createElement('div');note.className='ux455-overlap-note';
    note.innerHTML='<b>Exposure Map</b><span>Prioriza duplicações que aumentem concentração real; pequenas sobreposições podem ser intencionais.</span>';
    const head=overlap.querySelector('.ux454-overlap-head');head?head.insertAdjacentElement('afterend',note):overlap.prepend(note);
  }
  function openScenario(){
    const c=root();if(!c)return;const scenario=card('scenario',c);if(!scenario)return;
    if(scenario.classList.contains('is-collapsed'))scenario.querySelector('[data-collapse-toggle]')?.click();
    setTimeout(()=>scenario.scrollIntoView({behavior:'smooth',block:'start'}),30);
  }

  function style(){
    if(document.getElementById('vestra-portfolio-hierarchy-style'))return;
    const link=document.createElement('link');
    link.id='vestra-portfolio-hierarchy-style';
    link.rel='stylesheet';
    link.href='vestra-portfolio-hierarchy.css?v=1.1';
    document.head.appendChild(link);
  }

  function apply(){
    window.VestraPortfolioCollapsibles?.refresh?.();
    window.VestraPortfolioCardClassifier?.refresh?.();
    const c=root();if(!c)return;
    decorateBase(c);repairHierarchy(c);fixHeaderCollisions(c);swapLab(c);overlapCard(c);
    window.VestraSwapLab?.refresh?.();
    window.VestraPortfolioUI?.refresh?.();
    window.VestraPortfolioDiagnostics?.refresh?.();
    window.VestraPortfolioDossierRouting?.decorate?.();
  }
  function start(){
    style();apply();
    const sh=document.getElementById('marketSheet');if(!sh)return;
    const observerOptions={childList:true,subtree:true};
    let pending=false;
    const mo=new MutationObserver(()=>{
      if(pending)return;
      pending=true;
      requestAnimationFrame(()=>{
        pending=false;
        mo.disconnect();
        try{apply();}finally{
          mo.takeRecords();
          mo.observe(sh,observerOptions);
        }
      });
    });
    mo.observe(sh,observerOptions);
  }
  document.addEventListener('click',e=>{
    const open=e.target.closest?.('[data-ux454-open-swap]');
    if(open){e.preventDefault();e.stopPropagation();const x=open.closest('[data-ux-kind="swap"]');if(x?.classList.contains('is-collapsed'))x.querySelector('[data-collapse-toggle]')?.click();setTimeout(()=>x?.scrollIntoView({behavior:'smooth',block:'start'}),20);return;}
    if(e.target.closest?.('[data-ux455-simulate],[data-ux455-simulate="1"]')){e.preventDefault();e.stopPropagation();openScenario();}
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();

  window.VestraPortfolioHierarchy=Object.freeze({refresh:apply,version:'1.9'});
})();