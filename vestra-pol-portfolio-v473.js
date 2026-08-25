/* Vestra v4.73 — compact politician activity + remove redundant portfolio priority shell. */
(() => {
  'use strict';
  const t=v=>String(v??'').trim();
  const BUY=/purchase|buy|compr/i, SELL=/sale|sell|vend/i;
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmtDate=v=>{if(!v)return '—';const d=new Date(v);return Number.isNaN(d.valueOf())?t(v):new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d)};
  const isBuy=x=>BUY.test(t(x?.type)), isSell=x=>SELL.test(t(x?.type));
  const amountValue=v=>{const s=t(v).replace(/,/g,'');const nums=[...s.matchAll(/\$?([0-9]+(?:\.[0-9]+)?)([KMB])?/gi)].map(m=>{let n=Number(m[1]);const u=t(m[2]).toUpperCase();if(u==='K')n*=1e3;if(u==='M')n*=1e6;if(u==='B')n*=1e9;return n;});return nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:0;};
  const trumpRows=()=>{
    const src=window.__vestraTrumpTrades;
    if(Array.isArray(src)&&src.length)return src;
    return [
      {ticker:'BRK-B',asset:'Berkshire Hathaway',type:'purchase',amount:'$1,000,001 - $5,000,000',transaction_date:'2026-06-18',disclosure_date:'2026-08-22'},
      {ticker:'V',asset:'Visa',type:'purchase',amount:'≥ $1,000,000',transaction_date:'2026-06-18',disclosure_date:'2026-08-22'},
      {ticker:'MA',asset:'Mastercard',type:'purchase',amount:'≥ $1,000,000',transaction_date:'2026-06-18',disclosure_date:'2026-08-22'},
      {ticker:'CTAS',asset:'Cintas',type:'purchase',amount:'significant purchase',transaction_date:'2026-06-18',disclosure_date:'2026-08-22'},
      {ticker:'META',asset:'Meta Platforms',type:'sale',amount:'$1,000,001 - $5,000,000',transaction_date:'2026-06-18',disclosure_date:'2026-08-22'},
      {ticker:'PLTR',asset:'Palantir',type:'purchase',amount:'$1,001 - $15,000',transaction_date:'2026-06-03',disclosure_date:'2026-08-22'},
      {ticker:'PLTR',asset:'Palantir',type:'sale',amount:'$15,001 - $50,000',transaction_date:'2026-06-16',disclosure_date:'2026-08-22'},
      {ticker:'PLTR',asset:'Palantir',type:'sale',amount:'$500,001 - $1,000,000',transaction_date:'2026-06-18',disclosure_date:'2026-08-22'},
      {ticker:'PLTR',asset:'Palantir',type:'purchase',amount:'purchase disclosed',transaction_date:'2026-06-23',disclosure_date:'2026-08-22'},
      {ticker:'HD',asset:'Home Depot',type:'purchase',amount:'purchase disclosed',transaction_date:'2026-06-18',disclosure_date:'2026-08-22'}
    ];
  };

  function rows(section){
    const sel=section?.querySelector('[data-politician-select]');
    if(t(sel?.value)==='executive:donald-trump')return trumpRows();
    const ledger=section?.querySelector('.ux466-ledger');
    try{return JSON.parse(ledger?.dataset.rows||'[]')}catch{return[]}
  }
  function trade(x){const buy=isBuy(x);return `<button type="button" class="ux473-row ${buy?'is-buy':'is-sell'}" data-market-ticker="${esc(x.ticker)}"><span><b>${esc(x.ticker||'—')}</b><small>${esc(x.asset||'')}${x.transaction_date?' · '+esc(fmtDate(x.transaction_date)):''}</small></span><span><strong>${buy?'Compra':'Venda'}</strong><em>${esc(x.amount||'—')}</em>${x.disclosure_date?`<small>notificado ${esc(fmtDate(x.disclosure_date))}</small>`:''}</span></button>`;}
  function topChip(x){return `<button type="button" class="ux473-highlight ${isBuy(x)?'is-buy':'is-sell'}" data-market-ticker="${esc(x.ticker)}"><b>${esc(x.ticker||'—')}</b><span>${esc(x.amount||'—')}</span></button>`;}

  function cleanLegacy(section){
    // Empty/duplicated summary blocks from the base politicians view are no longer useful once activity exists.
    [...section.querySelectorAll('.market-detail-card')].forEach(card=>{
      const tx=t(card.textContent);
      if(/^RADAR RÁPIDO/i.test(tx)||/^Compras em destaque/i.test(tx)||/^Vendas em destaque/i.test(tx)) card.remove();
    });
    // Keep one Political Flow card only.
    const flows=[];
    [...section.querySelectorAll('h3,h4,strong')].forEach(h=>{
      if(!/O que o Congresso está a negociar agora/i.test(t(h.textContent)))return;
      let p=h; while(p&&p!==section&&!p.matches?.('.market-detail-card,.ux-political-flow,.political-flow-card'))p=p.parentElement;
      if(p&&p!==section&&!flows.includes(p))flows.push(p);
    });
    flows.slice(1).forEach(x=>x.remove());
  }

  function renderPoliticians(){
    const section=document.querySelector('.politicians-section');
    const profile=document.getElementById('politicianProfile');
    if(!section||!profile)return;
    cleanLegacy(section);
    // v4.72 activity is replaced by the compact v4.73 canonical activity.
    section.querySelectorAll('.ux472-activity,.ux473-activity').forEach(x=>x.remove());
    const all=rows(section).filter(x=>x?.ticker&&(isBuy(x)||isSell(x))).sort((a,b)=>t(b.transaction_date||b.disclosure_date).localeCompare(t(a.transaction_date||a.disclosure_date)));
    const buys=all.filter(isBuy), sells=all.filter(isSell);
    const top=[...buys].sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)).slice(0,2).concat([...sells].sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)).slice(0,2));
    const sel=section.querySelector('[data-politician-select]');
    const isTrump=t(sel?.value)==='executive:donald-trump';
    const box=document.createElement('section');box.className='ux473-activity';
    box.dataset.buyExpanded='0';box.dataset.sellExpanded='0';
    box.innerHTML=`<div class="ux473-head"><div><small>ATIVIDADE RECENTE</small><h4>Últimas compras e vendas notificadas</h4></div><span>${all.length} linhas disponíveis</span></div>
      ${top.length?`<div class="ux473-highlights"><div><small>DESTAQUES RECENTES</small><strong>Maiores movimentos disponíveis</strong></div><div>${top.map(topChip).join('')}</div></div>`:''}
      ${isTrump?'<p class="ux473-note">No Trump, estas são todas as operações individuais atualmente ingeridas pela Vestra deste filing. O OGE original contém 1.000+ linhas, por isso esta não é ainda a lista completa do documento.</p>':''}
      <div class="ux473-sides">
        <section data-ux473-side="buy"><div class="ux473-title"><h5>↗ Compras <span>${buys.length}</span></h5>${buys.length>5?`<button type="button" data-ux473-toggle="buy">Ver todas</button>`:''}</div><div class="ux473-list">${buys.slice(0,5).map(trade).join('')||'<p class="ux473-empty">Sem compras disponíveis.</p>'}</div></section>
        <section data-ux473-side="sell"><div class="ux473-title"><h5>↘ Vendas <span>${sells.length}</span></h5>${sells.length>5?`<button type="button" data-ux473-toggle="sell">Ver todas</button>`:''}</div><div class="ux473-list">${sells.slice(0,5).map(trade).join('')||'<p class="ux473-empty">Sem vendas disponíveis.</p>'}</div></section>
      </div>`;
    profile.appendChild(box);
  }

  function repaintSide(box,side){
    const section=document.querySelector('.politicians-section');if(!section)return;
    const all=rows(section).filter(x=>x?.ticker&&(isBuy(x)||isSell(x))).sort((a,b)=>t(b.transaction_date||b.disclosure_date).localeCompare(t(a.transaction_date||a.disclosure_date)));
    const arr=all.filter(side==='buy'?isBuy:isSell), key=side==='buy'?'buyExpanded':'sellExpanded';
    const expanded=box.dataset[key]==='1';
    const host=box.querySelector(`[data-ux473-side="${side}"]`);if(!host)return;
    host.querySelector('.ux473-list').innerHTML=(expanded?arr:arr.slice(0,5)).map(trade).join('')||`<p class="ux473-empty">Sem ${side==='buy'?'compras':'vendas'} disponíveis.</p>`;
    const b=host.querySelector(`[data-ux473-toggle="${side}"]`);if(b)b.textContent=expanded?'Mostrar só 5':`Ver todas (${arr.length})`;
  }

  function tidyPortfolio(){
    const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');
    if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)return;
    // The explanatory "Prioridades da carteira" shell duplicates the global overview and the actual reinforce/review cards.
    const priority=c.querySelector('[data-ux-kind="priority"]');
    if(priority){priority.hidden=true;priority.setAttribute('aria-hidden','true');}
    // Hide the old Priority shortcut if it points to a card that no longer adds information.
    c.querySelectorAll('.ux-portfolio-shortcuts button,.ux454-shortcut').forEach(b=>{if(/Prioridades/i.test(t(b.textContent)))b.hidden=true;});
  }

  function style(){if(document.getElementById('vestra-v473-style'))return;const s=document.createElement('style');s.id='vestra-v473-style';s.textContent=`
    .ux473-activity{margin:14px 0;padding:14px;border:1px solid var(--line);border-radius:20px;background:var(--card)}.ux473-head{display:flex;justify-content:space-between;gap:10px;align-items:start;margin-bottom:10px}.ux473-head small,.ux473-highlights small{font-size:8px;letter-spacing:.13em;font-weight:900;color:var(--accent,#168e89)}.ux473-head h4{margin:2px 0 0;font-size:16px}.ux473-head>span{font-size:8px;color:var(--text2);background:var(--soft);padding:5px 7px;border-radius:999px}.ux473-note{margin:0 0 10px;padding:8px 10px;border-radius:12px;background:var(--soft);font-size:9px;line-height:1.4;color:var(--text2)}
    .ux473-highlights{padding:10px 11px;border-radius:15px;background:linear-gradient(135deg,color-mix(in srgb,var(--accent,#168e89) 8%,var(--soft)),var(--soft));margin-bottom:12px;display:grid;gap:8px}.ux473-highlights>div:first-child{display:grid;gap:2px}.ux473-highlights strong{font-size:12px}.ux473-highlights>div:last-child{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.ux473-highlight{display:flex;justify-content:space-between;gap:7px;align-items:center;border:1px solid var(--line);border-radius:11px;background:var(--card);padding:8px;color:var(--text);text-align:left}.ux473-highlight b{font-size:10px}.ux473-highlight span{font-size:8px;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ux473-highlight.is-buy{border-left:3px solid #37aa83}.ux473-highlight.is-sell{border-left:3px solid #d76678}
    .ux473-sides{display:grid;grid-template-columns:1fr 1fr;gap:16px}.ux473-title{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:3px}.ux473-title h5{margin:0;font-size:12px}.ux473-title h5 span{font-size:9px;color:var(--text2);font-weight:700}.ux473-title button{border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:6px 8px;color:var(--text2);font-size:8.5px;font-weight:850}.ux473-row{display:flex;justify-content:space-between;gap:10px;width:100%;padding:9px 0;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--text);text-align:left}.ux473-row>span{display:grid;gap:2px;min-width:0}.ux473-row>span:last-child{text-align:right;flex:0 0 auto}.ux473-row b{font-size:11px}.ux473-row strong{font-size:9px}.ux473-row small,.ux473-row em{font-size:8.5px;color:var(--text2);font-style:normal}.ux473-row.is-buy strong{color:#168f73}.ux473-row.is-sell strong{color:#c34f65}.ux473-empty{font-size:10px;color:var(--text2);padding:8px 0}
    #marketSheetContent [data-ux-kind="priority"][hidden]{display:none!important}
    @media(max-width:620px){.ux473-sides{grid-template-columns:1fr}.ux473-highlights>div:last-child{grid-template-columns:1fr}.ux473-activity{padding:12px}}
  `;document.head.appendChild(s);}

  document.addEventListener('click',e=>{const b=e.target.closest?.('[data-ux473-toggle]');if(!b)return;const box=b.closest('.ux473-activity');if(!box)return;const side=b.dataset.ux473Toggle,key=side==='buy'?'buyExpanded':'sellExpanded';box.dataset[key]=box.dataset[key]==='1'?'0':'1';repaintSide(box,side);},true);
  document.addEventListener('change',e=>{if(e.target.matches?.('[data-politician-select]'))setTimeout(renderPoliticians,260);},true);
  function apply(){renderPoliticians();tidyPortfolio();}
  function start(){style();apply();let pending=false;const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
