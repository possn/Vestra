/* Vestra Politicians v4.74 — one canonical politician UI: follow + highlights + compact recent activity. */
(() => {
  'use strict';
  const FOLLOW_KEY='vestra-politician-follows-v4';
  const t=v=>String(v??'').trim();
  const BUY=/purchase|buy|compr/i, SELL=/sale|sell|vend/i;
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmtDate=v=>{if(!v)return '—';const d=new Date(v);return Number.isNaN(d.valueOf())?t(v):new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d)};
  const isBuy=x=>BUY.test(t(x?.type)), isSell=x=>SELL.test(t(x?.type));
  const amountValue=v=>{const s=t(v).replace(/,/g,'');const nums=[...s.matchAll(/\$?([0-9]+(?:\.[0-9]+)?)([KMB])?/gi)].map(m=>{let n=Number(m[1]);const u=t(m[2]).toUpperCase();if(u==='K')n*=1e3;if(u==='M')n*=1e6;if(u==='B')n*=1e9;return n;});return nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:0;};
  let pending=false;

  const TRUMP=[
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

  function section(){return document.querySelector('.politicians-section');}
  function select(s){return s?.querySelector('[data-politician-select]');}
  function current(s){const sel=select(s);return {value:t(sel?.value),label:t(sel?.selectedOptions?.[0]?.textContent).split(' · ')[0]};}
  function readFollows(){try{return JSON.parse(localStorage.getItem(FOLLOW_KEY)||'[]').filter(x=>x?.value&&x?.label)}catch{return[]}}
  function writeFollows(x){try{localStorage.setItem(FOLLOW_KEY,JSON.stringify(x))}catch{}}
  function rows(s){
    const c=current(s); if(c.value==='executive:donald-trump')return TRUMP.slice();
    const ledger=s?.querySelector('.ux466-ledger');
    try{return JSON.parse(ledger?.dataset.rows||'[]')}catch{return[]}
  }
  function trade(x){const buy=isBuy(x);return `<button type="button" class="ux474-row ${buy?'is-buy':'is-sell'}" data-market-ticker="${esc(x.ticker)}"><span><b>${esc(x.ticker||'—')}</b><small>${esc(x.asset||'')}${x.transaction_date?' · '+esc(fmtDate(x.transaction_date)):''}</small></span><span><strong>${buy?'Compra':'Venda'}</strong><em>${esc(x.amount||'—')}</em>${x.disclosure_date?`<small>notificado ${esc(fmtDate(x.disclosure_date))}</small>`:''}</span></button>`;}
  function chip(x){return `<button type="button" class="ux474-chip ${isBuy(x)?'is-buy':'is-sell'}" data-market-ticker="${esc(x.ticker)}"><b>${esc(x.ticker)}</b><span>${esc(x.amount||'—')}</span></button>`;}

  function cleanup(s){
    // Exactly one canonical activity/follow UI. Older renderers may still have left nodes in the DOM.
    s.querySelectorAll('.ux472-activity,.ux473-activity,.ux472-followhub,.ux472-followctl,.ux474-shell').forEach(x=>x.remove());
    s.querySelectorAll('.ux466-ledger').forEach(x=>{x.hidden=true;x.setAttribute('aria-hidden','true');});
    [...s.querySelectorAll('.market-detail-card')].forEach(card=>{
      const tx=t(card.textContent);
      if(/^RADAR RÁPIDO/i.test(tx)||/^Compras em destaque/i.test(tx)||/^Vendas em destaque/i.test(tx))card.remove();
    });
    const flows=[];[...s.querySelectorAll('h3,h4,strong')].forEach(h=>{if(!/O que o Congresso está a negociar agora/i.test(t(h.textContent)))return;let p=h;while(p&&p!==s&&!p.matches?.('.market-detail-card,.ux-political-flow,.political-flow-card'))p=p.parentElement;if(p&&p!==s&&!flows.includes(p))flows.push(p);});
    flows.slice(1).forEach(x=>x.remove());
  }

  function render(){
    const s=section(), profile=document.getElementById('politicianProfile'), picker=s?.querySelector('.politician-picker');
    if(!s||!profile||!picker)return;
    cleanup(s);
    const c=current(s), follows=readFollows(), on=follows.some(x=>x.value===c.value);
    const all=rows(s).filter(x=>x?.ticker&&(isBuy(x)||isSell(x))).sort((a,b)=>t(b.transaction_date||b.disclosure_date).localeCompare(t(a.transaction_date||a.disclosure_date)));
    const buys=all.filter(isBuy), sells=all.filter(isSell);
    const top=[...buys].sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)).slice(0,2).concat([...sells].sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)).slice(0,2));
    const isTrump=c.value==='executive:donald-trump';

    const shell=document.createElement('section'); shell.className='ux474-shell'; shell.dataset.buyExpanded='0';shell.dataset.sellExpanded='0';
    shell.innerHTML=`<div class="ux474-follow"><button type="button" data-ux474-follow class="${on?'is-on':''}">${on?'★ A seguir':'☆ Seguir político'}</button>${follows.length?`<div class="ux474-followed"><small>A SEGUIR</small>${follows.map(x=>`<button type="button" data-ux474-pick="${esc(x.value)}">${esc(x.label)}</button>`).join('')}</div>`:''}</div>
      <div class="ux474-head"><div><small>ATIVIDADE RECENTE</small><h4>Últimas compras e vendas notificadas</h4></div><span>${all.length} disponíveis</span></div>
      ${top.length?`<div class="ux474-highlights"><div><small>DESTAQUES RECENTES</small><strong>Maiores movimentos disponíveis</strong></div><div>${top.map(chip).join('')}</div></div>`:''}
      ${isTrump?'<p class="ux474-note">Mostram-se as operações individuais já ingeridas deste filing OGE. O documento original contém 1.000+ linhas, portanto esta ainda não é a lista integral.</p>':''}
      <div class="ux474-sides"><section data-ux474-side="buy"><div class="ux474-title"><h5>↗ Compras <span>${buys.length}</span></h5>${buys.length>5?`<button type="button" data-ux474-toggle="buy">Ver todas (${buys.length})</button>`:''}</div><div class="ux474-list">${buys.slice(0,5).map(trade).join('')||'<p class="ux474-empty">Sem compras disponíveis.</p>'}</div></section><section data-ux474-side="sell"><div class="ux474-title"><h5>↘ Vendas <span>${sells.length}</span></h5>${sells.length>5?`<button type="button" data-ux474-toggle="sell">Ver todas (${sells.length})</button>`:''}</div><div class="ux474-list">${sells.slice(0,5).map(trade).join('')||'<p class="ux474-empty">Sem vendas disponíveis.</p>'}</div></section></div>`;
    picker.insertAdjacentElement('afterend',shell);
  }

  function repaint(box,side){
    const s=section();if(!s)return;const arr=rows(s).filter(x=>x?.ticker&&(side==='buy'?isBuy(x):isSell(x))).sort((a,b)=>t(b.transaction_date||b.disclosure_date).localeCompare(t(a.transaction_date||a.disclosure_date)));
    const key=side==='buy'?'buyExpanded':'sellExpanded', expanded=box.dataset[key]==='1', host=box.querySelector(`[data-ux474-side="${side}"]`);if(!host)return;
    host.querySelector('.ux474-list').innerHTML=(expanded?arr:arr.slice(0,5)).map(trade).join('')||`<p class="ux474-empty">Sem ${side==='buy'?'compras':'vendas'} disponíveis.</p>`;
    const b=host.querySelector(`[data-ux474-toggle="${side}"]`);if(b)b.textContent=expanded?'Mostrar só 5':`Ver todas (${arr.length})`;
  }

  function tidyPortfolio(){const sh=document.getElementById('marketSheet'),c=document.getElementById('marketSheetContent');if(!sh||sh.hidden||t(sh.dataset.tool)!=='portfolio'||!c)return;const priority=c.querySelector('[data-ux-kind="priority"]');if(priority){priority.hidden=true;priority.setAttribute('aria-hidden','true');}c.querySelectorAll('.ux-portfolio-shortcuts button,.ux454-shortcut').forEach(b=>{if(/Prioridades/i.test(t(b.textContent)))b.hidden=true;});}

  function style(){if(document.getElementById('vestra-v474-style'))return;const st=document.createElement('style');st.id='vestra-v474-style';st.textContent=`
    .ux474-shell{margin:10px 0 14px;padding:14px;border:1px solid var(--line);border-radius:20px;background:var(--card)}.ux474-follow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:13px}.ux474-follow>button{border:1px solid var(--line);border-radius:999px;background:var(--card);padding:8px 12px;color:var(--text2);font-size:10px;font-weight:850}.ux474-follow>button.is-on{background:#fff8df;border-color:#ead79d;color:#946516}.ux474-followed{display:flex;align-items:center;gap:5px;overflow:auto}.ux474-followed small{font-size:8px;font-weight:900;letter-spacing:.12em;color:var(--text2)}.ux474-followed button{white-space:nowrap;border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:6px 9px;color:var(--text);font-size:9px;font-weight:800}
    .ux474-head{display:flex;justify-content:space-between;gap:10px;align-items:start;margin-bottom:10px}.ux474-head small,.ux474-highlights small{font-size:8px;letter-spacing:.13em;font-weight:900;color:var(--accent,#168e89)}.ux474-head h4{margin:2px 0 0;font-size:16px}.ux474-head>span{font-size:8px;color:var(--text2);background:var(--soft);padding:5px 7px;border-radius:999px}.ux474-highlights{padding:10px 11px;border-radius:15px;background:var(--soft);margin-bottom:12px;display:grid;gap:8px}.ux474-highlights>div:first-child{display:grid;gap:2px}.ux474-highlights strong{font-size:12px}.ux474-highlights>div:last-child{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:6px}.ux474-chip{display:flex;justify-content:space-between;gap:7px;align-items:center;border:1px solid var(--line);border-radius:11px;background:var(--card);padding:8px;color:var(--text);text-align:left}.ux474-chip b{font-size:10px}.ux474-chip span{font-size:8px;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ux474-chip.is-buy{border-left:3px solid #37aa83}.ux474-chip.is-sell{border-left:3px solid #d76678}.ux474-note{margin:0 0 10px;padding:8px 10px;border-radius:12px;background:var(--soft);font-size:9px;line-height:1.4;color:var(--text2)}
    .ux474-sides{display:grid;grid-template-columns:1fr 1fr;gap:16px}.ux474-title{display:flex;justify-content:space-between;gap:8px;align-items:center;margin-bottom:3px}.ux474-title h5{margin:0;font-size:12px}.ux474-title h5 span{font-size:9px;color:var(--text2)}.ux474-title button{border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:6px 8px;color:var(--text2);font-size:8.5px;font-weight:850}.ux474-row{display:flex;justify-content:space-between;gap:10px;width:100%;padding:9px 0;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--text);text-align:left}.ux474-row>span{display:grid;gap:2px;min-width:0}.ux474-row>span:last-child{text-align:right;flex:0 0 auto}.ux474-row b{font-size:11px}.ux474-row strong{font-size:9px}.ux474-row small,.ux474-row em{font-size:8.5px;color:var(--text2);font-style:normal}.ux474-row.is-buy strong{color:#168f73}.ux474-row.is-sell strong{color:#c34f65}.ux474-empty{font-size:10px;color:var(--text2);padding:8px 0}.politicians-section .ux466-ledger[hidden]{display:none!important}#marketSheetContent [data-ux-kind="priority"][hidden]{display:none!important}
    @media(max-width:620px){.ux474-sides{grid-template-columns:1fr}.ux474-highlights>div:last-child{grid-template-columns:1fr}.ux474-shell{padding:12px}}
  `;document.head.appendChild(st);}

  document.addEventListener('click',e=>{
    const s=section();if(!s)return;
    const follow=e.target.closest?.('[data-ux474-follow]');if(follow){e.preventDefault();e.stopPropagation();const c=current(s);let a=readFollows();const i=a.findIndex(x=>x.value===c.value);if(i>=0)a.splice(i,1);else a.unshift(c);writeFollows(a);render();return;}
    const pick=e.target.closest?.('[data-ux474-pick]');if(pick){const sel=select(s);if(sel){sel.value=pick.dataset.ux474Pick;sel.dispatchEvent(new Event('change',{bubbles:true}));}return;}
    const b=e.target.closest?.('[data-ux474-toggle]');if(b){const box=b.closest('.ux474-shell');const side=b.dataset.ux474Toggle,key=side==='buy'?'buyExpanded':'sellExpanded';box.dataset[key]=box.dataset[key]==='1'?'0':'1';repaint(box,side);}
  },true);
  document.addEventListener('change',e=>{if(e.target.matches?.('[data-politician-select]'))setTimeout(render,260);},true);
  function apply(){render();tidyPortfolio();}
  function start(){style();apply();const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();