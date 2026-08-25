/* Vestra UX v4.58 — decision pulse, opportunity lenses, political leaders. */
(() => {
  'use strict';
  const VERSION='4.58';
  const t=v=>String(v??'').trim();
  const n=v=>{if(v===null||v===undefined||v==='')return null;const x=Number(v);return Number.isFinite(x)?x:null;};
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  let stocks=[],byTicker=new Map(),loading=null,politicalRows=null;

  function loadStocks(){
    if(loading)return loading;
    loading=fetch(`./data/stocks.json?v=${VERSION}`,{cache:'no-store'}).then(r=>r.ok?r.json():Promise.reject()).then(d=>{
      stocks=Array.isArray(d)?d:(d?.stocks||[]);byTicker=new Map(stocks.map(s=>[t(s?.ticker).toUpperCase(),s]));return stocks;
    }).catch(()=>[]);return loading;
  }
  function stock(tk){const x=t(tk).toUpperCase();return byTicker.get(x)||stocks.find(s=>t(s?.ticker).toUpperCase().split('.')[0]===x.split('.')[0])||null;}
  function portfolioRoot(){const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');return(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)?null:c;}
  function card(kind,c){return c?.querySelector(`[data-ux-kind="${kind}"]`)||null;}
  function countRows(el){return el?[...el.querySelectorAll('.market-row,.market-research-queue-row,.market-fresh-row')].length:0;}
  function extractNumber(text){const m=t(text).replace(/\s/g,'').match(/(-?\d+(?:[.,]\d+)?)/);return m?Number(m[1].replace(',','.')):null;}

  function decisionPulse(){
    const c=portfolioRoot();if(!c)return;
    let box=c.querySelector('.ux458-pulse');
    const anchor=c.querySelector('.ux-portfolio-shortcuts')||c.querySelector('.ux453-focusbar')||c.querySelector('.market-collapse-toolbar');if(!anchor)return;
    const research=card('research',c),reinforce=card('reinforce',c),review=card('review',c),swap=card('swap',c),risk=card('risk',c);
    const pending=extractNumber(research?.textContent)||countRows(research);
    const reinforceCount=countRows(reinforce),reviewCount=countRows(review),swapCount=countRows(swap);
    const riskScore=extractNumber(risk?.textContent);
    const cells=[
      {kind:'research',label:'Research',value:pending||0,sub:'pendentes',tone:pending>50?'warn':'neutral'},
      {kind:'reinforce',label:'Reforçar',value:reinforceCount,sub:'candidatos',tone:reinforceCount?'good':'neutral'},
      {kind:'review',label:'Rever',value:reviewCount,sub:'posições',tone:reviewCount?'bad':'neutral'},
      {kind:'swap',label:'Trocas',value:swapCount,sub:'alternativas',tone:swapCount?'purple':'neutral'},
      {kind:'risk',label:'Risco',value:riskScore==null?'—':Math.round(riskScore),sub:riskScore==null?'sem score':'/100',tone:riskScore!=null&&riskScore<70?'warn':'neutral'}
    ];
    const sig=cells.map(x=>`${x.kind}:${x.value}`).join('|');if(box?.dataset.sig===sig)return;
    if(!box){box=document.createElement('div');box.className='ux458-pulse';anchor.insertAdjacentElement('afterend',box);}
    box.dataset.sig=sig;
    box.innerHTML=`<div class="ux458-pulse-head"><div><small>DECISION PULSE</small><strong>O que pede atenção primeiro</strong></div><span>toque para abrir</span></div><div class="ux458-pulse-grid">${cells.map(x=>`<button type="button" data-ux458-jump="${x.kind}" class="is-${x.tone}"><small>${x.label}</small><strong>${x.value}</strong><span>${x.sub}</span></button>`).join('')}</div>`;
  }

  function opportunityLens(){
    const section=[...document.querySelectorAll('.market-section')].find(x=>/Oportunidades agora|Melhores oportunidades/.test(t(x.querySelector('h3')?.textContent)));if(!section||!stocks.length)return;
    let bar=section.querySelector('.ux458-lenses');
    if(!bar){bar=document.createElement('div');bar.className='ux458-lenses';bar.innerHTML='<button class="is-active" data-ux458-lens="all">Todos</button><button data-ux458-lens="emerging">A começar</button><button data-ux458-lens="recovery">Recuperação</button><button data-ux458-lens="value">Value + timing</button>';const guide=section.querySelector('.ux454-opportunity-guide');(guide||section.querySelector('.market-section__head'))?.insertAdjacentElement('afterend',bar);}
    const active=t(bar.querySelector('.is-active')?.dataset.ux458Lens)||'all';
    const rows=[...section.querySelectorAll('.market-list .market-row')];let shown=0;
    rows.forEach(r=>{
      const s=stock(r.dataset.marketTicker);let ok=true;
      if(s&&active!=='all'){
        const est=t(s?.estimate_signal),rec=t(s?.recovery_status),val=t(s?.valuation_signal);const opp=n(s?.opportunity_timing_score);const fv=n(s?.fair_value_upside_pct),pt=n(s?.analyst_price_target_upside_pct);
        const hist=(Array.isArray(s?.price_history_1y)?s.price_history_1y:[]).map(x=>n(x?.close)).filter(x=>x>0);const ret=d=>hist.length>d?(hist.at(-1)/hist[hist.length-d-1]-1)*100:null;const r20=ret(20),r5=ret(5);const accel=r20!=null&&r5!=null?r5-r20/4:null;
        if(active==='emerging')ok=(accel!=null&&accel>0&&r20!=null&&r20>=-2&&r20<=12)||(opp!=null&&opp>=65&&r20!=null&&r20<=12);
        if(active==='recovery')ok=['confirmed','recovering'].includes(rec)||est==='improving';
        if(active==='value')ok=((fv!=null&&fv>=10)||(pt!=null&&pt>=12)||val==='undervalued')&&(opp==null||opp>=50);
      }
      r.hidden=!ok;if(ok)shown++;
    });
    let empty=section.querySelector('.ux458-lens-empty');if(shown===0&&active!=='all'){
      if(!empty){empty=document.createElement('div');empty.className='ux458-lens-empty';section.querySelector('.market-list')?.appendChild(empty);}empty.textContent='Sem candidatos fortes nesta lente neste momento.';
    } else empty?.remove();
  }

  async function loadPolitical(){if(politicalRows)return politicalRows;try{const r=await fetch('https://www.bargo.ai/free-apis/congress/v1/trades?limit=100&page=0',{cache:'no-store',mode:'cors'});if(!r.ok)throw 0;const d=await r.json();politicalRows=Array.isArray(d)?d:(d?.trades||d?.data||[]);return politicalRows;}catch{return[];}}
  function isBuy(x){return /purchase|buy|compr/.test(t(x?.type||x?.transaction||x?.transaction_type).toLowerCase());}
  function isSell(x){return /sale|sell|vend/.test(t(x?.type||x?.transaction||x?.transaction_type).toLowerCase());}
  function memberName(x){return t(x?.representative||x?.member||x?.name)||'Membro do Congresso';}
  function leaders(rows,pred){const m=new Map();rows.filter(pred).forEach(x=>{const name=memberName(x);const cur=m.get(name)||{name,count:0,tickers:new Set()};cur.count++;if(t(x?.ticker))cur.tickers.add(t(x.ticker).toUpperCase());m.set(name,cur);});return[...m.values()].sort((a,b)=>b.count-a.count).slice(0,5);}
  async function politicalLeaders(){
    const section=document.querySelector('.politicians-section');if(!section||section.querySelector('.ux458-politician-leaders'))return;
    const rows=await loadPolitical();if(!rows.length)return;
    const buys=leaders(rows,isBuy),sells=leaders(rows,isSell);
    const box=document.createElement('div');box.className='ux458-politician-leaders';box.innerHTML=`<div class="ux458-pol-head"><div><small>QUEM ESTÁ MAIS ATIVO</small><strong>Leaders das últimas divulgações</strong></div><span>janela recente</span></div><div class="ux458-pol-grid"><section><small>↗ MAIS COMPRADORES</small>${buys.map(x=>`<div><b>${esc(x.name)}</b><span>${x.count} operações · ${esc([...x.tickers].slice(0,3).join(' · ')||'—')}</span></div>`).join('')}</section><section><small>↘ MAIS VENDEDORES</small>${sells.map(x=>`<div><b>${esc(x.name)}</b><span>${x.count} operações · ${esc([...x.tickers].slice(0,3).join(' · ')||'—')}</span></div>`).join('')}</section></div>`;
    const flow=section.querySelector('.ux454-flow');flow?flow.insertAdjacentElement('afterend',box):section.querySelector('.politician-picker')?.insertAdjacentElement('beforebegin',box);
  }

  function dedupeLegacy(){
    const c=portfolioRoot();if(!c)return;
    const seen=new Set();[...c.querySelectorAll('.ux454-group-label,.ux455-group-label')].forEach(x=>{const key=t(x.textContent).replace(/\s+/g,' ');if(seen.has(key))x.remove();else seen.add(key);});
    const navs=[...c.querySelectorAll('.ux454-nav-title')];navs.slice(1).forEach(x=>x.remove());
    const bars=[...c.querySelectorAll('.ux453-focusbar')];bars.slice(1).forEach(x=>x.remove());
    const shortcuts=[...c.querySelectorAll('.ux-portfolio-shortcuts')];shortcuts.slice(1).forEach(x=>x.remove());
  }

  function addStyle(){if(document.getElementById('vestra-ux-v458-style'))return;const s=document.createElement('style');s.id='vestra-ux-v458-style';s.textContent=`
    .ux458-pulse{margin:8px 0 12px;padding:12px;border:1px solid var(--line);border-radius:18px;background:linear-gradient(145deg,color-mix(in srgb,var(--accent,#168e89) 7%,var(--card)),var(--card));box-shadow:0 8px 24px rgba(20,55,60,.05)}.ux458-pulse-head{display:flex;justify-content:space-between;gap:10px;align-items:end;margin-bottom:9px}.ux458-pulse-head>div{display:grid;gap:2px}.ux458-pulse-head small{font-size:8px;letter-spacing:.12em;font-weight:900;color:var(--accent,#168e89)}.ux458-pulse-head strong{font-size:14px}.ux458-pulse-head>span{font-size:8px;color:var(--text2)}.ux458-pulse-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}.ux458-pulse-grid button{border:1px solid var(--line);background:var(--card);border-radius:13px;padding:9px 6px;display:grid;gap:1px;text-align:left;color:var(--text)}.ux458-pulse-grid button small{font-size:7.5px;font-weight:850;color:var(--text2)}.ux458-pulse-grid button strong{font-size:16px}.ux458-pulse-grid button span{font-size:7px;color:var(--text2)}.ux458-pulse-grid button.is-good{box-shadow:inset 0 3px 0 #49b78e}.ux458-pulse-grid button.is-bad{box-shadow:inset 0 3px 0 #e27967}.ux458-pulse-grid button.is-warn{box-shadow:inset 0 3px 0 #e2ad46}.ux458-pulse-grid button.is-purple{box-shadow:inset 0 3px 0 #7b68b8}
    .ux458-lenses{display:flex;gap:6px;overflow-x:auto;margin:0 0 10px;padding:1px 0 2px;scrollbar-width:none}.ux458-lenses button{flex:0 0 auto;border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:7px 10px;font-size:9px;font-weight:850;color:var(--text2)}.ux458-lenses button.is-active{background:var(--accent,#168e89);color:white;border-color:transparent}.ux458-lens-empty{padding:18px;text-align:center;color:var(--text2);font-size:11px}
    .ux458-politician-leaders{margin:0 0 14px;padding:13px;border:1px solid var(--line);border-radius:18px;background:var(--card)}.ux458-pol-head{display:flex;justify-content:space-between;gap:10px;align-items:start;margin-bottom:9px}.ux458-pol-head>div{display:grid;gap:2px}.ux458-pol-head small{font-size:8px;letter-spacing:.1em;font-weight:900;color:var(--accent,#168e89)}.ux458-pol-head strong{font-size:14px}.ux458-pol-head>span{font-size:8px;color:var(--text2)}.ux458-pol-grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}.ux458-pol-grid section{display:grid;gap:6px;padding:10px;border-radius:14px;background:var(--soft)}.ux458-pol-grid section>small{font-size:8px;font-weight:900;letter-spacing:.07em;color:var(--text2)}.ux458-pol-grid section>div{display:grid;gap:1px}.ux458-pol-grid b{font-size:10px}.ux458-pol-grid span{font-size:8px;color:var(--text2)}
    @media(max-width:620px){.ux458-pulse-grid{grid-template-columns:repeat(3,1fr)}.ux458-pulse-grid button:nth-child(4),.ux458-pulse-grid button:nth-child(5){grid-column:auto}.ux458-pol-grid{grid-template-columns:1fr}}
  `;document.head.appendChild(s);}

  function apply(){dedupeLegacy();decisionPulse();opportunityLens();politicalLeaders();}
  document.addEventListener('click',e=>{
    const j=e.target.closest?.('[data-ux458-jump]');if(j){e.preventDefault();const c=portfolioRoot(),target=card(j.dataset.ux458Jump,c);if(target?.classList.contains('is-collapsed'))target.querySelector('[data-collapse-toggle]')?.click();setTimeout(()=>target?.scrollIntoView({behavior:'smooth',block:'start'}),25);return;}
    const lens=e.target.closest?.('[data-ux458-lens]');if(lens){e.preventDefault();const bar=lens.closest('.ux458-lenses');bar.querySelectorAll('button').forEach(x=>x.classList.toggle('is-active',x===lens));opportunityLens();}
  });
  function start(){addStyle();loadStocks().then(()=>{apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
