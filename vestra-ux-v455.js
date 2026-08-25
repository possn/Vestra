/* Vestra UX v4.55 — stable portfolio hierarchy, overlap repair, richer Swap Lab. */
(() => {
  'use strict';
  const VERSION='4.55';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};

  const ORDER=[
    {id:'decide',title:'Decidir agora',sub:'As ações que podem exigir atenção.',kinds:['research','priority','reinforce','review']},
    {id:'optimize',title:'Otimizar a carteira',sub:'Trocas, overlap e eficiência da alocação.',kinds:['swap','scenario','overlap','map']},
    {id:'monitor',title:'Monitorizar',sub:'Saúde, objetivos e resistência da carteira.',kinds:['target','history','risk','stress']}
  ];

  function root(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }
  function makeLabel(g){
    const d=document.createElement('div');d.className='ux455-group-label';d.dataset.ux455Group=g.id;
    d.innerHTML=`<span>${g.title}</span><small>${g.sub}</small>`;return d;
  }
  function card(kind,c){return c.querySelector(`[data-ux-kind="${kind}"]`);}

  function repairHierarchy(){
    const c=root();if(!c||c.dataset.ux455Ordered==='1')return;
    const anchor=c.querySelector('.ux-portfolio-shortcuts')||c.querySelector('.ux453-focusbar')||c.querySelector('.market-collapse-toolbar');
    if(!anchor)return;

    // Remove legacy group labels before doing an explicit, deterministic order.
    c.querySelectorAll('.ux454-group-label,.ux455-group-label').forEach(x=>x.remove());
    let cursor=anchor;
    ORDER.forEach(g=>{
      const cards=g.kinds.map(k=>card(k,c)).filter(Boolean);
      if(!cards.length)return;
      const label=makeLabel(g);cursor.insertAdjacentElement('afterend',label);cursor=label;
      cards.forEach(x=>{cursor.insertAdjacentElement('afterend',x);cursor=x;x.dataset.ux455Group=g.id;});
    });
    c.dataset.ux455Ordered='1';
  }

  function fixHeaderCollisions(){
    const c=root();if(!c)return;
    c.querySelectorAll('.market-detail-card[data-collapsible="1"]').forEach(x=>{
      const toggle=x.querySelector(':scope > .market-collapse-toggle');
      if(!toggle)return;
      x.classList.add('ux455-safe-head');
      // metadata such as “17% coberto” must not sit under the collapse button.
      const head=x.querySelector(':scope > .market-perspective-head');
      if(head)head.classList.add('ux455-safe-perspective-head');
    });
    const swap=card('swap',c);
    const swapHead=swap?.querySelector('.ux454-swap-head');
    if(swapHead)swapHead.classList.add('ux455-swap-head');
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
  function swapLab(){
    const c=root();if(!c)return;
    const swap=card('swap',c),scenario=card('scenario',c);if(!swap)return;
    const rows=[...swap.querySelectorAll('.market-row')];if(!rows.length)return;
    const alts=rows.map(parseAlternative).filter(x=>x.ticker);
    if(!alts.length)return;

    let panel=swap.querySelector('.ux455-swap-summary');
    if(!panel){panel=document.createElement('div');panel.className='ux455-swap-summary';const head=swap.querySelector('.ux454-swap-head');head?head.insertAdjacentElement('afterend',panel):swap.prepend(panel);}
    const best=[...alts].sort((a,b)=>(b.delta??-999)-(a.delta??-999))[0];
    panel.innerHTML=`<div><small>MELHOR MELHORIA DETETADA</small><strong>${best.source?best.source+' → ':''}${best.ticker}</strong><span>${best.delta!=null?`+${best.delta} pontos de Score Vestra`:''}${best.name?` · ${best.name}`:''}</span></div><button type="button" data-ux455-simulate>Ver impacto</button>`;

    rows.forEach((row,i)=>{
      if(row.querySelector('.ux455-swap-tag'))return;
      const a=alts[i]||parseAlternative(row);const tag=document.createElement('div');tag.className='ux455-swap-tag';
      const strength=a.delta==null?'Comparar':a.delta>=25?'Melhoria forte':a.delta>=12?'Melhoria relevante':'Melhoria moderada';
      tag.innerHTML=`<span>${strength}</span>${a.delta!=null?`<b>+${a.delta}</b>`:''}`;row.appendChild(tag);
    });

    const button=swap.querySelector('[data-ux454-open-swap]');if(button){button.textContent='Ver comparação';button.dataset.ux455Simulate='1';}
    if(scenario)scenario.classList.add('ux455-scenario');
  }

  function overlapCard(){
    const c=root();if(!c)return;const overlap=card('overlap',c);if(!overlap)return;
    if(!overlap.querySelector('.ux455-overlap-note')){
      const note=document.createElement('div');note.className='ux455-overlap-note';
      note.innerHTML='<b>Exposure Map</b><span>Prioriza duplicações que aumentem concentração real; pequenas sobreposições podem ser intencionais.</span>';
      const head=overlap.querySelector('.ux454-overlap-head');head?head.insertAdjacentElement('afterend',note):overlap.prepend(note);
    }
  }

  function style(){
    if(document.getElementById('vestra-ux-v455-style'))return;
    const s=document.createElement('style');s.id='vestra-ux-v455-style';s.textContent=`
      .ux455-group-label{display:grid;gap:2px;margin:19px 5px 9px;padding:0 2px}.ux455-group-label span{font-size:21px;line-height:1.08;font-weight:900;letter-spacing:-.025em}.ux455-group-label small{font-size:12px;color:var(--text2)}
      .ux455-safe-head{position:relative}.ux455-safe-head>.market-perspective-head,.ux455-safe-head>h4{padding-right:72px!important}.ux455-safe-perspective-head>span:last-child{max-width:86px;text-align:right;white-space:normal;line-height:1.15}.ux455-safe-head>.market-collapse-toggle{right:13px!important;top:13px!important;z-index:5!important}.ux455-safe-head.is-collapsed>.ux454-purpose{right:62px!important}
      .ux455-swap-head{padding-right:54px!important;position:relative}.ux455-swap-head>button{margin-right:0;max-width:118px}.ux455-swap-summary{display:flex;align-items:center;justify-content:space-between;gap:10px;margin:0 0 11px;padding:11px 12px;border-radius:15px;background:linear-gradient(135deg,#eee8ff,#f8f5ff);border:1px solid rgba(118,100,183,.15)}.ux455-swap-summary>div{display:grid;gap:2px;min-width:0}.ux455-swap-summary small{font-size:8px;letter-spacing:.1em;font-weight:900;color:#6a55aa}.ux455-swap-summary strong{font-size:14px}.ux455-swap-summary span{font-size:9px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ux455-swap-summary button{border:0;border-radius:999px;background:#7664b7;color:#fff;padding:8px 10px;font-size:9px;font-weight:850;flex:0 0 auto}.ux455-swap-tag{display:flex;gap:5px;align-items:center;margin-top:6px}.ux455-swap-tag span{font-size:8px;font-weight:850;color:#6651a8;background:#f1ecff;padding:4px 7px;border-radius:999px}.ux455-swap-tag b{font-size:9px;color:#15836c}.ux455-overlap-note{display:flex;gap:8px;align-items:flex-start;margin:0 0 10px;padding:10px 11px;border-radius:14px;background:#fff7e8}.ux455-overlap-note b{font-size:10px;color:#97651a;flex:0 0 auto}.ux455-overlap-note span{font-size:9px;line-height:1.35;color:var(--text2)}
      .ux455-scenario:not(.is-collapsed){border-color:rgba(118,100,183,.24)!important}
      @media(max-width:620px){.ux455-group-label span{font-size:19px}.ux455-swap-head{display:grid!important;padding-right:54px!important}.ux455-swap-head>button{justify-self:start}.ux455-swap-summary{align-items:flex-start}.ux455-safe-perspective-head>span:last-child{max-width:72px;font-size:9px}}
    `;document.head.appendChild(s);
  }

  function openScenario(){
    const c=root();if(!c)return;const scenario=card('scenario',c);if(!scenario)return;
    if(scenario.classList.contains('is-collapsed'))scenario.querySelector('[data-collapse-toggle]')?.click();
    setTimeout(()=>scenario.scrollIntoView({behavior:'smooth',block:'start'}),30);
  }

  function apply(){repairHierarchy();fixHeaderCollisions();swapLab();overlapCard();}
  function start(){style();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  document.addEventListener('click',e=>{
    if(e.target.closest?.('[data-ux455-simulate],[data-ux455-simulate="1"]')){e.preventDefault();e.stopPropagation();openScenario();}
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
