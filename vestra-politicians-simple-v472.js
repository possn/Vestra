/* Vestra Politicians v4.72 — one flow summary, one follow area, latest notified buys/sells. */
(() => {
  'use strict';
  const FOLLOW_KEY='vestra-politician-follows-v4';
  const t=v=>String(v??'').trim();
  const BUY=/purchase|buy|compr/i, SELL=/sale|sell|vend/i;
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmtDate=v=>{if(!v)return '—';const d=new Date(v);return Number.isNaN(d.valueOf())?t(v):new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d)};
  let pending=false;

  // Until the full OGE filing is ingested, these are the individual Trump lines already identified by Vestra.
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
  function isBuy(x){return BUY.test(t(x?.type));} function isSell(x){return SELL.test(t(x?.type));}
  function ledgerRows(s){
    const c=current(s); if(c.value==='executive:donald-trump') return TRUMP.slice();
    const box=s.querySelector('.ux466-ledger'); if(!box) return [];
    try{return JSON.parse(box.dataset.rows||'[]')}catch{return[]}
  }
  function tradeRow(x){const buy=isBuy(x);return `<button type="button" class="ux472-trade ${buy?'is-buy':'is-sell'}" data-market-ticker="${esc(x.ticker)}"><span><b>${esc(x.ticker||'—')}</b><small>${esc(x.asset||'')}${x.transaction_date?' · '+esc(fmtDate(x.transaction_date)):''}</small></span><span><strong>${buy?'Compra':'Venda'}</strong><em>${esc(x.amount||'—')}</em>${x.disclosure_date?`<small>notificado ${esc(fmtDate(x.disclosure_date))}</small>`:''}</span></button>`;}

  function dedupeFlow(s){
    const found=[];
    [...s.querySelectorAll('h3,h4,strong')].forEach(h=>{
      if(!/O que o Congresso está a negociar agora/i.test(t(h.textContent)))return;
      let p=h; while(p&&p!==s&&!p.matches?.('.market-detail-card,.ux-political-flow,.political-flow-card'))p=p.parentElement;
      if(p&&p!==s&&!found.includes(p))found.push(p);
    });
    found.slice(1).forEach(x=>x.remove());
  }

  function cleanup(s){
    // Remove legacy duplicated controls/summary blocks; v4.66 remains only as hidden data source for Congress.
    s.querySelectorAll('.ux-politician-controls,.ux467-followed,.ux467-ledger,.ux467-pulse,.ux468-controls,.ux468-activity,.ux-politician-pulse,.politician-callout,.politician-sides,.politician-all,.market-source-credit').forEach(x=>x.remove());
    s.querySelectorAll('.ux466-ledger').forEach(x=>{x.hidden=true;x.setAttribute('aria-hidden','true');});
    dedupeFlow(s);
  }

  function renderFollowHub(s){
    const picker=s.querySelector('.politician-picker'); if(!picker)return;
    const c=current(s), follows=readFollows();
    let hub=s.querySelector('.ux472-followhub');
    if(!hub){hub=document.createElement('div');hub.className='ux472-followhub';picker.insertAdjacentElement('beforebegin',hub);}
    hub.innerHTML=follows.length?`<div><small>A SEGUIR</small><div>${follows.map(x=>`<button type="button" data-ux472-pick="${esc(x.value)}">${esc(x.label)}</button>`).join('')}</div></div>`:`<div class="is-empty"><small>A SEGUIR</small><span>Segue políticos para os encontrares aqui rapidamente.</span></div>`;

    let ctl=s.querySelector('.ux472-followctl');
    if(!ctl){ctl=document.createElement('div');ctl.className='ux472-followctl';picker.insertAdjacentElement('afterend',ctl);}
    const on=follows.some(x=>x.value===c.value);
    ctl.innerHTML=`<button type="button" data-ux472-follow class="${on?'is-on':''}">${on?'★ A seguir':'☆ Seguir político'}</button>`;
  }

  function renderActivity(s){
    const profile=document.getElementById('politicianProfile'); if(!profile)return;
    const c=current(s);
    const rows=ledgerRows(s).filter(x=>x?.ticker&&(isBuy(x)||isSell(x))).sort((a,b)=>t(b.transaction_date||b.disclosure_date).localeCompare(t(a.transaction_date||a.disclosure_date)));
    const buys=rows.filter(isBuy).slice(0,10), sells=rows.filter(isSell).slice(0,10);
    let box=profile.querySelector('.ux472-activity'); if(!box){box=document.createElement('section');box.className='ux472-activity';profile.appendChild(box);}
    const limited=c.value==='executive:donald-trump';
    box.innerHTML=`<div class="ux472-head"><div><small>ATIVIDADE RECENTE</small><h4>Últimas compras e vendas notificadas</h4></div><span>${rows.length?rows.length+' linhas':'sem linhas'}</span></div>${limited?'<p class="ux472-note">Trump: mostram-se as operações individuais já identificadas no filing OGE carregado pela Vestra; o filing completo contém mais linhas.</p>':''}<div class="ux472-cols"><div><h5>↗ Compras</h5>${buys.map(tradeRow).join('')||'<p class="ux472-empty">Sem compras individuais disponíveis.</p>'}</div><div><h5>↘ Vendas</h5>${sells.map(tradeRow).join('')||'<p class="ux472-empty">Sem vendas individuais disponíveis.</p>'}</div></div>`;
  }

  function apply(){const s=section();if(!s)return;cleanup(s);renderFollowHub(s);renderActivity(s);}

  function style(){if(document.getElementById('vestra-politicians-v472-style'))return;const st=document.createElement('style');st.id='vestra-politicians-v472-style';st.textContent=`
    .ux472-followhub{margin:8px 0 10px}.ux472-followhub>div{display:grid;gap:6px;padding:9px 11px;border:1px solid var(--line);border-radius:14px;background:var(--soft)}.ux472-followhub small{font-size:8px;font-weight:900;letter-spacing:.13em;color:var(--accent,#168e89)}.ux472-followhub>div>div{display:flex;gap:6px;overflow:auto}.ux472-followhub button{white-space:nowrap;border:1px solid var(--line);background:var(--card);border-radius:999px;padding:6px 9px;color:var(--text);font-size:9px;font-weight:800}.ux472-followhub .is-empty{display:flex;justify-content:space-between;gap:10px;align-items:center}.ux472-followhub .is-empty span{font-size:9px;color:var(--text2)}
    .ux472-followctl{margin:-5px 0 12px}.ux472-followctl button{border:1px solid var(--line);border-radius:999px;background:var(--card);padding:8px 12px;color:var(--text2);font-size:10px;font-weight:850}.ux472-followctl button.is-on{background:#fff8df;border-color:#ead79d;color:#946516}
    .ux472-activity{margin:14px 0;padding:14px;border:1px solid var(--line);border-radius:20px;background:var(--card)}.ux472-head{display:flex;justify-content:space-between;gap:10px;align-items:start;margin-bottom:8px}.ux472-head small{font-size:8px;letter-spacing:.13em;font-weight:900;color:var(--accent,#168e89)}.ux472-head h4{font-size:16px;margin:2px 0 0}.ux472-head>span{font-size:8px;color:var(--text2);background:var(--soft);padding:5px 7px;border-radius:999px}.ux472-note{margin:0 0 10px;padding:8px 10px;border-radius:12px;background:var(--soft);font-size:9px;line-height:1.4;color:var(--text2)}.ux472-cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}.ux472-cols h5{margin:0 0 5px;font-size:11px}.ux472-trade{display:flex;justify-content:space-between;gap:10px;width:100%;padding:9px 0;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--text);text-align:left}.ux472-trade>span{display:grid;gap:2px;min-width:0}.ux472-trade>span:last-child{text-align:right;flex:0 0 auto}.ux472-trade b{font-size:11px}.ux472-trade strong{font-size:9px}.ux472-trade small,.ux472-trade em{font-size:8.5px;color:var(--text2);font-style:normal}.ux472-trade.is-buy strong{color:#168f73}.ux472-trade.is-sell strong{color:#c34f65}.ux472-empty{font-size:10px;color:var(--text2);padding:8px 0}
    .politicians-section .ux466-ledger[hidden]{display:none!important}
    @media(max-width:620px){.ux472-cols{grid-template-columns:1fr}.ux472-activity{padding:12px}.ux472-followhub .is-empty{display:grid}}
  `;document.head.appendChild(st);}

  document.addEventListener('click',e=>{const s=section();if(!s)return;const f=e.target.closest?.('[data-ux472-follow]');if(f){e.preventDefault();e.stopPropagation();const c=current(s);let arr=readFollows();const i=arr.findIndex(x=>x.value===c.value);if(i>=0)arr.splice(i,1);else arr.unshift(c);writeFollows(arr);renderFollowHub(s);return;}const p=e.target.closest?.('[data-ux472-pick]');if(p){const sel=select(s);if(!sel)return;sel.value=p.dataset.ux472Pick;sel.dispatchEvent(new Event('change',{bubbles:true}));}},true);
  document.addEventListener('change',e=>{if(e.target.matches?.('[data-politician-select]'))setTimeout(apply,220);},true);
  function start(){style();apply();const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;apply();});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();