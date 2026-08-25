/* Vestra UX v4.54 — portfolio hierarchy, swap focus, opportunity podium and political flow. */
(() => {
  'use strict';
  const VERSION='4.54';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let recentPolitical=null;

  const GROUPS=[
    {id:'decide',title:'Decidir agora',sub:'As ações que podem exigir atenção.',kinds:['priority','reinforce','review','research']},
    {id:'optimize',title:'Otimizar a carteira',sub:'Trocas, overlap e eficiência da alocação.',kinds:['swap','overlap','scenario','map']},
    {id:'monitor',title:'Monitorizar',sub:'Saúde, objetivos e resistência da carteira.',kinds:['target','history','risk','stress']}
  ];

  function portfolioRoot(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    return (!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;
  }
  function makeGroupLabel(g){
    const d=document.createElement('div');d.className='ux454-group-label';d.dataset.ux454Group=g.id;
    d.innerHTML=`<span>${esc(g.title)}</span><small>${esc(g.sub)}</small>`;return d;
  }
  function organizePortfolio(){
    const c=portfolioRoot();if(!c)return;
    c.classList.add('ux454-portfolio');

    // Compress the legacy controls into one navigation surface.
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

    // Add semantic section headers only once, positioned before the first card of each group.
    GROUPS.forEach(g=>{
      if(c.querySelector(`[data-ux454-group="${g.id}"]`))return;
      const cards=g.kinds.map(k=>c.querySelector(`[data-ux-kind="${k}"]`)).filter(Boolean);
      if(!cards.length)return;
      cards[0].insertAdjacentElement('beforebegin',makeGroupLabel(g));
      cards.forEach(card=>card.dataset.ux454GroupCard=g.id);
    });

    // Stronger closed-card hierarchy with useful one-line purpose.
    const purposes={
      research:'Pendências de research',priority:'O que merece atenção',map:'Como está distribuída',reinforce:'Onde colocar capital novo',review:'O que reavaliar',
      overlap:'Exposição duplicada',swap:'Melhores substitutos',scenario:'Simular antes de trocar',target:'Fit com os teus objetivos',history:'Evolução da qualidade',risk:'Concentração e diversificação',stress:'Comportamento em quedas'
    };
    c.querySelectorAll('[data-ux-kind]').forEach(card=>{
      const kind=card.dataset.uxKind;if(!kind||card.querySelector(':scope > .ux454-purpose'))return;
      const p=document.createElement('div');p.className='ux454-purpose';p.textContent=purposes[kind]||'';card.appendChild(p);
    });

    const swap=c.querySelector('[data-ux-kind="swap"]');
    if(swap&&!swap.querySelector('.ux454-swap-head')){
      const h=document.createElement('div');h.className='ux454-swap-head';
      h.innerHTML='<div><small>SWAP LAB</small><strong>Trocar só quando melhora a carteira</strong><span>Compara qualidade, valuation, momentum e impacto na concentração.</span></div><button type="button" data-ux454-open-swap>Comparar →</button>';
      swap.prepend(h);
    }
    const overlap=c.querySelector('[data-ux-kind="overlap"]');
    if(overlap&&!overlap.querySelector('.ux454-overlap-head')){
      const h=document.createElement('div');h.className='ux454-overlap-head';h.innerHTML='<small>EXPOSURE MAP</small><strong>Onde estás a comprar a mesma coisa duas vezes?</strong>';overlap.prepend(h);
    }
  }

  function rankOpportunityRows(){
    const section=[...document.querySelectorAll('.market-section')].find(x=>/Oportunidades agora|Melhores oportunidades/.test(t(x.querySelector('h3')?.textContent)));
    const list=section?.querySelector('.market-list');if(!section||!list)return;
    const rows=[...list.querySelectorAll('.market-row')];if(!rows.length)return;
    rows.forEach((r,i)=>{
      r.classList.toggle('ux454-podium',i<3);
      r.classList.toggle('ux454-podium-1',i===0);
      r.classList.toggle('ux454-podium-2',i===1);
      r.classList.toggle('ux454-podium-3',i===2);
      if(i<3&&!r.querySelector('.ux454-rank')){
        const b=document.createElement('span');b.className='ux454-rank';b.textContent=`#${i+1}`;r.prepend(b);
      }
    });
    if(!section.querySelector('.ux454-opportunity-guide')){
      const g=document.createElement('div');g.className='ux454-opportunity-guide';
      g.innerHTML='<span><b>ENTRY</b> combinação de qualidade + timing</span><span><b>Timing</b> evita perseguir preço esticado</span><span><b>Sinais</b> confirmações independentes</span>';
      const head=section.querySelector('.market-section__head');head?.insertAdjacentElement('afterend',g);
    }
  }

  async function loadPoliticalFlow(){
    if(recentPolitical)return recentPolitical;
    try{
      const r=await fetch('https://www.bargo.ai/free-apis/congress/v1/trades?limit=100&page=0',{cache:'no-store',mode:'cors'});if(!r.ok)throw 0;
      const d=await r.json();recentPolitical=Array.isArray(d)?d:(d?.trades||d?.data||[]);return recentPolitical;
    }catch{return[];}
  }
  function tradeType(x){return t(x?.type||x?.transaction||x?.transaction_type).toLowerCase();}
  function isBuy(x){return /purchase|buy|compr/.test(tradeType(x));}
  function isSell(x){return /sale|sell|vend/.test(tradeType(x));}
  function aggregate(rows,pred){
    const m=new Map();rows.filter(pred).forEach(x=>{const tk=t(x?.ticker).toUpperCase();if(!tk)return;m.set(tk,(m.get(tk)||0)+1);});
    return [...m.entries()].sort((a,b)=>b[1]-a[1]).slice(0,5);
  }
  async function enhancePoliticalFlow(){
    const section=document.querySelector('.politicians-section');if(!section||section.querySelector('.ux454-flow'))return;
    const rows=await loadPoliticalFlow();if(!rows.length)return;
    const buys=aggregate(rows,isBuy),sells=aggregate(rows,isSell);
    const box=document.createElement('div');box.className='ux454-flow';
    box.innerHTML=`<div class="ux454-flow-head"><div><small>POLITICAL FLOW · ÚLTIMAS 100</small><strong>O que o Congresso está a negociar agora</strong></div><span>${rows.length} divulgações</span></div><div class="ux454-flow-grid"><section><small>↗ MAIS COMPRADOS</small>${buys.map(([tk,c])=>`<button data-market-ticker="${esc(tk)}"><b>${esc(tk)}</b><span>${c} operações</span></button>`).join('')}</section><section><small>↘ MAIS VENDIDOS</small>${sells.map(([tk,c])=>`<button data-market-ticker="${esc(tk)}"><b>${esc(tk)}</b><span>${c} operações</span></button>`).join('')}</section></div>`;
    const picker=section.querySelector('.politician-picker');picker?.insertAdjacentElement('beforebegin',box);
  }

  function style(){
    if(document.getElementById('vestra-ux-v454-style'))return;
    const s=document.createElement('style');s.id='vestra-ux-v454-style';s.textContent=`
      .ux454-portfolio{--uxPad:14px}.ux454-nav-title{margin:10px 0 0;padding:14px 15px 4px;display:flex;align-items:end;justify-content:space-between}.ux454-nav-title div{display:grid}.ux454-nav-title small{font-size:8.5px;letter-spacing:.14em;font-weight:900;color:var(--accent,#168e89)}.ux454-nav-title strong{font-size:17px;margin-top:2px}.ux454-nav-title>span{font-size:9px;color:var(--text2);max-width:120px;text-align:right}.ux454-toolbar{margin-top:4px!important;border-radius:18px!important;background:linear-gradient(135deg,color-mix(in srgb,var(--accent,#168e89) 8%,var(--card)),var(--card))!important}.ux454-focus{margin-top:7px!important}.ux454-shortcuts{margin-top:7px!important;padding:3px!important;background:transparent!important;border:0!important;box-shadow:none!important}.ux454-shortcuts button{min-height:44px!important;border-radius:14px!important;background:var(--card)!important;border:1px solid var(--line)!important;box-shadow:0 4px 14px rgba(20,50,55,.045)!important}
      .ux454-group-label{display:grid;gap:2px;margin:18px 3px 8px;padding-left:3px}.ux454-group-label span{font-size:13px;font-weight:900;color:var(--text)}.ux454-group-label small{font-size:9.5px;color:var(--text2)}.ux454-purpose{display:none}.market-detail-card.is-collapsed>.ux454-purpose{display:block!important;position:absolute;left:52px;right:50px;bottom:12px;font-size:9px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ux454-portfolio .market-detail-card.is-collapsed{min-height:78px!important;padding-bottom:27px!important}.ux454-portfolio .market-detail-card:not(.is-collapsed){box-shadow:0 8px 26px rgba(18,52,58,.055)}
      .ux454-swap-head,.ux454-overlap-head{margin:-2px -2px 12px;padding:13px;border-radius:15px;background:linear-gradient(135deg,#f3efff,#faf8ff);display:flex;align-items:center;justify-content:space-between;gap:10px}.ux454-swap-head div{display:grid;gap:2px}.ux454-swap-head small,.ux454-overlap-head small{font-size:8px;font-weight:900;letter-spacing:.12em;color:#6a55aa}.ux454-swap-head strong,.ux454-overlap-head strong{font-size:14px}.ux454-swap-head span{font-size:9px;color:var(--text2)}.ux454-swap-head button{border:0;border-radius:999px;padding:8px 11px;background:#7664b7;color:white;font-size:10px;font-weight:800}.ux454-overlap-head{display:grid;background:linear-gradient(135deg,#fff3df,#fffaf1)}.ux454-overlap-head small{color:#9a6819}
      .ux454-opportunity-guide{display:flex;gap:6px;overflow-x:auto;padding:0 1px 9px;margin-top:-2px;scrollbar-width:none}.ux454-opportunity-guide span{flex:0 0 auto;padding:6px 8px;border-radius:999px;background:var(--soft);font-size:8.5px;color:var(--text2)}.ux454-opportunity-guide b{color:var(--text);margin-right:3px}.ux454-podium{position:relative!important;border-width:1.5px!important}.ux454-podium-1{background:linear-gradient(145deg,color-mix(in srgb,var(--accent,#168e89) 12%,var(--card)),var(--card))!important;box-shadow:0 10px 26px rgba(18,118,111,.10)!important}.ux454-podium-2{background:linear-gradient(145deg,#f3f6fb,var(--card))!important}.ux454-podium-3{background:linear-gradient(145deg,#fff7ec,var(--card))!important}.ux454-rank{position:absolute;right:8px;top:7px;font-size:8px;font-weight:900;letter-spacing:.08em;color:var(--text2);opacity:.8}
      .ux454-flow{margin:0 0 14px;padding:14px;border-radius:19px;background:linear-gradient(145deg,#123e49,#176b69);color:white;box-shadow:0 12px 30px rgba(18,62,73,.16)}.ux454-flow-head{display:flex;justify-content:space-between;align-items:start;gap:10px;margin-bottom:11px}.ux454-flow-head div{display:grid;gap:3px}.ux454-flow-head small{font-size:8px;letter-spacing:.13em;font-weight:900;opacity:.68}.ux454-flow-head strong{font-size:15px}.ux454-flow-head>span{font-size:8px;padding:5px 7px;border-radius:999px;background:rgba(255,255,255,.11)}.ux454-flow-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.ux454-flow-grid section{display:grid;gap:5px;padding:10px;border-radius:14px;background:rgba(255,255,255,.08)}.ux454-flow-grid section>small{font-size:8px;font-weight:900;letter-spacing:.07em;opacity:.75}.ux454-flow-grid button{display:flex;justify-content:space-between;gap:6px;border:0;background:transparent;color:white;padding:5px 0;text-align:left}.ux454-flow-grid button b{font-size:11px}.ux454-flow-grid button span{font-size:8px;opacity:.72}
      @media(max-width:620px){.ux454-nav-title>span{display:none}.ux454-group-label{margin-top:14px}.ux454-flow-grid{grid-template-columns:1fr}.ux454-swap-head{align-items:flex-start}.ux454-swap-head button{flex:0 0 auto}}
    `;document.head.appendChild(s);
  }

  function apply(){organizePortfolio();rankOpportunityRows();enhancePoliticalFlow();}
  function start(){style();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  document.addEventListener('click',e=>{
    const b=e.target.closest?.('[data-ux454-open-swap]');if(!b)return;e.preventDefault();e.stopPropagation();const card=b.closest('[data-ux-kind="swap"]');if(card?.classList.contains('is-collapsed'))card.querySelector('[data-collapse-toggle]')?.click();setTimeout(()=>card?.scrollIntoView({behavior:'smooth',block:'start'}),20);
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
