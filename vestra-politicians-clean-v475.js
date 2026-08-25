/* Vestra Politicians v4.75 — canonical simple UI: Compras, Vendas, A seguir. */
(() => {
  'use strict';
  const FOLLOW_KEY='vestra-politician-follows-v4';
  const t=v=>String(v??'').trim();
  const BUY=/purchase|buy|compr/i, SELL=/sale|sell|vend/i;
  const esc=v=>t(v).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const fmtDate=v=>{if(!v)return '—';const d=new Date(v);return Number.isNaN(d.valueOf())?t(v):new Intl.DateTimeFormat('pt-PT',{day:'2-digit',month:'2-digit',year:'numeric'}).format(d)};
  const isBuy=x=>BUY.test(t(x?.type)), isSell=x=>SELL.test(t(x?.type));
  const amountValue=v=>{const s=t(v).replace(/,/g,'');const nums=[...s.matchAll(/\$?([0-9]+(?:\.[0-9]+)?)([KMB])?/gi)].map(m=>{let n=Number(m[1]);const u=t(m[2]).toUpperCase();if(u==='K')n*=1e3;if(u==='M')n*=1e6;if(u==='B')n*=1e9;return n;});return nums.length?nums.reduce((a,b)=>a+b,0)/nums.length:0;};
  let view='buy', expanded=false, pending=false;

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

  const section=()=>document.querySelector('.politicians-section');
  const select=s=>s?.querySelector('[data-politician-select]');
  const current=s=>{const x=select(s);return {value:t(x?.value),label:t(x?.selectedOptions?.[0]?.textContent).split(' · ')[0],full:t(x?.selectedOptions?.[0]?.textContent)}};
  const readFollows=()=>{try{return JSON.parse(localStorage.getItem(FOLLOW_KEY)||'[]').filter(x=>x?.value&&x?.label)}catch{return[]}};
  const writeFollows=x=>{try{localStorage.setItem(FOLLOW_KEY,JSON.stringify(x))}catch{}};
  function rows(s){
    const c=current(s); if(c.value==='executive:donald-trump')return TRUMP.slice();
    const ledger=s?.querySelector('.ux466-ledger');
    try{return JSON.parse(ledger?.dataset.rows||'[]')}catch{return[]}
  }
  function cleanLegacy(s){
    // Do not remove nodes created by older observers: hide them so they cannot be recreated endlessly.
    s.querySelectorAll('.ux454-flow,.ux458-politician-leaders,.ux474-shell,.ux472-activity,.ux473-activity,.ux466-ledger,.politician-profile,.politician-callout,.politician-sides,.politician-all,.market-source-credit').forEach(x=>{x.hidden=true;x.setAttribute('aria-hidden','true');});
    // Hide legacy filter strips (Tudo / Compras / Vendas / Favorito) if an older layer renders them.
    [...s.querySelectorAll('div,nav,section')].forEach(x=>{
      if(x.classList.contains('ux475-shell'))return;
      const buttons=[...x.children].filter(c=>c.tagName==='BUTTON');
      if(buttons.length>=3){const txt=buttons.map(b=>t(b.textContent)).join(' | ');if(/Tudo/i.test(txt)&&/Compras/i.test(txt)&&/Vendas/i.test(txt)&&( /Favorito/i.test(txt)||/Seguir/i.test(txt)))x.hidden=true;}
    });
  }
  function tradeRow(x){const buy=isBuy(x);return `<button type="button" class="ux475-trade ${buy?'is-buy':'is-sell'}" data-market-ticker="${esc(x.ticker)}"><span><b>${esc(x.ticker||'—')}</b><small>${esc(x.asset||'')}${x.transaction_date?' · '+esc(fmtDate(x.transaction_date)):''}</small></span><span><strong>${buy?'Compra':'Venda'}</strong><em>${esc(x.amount||'—')}</em>${x.disclosure_date?`<small>notificado ${esc(fmtDate(x.disclosure_date))}</small>`:''}</span></button>`;}
  function topRow(x,i){return `<button type="button" class="ux475-toprow" data-market-ticker="${esc(x.ticker)}"><span><i>#${i+1}</i><b>${esc(x.ticker||'—')}</b><small>${esc(x.asset||'')}</small></span><strong>${esc(x.amount||'—')}</strong></button>`;}

  function render(){
    const s=section(), picker=s?.querySelector('.politician-picker'); if(!s||!picker)return;
    cleanLegacy(s);
    const c=current(s), follows=readFollows(), on=follows.some(x=>x.value===c.value);
    const all=rows(s).filter(x=>x?.ticker&&(isBuy(x)||isSell(x))).sort((a,b)=>t(b.transaction_date||b.disclosure_date).localeCompare(t(a.transaction_date||a.disclosure_date)));
    let shell=s.querySelector('.ux475-shell'); if(!shell){shell=document.createElement('section');shell.className='ux475-shell';picker.insertAdjacentElement('afterend',shell);}
    let body='';
    if(view==='follow'){
      body=`<div class="ux475-followview"><div class="ux475-viewhead"><div><small>A SEGUIR</small><h4>Políticos que acompanhas</h4></div><span>${follows.length}</span></div>${follows.length?`<div class="ux475-followlist">${follows.map(x=>`<div><button type="button" data-ux475-pick="${esc(x.value)}"><b>${esc(x.label)}</b><span>Ver atividade →</span></button><button type="button" class="is-remove" data-ux475-remove="${esc(x.value)}" aria-label="Deixar de seguir">×</button></div>`).join('')}</div>`:'<p class="ux475-empty">Ainda não segues nenhum político. Escolhe um perfil e toca em “Seguir”.</p>'}</div>`;
    }else{
      const arr=all.filter(view==='buy'?isBuy:isSell);
      const top=[...arr].sort((a,b)=>amountValue(b.amount)-amountValue(a.amount)).slice(0,3);
      const visible=expanded?arr:arr.slice(0,5);
      body=`<div class="ux475-viewhead"><div><small>${view==='buy'?'COMPRAS':'VENDAS'}</small><h4>${view==='buy'?'Últimas compras notificadas':'Últimas vendas notificadas'}</h4></div><span>${arr.length} disponíveis</span></div>${top.length?`<div class="ux475-top"><small>TOP POR VALOR DECLARADO</small>${top.map(topRow).join('')}</div>`:''}<div class="ux475-recent"><div class="ux475-recenthead"><strong>Mais recentes primeiro</strong>${arr.length>5?`<button type="button" data-ux475-expand>${expanded?'Mostrar só 5':`Ver todas (${arr.length})`}</button>`:''}</div>${visible.map(tradeRow).join('')||`<p class="ux475-empty">Sem ${view==='buy'?'compras':'vendas'} disponíveis neste período.</p>`}</div>${c.value==='executive:donald-trump'?'<p class="ux475-note">Trump: estas são as operações individuais já ingeridas pela Vestra. O filing OGE original contém 1.000+ linhas; a ingestão integral ainda não está concluída.</p>':''}`;
    }
    shell.innerHTML=`<div class="ux475-person"><div><small>POLÍTICO</small><strong>${esc(c.label||'—')}</strong></div><button type="button" data-ux475-follow class="${on?'is-on':''}">${on?'★ A seguir':'☆ Seguir'}</button></div><div class="ux475-tabs"><button type="button" data-ux475-view="buy" class="${view==='buy'?'is-active':''}">↗ Compras</button><button type="button" data-ux475-view="sell" class="${view==='sell'?'is-active':''}">↘ Vendas</button><button type="button" data-ux475-view="follow" class="${view==='follow'?'is-active':''}">★ A seguir${follows.length?` <b>${follows.length}</b>`:''}</button></div>${body}`;
    cleanLegacy(s);
  }

  function style(){if(document.getElementById('vestra-v475-style'))return;const st=document.createElement('style');st.id='vestra-v475-style';st.textContent=`
    .politicians-section .ux454-flow,.politicians-section .ux458-politician-leaders,.politicians-section .ux474-shell,.politicians-section .ux472-activity,.politicians-section .ux473-activity,.politicians-section .ux466-ledger,.politicians-section .politician-profile,.politicians-section .politician-callout,.politicians-section .politician-sides,.politicians-section .politician-all,.politicians-section .market-source-credit{display:none!important}
    .ux475-shell{margin:12px 0 16px;padding:14px;border:1px solid var(--line);border-radius:20px;background:var(--card);box-shadow:0 8px 22px rgba(18,48,54,.045)}.ux475-person{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:10px}.ux475-person>div{display:grid;gap:2px}.ux475-person small,.ux475-viewhead small,.ux475-top>small{font-size:8px;letter-spacing:.13em;font-weight:900;color:var(--accent,#168e89)}.ux475-person strong{font-size:14px}.ux475-person>button{border:1px solid var(--line);border-radius:999px;background:var(--soft);padding:8px 11px;color:var(--text2);font-size:9px;font-weight:850}.ux475-person>button.is-on{background:#fff8df;border-color:#ead79d;color:#946516}
    .ux475-tabs{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:14px}.ux475-tabs button{border:1px solid var(--line);background:var(--soft);border-radius:12px;padding:10px 6px;color:var(--text2);font-size:10px;font-weight:850}.ux475-tabs button.is-active{background:#145e6a;color:white;border-color:#145e6a}.ux475-tabs b{font-size:8px;margin-left:2px}
    .ux475-viewhead{display:flex;justify-content:space-between;gap:10px;align-items:start;margin-bottom:10px}.ux475-viewhead>div{display:grid;gap:2px}.ux475-viewhead h4{margin:0;font-size:17px}.ux475-viewhead>span{font-size:8px;color:var(--text2);background:var(--soft);padding:5px 7px;border-radius:999px}.ux475-top{display:grid;gap:6px;padding:10px;border-radius:14px;background:var(--soft);margin-bottom:12px}.ux475-toprow{display:flex;justify-content:space-between;gap:10px;align-items:center;border:0;border-bottom:1px solid var(--line);background:transparent;padding:7px 0;color:var(--text);text-align:left}.ux475-toprow:last-child{border-bottom:0}.ux475-toprow>span{display:flex;gap:7px;align-items:center;min-width:0}.ux475-toprow i{font-style:normal;font-size:8px;color:var(--text2)}.ux475-toprow b{font-size:11px}.ux475-toprow small{font-size:8px;color:var(--text2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.ux475-toprow>strong{font-size:9px;white-space:nowrap}
    .ux475-recent{display:grid}.ux475-recenthead{display:flex;justify-content:space-between;align-items:center;gap:8px;margin-bottom:3px}.ux475-recenthead strong{font-size:11px}.ux475-recenthead button{border:1px solid var(--line);background:var(--soft);border-radius:999px;padding:6px 9px;color:var(--text2);font-size:8.5px;font-weight:850}.ux475-trade{display:flex;justify-content:space-between;gap:10px;width:100%;padding:10px 0;border:0;border-bottom:1px solid var(--line);background:transparent;color:var(--text);text-align:left}.ux475-trade>span{display:grid;gap:2px;min-width:0}.ux475-trade>span:last-child{text-align:right;flex:0 0 auto}.ux475-trade b{font-size:11px}.ux475-trade strong{font-size:9px}.ux475-trade small,.ux475-trade em{font-size:8.5px;color:var(--text2);font-style:normal}.ux475-trade.is-buy strong{color:#168f73}.ux475-trade.is-sell strong{color:#c34f65}.ux475-note,.ux475-empty{font-size:9px;line-height:1.45;color:var(--text2)}.ux475-note{margin:10px 0 0;padding:9px 10px;border-radius:12px;background:var(--soft)}
    .ux475-followview{display:grid;gap:8px}.ux475-followlist{display:grid;gap:7px}.ux475-followlist>div{display:grid;grid-template-columns:1fr auto;gap:6px}.ux475-followlist button{border:1px solid var(--line);background:var(--soft);border-radius:12px;padding:10px;color:var(--text);display:flex;justify-content:space-between;gap:8px;text-align:left}.ux475-followlist button b{font-size:11px}.ux475-followlist button span{font-size:8.5px;color:var(--text2)}.ux475-followlist .is-remove{width:38px;display:grid;place-items:center;font-size:17px;color:var(--text2)}
    @media(max-width:620px){.ux475-shell{padding:12px}.ux475-tabs button{font-size:9px}.ux475-toprow small{max-width:120px}}
  `;document.head.appendChild(st);}

  document.addEventListener('click',e=>{
    const s=section();if(!s)return;
    const v=e.target.closest?.('[data-ux475-view]');if(v){view=v.dataset.ux475View;expanded=false;render();return;}
    const ex=e.target.closest?.('[data-ux475-expand]');if(ex){expanded=!expanded;render();return;}
    const f=e.target.closest?.('[data-ux475-follow]');if(f){const c=current(s);let a=readFollows();const i=a.findIndex(x=>x.value===c.value);if(i>=0)a.splice(i,1);else a.unshift(c);writeFollows(a);render();return;}
    const pick=e.target.closest?.('[data-ux475-pick]');if(pick){const sel=select(s);if(sel){sel.value=pick.dataset.ux475Pick;view='buy';expanded=false;sel.dispatchEvent(new Event('change',{bubbles:true}));}return;}
    const rm=e.target.closest?.('[data-ux475-remove]');if(rm){writeFollows(readFollows().filter(x=>x.value!==rm.dataset.ux475Remove));render();return;}
  },true);
  document.addEventListener('change',e=>{if(e.target.matches?.('[data-politician-select]')){view='buy';expanded=false;setTimeout(render,260);}},true);
  function start(){style();render();const mo=new MutationObserver(()=>{if(pending)return;pending=true;requestAnimationFrame(()=>{pending=false;const s=section();if(s){cleanLegacy(s);if(!s.querySelector('.ux475-shell'))render();}});});mo.observe(document.body,{childList:true,subtree:true});}
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
})();
